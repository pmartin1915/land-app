# Alabama Tax Auction Watcher

**Project Status: Data Cleaning & Scoring - COMPLETE**

This project automates the process of scraping, parsing, and scoring properties from the Alabama Department of Revenue's tax lien auction site. The goal is to identify high-potential real estate investment opportunities based on metrics like price per acre and land size.

## Data Validation & Cleaning Summary

The core data processing pipeline has been successfully implemented and validated. The following tasks were completed:

1.  **Initial Scraping**: Scraped all 2,053 properties listed for auction.
2.  **Acreage Parsing Fixes**: Implemented robust logic to parse acreage from various description formats (e.g., "100 X 200", "75' by 150'").
3.  **Targeted Zero-Acreage Fix**: Discovered that most data quality issues stemmed from properties having a '0' in the primary acreage field. A targeted script (`scripts/fix_zero_acreage.py`) was created to apply the dimension-parsing logic only to these specific cases.
4.  **Score Recalculation**: All property scores were recalculated with the improved data, including `price_per_acre` and the final `investment_score`.
5.  **Final Validation**: The final dataset now contains **1,890 valid properties**, representing **92.1%** of the total scraped data. The remaining ~8% of properties lack any usable acreage information in their listings.

## Final Assets

*   `alabama_auction_watcher.db`: The SQLite database containing all raw and processed data.
*   `final_property_dataset.csv`: A clean, sorted CSV file containing the 1,890 valid properties, ordered by `investment_score`. This is the primary output of this project phase.

## How to Use

The project is now at a stable checkpoint.

### To Re-create the Final Dataset

If you update the database or scoring logic in the future, you can regenerate the final CSV by running:

```bash
python scripts/create_final_dataset.py
```

### To Run a Quick Validation

To see a statistical summary and a list of the top-ranked properties directly from the database, run:

```bash
python quick_validate.py
```

## Next Steps

The data is now clean and ready for use. Potential next steps include:

-   **Analysis & Visualization**: Use the `final_property_dataset.csv` in tools like Jupyter Notebook, Tableau, or Excel to explore trends and identify top candidates.
-   **Web Application**: Build a simple web interface (e.g., using Flask or Django) to display the top-ranked properties in a user-friendly format.
-   **Alerting System**: Create a service that sends an email or notification when new properties are scraped that meet specific investment criteria.

---