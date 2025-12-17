# water_feature_processor.py

import re
import pandas as pd
import sqlite3
from typing import List, Dict, Tuple, Any

# Define the keyword tiers and scores
# Using a nested dictionary for clarity and easy access to metadata
WATER_FEATURE_KEYWORDS = {
    "premium": {
        "score": 10,
        "keywords": [
            "lakefront", "waterfront", "river frontage", "beachfront",
            "oceanfront", "bay front"
        ],
    },
    "high": {
        "score": 7,
        "keywords": ["lake", "river", "large creek", "canal with access", "marina"],
    },
    "medium": {
        "score": 4,
        "keywords": ["creek", "stream", "pond", "bayou", "inlet"],
    },
    "low": {
        "score": 2,
        "keywords": ["water view", "near water", "seasonal creek", "drainage"],
    },
}

def detect_and_score_water_features(
    description: str
) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Detects water features in a text description and calculates a composite score.

    The scoring algorithm is:
    - Score of the highest-value feature found.
    - Plus a 10% bonus of the score of each additional, unique feature.
      This rewards variety without over-inflating the score.

    Args:
        description: The property description text.

    Returns:
        A tuple containing:
        - The calculated composite water score (float).
        - A list of dictionaries, one for each unique feature found.
    """
    if not isinstance(description, str) or not description:
        return 0.0, []

    # Use a set to store found keywords to avoid duplicate counting
    found_features = set()
    description_lower = description.lower()

    for tier, details in WATER_FEATURE_KEYWORDS.items():
        for keyword in details["keywords"]:
            # Use regex with word boundaries to avoid partial matches (e.g., 'creek' in 'screech')
            if re.search(r"\b" + re.escape(keyword) + r"\b", description_lower):
                found_features.add(keyword)

    if not found_features:
        return 0.0, []

    # Map found keywords back to their full feature details
    detected_features_details = []
    for tier, details in WATER_FEATURE_KEYWORDS.items():
        for keyword in details["keywords"]:
            if keyword in found_features:
                detected_features_details.append({
                    "feature_name": keyword,
                    "feature_tier": tier,
                    "score": details["score"]
                })

    # Sort by score descending to easily find the max score
    detected_features_details.sort(key=lambda x: x["score"], reverse=True)

    # Calculate composite score
    highest_score = detected_features_details[0]["score"]
    bonus_score = sum(
        0.1 * feature["score"] for feature in detected_features_details[1:]
    )
    composite_score = float(highest_score + bonus_score)

    return composite_score, detected_features_details


def batch_update_properties(db_path: str):
    """
    Reads all properties, processes their descriptions for water features,
    and updates the database with the new scores and feature details.
    """
    conn = sqlite3.connect(db_path)
    # Read all properties for initial backfill
    df = pd.read_sql_query(
        "SELECT id, description FROM properties",
        conn
    )

    print(f"Found {len(df)} properties to process for water features.")

    properties_to_update = []
    features_to_insert = []

    for _, row in df.iterrows():
        property_id = row["id"]
        description = row["description"]

        score, features = detect_and_score_water_features(description)

        if score > 0:
            properties_to_update.append({"id": property_id, "water_score": score})
            for feature in features:
                features_to_insert.append({
                    "property_id": property_id,
                    "feature_name": feature["feature_name"],
                    "feature_tier": feature["feature_tier"],
                    "score": feature["score"],
                })

    if not properties_to_update:
        print("No water features found. Database is up to date.")
        conn.close()
        return

    print(f"\nFound water features in {len(properties_to_update)} properties:")
    print(f"  - Properties with water: {len(properties_to_update)}")
    print(f"  - Total feature instances: {len(features_to_insert)}")

    # Use transactions for atomicity and performance
    with conn:
        cursor = conn.cursor()

        # 1. Clear old feature data for the properties being updated
        # This prevents duplication if the script is run multiple times
        property_ids_to_clear = tuple(p['id'] for p in properties_to_update)
        cursor.execute(
            f"DELETE FROM property_water_features WHERE property_id IN ({','.join('?' for _ in property_ids_to_clear)})",
            property_ids_to_clear
        )

        # 2. Update properties table with new water_score
        cursor.executemany(
            "UPDATE properties SET water_score = :water_score WHERE id = :id",
            properties_to_update
        )
        print(f"\nUpdated water_score for {len(properties_to_update)} properties.")

        # 3. Insert new feature details into property_water_features
        cursor.executemany(
            """
            INSERT INTO property_water_features (property_id, feature_name, feature_tier, score)
            VALUES (:property_id, :feature_name, :feature_tier, :score)
            """,
            features_to_insert
        )
        print(f"Inserted {len(features_to_insert)} water feature records.")

    conn.close()
    print("\nBatch update complete!")


def calculate_investment_boost(water_score: float) -> float:
    """
    Calculates an investment score multiplier based on the water score.

    - No water features (score=0): 0% boost (1.0x multiplier)
    - Max possible score (e.g., 15): 25% boost (1.25x multiplier)
    - Min water score (e.g., 2): 15% boost (1.15x multiplier)
    """
    if water_score <= 0:
        return 1.0  # No boost

    # Define the range of scores and boosts
    min_score = 2.0
    # A theoretical max score could be a premium feature + bonuses from all other tiers
    max_score_cap = 15.0

    min_boost = 0.15
    max_boost = 0.25

    # Normalize the score to a 0-1 range
    if water_score >= max_score_cap:
        normalized_score = 1.0
    elif water_score < min_score:
        normalized_score = 0.0
    else:
        normalized_score = (water_score - min_score) / (max_score_cap - min_score)

    # Calculate boost and return the multiplier
    boost = min_boost + normalized_score * (max_boost - min_boost)
    return 1.0 + boost


if __name__ == '__main__':
    # Example Usage:
    DATABASE_FILE = 'alabama_auction_watcher.db'

    print("=== Water Feature Detection Test Cases ===\n")

    # --- Test cases to validate the logic ---
    desc1 = "Vacant lot with creek running through property, 2.3 acres"
    score1, features1 = detect_and_score_water_features(desc1)
    print(f"Description: '{desc1}'")
    print(f"Score: {score1}, Features: {features1}\n")

    desc2 = "Waterfront property on Mobile Bay with a small pond"
    score2, features2 = detect_and_score_water_features(desc2)
    print(f"Description: '{desc2}'")
    print(f"Score: {score2}, Features: {features2}\n")

    desc3 = "Residential parcel near water access"
    score3, features3 = detect_and_score_water_features(desc3)
    print(f"Description: '{desc3}'")
    print(f"Score: {score3}, Features: {features3}\n")

    desc4 = "Beautiful lakefront property with creek frontage"
    score4, features4 = detect_and_score_water_features(desc4)
    print(f"Description: '{desc4}'")
    print(f"Score: {score4}, Features: {features4}\n")

    print("\n=== Investment Boost Calculation Examples ===\n")

    for test_score in [0, 2, 5, 10, 15]:
        boost = calculate_investment_boost(test_score)
        print(f"Water Score: {test_score:>2} -> Boost Multiplier: {boost:.2f}x ({(boost-1)*100:.0f}% increase)")

    print("\n" + "="*60)
    print("To run batch update on database:")
    print(f"  python -c \"from water_feature_processor import batch_update_properties; batch_update_properties('{DATABASE_FILE}')\"")
    print("="*60)
