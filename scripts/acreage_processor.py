# acreage_processor.py
"""
Enhanced acreage extraction with PLSS aliquot parsing and data lineage tracking.

Extraction Hierarchy:
1. Explicit fractional acreage (e.g., "1/2 ACRE") - checked first to avoid "1/2" -> "2"
2. Explicit numeric acreage (e.g., "2.5 AC") - highest confidence
3. PLSS aliquot parts (e.g., "NE 1/4 of SE 1/4") - calculated from section math
4. Lot dimensions (e.g., "100x200") - lowest priority
"""
import re
import sqlite3
import pandas as pd
from typing import Optional, Tuple
from dataclasses import dataclass

# --- Constants and Configuration ---
SQ_FT_PER_ACRE = 43560.0
VALID_ACREAGE_RANGE = (0.01, 1000.0)
SECTION_ACRES = 640.0  # Standard PLSS section size

# Low-bid filter threshold
LOW_BID_THRESHOLD = 150.0

# --- Pre-compiled Regex Patterns ---
# Priority 1: Explicit acreage mentions
# Note: Fractional must be checked BEFORE numeric to avoid "1/2 acre" matching as "2 acre"
FRACTIONAL_ACREAGE_RE = re.compile(r"(\d+/\d+)\s*(?:ac\b|acres?\b)", re.IGNORECASE)
NUMERIC_ACREAGE_RE = re.compile(r"(?<!/)\b(\d+(?:\.\d+)?)\s*(?:a\b|ac\b|acres?\b)", re.IGNORECASE)

# Priority 2: PLSS Aliquot parts (NE 1/4, S 1/2, etc.)
# Matches patterns like: NE 1/4, N 1/2, NE1/4, SW 1/4 OF SE 1/4
ALIQUOT_RE = re.compile(r'\b([NSEW]{1,2})\s*1/([24])\b', re.IGNORECASE)

# Detect partial/exception markers that reduce confidence
PARTIAL_MARKERS_RE = re.compile(r'\b(PT|PART|EXC|EXCEPT|LESS|PORTION)\b', re.IGNORECASE)

# Priority 3: Lot dimensions (e.g., 100x200 or 100' X 200')
DIMENSIONS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*'?\s*[xX]\s*'?\s*(\d+(?:\.\d+)?)", re.IGNORECASE)

# Red flag keywords for low-bid filtering
RED_FLAG_KEYWORDS = [
    'MINERAL', 'MIN RIGHTS', 'MINERAL RIGHTS',
    'COMMON AREA', 'GREENBELT', 'GREEN BELT',
    'UTILITY', 'EASEMENT ONLY', 'UTILITY EASEMENT',
    'DRAINAGE', 'RETENTION', 'POND ONLY',
    'SEVERED', 'SUBSURFACE'
]

# Owner name red flags (HOA common areas, etc.)
OWNER_RED_FLAGS = [
    'PROPERTY OWNERS ASSOCIATION', 'POA', 'HOA',
    'HOMEOWNERS ASSOCIATION', 'HOMEOWNER ASSOCIATION',
    'OWNERS ASSOCIATION'
]


@dataclass
class AcreageResult:
    """Result of acreage extraction with lineage data."""
    acreage: float
    source: str  # 'parsed_explicit', 'parsed_plss', 'parsed_dimensions'
    confidence: str  # 'high', 'medium', 'low'
    raw_text: str  # The text that was parsed


def parse_aliquot_acreage(description: str) -> Optional[AcreageResult]:
    """
    Parse PLSS aliquot parts to estimate acreage.

    A standard Section is 640 acres. Aliquot parts divide it:
    - 1/4 = 160 acres (quarter section)
    - 1/2 = 320 acres (half section)
    - NE 1/4 of SE 1/4 = 640 * 0.25 * 0.25 = 40 acres

    Args:
        description: Legal description text

    Returns:
        AcreageResult if aliquot parts found, None otherwise
    """
    if not isinstance(description, str) or not description:
        return None

    desc_upper = description.upper()

    # Find all aliquot fractions
    matches = ALIQUOT_RE.findall(desc_upper)

    if not matches:
        return None

    # Start with full section
    acreage = SECTION_ACRES

    # Apply each fraction found
    for direction, denominator in matches:
        denom = int(denominator)
        acreage *= (1.0 / denom)

    # Validate result
    if not (VALID_ACREAGE_RANGE[0] <= acreage <= VALID_ACREAGE_RANGE[1]):
        return None

    # Check for partial markers that reduce confidence
    has_partial_marker = bool(PARTIAL_MARKERS_RE.search(desc_upper))

    # Build raw text from matched parts
    raw_parts = [f"{d} 1/{n}" for d, n in matches]
    raw_text = " ".join(raw_parts)

    return AcreageResult(
        acreage=round(acreage, 4),
        source='parsed_plss',
        confidence='low' if has_partial_marker else 'medium',
        raw_text=raw_text
    )


def extract_acreage_with_lineage(description: str) -> Optional[AcreageResult]:
    """
    Extracts acreage from a property description with full lineage tracking.

    Hierarchy:
    1. Explicit fractional acreage (e.g., "1/2 ACRE") - checked first
    2. Explicit numeric acreage (e.g., "2.5 AC") - high confidence
    3. PLSS aliquot parts (e.g., "NE 1/4 of SE 1/4") - medium confidence
    4. Lot dimensions (e.g., "100x200") - low confidence

    Args:
        description: The property description text.

    Returns:
        AcreageResult with acreage and lineage data, or None if not found.
    """
    if not isinstance(description, str) or not description:
        return None

    # 1. Check for explicit fractional acreage FIRST (to avoid "1/2 acre" -> "2 acre")
    fractional_match = FRACTIONAL_ACREAGE_RE.search(description)
    if fractional_match:
        try:
            num, den = map(float, fractional_match.group(1).split('/'))
            if den != 0:
                acreage = num / den
                if VALID_ACREAGE_RANGE[0] <= acreage <= VALID_ACREAGE_RANGE[1]:
                    return AcreageResult(
                        acreage=round(acreage, 4),
                        source='parsed_explicit',
                        confidence='high',
                        raw_text=fractional_match.group(0)
                    )
        except (ValueError, IndexError, ZeroDivisionError):
            pass

    # 2. Check for explicit numeric acreage
    numeric_match = NUMERIC_ACREAGE_RE.search(description)
    if numeric_match:
        try:
            acreage = float(numeric_match.group(1))
            if VALID_ACREAGE_RANGE[0] <= acreage <= VALID_ACREAGE_RANGE[1]:
                return AcreageResult(
                    acreage=round(acreage, 4),
                    source='parsed_explicit',
                    confidence='high',
                    raw_text=numeric_match.group(0)
                )
        except (ValueError, IndexError):
            pass

    # 3. Check for PLSS aliquot parts
    aliquot_result = parse_aliquot_acreage(description)
    if aliquot_result:
        return aliquot_result

    # 4. Check for dimensions (lowest priority)
    all_dims = DIMENSIONS_RE.finditer(description)
    max_sq_ft = 0
    best_match = None

    for match in all_dims:
        try:
            dim1 = float(match.group(1))
            dim2 = float(match.group(2))
            sq_ft = dim1 * dim2
            if sq_ft > max_sq_ft:
                max_sq_ft = sq_ft
                best_match = match
        except (ValueError, IndexError):
            continue

    if max_sq_ft > 0:
        acreage = max_sq_ft / SQ_FT_PER_ACRE
        if VALID_ACREAGE_RANGE[0] <= acreage <= VALID_ACREAGE_RANGE[1]:
            return AcreageResult(
                acreage=round(acreage, 4),
                source='parsed_dimensions',
                confidence='low',
                raw_text=best_match.group(0) if best_match else ''
            )

    return None


def extract_acreage_from_description(description: str) -> Optional[float]:
    """
    Legacy function for backward compatibility.
    Returns just the acreage value without lineage data.
    """
    result = extract_acreage_with_lineage(description)
    return result.acreage if result else None


def check_owner_red_flags(owner_name: Optional[str]) -> Tuple[bool, str]:
    """
    Check if owner name indicates HOA common area or similar.

    Args:
        owner_name: Property owner name

    Returns:
        Tuple of (is_red_flag: bool, reason: str)
    """
    if not owner_name:
        return (False, '')

    owner_upper = owner_name.upper()
    for flag in OWNER_RED_FLAGS:
        if flag in owner_upper:
            return (True, f'Owner is HOA/POA: {flag}')

    return (False, '')


def should_filter_low_bid(amount: float, acreage: Optional[float],
                          description: str) -> Tuple[bool, str]:
    """
    Determine if a low-bid parcel should be filtered out.

    Low-bid parcels (<$150) are often:
    - Mineral rights only
    - HOA common areas
    - Utility easements
    - Unusable remnants

    Args:
        amount: Bid amount in USD
        acreage: Property acreage (may be None)
        description: Legal description text

    Returns:
        Tuple of (should_filter: bool, reason: str)
    """
    # Only apply filter to low-bid properties
    if amount >= LOW_BID_THRESHOLD:
        return (False, '')

    # Check for red flag keywords
    desc_upper = description.upper() if description else ''
    for keyword in RED_FLAG_KEYWORDS:
        if keyword in desc_upper:
            return (True, f'Contains red flag: {keyword}')

    # If no acreage and low bid, likely junk
    if acreage is None or acreage < 0.1:
        # Exception: If description has "LOT" with dimensions, might be valid
        if 'LOT' in desc_upper and DIMENSIONS_RE.search(description or ''):
            return (False, '')
        return (True, 'Low bid with no verified acreage')

    return (False, '')


def batch_update_acreage(db_path: str, dry_run: bool = True,
                         state_filter: Optional[str] = None):
    """
    Finds properties with invalid acreage and updates them based on their description.
    Now includes data lineage tracking.

    Args:
        db_path: Path to the SQLite database file.
        dry_run: If True, prints proposed changes without modifying the database.
        state_filter: Optional state code to filter (e.g., 'AR' for Arkansas only)
    """
    print("Starting enhanced acreage update process...")
    if dry_run:
        print("--- RUNNING IN DRY-RUN MODE: No changes will be saved to the database. ---")

    conn = sqlite3.connect(db_path)
    try:
        # Build query with optional state filter
        query = """
            SELECT id, description, acreage, amount, state
            FROM properties
            WHERE (acreage IS NULL OR acreage < 0.01)
        """
        if state_filter:
            query += f" AND state = '{state_filter}'"

        df = pd.read_sql_query(query, conn)
        print(f"Found {len(df)} properties with invalid acreage to process.")

        updates = []
        filtered_count = 0
        filtered_reasons = {}

        for _, row in df.iterrows():
            # Check if this should be filtered as junk data
            should_filter, filter_reason = should_filter_low_bid(
                row['amount'] or 0,
                row['acreage'],
                row['description'] or ''
            )

            if should_filter:
                filtered_count += 1
                filtered_reasons[filter_reason] = filtered_reasons.get(filter_reason, 0) + 1
                continue

            # Try to extract acreage with lineage
            result = extract_acreage_with_lineage(row['description'])
            if result:
                updates.append({
                    "id": row["id"],
                    "new_acreage": result.acreage,
                    "old_acreage": row["acreage"],
                    "description": row["description"],
                    "source": result.source,
                    "confidence": result.confidence,
                    "raw_text": result.raw_text[:200] if result.raw_text else ''
                })

        # Report filtered properties
        if filtered_count > 0:
            print(f"\n--- Filtered {filtered_count} low-quality parcels ---")
            for reason, count in filtered_reasons.items():
                print(f"  {reason}: {count}")

        if not updates:
            print("No new acreage information could be extracted. No updates to perform.")
            return

        # Summary by source type
        by_source = {}
        for u in updates:
            by_source[u['source']] = by_source.get(u['source'], 0) + 1

        print(f"\n--- Proposed Updates: {len(updates)} ---")
        print("By extraction method:")
        for source, count in by_source.items():
            print(f"  {source}: {count}")

        print("\nSample updates:")
        for update in updates[:15]:
            old_val = f"{update['old_acreage']:.4f}" if update['old_acreage'] else 'NULL'
            print(
                f"  [{update['source'][:10]:10}] {update['new_acreage']:8.4f} ac "
                f"(was {old_val}) <- '{update['description'][:50]}...'"
            )
        if len(updates) > 15:
            print(f"  ... and {len(updates) - 15} more.")

        if not dry_run:
            print("\n--- Applying updates to the database... ---")
            with conn:
                cursor = conn.cursor()
                for u in updates:
                    cursor.execute("""
                        UPDATE properties
                        SET acreage = ?,
                            price_per_acre = amount / ?,
                            acreage_source = ?,
                            acreage_confidence = ?,
                            acreage_raw_text = ?
                        WHERE id = ?
                    """, (
                        u['new_acreage'],
                        u['new_acreage'],
                        u['source'],
                        u['confidence'],
                        u['raw_text'],
                        u['id']
                    ))
                print(f"Successfully updated {len(updates)} properties in the database.")
        else:
            print("\n--- Dry run complete. To apply changes, run with dry_run=False. ---")

    finally:
        conn.close()


def update_existing_acreage_lineage(db_path: str, dry_run: bool = True):
    """
    Update lineage fields for properties that already have acreage from API.
    Sets acreage_source='api' and acreage_confidence='high' for these.

    Args:
        db_path: Path to the SQLite database file.
        dry_run: If True, prints proposed changes without modifying.
    """
    print("Updating lineage for properties with API-sourced acreage...")

    conn = sqlite3.connect(db_path)
    try:
        # Find properties with acreage but no source tracked
        df = pd.read_sql_query("""
            SELECT id, acreage, data_source
            FROM properties
            WHERE acreage IS NOT NULL
              AND acreage >= 0.01
              AND (acreage_source IS NULL OR acreage_source = '')
        """, conn)

        print(f"Found {len(df)} properties with acreage but no lineage data.")

        if not dry_run and len(df) > 0:
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE properties
                    SET acreage_source = 'api',
                        acreage_confidence = 'high'
                    WHERE acreage IS NOT NULL
                      AND acreage >= 0.01
                      AND (acreage_source IS NULL OR acreage_source = '')
                """)
                print(f"Updated {cursor.rowcount} properties with API source lineage.")
        elif dry_run:
            print("Dry run - would update these to acreage_source='api'")

    finally:
        conn.close()


if __name__ == '__main__':
    # --- Validation and Testing ---
    test_cases = {
        # Explicit acreage (high confidence)
        "LOT 1 BLOCK 1 2.53 AC": (2.53, 'parsed_explicit', 'high'),
        "some text with 1/2 acre lot": (0.5, 'parsed_explicit', 'high'),
        "HOUSE ON A 10A PARCEL": (10.0, 'parsed_explicit', 'high'),

        # PLSS aliquot (medium confidence)
        "NE 1/4 OF SEC 12": (160.0, 'parsed_plss', 'medium'),
        "NE 1/4 OF SE 1/4 SEC 30": (40.0, 'parsed_plss', 'medium'),
        "S 1/2 OF NE 1/4": (80.0, 'parsed_plss', 'medium'),
        "PT NE 1/4 SEC 5": (160.0, 'parsed_plss', 'low'),  # Has "PT" marker

        # Dimensions (low confidence)
        "A 50' X 100.5' LOT": (0.1154, 'parsed_dimensions', 'low'),
        "75x150 IRR": (0.2583, 'parsed_dimensions', 'low'),

        # No acreage extractable
        "LOT 25 FIVE MILE CREEK ROAD": (None, None, None),
        "BLK 19 PLAT A ISHKOODA SUB 35/59": (None, None, None),

        # Priority test: explicit beats PLSS
        "NE 1/4 SEC 12 2.5 ACRES": (2.5, 'parsed_explicit', 'high'),
    }

    print("--- Running Enhanced Test Cases ---")
    all_passed = True

    for desc, (expected_acres, expected_source, expected_conf) in test_cases.items():
        result = extract_acreage_with_lineage(desc)

        if result is None and expected_acres is None:
            status = "PASS"
        elif result is None or expected_acres is None:
            status = f"FAIL (Got: {result})"
            all_passed = False
        else:
            acres_match = abs(result.acreage - expected_acres) < 0.01
            source_match = result.source == expected_source
            conf_match = result.confidence == expected_conf

            if acres_match and source_match and conf_match:
                status = "PASS"
            else:
                status = f"FAIL (Got: {result.acreage:.2f}/{result.source}/{result.confidence})"
                all_passed = False

        print(f"'{desc[:45]:45}' -> {status}")

    print()

    # Test low-bid filter
    print("--- Testing Low-Bid Filter ---")
    filter_tests = [
        (100, None, "MINERAL RIGHTS ONLY", True, "Should filter mineral rights"),
        (100, 0.5, "LOT 1 BLK 2", False, "Has acreage, not junk"),
        (100, None, "COMMON AREA GREENBELT", True, "Should filter common area"),
        (200, None, "SOME PARCEL", False, "Above threshold, not filtered"),
        (50, None, "LOT 1 50x100", False, "Has dimensions, might be valid"),
    ]

    for amount, acreage, desc, expected_filter, note in filter_tests:
        should_filter, reason = should_filter_low_bid(amount, acreage, desc)
        status = "PASS" if should_filter == expected_filter else "FAIL"
        print(f"${amount} / {acreage or 'None':4} / '{desc[:25]:25}' -> filter={should_filter} ({status}) - {note}")

    if all_passed:
        print("\n[SUCCESS] All test cases passed!")
    else:
        print("\n[WARNING] Some test cases failed!")

    # --- Example Usage ---
    print("\n" + "="*70)
    print("Usage:")
    print("  # Dry run on Arkansas properties:")
    print("  python -c \"from scripts.acreage_processor import batch_update_acreage; batch_update_acreage('data/alabama_auction_watcher.db', dry_run=True, state_filter='AR')\"")
    print()
    print("  # Apply updates:")
    print("  python -c \"from scripts.acreage_processor import batch_update_acreage; batch_update_acreage('data/alabama_auction_watcher.db', dry_run=False, state_filter='AR')\"")
    print()
    print("  # Update lineage for existing API data:")
    print("  python -c \"from scripts.acreage_processor import update_existing_acreage_lineage; update_existing_acreage_lineage('data/alabama_auction_watcher.db', dry_run=False)\"")
    print("="*70)
