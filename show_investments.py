#!/usr/bin/env python
"""Display top investment properties under $10k with water access."""

import requests
import sys

def main():
    # Get a fresh token
    token_resp = requests.post(
        'http://localhost:8001/api/v1/auth/device/token',
        json={
            'device_id': 'investment-viewer-12345',
            'app_version': '1.0.0',
            'device_name': 'Investment Viewer'
        }
    )
    token = token_resp.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    # Query parameters
    max_price = 10000
    min_acres = 1.0
    min_water = 3

    if len(sys.argv) > 1:
        max_price = float(sys.argv[1])
    if len(sys.argv) > 2:
        min_acres = float(sys.argv[2])
    if len(sys.argv) > 3:
        min_water = float(sys.argv[3])

    resp = requests.get(
        'http://localhost:8001/api/v1/properties/',
        params={
            'page': 1,
            'page_size': 20,
            'sort_by': 'investment_score',
            'sort_order': 'desc',
            'max_price': max_price,
            'min_acreage': min_acres,
            'min_water_score': min_water
        },
        headers=headers
    )
    data = resp.json()

    print()
    print(f"BEST INVESTMENTS: Under ${max_price:,.0f} | {min_acres}+ Acres | Water >= {min_water}")
    print("=" * 90)
    print(f"Total matching: {data['total_count']} properties")
    print()

    for i, p in enumerate(data['properties'][:20], 1):
        desc = (p.get('description') or '')[:50]
        amt = p.get('amount') or 0
        est = p.get('estimated_all_in_cost') or amt * 1.1
        acres = p.get('acreage') or 0
        ppa = p.get('price_per_acre') or 0
        score = p.get('investment_score') or 0
        water = p.get('water_score') or 0
        county = (p.get('county') or '')[:12]
        year = p.get('year_sold') or '?'
        parcel = p.get('parcel_id') or ''

        print(f"{i:2}. {county} County - {acres:.1f} acres")
        print(f"    Bid: ${amt:,.0f} | Est Total: ${est:,.0f} | $/Acre: ${ppa:,.0f}")
        print(f"    Scores: Investment={score:.0f}, Water={water:.0f} | Sale Year: {year}")
        print(f"    {desc}")
        print(f"    Parcel: {parcel}")
        print()

if __name__ == '__main__':
    main()
