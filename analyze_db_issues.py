"""
Analyze database for scoring and acreage miscalculations
"""
import sqlite3
import pandas as pd

# Connect to database
conn = sqlite3.connect('alabama_auction_watcher.db')

print("="*80)
print("DATABASE ANALYSIS: Property Scoring Issues")
print("="*80)

# Overall statistics
query1 = """
SELECT 
    COUNT(*) as total_properties,
    COUNT(CASE WHEN acreage < 0.01 THEN 1 END) as tiny_acreage,
    COUNT(CASE WHEN acreage > 100 THEN 1 END) as huge_acreage,
    COUNT(CASE WHEN price_per_acre > 50000 THEN 1 END) as expensive_per_acre,
    COUNT(CASE WHEN price_per_acre > 1000000 THEN 1 END) as extreme_per_acre,
    MIN(acreage) as min_acreage,
    MAX(acreage) as max_acreage,
    AVG(acreage) as avg_acreage,
    MIN(price_per_acre) as min_ppa,
    MAX(price_per_acre) as max_ppa,
    AVG(price_per_acre) as avg_ppa
FROM properties
"""
df_stats = pd.read_sql_query(query1, conn)
print("\n1. OVERALL STATISTICS:")
print(df_stats.to_string(index=False))

# Properties with tiny acreage (likely calculation errors)
query2 = """
SELECT parcel_id, county, amount, acreage, price_per_acre, description
FROM properties
WHERE acreage < 0.01
ORDER BY price_per_acre DESC
LIMIT 20
"""
df_tiny = pd.read_sql_query(query2, conn)
print(f"\n2. PROPERTIES WITH TINY ACREAGE (<0.01 acres) - {len(df_tiny)} found:")
if len(df_tiny) > 0:
    pd.set_option('display.max_colwidth', 70)
    print(df_tiny.to_string(index=False))
else:
    print("   None found!")

# Properties with expensive price per acre (likely calculation errors)
query3 = """
SELECT parcel_id, county, amount, acreage, price_per_acre, description
FROM properties  
WHERE price_per_acre > 50000
ORDER BY price_per_acre DESC
LIMIT 20
"""
df_expensive = pd.read_sql_query(query3, conn)
print(f"\n3. PROPERTIES WITH EXTREME PRICE PER ACRE (>$50k/acre) - {len(df_expensive)} found:")
if len(df_expensive) > 0:
    print(df_expensive.to_string(index=False))
else:
    print("   None found!")

# Top ranked properties (to see if they're actually good or just miscalculated)
query4 = """
SELECT parcel_id, county, amount, acreage, price_per_acre, investment_score, water_score, description
FROM properties
ORDER BY investment_score DESC
LIMIT 15
"""
df_top = pd.read_sql_query(query4, conn)
print("\n4. TOP 15 RANKED PROPERTIES (by investment_score):")
print(df_top.to_string(index=False))

# Properties with huge acreage (might be miscalculated from dimensions)  
query5 = """
SELECT parcel_id, county, amount, acreage, price_per_acre, description
FROM properties
WHERE acreage > 50
ORDER BY acreage DESC
LIMIT 15
"""
df_huge = pd.read_sql_query(query5, conn)
print(f"\n5. PROPERTIES WITH HUGE ACREAGE (>50 acres) - {len(df_huge)} found:")
if len(df_huge) > 0:
    print(df_huge.to_string(index=False))

# Check for patterns in descriptions with likely dimension misinterpretation
query6 = """
SELECT description, acreage, amount, price_per_acre
FROM properties
WHERE description LIKE '%X%'
AND (acreage > 50 OR acreage < 0.01 OR price_per_acre > 50000)
LIMIT 20
"""
df_dimensions = pd.read_sql_query(query6, conn)
print(f"\n6. PROPERTIES WITH DIMENSION PATTERNS (X) AND SUSPECT VALUES - {len(df_dimensions)} found:")
if len(df_dimensions) > 0:
    pd.set_option('display.max_colwidth', 80)
    print(df_dimensions.to_string(index=False))

conn.close()

print("\n" + "="*80)
print("Analysis complete!")
print("="*80)
