"""
Value Objects for Auction Watcher domain.

Value Objects are immutable, identity-less objects that represent descriptive
aspects of the domain. They are defined by their attributes rather than by
a unique identifier.

Key characteristics:
- Immutable (frozen=True)
- Equality based on attributes, not identity
- Self-validating
- Side-effect free
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple


@dataclass(frozen=True, slots=True)
class InvestmentScore:
    """
    Value Object representing a property's investment score.

    Range: 0.0 to 100.0
    Higher scores indicate better investment opportunities.

    This is the core metric used to rank and prioritize properties
    in the Auction Watcher system.
    """
    value: float

    def __post_init__(self):
        """Validate investment score constraints."""
        if not isinstance(self.value, (int, float)):
            raise TypeError(f"InvestmentScore value must be numeric, got {type(self.value).__name__}")
        if self.value < 0.0:
            raise ValueError(f"InvestmentScore cannot be negative: {self.value}")
        if self.value > 100.0:
            raise ValueError(f"InvestmentScore cannot exceed 100.0: {self.value}")

    @classmethod
    def create(cls, value: float) -> "InvestmentScore":
        """
        Factory method to create an InvestmentScore.

        Args:
            value: The score value (0.0 - 100.0)

        Returns:
            InvestmentScore instance

        Raises:
            ValueError: If value is outside valid range
            TypeError: If value is not numeric
        """
        return cls(float(value))

    @classmethod
    def create_or_none(cls, value: Optional[float]) -> Optional["InvestmentScore"]:
        """
        Factory method that returns None if value is None.

        Args:
            value: The score value or None

        Returns:
            InvestmentScore instance or None
        """
        if value is None:
            return None
        return cls.create(value)

    @classmethod
    def zero(cls) -> "InvestmentScore":
        """Create a zero investment score."""
        return cls(0.0)

    @classmethod
    def maximum(cls) -> "InvestmentScore":
        """Create maximum investment score."""
        return cls(100.0)

    def is_high_value(self, threshold: float = 70.0) -> bool:
        """Check if this is a high-value investment score."""
        return self.value >= threshold

    def is_low_value(self, threshold: float = 30.0) -> bool:
        """Check if this is a low-value investment score."""
        return self.value <= threshold

    def to_percentage_string(self) -> str:
        """Format as percentage string."""
        return f"{self.value:.1f}%"

    def to_rating(self) -> str:
        """Convert score to letter rating."""
        if self.value >= 90:
            return "A+"
        elif self.value >= 80:
            return "A"
        elif self.value >= 70:
            return "B"
        elif self.value >= 60:
            return "C"
        elif self.value >= 50:
            return "D"
        else:
            return "F"

    def __str__(self) -> str:
        return f"{self.value:.2f}"

    def __repr__(self) -> str:
        return f"InvestmentScore({self.value})"

    def __float__(self) -> float:
        return self.value

    def __lt__(self, other: "InvestmentScore") -> bool:
        if isinstance(other, InvestmentScore):
            return self.value < other.value
        return NotImplemented

    def __le__(self, other: "InvestmentScore") -> bool:
        if isinstance(other, InvestmentScore):
            return self.value <= other.value
        return NotImplemented

    def __gt__(self, other: "InvestmentScore") -> bool:
        if isinstance(other, InvestmentScore):
            return self.value > other.value
        return NotImplemented

    def __ge__(self, other: "InvestmentScore") -> bool:
        if isinstance(other, InvestmentScore):
            return self.value >= other.value
        return NotImplemented


@dataclass(frozen=True, slots=True)
class WaterScore:
    """
    Value Object representing a property's water feature score.

    Range: 0.0 to 15.0 (can exceed 15.0 for exceptional properties)
    Higher scores indicate more/better water features.

    Water features include:
    - Creek, river, stream access
    - Lake frontage
    - Pond presence
    - Wetlands
    - Springs
    """
    value: float

    # Standard scoring thresholds
    NO_WATER: float = field(default=0.0, init=False, repr=False)
    MINIMAL_WATER: float = field(default=3.0, init=False, repr=False)
    MODERATE_WATER: float = field(default=7.0, init=False, repr=False)
    EXCELLENT_WATER: float = field(default=12.0, init=False, repr=False)
    EXCEPTIONAL_WATER: float = field(default=15.0, init=False, repr=False)

    def __post_init__(self):
        """Validate water score constraints."""
        if not isinstance(self.value, (int, float)):
            raise TypeError(f"WaterScore value must be numeric, got {type(self.value).__name__}")
        if self.value < 0.0:
            raise ValueError(f"WaterScore cannot be negative: {self.value}")
        # Note: WaterScore can exceed 15.0 for exceptional properties

    @classmethod
    def create(cls, value: float) -> "WaterScore":
        """
        Factory method to create a WaterScore.

        Args:
            value: The score value (>= 0.0)

        Returns:
            WaterScore instance

        Raises:
            ValueError: If value is negative
            TypeError: If value is not numeric
        """
        return cls(float(value))

    @classmethod
    def create_or_default(cls, value: Optional[float]) -> "WaterScore":
        """
        Factory method that returns zero score if value is None.

        Args:
            value: The score value or None

        Returns:
            WaterScore instance (defaults to 0.0)
        """
        if value is None:
            return cls.zero()
        return cls.create(value)

    @classmethod
    def zero(cls) -> "WaterScore":
        """Create a zero water score."""
        return cls(0.0)

    def has_water_features(self) -> bool:
        """Check if property has any water features."""
        return self.value > 0.0

    def get_water_category(self) -> str:
        """
        Categorize water feature quality.

        Returns:
            String category: "none", "minimal", "moderate", "excellent", "exceptional"
        """
        if self.value <= 0:
            return "none"
        elif self.value < 3.0:
            return "minimal"
        elif self.value < 7.0:
            return "moderate"
        elif self.value < 12.0:
            return "excellent"
        else:
            return "exceptional"

    def is_premium_water(self, threshold: float = 10.0) -> bool:
        """Check if this qualifies as premium water access."""
        return self.value >= threshold

    def to_display_string(self) -> str:
        """Format for display with category."""
        category = self.get_water_category()
        return f"{self.value:.1f} ({category})"

    def __str__(self) -> str:
        return f"{self.value:.2f}"

    def __repr__(self) -> str:
        return f"WaterScore({self.value})"

    def __float__(self) -> float:
        return self.value

    def __bool__(self) -> bool:
        """Water score is truthy if it has any water features."""
        return self.value > 0.0

    def __lt__(self, other: "WaterScore") -> bool:
        if isinstance(other, WaterScore):
            return self.value < other.value
        return NotImplemented

    def __le__(self, other: "WaterScore") -> bool:
        if isinstance(other, WaterScore):
            return self.value <= other.value
        return NotImplemented

    def __gt__(self, other: "WaterScore") -> bool:
        if isinstance(other, WaterScore):
            return self.value > other.value
        return NotImplemented

    def __ge__(self, other: "WaterScore") -> bool:
        if isinstance(other, WaterScore):
            return self.value >= other.value
        return NotImplemented


@dataclass(frozen=True, slots=True)
class PricePerAcre:
    """
    Value Object representing price per acre calculation.

    Range: > 0.0 (must be positive)
    Lower values indicate potentially better deals.
    """
    value: float

    def __post_init__(self):
        """Validate price per acre constraints."""
        if not isinstance(self.value, (int, float)):
            raise TypeError(f"PricePerAcre value must be numeric, got {type(self.value).__name__}")
        if self.value <= 0.0:
            raise ValueError(f"PricePerAcre must be positive: {self.value}")

    @classmethod
    def calculate(cls, amount: float, acreage: float) -> "PricePerAcre":
        """
        Calculate price per acre from amount and acreage.

        Args:
            amount: Total price in USD
            acreage: Property acreage

        Returns:
            PricePerAcre instance

        Raises:
            ValueError: If acreage is zero or negative
        """
        if acreage <= 0:
            raise ValueError(f"Cannot calculate price per acre with acreage: {acreage}")
        return cls(amount / acreage)

    @classmethod
    def calculate_or_none(
        cls, amount: Optional[float], acreage: Optional[float]
    ) -> Optional["PricePerAcre"]:
        """
        Calculate price per acre, returning None if inputs are invalid.

        Args:
            amount: Total price in USD or None
            acreage: Property acreage or None

        Returns:
            PricePerAcre instance or None
        """
        if amount is None or acreage is None or acreage <= 0:
            return None
        return cls.calculate(amount, acreage)

    def is_below_market(self, market_rate: float) -> bool:
        """Check if price per acre is below market rate."""
        return self.value < market_rate

    def to_currency_string(self) -> str:
        """Format as currency string."""
        return f"${self.value:,.2f}/acre"

    def __str__(self) -> str:
        return f"{self.value:.2f}"

    def __repr__(self) -> str:
        return f"PricePerAcre({self.value})"

    def __float__(self) -> float:
        return self.value


@dataclass(frozen=True, slots=True)
class AssessedValueRatio:
    """
    Value Object representing the ratio of bid amount to assessed value.

    Range: > 0.0
    Values < 1.0 indicate bid is below assessed value (potential opportunity).
    Values > 1.0 indicate bid exceeds assessed value.
    """
    value: float

    def __post_init__(self):
        """Validate ratio constraints."""
        if not isinstance(self.value, (int, float)):
            raise TypeError(f"AssessedValueRatio must be numeric, got {type(self.value).__name__}")
        if self.value <= 0.0:
            raise ValueError(f"AssessedValueRatio must be positive: {self.value}")

    @classmethod
    def calculate(cls, amount: float, assessed_value: float) -> "AssessedValueRatio":
        """
        Calculate ratio from amount and assessed value.

        Args:
            amount: Bid/sale amount in USD
            assessed_value: County assessed value

        Returns:
            AssessedValueRatio instance

        Raises:
            ValueError: If assessed_value is zero or negative
        """
        if assessed_value <= 0:
            raise ValueError(f"Cannot calculate ratio with assessed value: {assessed_value}")
        return cls(amount / assessed_value)

    @classmethod
    def calculate_or_none(
        cls, amount: Optional[float], assessed_value: Optional[float]
    ) -> Optional["AssessedValueRatio"]:
        """
        Calculate ratio, returning None if inputs are invalid.

        Args:
            amount: Bid/sale amount or None
            assessed_value: Assessed value or None

        Returns:
            AssessedValueRatio instance or None
        """
        if amount is None or assessed_value is None or assessed_value <= 0:
            return None
        return cls.calculate(amount, assessed_value)

    def is_undervalued(self, threshold: float = 0.5) -> bool:
        """Check if property appears undervalued (ratio below threshold)."""
        return self.value <= threshold

    def is_overvalued(self, threshold: float = 1.5) -> bool:
        """Check if property appears overvalued (ratio above threshold)."""
        return self.value >= threshold

    def to_percentage_string(self) -> str:
        """Format as percentage of assessed value."""
        return f"{self.value * 100:.1f}%"

    def __str__(self) -> str:
        return f"{self.value:.3f}"

    def __repr__(self) -> str:
        return f"AssessedValueRatio({self.value})"

    def __float__(self) -> float:
        return self.value
