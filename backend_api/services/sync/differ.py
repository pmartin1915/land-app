"""
Sync Differ for calculating deltas between client and server state.
Pure functions for determining changes to apply.
"""

import logging
from typing import List, Tuple
from datetime import datetime

from sqlalchemy.orm import Session

from ...database.models import Property
from ...models.sync import PropertyChange, SyncOperation, create_property_change

logger = logging.getLogger(__name__)


class SyncDiffer:
    """
    Calculates differences between client and server state.
    Pure logic for determining what needs to sync.
    """

    def __init__(self, db: Session):
        """
        Initialize SyncDiffer.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_server_changes(
        self,
        device_id: str,
        since_timestamp: datetime,
        limit: int = None
    ) -> List[PropertyChange]:
        """
        Get server changes since last sync, excluding device's own changes.

        Args:
            device_id: Device requesting changes (excluded from results)
            since_timestamp: Timestamp to get changes after
            limit: Maximum number of changes to return (for pagination)

        Returns:
            List of PropertyChange objects representing server changes
        """
        query = self.db.query(Property).filter(
            Property.updated_at > since_timestamp,
            Property.device_id != device_id  # Exclude changes from this device
        )

        if limit:
            query = query.limit(limit)

        server_properties = query.all()

        return [
            self._property_to_change(prop)
            for prop in server_properties
        ]

    def get_all_active_properties(
        self,
        include_deleted: bool = False
    ) -> Tuple[List[dict], List[int]]:
        """
        Get all properties for full sync.

        Args:
            include_deleted: Whether to include deleted property IDs

        Returns:
            Tuple of (active property dicts, deleted property IDs)
        """
        # Get active properties
        active_properties = self.db.query(Property).filter(
            Property.is_deleted == False
        ).all()
        all_properties = [prop.to_dict() for prop in active_properties]

        # Get deleted property IDs if requested
        deleted_ids = []
        if include_deleted:
            deleted_props = self.db.query(Property.id).filter(
                Property.is_deleted == True
            ).all()
            deleted_ids = [prop.id for prop in deleted_props]

        return all_properties, deleted_ids

    def get_pending_change_count(
        self,
        device_id: str,
        since_timestamp: datetime = None
    ) -> int:
        """
        Count pending changes for a device.

        Args:
            device_id: Device to check
            since_timestamp: Timestamp to check from (None = all changes)

        Returns:
            Count of pending changes
        """
        if since_timestamp:
            return self.db.query(Property).filter(
                Property.updated_at > since_timestamp,
                Property.device_id != device_id
            ).count()
        else:
            return self.db.query(Property).filter(
                Property.is_deleted == False
            ).count()

    def get_batch(
        self,
        start_from: int = None,
        batch_size: int = 100,
        include_calculations: bool = False,
        property_service=None
    ) -> Tuple[List[dict], int, bool]:
        """
        Get a batch of properties for paginated sync.

        Args:
            start_from: Property ID to start after
            batch_size: Number of properties per batch
            include_calculations: Whether to include calculated fields
            property_service: PropertyService for calculations

        Returns:
            Tuple of (batch_data, next_start_id, has_more_data)
        """
        # Build query for active properties
        query = self.db.query(Property).filter(Property.is_deleted == False)

        # Apply starting point if provided
        if start_from:
            query = query.filter(Property.id > start_from)

        # Order by ID for consistent pagination
        query = query.order_by(Property.id)

        # Get batch + 1 to check if more data exists
        properties = query.limit(batch_size + 1).all()

        # Determine if more data is available
        has_more = len(properties) > batch_size
        if has_more:
            properties = properties[:-1]  # Remove the extra item

        # Convert to dictionaries
        batch_data = []
        for prop in properties:
            prop_dict = prop.to_dict()

            # Include algorithm calculations if requested
            if include_calculations and property_service:
                if not prop_dict.get('investment_score'):
                    calculated = property_service.calculate_property_metrics(prop_dict)
                    prop_dict.update(calculated)

            batch_data.append(prop_dict)

        # Determine next batch start
        next_start = properties[-1].id if properties else None

        return batch_data, next_start, has_more

    def _property_to_change(self, prop: Property) -> PropertyChange:
        """
        Convert a Property to a PropertyChange.

        Args:
            prop: Property instance

        Returns:
            PropertyChange representing the property state
        """
        operation = SyncOperation.DELETE if prop.is_deleted else SyncOperation.UPDATE
        return create_property_change(
            prop.id,
            operation,
            prop.to_dict() if not prop.is_deleted else None,
            prop.device_id or "server"
        )
