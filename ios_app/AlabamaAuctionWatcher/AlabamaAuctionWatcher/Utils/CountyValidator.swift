import Foundation

struct AlabamaCounties {

    static let codes: [String: String] = [
        "01": "Autauga",
        "02": "Mobile",
        "03": "Barbour",
        "04": "Bibb",
        "05": "Baldwin",
        "06": "Blount",
        "07": "Bullock",
        "08": "Butler",
        "09": "Calhoun",
        "10": "Chambers",
        "11": "Cherokee",
        "12": "Chilton",
        "13": "Choctaw",
        "14": "Clarke",
        "15": "Clay",
        "16": "Cleburne",
        "17": "Coffee",
        "18": "Colbert",
        "19": "Conecuh",
        "20": "Coosa",
        "21": "Covington",
        "22": "Crenshaw",
        "23": "Cullman",
        "24": "Dale",
        "25": "Dallas",
        "26": "DeKalb",
        "27": "Elmore",
        "28": "Escambia",
        "29": "Etowah",
        "30": "Fayette",
        "31": "Franklin",
        "32": "Geneva",
        "33": "Greene",
        "34": "Hale",
        "35": "Henry",
        "36": "Houston",
        "37": "Jackson",
        "38": "Jefferson",
        "39": "Lamar",
        "40": "Lauderdale",
        "41": "Lawrence",
        "42": "Lee",
        "43": "Limestone",
        "44": "Lowndes",
        "45": "Macon",
        "46": "Madison",
        "47": "Marengo",
        "48": "Marion",
        "49": "Marshall",
        "50": "Monroe",
        "51": "Montgomery",
        "52": "Morgan",
        "53": "Perry",
        "54": "Pickens",
        "55": "Pike",
        "56": "Randolph",
        "57": "Russell",
        "58": "Saint Clair",
        "59": "Shelby",
        "60": "Sumter",
        "61": "Talladega",
        "62": "Tallapoosa",
        "63": "Tuscaloosa",
        "64": "Walker",
        "65": "Washington",
        "66": "Wilcox",
        "67": "Winston"
    ]

    static let nameToCode: [String: String] = {
        var reversed: [String: String] = [:]
        for (code, name) in codes {
            reversed[name.lowercased()] = code
        }
        return reversed
    }()

    static var allCounties: [(code: String, name: String)] {
        return codes.sorted { $0.key < $1.key }.map { (code: $0.key, name: $0.value) }
    }

    static var totalCount: Int {
        return codes.count
    }
}

enum CountyValidationError: Error, LocalizedError {
    case invalidCode(String)
    case invalidName(String)
    case emptyInput

    var errorDescription: String? {
        switch self {
        case .invalidCode(let code):
            return "Invalid county code: '\(code)'. Must be a 2-digit code from 01-67."
        case .invalidName(let name):
            return "Invalid county name: '\(name)'. County not found in Alabama."
        case .emptyInput:
            return "County input cannot be empty."
        }
    }
}

struct CountyValidator {

    static func validateCountyCode(_ input: String) throws -> String {
        let trimmed = input.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !trimmed.isEmpty else {
            throw CountyValidationError.emptyInput
        }

        let paddedCode = trimmed.count == 1 ? "0\(trimmed)" : trimmed

        guard AlabamaCounties.codes[paddedCode] != nil else {
            throw CountyValidationError.invalidCode(trimmed)
        }

        return paddedCode
    }

    static func getCountyName(for code: String) -> String? {
        let validCode = try? validateCountyCode(code)
        return validCode != nil ? AlabamaCounties.codes[validCode!] : nil
    }

    static func getCountyCode(for name: String) throws -> String {
        let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !trimmed.isEmpty else {
            throw CountyValidationError.emptyInput
        }

        let lowercaseName = trimmed.lowercased()

        guard let code = AlabamaCounties.nameToCode[lowercaseName] else {
            throw CountyValidationError.invalidName(trimmed)
        }

        return code
    }

    static func normalizeCountyInput(_ input: String) -> (code: String, name: String)? {
        let trimmed = input.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !trimmed.isEmpty else { return nil }

        // Try as county code first
        if let code = try? validateCountyCode(trimmed),
           let name = AlabamaCounties.codes[code] {
            return (code: code, name: name)
        }

        // Try as county name
        if let code = try? getCountyCode(for: trimmed),
           let name = AlabamaCounties.codes[code] {
            return (code: code, name: name)
        }

        return nil
    }

    static func isValidCounty(code: String) -> Bool {
        return (try? validateCountyCode(code)) != nil
    }

    static func isValidCounty(name: String) -> Bool {
        return (try? getCountyCode(for: name)) != nil
    }

    static func searchCounties(query: String) -> [(code: String, name: String)] {
        let lowercaseQuery = query.lowercased()

        return AlabamaCounties.allCounties.filter { county in
            county.code.contains(lowercaseQuery) ||
            county.name.lowercased().contains(lowercaseQuery)
        }
    }
}