//
//  NetworkRetryManager.swift
//  AlabamaAuctionWatcher
//
//  Network retry logic with exponential backoff and circuit breaker
//  Enhances NetworkManager with robust error handling and recovery
//

import Foundation
import Network

// MARK: - Retry Configuration

struct RetryConfiguration {
    let maxRetries: Int
    let baseDelay: TimeInterval
    let maxDelay: TimeInterval
    let backoffMultiplier: Double
    let jitterRange: Double

    static let `default` = RetryConfiguration(
        maxRetries: 3,
        baseDelay: 1.0,
        maxDelay: 30.0,
        backoffMultiplier: 2.0,
        jitterRange: 0.1
    )

    static let aggressive = RetryConfiguration(
        maxRetries: 5,
        baseDelay: 0.5,
        maxDelay: 60.0,
        backoffMultiplier: 1.5,
        jitterRange: 0.2
    )

    static let conservative = RetryConfiguration(
        maxRetries: 2,
        baseDelay: 2.0,
        maxDelay: 15.0,
        backoffMultiplier: 3.0,
        jitterRange: 0.05
    )
}

// MARK: - Retry Policy

enum RetryPolicy {
    case none
    case exponentialBackoff(RetryConfiguration)
    case immediateRetry(maxAttempts: Int)
    case customDelay([TimeInterval])

    var shouldRetry: Bool {
        switch self {
        case .none:
            return false
        default:
            return true
        }
    }
}

// MARK: - Circuit Breaker

class CircuitBreaker {
    enum State {
        case closed    // Normal operation
        case open      // Failing, reject requests
        case halfOpen  // Testing if service recovered
    }

    private var state: State = .closed
    private var failureCount = 0
    private var lastFailureTime: Date?
    private var successCount = 0

    private let failureThreshold: Int
    private let timeout: TimeInterval
    private let recoveryTimeout: TimeInterval

    init(
        failureThreshold: Int = 5,
        timeout: TimeInterval = 60.0,
        recoveryTimeout: TimeInterval = 10.0
    ) {
        self.failureThreshold = failureThreshold
        self.timeout = timeout
        self.recoveryTimeout = recoveryTimeout
    }

    func canExecute() -> Bool {
        switch state {
        case .closed:
            return true
        case .open:
            // Check if we should transition to half-open
            if let lastFailure = lastFailureTime,
               Date().timeIntervalSince(lastFailure) > timeout {
                state = .halfOpen
                return true
            }
            return false
        case .halfOpen:
            return true
        }
    }

    func recordSuccess() {
        switch state {
        case .closed:
            break // Already in good state
        case .open:
            break // Shouldn't happen
        case .halfOpen:
            successCount += 1
            if successCount >= 3 { // Require multiple successes
                state = .closed
                failureCount = 0
                successCount = 0
                lastFailureTime = nil
            }
        }
    }

    func recordFailure() {
        failureCount += 1
        lastFailureTime = Date()
        successCount = 0

        if failureCount >= failureThreshold {
            state = .open
        }
    }

    func reset() {
        state = .closed
        failureCount = 0
        successCount = 0
        lastFailureTime = nil
    }
}

// MARK: - Request Queue Item

struct QueuedRequest {
    let id: UUID
    let urlRequest: URLRequest
    let retryPolicy: RetryPolicy
    let priority: RequestPriority
    let createdAt: Date
    let completion: (Result<Data, Error>) -> Void

    enum RequestPriority: Int, Comparable {
        case low = 1
        case normal = 2
        case high = 3
        case critical = 4

        static func < (lhs: RequestPriority, rhs: RequestPriority) -> Bool {
            return lhs.rawValue < rhs.rawValue
        }
    }
}

// MARK: - Network Retry Manager

@MainActor
class NetworkRetryManager: ObservableObject {

    // MARK: - Published Properties

    @Published var isOnline = true
    @Published var queuedRequestCount = 0
    @Published var circuitBreakerState: CircuitBreaker.State = .closed

    // MARK: - Private Properties

    private let session: URLSession
    private let circuitBreaker = CircuitBreaker()
    private var requestQueue: [QueuedRequest] = []
    private let monitor = NWPathMonitor()
    private let monitorQueue = DispatchQueue(label: "NetworkRetryMonitor")
    private var isProcessingQueue = false

    // MARK: - Statistics

    private var retryAttempts = 0
    private var successfulRequests = 0
    private var failedRequests = 0

    // MARK: - Initialization

    init(session: URLSession = URLSession.shared) {
        self.session = session
        setupNetworkMonitoring()
    }

    // MARK: - Network Monitoring

    private func setupNetworkMonitoring() {
        monitor.pathUpdateHandler = { [weak self] path in
            Task { @MainActor in
                let wasOnline = self?.isOnline ?? false
                self?.isOnline = path.status == .satisfied

                // Process queued requests when coming back online
                if !wasOnline && path.status == .satisfied {
                    self?.processQueuedRequests()
                }
            }
        }
        monitor.start(queue: monitorQueue)
    }

    // MARK: - Public Methods

    /// Perform request with retry logic
    func performRequest(
        _ urlRequest: URLRequest,
        retryPolicy: RetryPolicy = .exponentialBackoff(.default),
        priority: QueuedRequest.RequestPriority = .normal
    ) async throws -> Data {

        // Check circuit breaker
        guard circuitBreaker.canExecute() else {
            throw NetworkError.serverError(503, "Service temporarily unavailable (circuit breaker open)")
        }

        // If offline and policy allows queuing, add to queue
        if !isOnline && retryPolicy.shouldRetry {
            return try await queueRequest(urlRequest, retryPolicy: retryPolicy, priority: priority)
        }

        // Perform request with retry logic
        return try await performRequestWithRetry(urlRequest, retryPolicy: retryPolicy)
    }

    /// Queue request for later execution
    private func queueRequest(
        _ urlRequest: URLRequest,
        retryPolicy: RetryPolicy,
        priority: QueuedRequest.RequestPriority
    ) async throws -> Data {

        return try await withCheckedThrowingContinuation { continuation in
            let queuedRequest = QueuedRequest(
                id: UUID(),
                urlRequest: urlRequest,
                retryPolicy: retryPolicy,
                priority: priority,
                createdAt: Date()
            ) { result in
                switch result {
                case .success(let data):
                    continuation.resume(returning: data)
                case .failure(let error):
                    continuation.resume(throwing: error)
                }
            }

            requestQueue.append(queuedRequest)
            requestQueue.sort { $0.priority > $1.priority } // Sort by priority
            queuedRequestCount = requestQueue.count

            print("📥 Queued request (\(requestQueue.count) total)")
        }
    }

    /// Process all queued requests
    private func processQueuedRequests() {
        guard !isProcessingQueue, !requestQueue.isEmpty, isOnline else {
            return
        }

        isProcessingQueue = true

        Task {
            print("🔄 Processing \(requestQueue.count) queued requests")

            while !requestQueue.isEmpty && isOnline {
                let request = requestQueue.removeFirst()
                queuedRequestCount = requestQueue.count

                do {
                    let data = try await performRequestWithRetry(
                        request.urlRequest,
                        retryPolicy: request.retryPolicy
                    )
                    request.completion(.success(data))
                } catch {
                    request.completion(.failure(error))
                }

                // Small delay between requests to avoid overwhelming the server
                try? await Task.sleep(nanoseconds: 100_000_000) // 0.1 seconds
            }

            isProcessingQueue = false
            print("✅ Finished processing queued requests")
        }
    }

    // MARK: - Retry Logic

    private func performRequestWithRetry(
        _ urlRequest: URLRequest,
        retryPolicy: RetryPolicy,
        attempt: Int = 1
    ) async throws -> Data {

        do {
            let (data, response) = try await session.data(for: urlRequest)

            // Check HTTP response
            guard let httpResponse = response as? HTTPURLResponse else {
                throw NetworkError.serverError(0, "Invalid response")
            }

            // Handle HTTP errors
            if httpResponse.statusCode >= 400 {
                let errorMessage = String(data: data, encoding: .utf8) ?? "Unknown error"

                // Determine if error is retryable
                if shouldRetryForStatusCode(httpResponse.statusCode) && shouldRetry(retryPolicy, attempt: attempt) {
                    circuitBreaker.recordFailure()
                    return try await retryRequest(urlRequest, retryPolicy: retryPolicy, attempt: attempt)
                } else {
                    circuitBreaker.recordFailure()
                    throw NetworkError.serverError(httpResponse.statusCode, errorMessage)
                }
            }

            // Success
            circuitBreaker.recordSuccess()
            successfulRequests += 1
            return data

        } catch {
            // Network or other error
            if shouldRetryForError(error) && shouldRetry(retryPolicy, attempt: attempt) {
                circuitBreaker.recordFailure()
                return try await retryRequest(urlRequest, retryPolicy: retryPolicy, attempt: attempt)
            } else {
                circuitBreaker.recordFailure()
                failedRequests += 1
                throw error
            }
        }
    }

    private func retryRequest(
        _ urlRequest: URLRequest,
        retryPolicy: RetryPolicy,
        attempt: Int
    ) async throws -> Data {

        retryAttempts += 1

        let delay = calculateDelay(for: retryPolicy, attempt: attempt)
        print("🔄 Retrying request (attempt \(attempt + 1)) after \(delay)s delay")

        try await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))

        return try await performRequestWithRetry(
            urlRequest,
            retryPolicy: retryPolicy,
            attempt: attempt + 1
        )
    }

    // MARK: - Retry Decision Logic

    private func shouldRetry(_ retryPolicy: RetryPolicy, attempt: Int) -> Bool {
        switch retryPolicy {
        case .none:
            return false
        case .exponentialBackoff(let config):
            return attempt <= config.maxRetries
        case .immediateRetry(let maxAttempts):
            return attempt <= maxAttempts
        case .customDelay(let delays):
            return attempt <= delays.count
        }
    }

    private func shouldRetryForStatusCode(_ statusCode: Int) -> Bool {
        // Retry for server errors and rate limiting
        switch statusCode {
        case 429: // Too Many Requests
            return true
        case 500...599: // Server errors
            return true
        case 408: // Request Timeout
            return true
        default:
            return false
        }
    }

    private func shouldRetryForError(_ error: Error) -> Bool {
        if let urlError = error as? URLError {
            switch urlError.code {
            case .timedOut,
                 .cannotConnectToHost,
                 .cannotFindHost,
                 .dnsLookupFailed,
                 .networkConnectionLost,
                 .notConnectedToInternet:
                return true
            default:
                return false
            }
        }
        return false
    }

    // MARK: - Delay Calculation

    private func calculateDelay(for retryPolicy: RetryPolicy, attempt: Int) -> TimeInterval {
        switch retryPolicy {
        case .none:
            return 0

        case .exponentialBackoff(let config):
            let baseDelay = config.baseDelay * pow(config.backoffMultiplier, Double(attempt - 1))
            let delayWithJitter = addJitter(to: baseDelay, range: config.jitterRange)
            return min(delayWithJitter, config.maxDelay)

        case .immediateRetry:
            return 0.1 // Small delay to avoid hammering

        case .customDelay(let delays):
            if attempt <= delays.count {
                return delays[attempt - 1]
            } else {
                return delays.last ?? 1.0
            }
        }
    }

    private func addJitter(to delay: TimeInterval, range: Double) -> TimeInterval {
        let jitter = Double.random(in: -range...range)
        return delay * (1.0 + jitter)
    }

    // MARK: - Statistics

    func getStatistics() -> NetworkStatistics {
        return NetworkStatistics(
            successfulRequests: successfulRequests,
            failedRequests: failedRequests,
            retryAttempts: retryAttempts,
            queuedRequests: queuedRequestCount,
            circuitBreakerState: circuitBreaker.state
        )
    }

    func resetStatistics() {
        successfulRequests = 0
        failedRequests = 0
        retryAttempts = 0
        circuitBreaker.reset()
    }

    // MARK: - Queue Management

    func clearQueue() {
        for request in requestQueue {
            request.completion(.failure(NetworkError.networkUnavailable))
        }
        requestQueue.removeAll()
        queuedRequestCount = 0
    }

    func getQueuedRequestsByPriority() -> [QueuedRequest.RequestPriority: Int] {
        var counts: [QueuedRequest.RequestPriority: Int] = [:]
        for request in requestQueue {
            counts[request.priority, default: 0] += 1
        }
        return counts
    }
}

// MARK: - Network Statistics

struct NetworkStatistics {
    let successfulRequests: Int
    let failedRequests: Int
    let retryAttempts: Int
    let queuedRequests: Int
    let circuitBreakerState: CircuitBreaker.State

    var successRate: Double {
        let total = successfulRequests + failedRequests
        return total > 0 ? Double(successfulRequests) / Double(total) : 0.0
    }

    var averageRetriesPerRequest: Double {
        let total = successfulRequests + failedRequests
        return total > 0 ? Double(retryAttempts) / Double(total) : 0.0
    }
}

// MARK: - NetworkManager Extension for Statistics

extension NetworkManager {
    /// Get network statistics
    func getNetworkStatistics() -> NetworkStatistics {
        return Self.retryManager.getStatistics()
    }

    /// Clear request queue
    func clearRequestQueue() {
        Self.retryManager.clearQueue()
    }

    /// Reset network statistics
    func resetNetworkStatistics() {
        Self.retryManager.resetStatistics()
    }
}

// MARK: - Retry Policy Helpers

extension RetryPolicy {

    /// Get retry policy based on operation type
    static func forOperation(_ operation: NetworkOperation) -> RetryPolicy {
        switch operation {
        case .sync:
            return .exponentialBackoff(.aggressive) // Critical for sync
        case .create, .update, .delete:
            return .exponentialBackoff(.default) // Important but not critical
        case .read:
            return .exponentialBackoff(.conservative) // Less critical
        case .healthCheck:
            return .immediateRetry(maxAttempts: 2) // Quick check
        }
    }
}

enum NetworkOperation {
    case sync
    case create
    case update
    case delete
    case read
    case healthCheck
}