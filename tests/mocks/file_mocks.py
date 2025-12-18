"""
File system mocking utilities for isolating file operations in tests.

This module provides a mock file system that operates entirely in memory,
preventing tests from reading from or writing to the actual disk. It is
particularly useful for testing components that handle file I/O, such as
CSV generation or report writing.
"""
from __future__ import annotations

import io
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Generator, Set
from unittest.mock import patch

import pandas as pd


class MockFileSystem:
    """An in-memory mock of a file system."""

    def __init__(self):
        """Initializes the in-memory file system."""
        self.files: Dict[str, str] = {}
        self.directories: Set[str] = set()

    def write_csv(self, path: str | Path, dataframe: pd.DataFrame) -> None:
        """
        Simulates writing a pandas DataFrame to a CSV file in memory.

        Args:
            path: The file path to write to.
            dataframe: The pandas DataFrame to serialize.
        """
        path_str = str(path).replace('\\', '/')
        self._ensure_parent_dir_exists(path_str)
        with io.StringIO() as buffer:
            # Use pandas' original to_csv without triggering patches
            pd.DataFrame.to_csv(dataframe, buffer, index=False)
            self.files[path_str] = buffer.getvalue()

    def read_csv(self, path: str | Path) -> pd.DataFrame:
        """
        Simulates reading a CSV file from memory into a pandas DataFrame.

        Args:
            path: The file path to read from.

        Returns:
            The deserialized pandas DataFrame.

        Raises:
            FileNotFoundError: If the path does not exist in the mock file system.
        """
        path_str = str(path).replace('\\', '/')
        if path_str not in self.files:
            raise FileNotFoundError(f"Mock file not found: {path_str}")
        content = self.files[path_str]
        with io.StringIO(content) as buffer:
            return pd.read_csv(buffer)

    def exists(self, path: str | Path) -> bool:
        """
        Checks if a file or directory exists in the mock file system.

        Args:
            path: The path to check.

        Returns:
            True if the path exists, False otherwise.
        """
        path_str = str(path).replace('\\', '/')
        return path_str in self.files or path_str in self.directories

    def mkdir(self, path: str | Path, parents: bool = False, exist_ok: bool = False) -> None:
        """
        Simulates creating a directory.

        Args:
            path: The directory path to create.
            parents: If True, create parent directories as needed.
            exist_ok: If False, FileExistsError is raised if the target
                      directory already exists.
        """
        path_str = str(path).replace('\\', '/')
        if self.exists(path_str) and not exist_ok:
            raise FileExistsError(f"Mock directory already exists: {path_str}")

        if parents:
            parts = path_str.split('/')
            for i in range(1, len(parts)):
                parent = '/'.join(parts[:i])
                if parent and parent != '.':
                    self.directories.add(parent)

        self.directories.add(path_str)

    def _ensure_parent_dir_exists(self, path_str: str) -> None:
        """Ensures the parent directory for a file path exists."""
        # path_str is already normalized with forward slashes
        parts = path_str.split('/')
        if len(parts) > 1:
            # Add all parent directories
            for i in range(1, len(parts)):
                parent = '/'.join(parts[:i])
                if parent:
                    self.directories.add(parent)


@contextmanager
def mock_file_operations() -> Generator[MockFileSystem, None, None]:
    """
    A context manager to patch file system operations.

    This manager patches `pandas.read_csv`, `pandas.DataFrame.to_csv`,
    `os.path.exists`, and `os.makedirs` to use a `MockFileSystem` instance.

    Yields:
        A MockFileSystem instance.
    """
    fs = MockFileSystem()

    # Store original methods to avoid recursion
    original_to_csv = pd.DataFrame.to_csv
    original_read_csv = pd.read_csv

    def mock_to_csv(self, path, **kwargs):
        # self is the DataFrame instance
        path_str = str(path).replace('\\', '/')
        fs._ensure_parent_dir_exists(path_str)
        with io.StringIO() as buffer:
            original_to_csv(self, buffer, index=False)
            fs.files[path_str] = buffer.getvalue()

    def mock_read_csv(path, **kwargs):
        path_str = str(path).replace('\\', '/')
        if path_str not in fs.files:
            raise FileNotFoundError(f"Mock file not found: {path_str}")
        content = fs.files[path_str]
        with io.StringIO(content) as buffer:
            return original_read_csv(buffer)

    def mock_exists(path):
        return fs.exists(str(path))

    def mock_makedirs(path, exist_ok=False):
        fs.mkdir(str(path), parents=True, exist_ok=exist_ok)

    with patch("pandas.DataFrame.to_csv", new=mock_to_csv), \
         patch("pandas.read_csv", new=mock_read_csv), \
         patch("os.path.exists", new=mock_exists), \
         patch("os.makedirs", new=mock_makedirs):
        yield fs
