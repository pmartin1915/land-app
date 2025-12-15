import XCTest
@testable import AlabamaAuctionWatcher

final class CountyValidatorTests: XCTestCase {

    func testAlabamaCountiesStructure() {
        // Verify we have exactly 67 Alabama counties
        XCTAssertEqual(AlabamaCounties.totalCount, 67, "Alabama should have exactly 67 counties")

        // Verify specific key counties from the Python implementation
        XCTAssertEqual(AlabamaCounties.codes["01"], "Autauga")
        XCTAssertEqual(AlabamaCounties.codes["02"], "Mobile") // Was corrected from Baldwin
        XCTAssertEqual(AlabamaCounties.codes["05"], "Baldwin") // Was corrected from Blount
        XCTAssertEqual(AlabamaCounties.codes["38"], "Jefferson")
        XCTAssertEqual(AlabamaCounties.codes["67"], "Winston")

        // Verify all codes are 2-digit strings from 01-67
        for code in AlabamaCounties.codes.keys {
            XCTAssertEqual(code.count, 2, "County code should be 2 digits: \(code)")
            XCTAssertTrue(code.allSatisfy { $0.isNumber }, "County code should contain only numbers: \(code)")

            if let intCode = Int(code) {
                XCTAssertTrue(intCode >= 1 && intCode <= 67, "County code should be between 01-67: \(code)")
            } else {
                XCTFail("County code should be convertible to integer: \(code)")
            }
        }
    }

    func testNameToCodeMapping() {
        // Test that nameToCode mapping is correctly generated
        XCTAssertEqual(AlabamaCounties.nameToCode["autauga"], "01")
        XCTAssertEqual(AlabamaCounties.nameToCode["mobile"], "02")
        XCTAssertEqual(AlabamaCounties.nameToCode["baldwin"], "05")
        XCTAssertEqual(AlabamaCounties.nameToCode["jefferson"], "38")
        XCTAssertEqual(AlabamaCounties.nameToCode["winston"], "67")

        // Verify all names are lowercase in the mapping
        for name in AlabamaCounties.nameToCode.keys {
            XCTAssertEqual(name, name.lowercased(), "County names in mapping should be lowercase")
        }
    }

    func testValidCountyCodeValidation() throws {
        // Test valid codes with leading zeros
        XCTAssertEqual(try CountyValidator.validateCountyCode("01"), "01")
        XCTAssertEqual(try CountyValidator.validateCountyCode("05"), "05")
        XCTAssertEqual(try CountyValidator.validateCountyCode("38"), "38")
        XCTAssertEqual(try CountyValidator.validateCountyCode("67"), "67")

        // Test valid codes without leading zeros (should be padded)
        XCTAssertEqual(try CountyValidator.validateCountyCode("1"), "01")
        XCTAssertEqual(try CountyValidator.validateCountyCode("5"), "05")
        XCTAssertEqual(try CountyValidator.validateCountyCode("9"), "09")
    }

    func testInvalidCountyCodeValidation() {
        // Test invalid codes
        XCTAssertThrowsError(try CountyValidator.validateCountyCode("00")) { error in
            XCTAssertTrue(error is CountyValidationError)
            if case CountyValidationError.invalidCode(let code) = error {
                XCTAssertEqual(code, "00")
            }
        }

        XCTAssertThrowsError(try CountyValidator.validateCountyCode("68")) { error in
            XCTAssertTrue(error is CountyValidationError)
        }

        XCTAssertThrowsError(try CountyValidator.validateCountyCode("99")) { error in
            XCTAssertTrue(error is CountyValidationError)
        }

        XCTAssertThrowsError(try CountyValidator.validateCountyCode("ABC")) { error in
            XCTAssertTrue(error is CountyValidationError)
        }
    }

    func testEmptyInputValidation() {
        XCTAssertThrowsError(try CountyValidator.validateCountyCode("")) { error in
            XCTAssertTrue(error is CountyValidationError)
            if case CountyValidationError.emptyInput = error {
                // Correct error type
            } else {
                XCTFail("Should throw emptyInput error")
            }
        }

        XCTAssertThrowsError(try CountyValidator.validateCountyCode("   ")) { error in
            XCTAssertTrue(error is CountyValidationError)
        }
    }

    func testGetCountyName() {
        // Test valid codes
        XCTAssertEqual(CountyValidator.getCountyName(for: "01"), "Autauga")
        XCTAssertEqual(CountyValidator.getCountyName(for: "1"), "Autauga") // Should pad
        XCTAssertEqual(CountyValidator.getCountyName(for: "05"), "Baldwin")
        XCTAssertEqual(CountyValidator.getCountyName(for: "38"), "Jefferson")

        // Test invalid codes
        XCTAssertNil(CountyValidator.getCountyName(for: "00"))
        XCTAssertNil(CountyValidator.getCountyName(for: "99"))
        XCTAssertNil(CountyValidator.getCountyName(for: "ABC"))
    }

    func testGetCountyCodeByName() throws {
        // Test valid names (case insensitive)
        XCTAssertEqual(try CountyValidator.getCountyCode(for: "Autauga"), "01")
        XCTAssertEqual(try CountyValidator.getCountyCode(for: "autauga"), "01")
        XCTAssertEqual(try CountyValidator.getCountyCode(for: "AUTAUGA"), "01")
        XCTAssertEqual(try CountyValidator.getCountyCode(for: "Baldwin"), "05")
        XCTAssertEqual(try CountyValidator.getCountyCode(for: "Jefferson"), "38")
        XCTAssertEqual(try CountyValidator.getCountyCode(for: "Saint Clair"), "58")

        // Test invalid names
        XCTAssertThrowsError(try CountyValidator.getCountyCode(for: "NonExistent")) { error in
            XCTAssertTrue(error is CountyValidationError)
            if case CountyValidationError.invalidName(let name) = error {
                XCTAssertEqual(name, "NonExistent")
            }
        }

        XCTAssertThrowsError(try CountyValidator.getCountyCode(for: "")) { error in
            XCTAssertTrue(error is CountyValidationError)
        }
    }

    func testNormalizeCountyInput() {
        // Test valid code input
        let result1 = CountyValidator.normalizeCountyInput("05")
        XCTAssertEqual(result1?.code, "05")
        XCTAssertEqual(result1?.name, "Baldwin")

        // Test valid name input
        let result2 = CountyValidator.normalizeCountyInput("Baldwin")
        XCTAssertEqual(result2?.code, "05")
        XCTAssertEqual(result2?.name, "Baldwin")

        // Test case insensitive name
        let result3 = CountyValidator.normalizeCountyInput("baldwin")
        XCTAssertEqual(result3?.code, "05")
        XCTAssertEqual(result3?.name, "Baldwin")

        // Test padding for single digit codes
        let result4 = CountyValidator.normalizeCountyInput("5")
        XCTAssertEqual(result4?.code, "05")
        XCTAssertEqual(result4?.name, "Baldwin")

        // Test invalid input
        let result5 = CountyValidator.normalizeCountyInput("Invalid")
        XCTAssertNil(result5)

        let result6 = CountyValidator.normalizeCountyInput("")
        XCTAssertNil(result6)
    }

    func testIsValidCountyMethods() {
        // Test valid counties by code
        XCTAssertTrue(CountyValidator.isValidCounty(code: "01"))
        XCTAssertTrue(CountyValidator.isValidCounty(code: "1"))
        XCTAssertTrue(CountyValidator.isValidCounty(code: "05"))
        XCTAssertTrue(CountyValidator.isValidCounty(code: "67"))

        // Test invalid counties by code
        XCTAssertFalse(CountyValidator.isValidCounty(code: "00"))
        XCTAssertFalse(CountyValidator.isValidCounty(code: "68"))
        XCTAssertFalse(CountyValidator.isValidCounty(code: "ABC"))

        // Test valid counties by name
        XCTAssertTrue(CountyValidator.isValidCounty(name: "Autauga"))
        XCTAssertTrue(CountyValidator.isValidCounty(name: "baldwin"))
        XCTAssertTrue(CountyValidator.isValidCounty(name: "JEFFERSON"))

        // Test invalid counties by name
        XCTAssertFalse(CountyValidator.isValidCounty(name: "NonExistent"))
        XCTAssertFalse(CountyValidator.isValidCounty(name: ""))
    }

    func testSearchCounties() {
        // Test code search
        let codeResults = CountyValidator.searchCounties(query: "05")
        XCTAssertEqual(codeResults.count, 1)
        XCTAssertEqual(codeResults.first?.code, "05")
        XCTAssertEqual(codeResults.first?.name, "Baldwin")

        // Test name search
        let nameResults = CountyValidator.searchCounties(query: "Baldwin")
        XCTAssertEqual(nameResults.count, 1)
        XCTAssertEqual(nameResults.first?.code, "05")

        // Test partial name search
        let partialResults = CountyValidator.searchCounties(query: "Jeff")
        XCTAssertTrue(partialResults.contains { $0.name == "Jefferson" })

        // Test case insensitive search
        let caseResults = CountyValidator.searchCounties(query: "baldwin")
        XCTAssertEqual(caseResults.count, 1)
        XCTAssertEqual(caseResults.first?.name, "Baldwin")

        // Test empty query
        let emptyResults = CountyValidator.searchCounties(query: "")
        XCTAssertEqual(emptyResults.count, 67, "Empty query should return all counties")

        // Test no matches
        let noResults = CountyValidator.searchCounties(query: "XYZ123")
        XCTAssertEqual(noResults.count, 0)
    }

    func testAllCountiesProperty() {
        let allCounties = AlabamaCounties.allCounties

        // Should have all 67 counties
        XCTAssertEqual(allCounties.count, 67)

        // Should be sorted by code
        for i in 0..<allCounties.count-1 {
            let currentCode = Int(allCounties[i].code) ?? 0
            let nextCode = Int(allCounties[i+1].code) ?? 0
            XCTAssertLessThan(currentCode, nextCode, "Counties should be sorted by code")
        }

        // Verify first and last entries
        XCTAssertEqual(allCounties.first?.code, "01")
        XCTAssertEqual(allCounties.first?.name, "Autauga")
        XCTAssertEqual(allCounties.last?.code, "67")
        XCTAssertEqual(allCounties.last?.name, "Winston")
    }

    func testSpecificCountyCorrections() {
        // Test the corrected mappings mentioned in the Python comments
        XCTAssertEqual(AlabamaCounties.codes["02"], "Mobile", "Code 02 should be Mobile (was incorrectly Baldwin)")
        XCTAssertEqual(AlabamaCounties.codes["05"], "Baldwin", "Code 05 should be Baldwin (was incorrectly Blount)")

        // These should work in both directions
        XCTAssertEqual(try CountyValidator.getCountyCode(for: "Mobile"), "02")
        XCTAssertEqual(try CountyValidator.getCountyCode(for: "Baldwin"), "05")
        XCTAssertEqual(CountyValidator.getCountyName(for: "02"), "Mobile")
        XCTAssertEqual(CountyValidator.getCountyName(for: "05"), "Baldwin")
    }

    func testErrorMessages() {
        do {
            _ = try CountyValidator.validateCountyCode("99")
            XCTFail("Should have thrown an error")
        } catch CountyValidationError.invalidCode(let code) {
            XCTAssertEqual(code, "99")
            XCTAssertTrue(error.localizedDescription.contains("Invalid county code"))
        } catch {
            XCTFail("Wrong error type thrown")
        }

        do {
            _ = try CountyValidator.getCountyCode(for: "InvalidCounty")
            XCTFail("Should have thrown an error")
        } catch CountyValidationError.invalidName(let name) {
            XCTAssertEqual(name, "InvalidCounty")
            XCTAssertTrue(error.localizedDescription.contains("Invalid county name"))
        } catch {
            XCTFail("Wrong error type thrown")
        }
    }
}