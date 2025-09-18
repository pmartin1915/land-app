# Alabama Tax Delinquent Property Auction Watcher

A Python tool for analyzing Alabama Department of Revenue tax delinquent property auction CSVs to identify potential investment opportunities, with a focus on properties with water features.

## ⚠️ IMPORTANT LEGAL NOTICE

**Alabama Redemption Period:** Properties purchased at tax auctions in Alabama are subject to a **3-year redemption period** during which the original owner can reclaim the property by paying the purchase price plus interest and costs. During this period, you cannot take possession of the property. Always consult with a real estate attorney before participating in tax auctions.

## 🎯 Features

- **Smart CSV Parsing**: Flexible parser that adapts to various ADOR CSV formats
- **Automated Web Scraping**: Direct data collection from ADOR website (no manual CSV downloads!)
- **Targeted Filtering**: Finds properties 1-5 acres under $20,000
- **Water Feature Detection**: Flags parcels mentioning creeks, streams, springs, etc.
- **Price Analytics**: Calculates price per acre and estimated all-in costs
- **Interactive Dashboard**: Streamlit app for browsing and analyzing properties
- **Export Capability**: Generates ranked watchlists in CSV format

## 📋 Requirements

- Python 3.10+
- pandas
- streamlit
- plotly
- numpy
- openpyxl (for Excel support)
- requests (for web scraping)
- beautifulsoup4 (for HTML parsing)
- lxml (for XML/HTML parsing)

## 🚀 Quick Start

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/auction-watcher.git
cd auction-watcher
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Option A: Automated Web Scraping (Recommended)**
```bash
# Scrape data directly from ADOR website (no manual downloads!)
python scripts/parser.py --scrape-county Baldwin --infer-acres
python scripts/parser.py --scrape-county 05 --output data/processed/baldwin_watchlist.csv

# List all available counties
python scripts/parser.py --list-counties
```

**Option B: Manual CSV Processing**
   - Visit https://www.revenue.alabama.gov/property-tax/delinquent-search/
   - Download county delinquent property lists
   - Place CSV files in the `data/raw/` directory
```bash
python scripts/parser.py --input data/raw/county_delinquent.csv --infer-acres
```

4. **Launch the dashboard:**
```bash
python -m streamlit run streamlit_app/app.py
```

## 📁 Project Structure

```
/auction-watcher/
│
├── README.md              # This file
├── requirements.txt       # Python dependencies
├── .gitignore            # Git ignore file
│
├── data/                 # Data directory (gitignored)
│   ├── raw/             # Original ADOR CSV files
│   └── processed/       # Filtered watchlists
│
├── scripts/             # Core processing scripts
│   ├── __init__.py
│   ├── parser.py        # Main CSV parser and filter
│   └── utils.py         # Utility functions
│
├── streamlit_app/       # Streamlit dashboard
│   ├── __init__.py
│   ├── app.py          # Main Streamlit application
│   └── components/     # Reusable UI components
│       ├── __init__.py
│       ├── filters.py
│       └── visualizations.py
│
└── config/              # Configuration files
    └── settings.py      # Application settings

```

## 🔧 Configuration

Edit `config/settings.py` to customize:
- Acreage range (default: 1-5 acres)
- Maximum price (default: $20,000)
- Water feature keywords
- Cost estimation formulas
- Column name mappings for different CSV formats

## 📊 Metrics Calculated

1. **Price per Acre**: Total amount / Acreage
2. **Estimated All-in Cost**: Bid + estimated fees (configurable formula)
3. **Water Score**: Keyword match strength for water features
4. **Investment Score**: Composite ranking based on multiple factors

## 🌊 Water Feature Keywords

The system searches for these water-related terms in property descriptions:
- Primary: creek, stream, river, lake, pond, spring
- Secondary: branch, run, brook, tributary, wetland, marsh
- Tertiary: water, aquatic, riparian, shore, bank

## 🕸️ Web Scraping Details

### County Codes
The system supports all 67 Alabama counties. Use either county code (01-67) or county name:

```bash
# Major counties (examples)
python scripts/parser.py --scrape-county 05    # Baldwin
python scripts/parser.py --scrape-county 37    # Jefferson
python scripts/parser.py --scrape-county 49    # Mobile
python scripts/parser.py --scrape-county 51    # Montgomery
python scripts/parser.py --scrape-county 63    # Tuscaloosa

# Or use county names
python scripts/parser.py --scrape-county "Baldwin"
python scripts/parser.py --scrape-county "Mobile"
```

### Scraping Features
- **Automatic Pagination**: Handles multiple pages of results
- **Rate Limiting**: Respectful delays between requests
- **Data Validation**: Cleans and normalizes scraped data
- **Raw Data Backup**: Saves original scraped data for reference
- **Error Handling**: Graceful fallback options

### Troubleshooting Web Scraping
If scraping fails:
1. Check internet connection
2. Verify county code with `--list-counties`
3. Try again later (ADOR website may be temporarily unavailable)
4. Use CSV file processing as fallback
5. Reduce `--max-pages` if timing out

## 🗺️ Future Enhancements

- **Geospatial Analysis**: Overlay parcels with USGS/OpenStreetMap waterway data
- **Historical Analysis**: Track auction results over time
- **Automated Alerts**: Email notifications for new matching properties
- **ML Predictions**: Predict likelihood of redemption or resale value
- **Parcel Mapping**: Visual map integration with satellite imagery

## 📝 Usage Examples

### Web Scraping (Automated):
```bash
# Scrape by county name
python scripts/parser.py --scrape-county Baldwin --infer-acres

# Scrape by county code with custom filters
python scripts/parser.py --scrape-county 05 \
    --min-acres 2 \
    --max-acres 10 \
    --max-price 15000 \
    --output data/processed/baldwin_custom.csv

# Scrape with pagination control
python scripts/parser.py --scrape-county Mobile --max-pages 20

# List available counties
python scripts/parser.py --list-counties
```

### CSV File Processing (Manual):
```bash
# Basic filtering
python scripts/parser.py --input data/raw/jefferson_county.csv --infer-acres

# Advanced filtering with custom parameters
python scripts/parser.py \
    --input data/raw/jefferson_county.csv \
    --min-acres 2 \
    --max-acres 10 \
    --max-price 15000 \
    --output data/processed/custom_watchlist.csv
```

## 🤝 Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.

## 📜 License

MIT License - See LICENSE file for details

## ⚖️ Disclaimer

This tool is for informational purposes only. Always perform due diligence and consult with legal and real estate professionals before participating in tax auctions. The authors assume no responsibility for investment decisions made using this tool.

## 🆘 Support

For issues or questions:
1. Check the FAQ section below
2. Open an issue on GitHub
3. Contact: [your-email@example.com]

## ❓ FAQ

**Q: Why are some properties showing $0 or very low prices?**
A: This typically means back taxes only. Check the "minimum bid" or "face value" columns.

**Q: Can I trust the acreage data?**
A: ADOR data may have errors. Always verify with county records before bidding.

**Q: How accurate is the water feature detection?**
A: Keyword matching is ~70% accurate. Visual/geospatial verification recommended.

---
*Built with ❤️ for Alabama property investors*