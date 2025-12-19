from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime

class Lien(BaseModel):
    amount: float
    holder: str
    date_recorded: Optional[datetime] = None

class Parcel(BaseModel):
    parcel_id: str
    county: str
    assessed_value: float = Field(..., gt=0, description="Must be greater than 0")
    market_value_estimate: float
    # If Gemini scrapes a road or 'common area', we flag it here
    property_type: str 
    
    # Financials
    tax_due: float
    other_liens: List[Lien] = []

    def total_encumbrance(self) -> float:
        """Calculates total debt on property."""
        return self.tax_due + sum(lien.amount for lien in self.other_liens)

    def ltv_ratio(self) -> float:
        """Loan-to-Value ratio based on total debt vs market estimate."""
        if self.market_value_estimate == 0:
            return 999.0 # High risk
        return self.total_encumbrance / self.market_value_estimate

class BidDecision(BaseModel):
    parcel_id: str
    should_bid: bool
    max_bid_amount: float
    reason: str
    timestamp: datetime = Field(default_factory=datetime.now)
