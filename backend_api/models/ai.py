"""
AI Triage Models for Investment Priority Suggestions
Pydantic models for the /api/v1/ai/triage endpoint.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
from uuid import UUID


class AISuggestionResponse(BaseModel):
    """
    AI suggestion response matching frontend AISuggestion interface.

    For investment priority triage, we adapt this interface:
    - field: "investment_priority" (virtual field indicating this is a recommendation)
    - proposed_value: Triage tier name
    - confidence: Based on investment_score with modifiers
    - reason: Human-readable explanation
    """
    id: UUID = Field(..., description="Unique suggestion ID")
    parcel_id: UUID = Field(..., description="Property parcel ID (UUID)")
    field: str = Field(
        default="investment_priority",
        description="Virtual field name - always 'investment_priority' for triage"
    )
    proposed_value: str = Field(
        ...,
        description="Triage tier: 'Tier 1: Elite', 'Tier 2: Waterfront', 'Tier 2: Deep Value'"
    )
    confidence: float = Field(
        ...,
        ge=0,
        le=100,
        description="Confidence score 0-100 based on investment_score with modifiers"
    )
    reason: Optional[str] = Field(
        None,
        description="Human-readable explanation of why this property is recommended"
    )
    source_ids: List[UUID] = Field(
        default_factory=list,
        description="Source property IDs (self-referential for investment triage)"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when suggestion was generated"
    )
    applied_by: Optional[str] = Field(
        None,
        description="User ID who applied this suggestion (if applicable)"
    )
    applied_at: Optional[datetime] = Field(
        None,
        description="Timestamp when suggestion was applied (if applicable)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "parcel_id": "550e8400-e29b-41d4-a716-446655440001",
                "field": "investment_priority",
                "proposed_value": "Tier 1: Elite",
                "confidence": 92.5,
                "reason": "Score 92.5/100. High investment score with water features. Located in Baldwin County with strong market timing.",
                "source_ids": ["550e8400-e29b-41d4-a716-446655440001"],
                "created_at": "2025-12-26T10:30:00Z",
                "applied_by": None,
                "applied_at": None
            }
        }


class TriageQueueResponse(BaseModel):
    """Response wrapper for triage queue with metadata."""
    suggestions: List[AISuggestionResponse] = Field(
        ...,
        description="List of investment priority suggestions"
    )
    total_count: int = Field(..., description="Total number of suggestions")
    tiers: dict = Field(
        default_factory=dict,
        description="Count of suggestions by tier"
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when queue was generated"
    )
    processing_time_seconds: float = Field(
        ...,
        description="Time taken to generate suggestions"
    )
