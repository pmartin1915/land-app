import Foundation

/// Alabama counties with ADOR (Dept of Revenue) official codes
/// Source: https://www.revenue.alabama.gov/property-tax/delinquent-search/
/// CRITICAL: This mapping MUST match backend models.py AND core/scrapers/alabama_dor.py
/// Note: ADOR uses non-sequential codes. Jefferson County is split into Birmingham (01) and Bessemer (68).
struct AlabamaCounties {

    static let codes: [String: String] = [
        // ADOR special codes (large counties)
        "01": "Jefferson-Bham",
        "02": "Mobile",
        "03": "Montgomery",
        // Standard ADOR alphabetical codes (04-67)
        "04": "Autauga",
        "05": "Baldwin",
        "06": "Barbour",
        "07": "Bibb",
        "08": "Blount",
        "09": "Bullock",
        "10": "Butler",
        "11": "Calhoun",
        "12": "Chambers",
        "13": "Cherokee",
        "14": "Chilton",
        "15": "Choctaw",
        "16": "Clarke",
        "17": "Clay",
        "18": "Cleburne",
        "19": "Coffee",
        "20": "Colbert",
        "21": "Conecuh",
        "22": "Coosa",
        "23": "Covington",
        "24": "Crenshaw",
        "25": "Cullman",
        "26": "Dale",
        "27": "Dallas",
        "28": "DeKalb",
        "29": "Elmore",
        "30": "Escambia",
        "31": "Etowah",
        "32": "Fayette",
        "33": "Franklin",
        "34": "Geneva",
        "35": "Greene",
        "36": "Hale",
        "37": "Henry",
        "38": "Houston",
        "39": "Jackson",
        "40": "Lamar",
        "41": "Lauderdale",
        "42": "Lawrence",
        "43": "Lee",
        "44": "Limestone",
        "45": "Lowndes",
        "46": "Macon",
        "47": "Madison",
        "48": "Marengo",
        "49": "Marion",
        "50": "Marshall",
        "51": "Monroe",
        "52": "Morgan",
        "53": "Perry",
        "54": "Pickens",
        "55": "Pike",
        "56": "Randolph",
        "57": "Russell",
        "58": "Shelby",
        "59": "St_Clair",
        "60": "Sumter",
        "61": "Talladega",
        "62": "Tallapoosa",
        "63": "Tuscaloosa",
        "64": "Walker",
        "65": "Washington",
        "66": "Wilcox",
        "67": "Winston",
        // Jefferson County Bessemer Division (separate tax district)
        "68": "Jefferson-Bess"
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
            return "Invalid county code: '\(code)'. Must be a valid ADOR code (01-68)."
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