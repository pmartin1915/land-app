import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime

# HARD RULES - The Co-Founders' Agreement
MAX_LTV = 0.60  # We never buy if debt is > 60% of value
MIN_VALUE = 5000.0 # We don't buy scraps of land worth $500
BANNED_TYPES = ["COMMON AREA", "ROAD", "RETENTION POND", "UNKNOWN"]
PROFIT_MARGIN = 0.30 # 30% profit margin target

def check_kill_switch():
    """
    Checks for a local file 'STOP' or an ENV variable 'KILL_SWITCH=TRUE'.
    If found, the process dies immediately.
    """
    if os.path.exists("STOP") or os.getenv("KILL_SWITCH") == "TRUE":
        print("!!! KILL SWITCH ACTIVATED. TERMINATING PROCESS !!!", file=sys.stderr)
        sys.exit(1)

def apply_decision_engine(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies the core business guardrails to a DataFrame of properties.
    This function operates in a vectorized way for performance.

    Args:
        df: A DataFrame that must contain the following columns:
            - 'parcel_id'
            - 'assessed_value'
            - 'amount' (can be used as a proxy for market_value if needed)
            - 'property_type' (or a 'description' to infer it from)
            - 'tax_due' (or a proxy for it)

    Returns:
        The original DataFrame with added decision columns:
            - 'should_bid' (bool)
            - 'max_bid_amount' (float)
            - 'bid_reason' (str)
    """
    print("Applying decision engine guardrails...")
    if df.empty:
        print("  DataFrame is empty, skipping.")
        return df

    # --- Create normalized columns for calculation ---
    # Ensure necessary columns exist, filling with safe defaults if they don't.
    if 'market_value_estimate' not in df.columns:
        # Use 'assessed_value' or 'amount' as a fallback for market value
        if 'assessed_value' in df.columns:
             df['market_value_estimate'] = df['assessed_value'] * 1.2 # A simple heuristic
        elif 'amount' in df.columns:
            df['market_value_estimate'] = df['amount']
        else:
            df['market_value_estimate'] = 0

    if 'tax_due' not in df.columns:
        df['tax_due'] = 0 # Assume no taxes due if not specified
        
    if 'other_liens_total' not in df.columns:
        df['other_liens_total'] = 0 # Assume no other liens

    if 'property_type' not in df.columns:
        # A simple heuristic to infer property type from description
        if 'description' in df.columns:
            df['property_type'] = df['description'].str.upper().apply(
                lambda x: 'ROAD' if 'ROAD' in str(x) else 'PARCEL'
            )
        else:
            df['property_type'] = 'UNKNOWN'

    # --- Vectorized Calculations ---
    
    # 1. Calculate Total Encumbrance and LTV
    df['total_encumbrance'] = df['tax_due'] + df['other_liens_total']
    
    # Use np.divide for safe division
    df['ltv_ratio'] = np.divide(
        df['total_encumbrance'], 
        df['market_value_estimate'], 
        out=np.full_like(df['total_encumbrance'], 999.0), # Default to high risk
        where=df['market_value_estimate']!=0
    )

    # 2. Calculate Maximum Safe Bid
    df['max_bid_amount'] = (df['market_value_estimate'] * (1 - PROFIT_MARGIN)) - df['total_encumbrance']
    df['max_bid_amount'] = df['max_bid_amount'].round(2)
    df.loc[df['max_bid_amount'] < 0, 'max_bid_amount'] = 0


    # --- Decision Logic using np.select ---
    
    conditions = [
        df['property_type'].str.upper().isin(BANNED_TYPES),
        df['ltv_ratio'] > MAX_LTV,
        df['market_value_estimate'] < MIN_VALUE,
        df['max_bid_amount'] <= 0
    ]

    choices = [
        f"Banned Property Type",
        f"LTV too high (>{MAX_LTV:.0%})",
        f"Market value too low (<${MIN_VALUE:,.0f})",
        "Negative Equity Potential"
    ]

    # `default` is the success case
    df['bid_reason'] = np.select(conditions, choices, default='Passed all guardrails')
    df['should_bid'] = (df['bid_reason'] == 'Passed all guardrails')

    # Final cleanup
    df.loc[~df['should_bid'], 'max_bid_amount'] = 0

    # --- Report Results ---
    passed_count = df['should_bid'].sum()
    rejected_count = len(df) - passed_count
    
    print(f"  {passed_count} properties passed guardrails.")
    print(f"  {rejected_count} properties rejected.")
    if rejected_count > 0:
        print("  Rejection reasons:")
        print(df[~df['should_bid']]['bid_reason'].value_counts().to_string())
        
    return df
