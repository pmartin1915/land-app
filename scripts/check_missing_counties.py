from pathlib import Path
import re

def get_scraped_counties():
    """Get list of counties that have been scraped from raw data files."""
    raw_dir = Path('data/raw')
    scraped_counties = set()

    if not raw_dir.exists():
        return set()

    # Regex to match scraped files: scraped_[county_name]_county_[timestamp].csv
    pattern = r'scraped_(.+?)_county_\d{8}_\d{6}\.csv'

    for file_path in raw_dir.glob('scraped_*_county_*.csv'):
        match = re.match(pattern, file_path.name)
        if match:
            county_name = match.group(1).lower().replace('_', ' ')
            scraped_counties.add(county_name)

    return scraped_counties

def get_all_counties():
    """Get all 67 Alabama counties."""
    import sys
    from pathlib import Path
    # Add the parent directory to sys.path to allow importing from scripts
    parent_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(parent_dir))

    from scripts.scraper import ALABAMA_COUNTY_CODES
    return {name.lower() for name in ALABAMA_COUNTY_CODES.values()}

def main():
    scraped = get_scraped_counties()
    all_counties = get_all_counties()

    missing = all_counties - scraped

    print(f"Total counties: {len(all_counties)}")
    print(f"Scraped counties: {len(scraped)}")
    print(f"Missing counties: {len(missing)}")

    if missing:
        print("\nMissing counties:")
        for county in sorted(missing):
            print(f"  - {county}")
    else:
        print("All counties have been scraped!")

if __name__ == "__main__":
    main()
