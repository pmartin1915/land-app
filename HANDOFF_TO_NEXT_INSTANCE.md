# Handoff for Next AI Instance

## Mission Status
The "Iron Logic Refactor" is complete and has been validated. We have successfully moved the application's core from a purely AI-driven model to a deterministic, rules-based system for making bid decisions.

### Key Accomplishments:
1.  **`scripts/guardrails.py` Created:** A new, vectorized, pandas-native module now contains our core business rules (max LTV, min value, etc.). This is our "Iron Logic".
2.  **`scripts/parser.py` Integrated:** The guardrail logic is now deeply integrated into the main data processing script. It is called for all processing methods (single file, single scrape, batch scrape).
3.  **Validation Complete:** We validated the new engine using the local file `data/raw/baldwin_test_scrape.csv`. The test confirmed the engine correctly filters and rejects properties based on our rules, with clear logging of rejection reasons.

### Known Issues:
- **None.** The critical scraper issue has been resolved.

## Next Objectives

With the live data feed restored, the next priorities are to validate our investment strategy and build a comprehensive dataset.

1.  **Perform a Full-Scale Data Scraping:**
    - **Goal:** Scrape all available data from the Alabama Department of Revenue website to build a comprehensive dataset for back-testing and analysis.
    - **Action:** A script, `full_scrape.py`, has been created at the project root (`C:\auction\full_scrape.py`) to iterate through all counties and scrape available data. This script saves raw data to `data/raw/` and processed watchlists to `data/processed/` for each county.
    - **Important Note for Execution:** Due to the potentially long runtime for scraping all counties (which can exceed typical CLI tool timeouts), this script is designed to be run manually in your local environment.
        -   **How to Run:** Open a terminal or command prompt in the `C:\auction` directory and execute:
            ```bash
            python full_scrape.py
            ```
        -   The script includes enhanced logging to differentiate between genuine scraping failures and counties for which no delinquent property data was found (an expected outcome for some counties).
        -   **Validation:** After the `full_scrape.py` script has completed, you should run the `quick_validate.py` script manually to perform a final validation of the collected data:
            ```bash
            python quick_validate.py
            ```

2.  **Back-test the Guardrail Strategy:**
    - **Goal:** Fine-tune our investment parameters (`MAX_LTV`, `PROFIT_MARGIN`, etc.).
    - **Action:** The `data/raw/` directory now contains live, up-to-date data. Create a new script (`backtest.py`) that iterates through these files, runs our `apply_decision_engine` on the historical data, and simulates the profitability of the "bids" we would have made.

3.  **Develop an Observability Dashboard:**
    - **Goal:** Create a simple UI to visualize the results of the parsing and decision-making process.
    - **Action:** Build a simple `streamlit` application (`dashboard.py`) that can read a processed watchlist CSV and display key metrics: number of properties analyzed, pass/fail rates, and a breakdown of rejection reasons. This is crucial for monitoring and building trust in the system.
