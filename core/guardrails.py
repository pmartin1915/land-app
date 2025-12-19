from .models import Parcel, BidDecision

# HARD RULES - The Co-Founders' Agreement
MAX_LTV = 0.60  # We never buy if debt is > 60% of value
MIN_VALUE = 5000.0 # We don't buy scraps of land worth $500
BANNED_TYPES = ["COMMON AREA", "ROAD", "RETENTION POND", "UNKNOWN"]

def evaluate_parcel(parcel: Parcel) -> BidDecision:
    """
    The Judge. Takes a validated Parcel object and issues a binding ruling.
    """
    
    # 1. Filter junk land
    if any(banned in parcel.property_type.upper() for banned in BANNED_TYPES):
        return BidDecision(
            parcel_id=parcel.parcel_id,
            should_bid=False,
            max_bid_amount=0.0,
            reason=f"Banned Property Type: {parcel.property_type}"
        )

    # 2. Financial Safety Check
    if parcel.ltv_ratio > MAX_LTV:
        return BidDecision(
            parcel_id=parcel.parcel_id,
            should_bid=False,
            max_bid_amount=0.0,
            reason=f"LTV too high: {parcel.ltv_ratio:.2f} > {MAX_LTV}"
        )
        
    if parcel.market_value_estimate < MIN_VALUE:
        return BidDecision(
            parcel_id=parcel.parcel_id,
            should_bid=False,
            max_bid_amount=0.0,
            reason=f"Value too low: ${parcel.market_value_estimate}"
        )

    # 3. Calculate Safe Bid (e.g., 70% of value minus existing liens)
    # This ensures we have equity margin.
    margin = 0.30 # 30% profit margin target
    safe_bid = (parcel.market_value_estimate * (1 - margin)) - parcel.total_encumbrance

    if safe_bid <= 0:
        return BidDecision(
            parcel_id=parcel.parcel_id,
            should_bid=False,
            max_bid_amount=0.0,
            reason="Negative Equity potential"
        )

    return BidDecision(
        parcel_id=parcel.parcel_id,
        should_bid=True,
        max_bid_amount=round(safe_bid, 2),
        reason="Passed all guardrails"
    )
