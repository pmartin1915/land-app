"""
Arkansas GIS Enricher - Batch enrichment of parcel acreage from Arkansas GIS API.

Queries the Arkansas GIS Office (AGIO) Planning_Cadastre FeatureServer to get
Shape__Area (square meters) for parcels, then converts to acreage.

API Endpoint: https://gis.arkansas.gov/arcgis/rest/services/FEATURESERVICES/Planning_Cadastre/FeatureServer/6

Usage:
    # Dry run (no database changes)
    python scripts/arkansas_gis_enricher.py --dry-run

    # Process all Arkansas properties missing acreage
    python scripts/arkansas_gis_enricher.py

    # Process specific county
    python scripts/arkansas_gis_enricher.py --county Phillips

    # Limit number of properties
    python scripts/arkansas_gis_enricher.py --limit 100
"""

import asyncio
import aiohttp
import argparse
import sqlite3
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

# Add project root for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.logging_config import get_logger
from core.scoring import calculate_buy_hold_score

logger = get_logger(__name__)

# Arkansas GIS API Configuration
GIS_BASE_URL = "https://gis.arkansas.gov/arcgis/rest/services/FEATURESERVICES/Planning_Cadastre/FeatureServer/6"
GIS_QUERY_ENDPOINT = f"{GIS_BASE_URL}/query"

# Conversion: 1 acre = 4046.8564224 square meters
SQ_METERS_PER_ACRE = 4046.8564224

# Rate limiting
BATCH_SIZE = 50  # Properties per batch
DELAY_BETWEEN_BATCHES = 1.0  # Seconds
MAX_CONCURRENT_REQUESTS = 5


@dataclass
class GISResult:
    """Result from GIS API query."""
    parcel_id: str
    county: str
    shape_area_sqm: float
    acreage: float
    owner_name: Optional[str] = None
    assessed_value: Optional[float] = None


@dataclass
class EnrichmentStats:
    """Statistics for enrichment run."""
    total_properties: int = 0
    properties_enriched: int = 0
    properties_not_found: int = 0
    properties_error: int = 0
    properties_multi_match: int = 0


class ArkansasGISEnricher:
    """
    Enriches Arkansas property data with acreage from the state GIS API.

    The AGIO Planning_Cadastre layer contains Shape__Area in square meters
    (projected in EPSG:26915 - UTM Zone 15N). We convert to acres.
    """

    def __init__(self, db_path: str, dry_run: bool = False):
        self.db_path = db_path
        self.dry_run = dry_run
        self._session: Optional[aiohttp.ClientSession] = None
        self.stats = EnrichmentStats()

    async def __aenter__(self):
        """Async context manager entry."""
        self._session = aiohttp.ClientSession(
            headers={
                'User-Agent': 'AlabamaAuctionWatcher/1.0 (Land Investment Research)',
                'Accept': 'application/json',
            },
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.close()

    def _normalize_county_name(self, county: str) -> str:
        """
        Normalize county name for GIS query.

        Database has: 'PHILLIPS', 'BAXTER'
        GIS has: 'Phillips', 'Baxter'
        """
        return county.strip().title()

    async def query_gis(self, parcel_id: str, county: str) -> Optional[GISResult]:
        """
        Query Arkansas GIS API for parcel data.

        Returns GISResult if found, None if not found.
        """
        if not self._session:
            raise RuntimeError("Session not initialized. Use async with context manager.")

        # Normalize county name
        county_normalized = self._normalize_county_name(county)

        # Build query - exact match on parcel_id and county
        where_clause = f"parcelid='{parcel_id}' AND county='{county_normalized}'"

        params = {
            'where': where_clause,
            'outFields': 'parcelid,county,ownername,assessvalue,Shape__Area',
            'returnGeometry': 'false',
            'f': 'json'
        }

        try:
            async with self._session.get(GIS_QUERY_ENDPOINT, params=params) as response:
                if response.status != 200:
                    logger.warning(f"GIS API error for {parcel_id}: HTTP {response.status}")
                    return None

                data = await response.json()

                features = data.get('features', [])

                if not features:
                    logger.debug(f"No GIS data found for {parcel_id} in {county_normalized}")
                    return None

                if len(features) > 1:
                    # Multiple matches - take the first one but log it
                    logger.warning(f"Multiple GIS matches ({len(features)}) for {parcel_id} in {county_normalized}, using first")
                    self.stats.properties_multi_match += 1

                attrs = features[0].get('attributes', {})
                shape_area = attrs.get('Shape__Area', 0)

                if not shape_area or shape_area <= 0:
                    logger.debug(f"No valid Shape__Area for {parcel_id}")
                    return None

                # Convert square meters to acres
                acreage = shape_area / SQ_METERS_PER_ACRE

                return GISResult(
                    parcel_id=parcel_id,
                    county=county,
                    shape_area_sqm=shape_area,
                    acreage=round(acreage, 4),
                    owner_name=attrs.get('ownername'),
                    assessed_value=attrs.get('assessvalue')
                )

        except aiohttp.ClientError as e:
            logger.error(f"Network error querying GIS for {parcel_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error querying GIS for {parcel_id}: {e}")
            return None

    def get_properties_missing_acreage(self, county_filter: Optional[str] = None,
                                        limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get Arkansas properties missing acreage from database.

        Returns list of dicts with id, parcel_id, county, amount.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = """
            SELECT id, parcel_id, county, amount, description
            FROM properties
            WHERE state = 'AR'
              AND (acreage IS NULL OR acreage = 0 OR acreage < 0.001)
        """
        params = []

        if county_filter:
            query += " AND UPPER(county) = UPPER(?)"
            params.append(county_filter)

        query += " ORDER BY county, parcel_id"

        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def update_property_acreage(self, property_id: str, gis_result: GISResult,
                                 bid_amount: float) -> bool:
        """
        Update property with GIS-derived acreage and recalculate scores.

        Returns True if successful.
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would update {property_id}: {gis_result.acreage:.4f} acres")
            return True

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Calculate price per acre
            price_per_acre = bid_amount / gis_result.acreage if gis_result.acreage > 0 else None

            # Get water score for scoring calculation
            cursor.execute("""
                SELECT water_score FROM properties WHERE id = ?
            """, (property_id,))
            row = cursor.fetchone()
            water_score = row[0] if row and row[0] else 0

            # Recalculate investment score with new acreage
            investment_score = calculate_buy_hold_score(
                state='AR',
                sale_type='tax_deed',
                amount=bid_amount,
                acreage=gis_result.acreage,
                water_score=water_score
            )

            # Update the property
            cursor.execute("""
                UPDATE properties
                SET acreage = ?,
                    price_per_acre = ?,
                    investment_score = ?,
                    acreage_source = 'gis',
                    acreage_confidence = 'high',
                    acreage_raw_text = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                gis_result.acreage,
                price_per_acre,
                investment_score,
                f"GIS Shape__Area: {gis_result.shape_area_sqm:.2f} sqm",
                property_id
            ))

            conn.commit()
            logger.info(f"Updated {property_id}: {gis_result.acreage:.4f} acres, score={investment_score:.1f}")
            return True

        except Exception as e:
            logger.error(f"Error updating {property_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    async def enrich_batch(self, properties: List[Dict[str, Any]]) -> int:
        """
        Enrich a batch of properties with GIS data.

        Returns count of successfully enriched properties.
        """
        enriched = 0

        # Create semaphore for rate limiting
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        async def process_property(prop: Dict[str, Any]) -> bool:
            async with semaphore:
                result = await self.query_gis(prop['parcel_id'], prop['county'])

                if result:
                    success = self.update_property_acreage(
                        prop['id'], result, prop['amount']
                    )
                    if success:
                        self.stats.properties_enriched += 1
                        return True
                    else:
                        self.stats.properties_error += 1
                else:
                    self.stats.properties_not_found += 1

                return False

        # Process all properties in batch concurrently
        tasks = [process_property(prop) for prop in properties]
        results = await asyncio.gather(*tasks)

        return sum(1 for r in results if r)

    async def run_enrichment(self, county_filter: Optional[str] = None,
                              limit: Optional[int] = None) -> EnrichmentStats:
        """
        Run the full enrichment process.

        Returns statistics about the run.
        """
        # Get properties to enrich
        properties = self.get_properties_missing_acreage(county_filter, limit)
        self.stats.total_properties = len(properties)

        if not properties:
            logger.info("No properties found to enrich")
            return self.stats

        logger.info(f"Found {len(properties)} Arkansas properties missing acreage")

        if county_filter:
            logger.info(f"Filtering to county: {county_filter}")

        # Process in batches
        for i in range(0, len(properties), BATCH_SIZE):
            batch = properties[i:i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (len(properties) + BATCH_SIZE - 1) // BATCH_SIZE

            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} properties)")

            enriched = await self.enrich_batch(batch)

            logger.info(f"Batch {batch_num} complete: {enriched} enriched")

            # Rate limiting between batches
            if i + BATCH_SIZE < len(properties):
                await asyncio.sleep(DELAY_BETWEEN_BATCHES)

        return self.stats


async def main():
    parser = argparse.ArgumentParser(
        description="Enrich Arkansas properties with acreage from state GIS API"
    )
    parser.add_argument(
        '--db',
        default='data/alabama_auction_watcher.db',
        help='Path to SQLite database'
    )
    parser.add_argument(
        '--county',
        help='Filter to specific county (e.g., Phillips, Baxter)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of properties to process'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )

    args = parser.parse_args()

    # Resolve database path
    db_path = Path(project_root) / args.db
    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("Arkansas GIS Enricher")
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")

    async with ArkansasGISEnricher(str(db_path), dry_run=args.dry_run) as enricher:
        stats = await enricher.run_enrichment(
            county_filter=args.county,
            limit=args.limit
        )

    # Print summary
    logger.info("=" * 60)
    logger.info("Enrichment Summary")
    logger.info("=" * 60)
    logger.info(f"Total properties processed: {stats.total_properties}")
    logger.info(f"Successfully enriched:      {stats.properties_enriched}")
    logger.info(f"Not found in GIS:           {stats.properties_not_found}")
    logger.info(f"Errors:                     {stats.properties_error}")
    logger.info(f"Multiple matches:           {stats.properties_multi_match}")

    if stats.total_properties > 0:
        success_rate = (stats.properties_enriched / stats.total_properties) * 100
        logger.info(f"Success rate:               {success_rate:.1f}%")


if __name__ == "__main__":
    asyncio.run(main())
