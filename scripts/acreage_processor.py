# acreage_processor.py
import re
import sqlite3
import pandas as pd
from typing import Optional

# --- Constants and Configuration ---
SQ_FT_PER_ACRE = 43560.0
VALID_ACREAGE_RANGE = (0.01, 1000.0)

# --- Pre-compiled Regex Patterns ---
# Using re.IGNORECASE for robust matching
# Priority 1: Explicit acreage mentions
NUMERIC_ACREAGE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:a\b|ac\b|acres?\b)", re.IGNORECASE)
FRACTIONAL_ACREAGE_RE = re.compile(r"(\d+/\d+)\s*(?:ac\b|acres?\b)", re.IGNORECASE)

# Priority 2: Lot dimensions (e.g., 100x200 or 100' X 200')
DIMENSIONS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*'?\s*[xX]\s*'?\s*(\d+(?:\.\d+)?)", re.IGNORECASE)


def extract_acreage_from_description(description: str) -> Optional[float]:
    """
    Extracts acreage from a property description using a fallback hierarchy.

    Hierarchy:
    1. Tries to find explicit numeric acreage (e.g., "2.5 AC").
    2. Tries to find explicit fractional acreage (e.g., "1/2 ACRE").
    3. Tries to find lot dimensions and calculates acreage (e.g., "100x200").

    Args:
        description: The property description text.

    Returns:
        The extracted acreage as a float if found and valid, otherwise None.
    """
    if not isinstance(description, str) or not description:
        return None

    acreage = None

    # 1. Check for explicit numeric acreage
    numeric_match = NUMERIC_ACREAGE_RE.search(description)
    if numeric_match:
        try:
            acreage = float(numeric_match.group(1))
        except (ValueError, IndexError):
            acreage = None

    # 2. Check for explicit fractional acreage if numeric not found
    if acreage is None:
        fractional_match = FRACTIONAL_ACREAGE_RE.search(description)
        if fractional_match:
            try:
                num, den = map(float, fractional_match.group(1).split('/'))
                if den != 0:
                    acreage = num / den
            except (ValueError, IndexError, ZeroDivisionError):
                acreage = None

    # 3. Check for dimensions if no explicit acreage found
    if acreage is None:
        # Find all dimension matches, use the one with the largest area
        # to handle cases like "house on 50x100 lot on 2 acre parcel"
        all_dims = DIMENSIONS_RE.finditer(description)
        max_sq_ft = 0
        for match in all_dims:
            try:
                dim1 = float(match.group(1))
                dim2 = float(match.group(2))
                max_sq_ft = max(max_sq_ft, dim1 * dim2)
            except (ValueError, IndexError):
                continue

        if max_sq_ft > 0:
            acreage = max_sq_ft / SQ_FT_PER_ACRE

    # Final validation before returning
    if acreage is not None:
        if VALID_ACREAGE_RANGE[0] <= acreage <= VALID_ACREAGE_RANGE[1]:
            return round(acreage, 4) # Standardize precision

    return None


def batch_update_acreage(db_path: str, dry_run: bool = True):
    """
    Finds properties with invalid acreage and updates them based on their description.

    Args:
        db_path: Path to the SQLite database file.
        dry_run: If True, prints proposed changes without modifying the database.
                 If False, executes the UPDATE statements.
    """
    print("Starting acreage update process...")
    if dry_run:
        print("--- RUNNING IN DRY-RUN MODE: No changes will be saved to the database. ---")

    conn = sqlite3.connect(db_path)
    try:
        # Select only properties where acreage is missing or invalid
        df = pd.read_sql_query(
            "SELECT id, description, acreage FROM properties WHERE acreage IS NULL OR acreage < 0.01",
            conn
        )

        print(f"Found {len(df)} properties with invalid acreage to process.")

        updates = []
        for _, row in df.iterrows():
            new_acreage = extract_acreage_from_description(row['description'])
            if new_acreage:
                updates.append({
                    "id": row["id"],
                    "new_acreage": new_acreage,
                    "old_acreage": row["acreage"],
                    "description": row["description"]
                })

        if not updates:
            print("No new acreage information could be extracted. No updates to perform.")
            return

        print(f"\n--- Proposed Updates: {len(updates)} ---")
        for update in updates[:20]: # Print a sample
            print(
                f"ID: {update['id']}, "
                f"Old: {update['old_acreage']:.4f}, "
                f"New: {update['new_acreage']:.4f} "
                f"<- Desc: '{update['description'][:70]}...'"
            )
        if len(updates) > 20:
            print(f"... and {len(updates) - 20} more.")

        if not dry_run:
            print("\n--- Applying updates to the database... ---")
            update_data = [(u['new_acreage'], u['id']) for u in updates]
            # Also update price_per_acre when acreage changes
            with conn:
                cursor = conn.cursor()
                for new_acreage, prop_id in update_data:
                    cursor.execute(
                        "UPDATE properties SET acreage = ?, price_per_acre = amount / ? WHERE id = ?",
                        (new_acreage, new_acreage, prop_id)
                    )
                print(f"Successfully updated {len(update_data)} properties in the database.")
        else:
            print("\n--- Dry run complete. To apply these changes, run with dry_run=False. ---")

    finally:
        conn.close()


if __name__ == '__main__':
    # --- Validation and Testing ---
    test_cases = {
        "LOT 1 BLOCK 1 2.53 AC": 2.53,
        "A 50' X 100.5' LOT": 0.1154,
        "some text with 1/2 acre lot": 0.5,
        "HOUSE ON A 10A PARCEL": 10.0,
        "75x150 IRR": 0.2583,
        "LOT 25 FIVE MILE CREEK ROAD": None,
        "BLK 19 PLAT A ISHKOODA SUB 35/59": None,
        "A 20000 acre lot": None, # Exceeds validation range
        "LOT 10, 50x100 ON A 1/2 AC PARCEL": 0.5 # Test priority
    }

    print("--- Running Test Cases ---")
    all_passed = True
    for desc, expected in test_cases.items():
        result = extract_acreage_from_description(desc)
        if result is not None and expected is not None:
            passed = abs(result - expected) < 0.001
        else:
            passed = result == expected
        status = "PASS" if passed else f"FAIL (Got: {result})"
        if not passed:
            all_passed = False
        print(f"'{desc[:40]}...': Expected: {expected}, Got: {result} -> {status}")

    if all_passed:
        print("\n[SUCCESS] All test cases passed!")
    else:
        print("\n[WARNING] Some test cases failed!")

    # --- Example Batch Update Usage ---
    DATABASE_FILE = 'alabama_auction_watcher.db'

    # It is CRITICAL to run in dry_run=True first to validate the changes
    print("\n" + "="*70)
    print("To run batch update (dry run first):")
    print(f"  python -c \"from scripts.acreage_processor import batch_update_acreage; batch_update_acreage('{DATABASE_FILE}', dry_run=True)\"")
    print("\nAfter verifying dry run output, apply changes:")
    print(f"  python -c \"from scripts.acreage_processor import batch_update_acreage; batch_update_acreage('{DATABASE_FILE}', dry_run=False)\"")
    print("="*70)
