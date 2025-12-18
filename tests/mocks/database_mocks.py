"""
Database mocking utilities for SQLAlchemy async sessions.

This module provides mock objects that simulate the behavior of an asynchronous
SQLAlchemy session, allowing database interactions to be tested without a live
database connection. It supports tracking executed queries, managing transaction
states (commit/rollback), and returning predefined results.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional, Sequence, Union

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ClauseElement


class MockScalars:
    """Mocks the behavior of the SQLAlchemy `scalars` result object."""

    def __init__(self, results: Sequence[Any]):
        """
        Initializes the MockScalars object with a sequence of results.

        Args:
            results: A sequence of data rows to be returned.
        """
        self._results = results
        self._index = 0

    def all(self) -> List[Any]:
        """
        Returns all results as a list.

        Returns:
            A list containing all result rows.
        """
        return list(self._results)

    def __iter__(self):
        return self

    def __next__(self):
        if self._index < len(self._results):
            result = self._results[self._index]
            self._index += 1
            return result
        raise StopIteration


class MockResult:
    """Mocks the SQLAlchemy `Result` object returned by `session.execute()`."""

    def __init__(self, results: Sequence[Any]):
        """
        Initializes the MockResult object.

        Args:
            results: A sequence of data to be wrapped by the mock result.
        """
        self._results = results

    def scalars(self) -> MockScalars:
        """
        Mocks the `scalars()` method, returning an iterable scalar result.

        Returns:
            A MockScalars instance.
        """
        return MockScalars(self._results)

    def all(self) -> List[Any]:
        """
        Returns all results as a list of tuples/rows.

        Returns:
            A list of all results.
        """
        return list(self._results)


class MockAsyncSession:
    """
    A mock for `sqlalchemy.ext.asyncio.AsyncSession`.

    This class simulates the core async methods of an SQLAlchemy session,
    tracking executed queries and transaction state for test assertions.
    """

    def __init__(self):
        """Initializes the mock session."""
        self.executed_queries: List[str] = []
        self.committed: bool = False
        self.rolled_back: bool = False
        self.closed: bool = False
        self._results_map: Dict[str, Any] = {}

    def prime_result(self, statement: Union[str, ClauseElement], result: Sequence[Any]) -> None:
        """
        Primes the mock session to return a specific result for a given query.

        Args:
            statement: The SQLAlchemy statement or its string representation.
            result: The list of results to return when the statement is executed.
        """
        query_str = self._normalize_statement(statement)
        self._results_map[query_str] = result

    async def execute(self, statement: ClauseElement, params: Optional[Dict[str, Any]] = None) -> MockResult:
        """
        Simulates executing a query.

        Args:
            statement: The SQLAlchemy statement to execute.
            params: Optional query parameters.

        Returns:
            A MockResult instance containing the primed result for the query.
        """
        query_str = self._normalize_statement(statement)
        self.executed_queries.append(query_str)
        await asyncio.sleep(0)  # Simulate async behavior
        results = self._results_map.get(query_str, [])
        return MockResult(results)

    async def commit(self) -> None:
        """Simulates committing a transaction."""
        self.committed = True
        await asyncio.sleep(0)

    async def rollback(self) -> None:
        """Simulates rolling back a transaction."""
        self.rolled_back = True
        await asyncio.sleep(0)

    async def close(self) -> None:
        """Simulates closing the session."""
        self.closed = True
        await asyncio.sleep(0)

    def _normalize_statement(self, statement: Union[str, ClauseElement]) -> str:
        """Converts a statement to a comparable string representation."""
        if isinstance(statement, str):
            return statement.strip()
        # In a real scenario, you might compile the statement for better accuracy
        # str() is a simplification for mock testing purposes.
        return str(statement).strip().replace("\n", "")


@asynccontextmanager
async def mock_database_transaction() -> AsyncGenerator[MockAsyncSession, None]:
    """
    A context manager that provides a mock `AsyncSession` and ensures
    a rollback is simulated upon exit.

    This is useful for tests that should not commit any data.

    Yields:
        A MockAsyncSession instance.
    """
    session = MockAsyncSession()
    try:
        yield session
    finally:
        if not session.committed:
            await session.rollback()
