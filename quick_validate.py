"""Quick validation of fixes"""
import sqlite3
# import pandas as pd # Switched to manual iteration for clarity

conn = sqlite3.connect('alabama_auction_watcher.db')

print("="*60)
print("VALIDATION AFTER FIXES")
print("="*60)

# Get stats  
cursor = conn.cursor()
cursor.execute("""
    SELECT  
        COUNT(*) as total,
        SUM(CASE WHEN acreage = 0 THEN 1 ELSE 0 END) as zero_acres,
        SUM(CASE WHEN acreage > 0 AND acreage < 0.01 THEN 1 ELSE 0 END) as tiny_acres,
        SUM(CASE WHEN price_per_acre > 50000 THEN 1 ELSE 0 END) as expensive_ppa,
        SUM(CASE WHEN acreage IS NULL THEN 1 ELSE 0 END) as null_acres,
        MIN(CASE WHEN acreage > 0 THEN acreage ELSE NULL END) as min_acres,
        MAX(acreage) as max_acres,
        AVG(acreage) as avg_acres
    FROM properties
""")
result = cursor.fetchone()

total, zero, tiny, expensive, null_ac, min_ac, max_ac, avg_ac = result
invalid = zero + tiny + null_ac

print(f"\nProperty Statistics:")
print(f"  Total properties: {total}")
print(f"  Zero acreage: {zero} ({zero/total*100:.1f}%)")
print(f"  Tiny acreage (<0.01): {tiny} ({tiny/total*100:.1f}%)")
print(f"  Null acreage: {null_ac} ({null_ac/total*100:.1f}%)")
print(f"  Total invalid: {invalid} ({invalid/total*100:.1f}%)")
print(f"  Expensive per acre (>$50k): {expensive} ({expensive/total*100:.1f}%)")
print(f"\nAcreage range (valid): {min_ac or 0:.3f} to {max_ac or 0:.1f} (avg: {avg_ac or 0:.3f})")

# Check top 10 ranked
print(f"\n{'-'*60}")
print("TOP 50 RANKED PROPERTIES (After Fix):")
print(f"{'-'*60}")

cursor.execute("""
    SELECT parcel_id, county, amount, acreage, price_per_acre, investment_score, description
    FROM properties
    ORDER BY investment_score DESC
    LIMIT 50
""")
top_10_results = cursor.fetchall()

for idx, row in enumerate(top_10_results):
    parcel_id, county, amount, acreage, ppa, score, desc = row
    print(f"\n{idx+1}. {parcel_id} - Score: {score or 0:.1f}")
    print(f"   County: {county}, Amount: ${amount or 0:.2f}")
    print(f"   Acreage: {acreage or 0:.3f}, Price/acre: ${ppa or 0:.2f}")
    print(f"   Desc: {desc[:60] if desc else 'N/A'}...")

conn.close()

print(f"\n{'='*60}")
print("Validation Complete")
print(f"{'='*60}")
