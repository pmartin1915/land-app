# Transaction Management Patterns

## The "Services Never Commit" Pattern

### Overview

In this codebase, **service layer methods should not commit transactions**. Transaction control is delegated to the caller (routers, orchestrators, or test fixtures).

### Why This Matters

1. **Composability**: Multiple service calls can be wrapped in a single transaction
2. **Testability**: Tests can roll back changes without special handling
3. **Atomicity**: Complex operations succeed or fail as a unit
4. **Cache Consistency**: The caller can invalidate caches after commit

### Current Implementation

The sync orchestrator demonstrates this pattern:

```python
# backend_api/services/sync/orchestrator.py

def process_delta_sync(self, request: DeltaSyncRequest):
    # Service methods called with auto_commit=False
    self.property_service.update_property(..., auto_commit=False)

    # Orchestrator controls the commit
    self.db.commit()

    # Caller handles cache invalidation after commit
    self._invalidate_sync_caches(affected_ids)
```

### Service Method Contract

Service methods should:
- Accept an `auto_commit` parameter (default `True` for backwards compatibility)
- Use `self.db.flush()` to get IDs without committing
- Only commit when `auto_commit=True`

```python
def update_property(self, property_id: str, data: PropertyUpdate,
                    device_id: str, auto_commit: bool = True):
    # ... perform update ...

    if auto_commit:
        self.db.commit()
        self._invalidate_property_caches(property_obj.county, property_obj.id)
    else:
        self.db.flush()  # Get IDs without committing
```

### When Callers Should Commit

| Context | Who Commits | Cache Invalidation |
|---------|-------------|-------------------|
| Single API endpoint | Service (auto_commit=True) | Service handles it |
| Sync orchestrator | Orchestrator | Orchestrator handles it |
| Batch operations | Orchestrator/Router | Caller handles it |
| Tests | Rollback (no commit) | Not needed |

### Related: Cache Invalidation

When `auto_commit=False`, caches are NOT automatically invalidated.

The caller MUST explicitly invalidate caches after committing:

```python
# After orchestrator commits
self.db.commit()
self._invalidate_sync_caches(affected_property_ids)
```

See `orchestrator.py:_invalidate_sync_caches()` for the implementation.

### Migration Path

To adopt this pattern in existing services:

1. Add `auto_commit: bool = True` parameter to methods that commit
2. Wrap `db.commit()` calls in `if auto_commit:`
3. Move cache invalidation to after the commit check
4. Update callers that need transaction control to pass `auto_commit=False`

### Files Implementing This Pattern

- `backend_api/services/property_service.py` - Uses auto_commit parameter
- `backend_api/services/sync/orchestrator.py` - Manages transaction boundary
- `backend_api/services/sync/conflict_resolver.py` - Commits for conflict resolution
