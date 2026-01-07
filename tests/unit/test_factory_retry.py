"""
Unit tests for ScraperFactory subprocess retry logic.

Tests the exponential backoff retry mechanism for subprocess-based scrapers
(Alabama, Texas) including:
- Success on first attempt
- Retry on transient errors (EXIT_TRANSIENT)
- No retry on permanent errors (EXIT_PERMANENT)
- Extended cooldown on rate limiting (EXIT_RATE_LIMIT)
- Timeout handling with retry
- Max retries exhaustion
- Stderr logging
"""

import pytest
import asyncio
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import subprocess

from core.scrapers.factory import (
    _run_subprocess_with_retry,
    ScrapeResult,
    EXIT_SUCCESS,
    EXIT_TRANSIENT,
    EXIT_PERMANENT,
    EXIT_RATE_LIMIT,
    MAX_RETRIES,
    BASE_DELAY,
    RATE_LIMIT_DELAY,
)


class TestSubprocessRetrySuccess:
    """Tests for successful scrape scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_success_first_attempt(self, tmp_path):
        """Successful scrape returns immediately without retry."""
        # Create a mock script that succeeds
        output_file = tmp_path / "output.json"
        properties = [{"parcel_id": "TX-HARRIS-123", "amount": 1000.0}]

        with patch('core.scrapers.factory.subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.communicate.return_value = ("", "")
            mock_process.returncode = EXIT_SUCCESS
            mock_popen.return_value = mock_process

            # Mock the temp file creation and reading
            with patch('core.scrapers.factory.tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = str(output_file)

                # Create the output file that would be written by subprocess
                output_file.write_text(json.dumps(properties))

                with patch('core.scrapers.factory.os.path.exists', return_value=True):
                    with patch('builtins.open', create=True) as mock_open:
                        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(properties)
                        mock_file = MagicMock()
                        mock_file.__enter__ = MagicMock(return_value=mock_file)
                        mock_file.__exit__ = MagicMock(return_value=False)
                        mock_file.read.return_value = json.dumps(properties)

                        with patch('json.load', return_value=properties):
                            result = await _run_subprocess_with_retry(
                                script_path=Path("test_script.py"),
                                args=["Harris"],
                                timeout=60,
                                state_name="Texas"
                            )

        assert result.error_message is None
        assert result.items_found == 1
        assert len(result.properties) == 1
        assert result.properties[0]["parcel_id"] == "TX-HARRIS-123"
        # Verify only one call (no retries)
        assert mock_popen.call_count == 1


class TestSubprocessRetryTransient:
    """Tests for transient error retry scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_retry_on_transient_error(self, tmp_path):
        """Transient errors trigger retry with exponential backoff."""
        output_file = tmp_path / "output.json"
        properties = [{"parcel_id": "AL-BALDWIN-456", "amount": 500.0}]

        call_count = [0]  # Use list to allow mutation in nested function

        def create_mock_process():
            call_count[0] += 1
            mock_process = MagicMock()
            if call_count[0] <= 2:
                # First two attempts fail with transient error
                mock_process.communicate.return_value = ("", "Network timeout")
                mock_process.returncode = EXIT_TRANSIENT
            else:
                # Third attempt succeeds
                mock_process.communicate.return_value = ("", "")
                mock_process.returncode = EXIT_SUCCESS
                # Write output file for successful case
                output_file.write_text(json.dumps(properties))
            return mock_process

        with patch('core.scrapers.factory.subprocess.Popen', side_effect=lambda *args, **kwargs: create_mock_process()):
            with patch('core.scrapers.factory.tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = str(output_file)

                with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                    result = await _run_subprocess_with_retry(
                        script_path=Path("test_script.py"),
                        args=["Baldwin"],
                        timeout=60,
                        state_name="Alabama"
                    )

        assert result.error_message is None
        assert result.items_found == 1
        # Verify 3 calls (2 failures + 1 success)
        assert call_count[0] == 3
        # Verify backoff delays were used (2 sleeps for 2 retries)
        assert mock_sleep.call_count == 2


class TestSubprocessRetryPermanent:
    """Tests for permanent error scenarios (no retry)."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_no_retry_on_permanent_error(self):
        """Permanent errors fail immediately without retry."""
        with patch('core.scrapers.factory.subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.communicate.return_value = ("", "Invalid county: Fake")
            mock_process.returncode = EXIT_PERMANENT
            mock_popen.return_value = mock_process

            with patch('core.scrapers.factory.tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = "/tmp/test.json"

                result = await _run_subprocess_with_retry(
                    script_path=Path("test_script.py"),
                    args=["Fake"],
                    timeout=60,
                    state_name="Texas"
                )

        assert result.error_message is not None
        assert "failed" in result.error_message.lower()
        assert result.items_found == 0
        # Verify only one call (no retries for permanent errors)
        assert mock_popen.call_count == 1


class TestSubprocessRetryRateLimit:
    """Tests for rate limiting scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_rate_limit_extended_backoff(self, tmp_path):
        """Rate limit triggers 60s cooldown instead of exponential backoff."""
        output_file = tmp_path / "output.json"
        properties = [{"parcel_id": "TX-ELPASO-789", "amount": 2000.0}]

        call_count = [0]

        def create_mock_process():
            call_count[0] += 1
            mock_process = MagicMock()
            if call_count[0] == 1:
                # First attempt rate limited
                mock_process.communicate.return_value = ("", "Rate limited")
                mock_process.returncode = EXIT_RATE_LIMIT
            else:
                # Second attempt succeeds
                mock_process.communicate.return_value = ("", "")
                mock_process.returncode = EXIT_SUCCESS
                output_file.write_text(json.dumps(properties))
            return mock_process

        with patch('core.scrapers.factory.subprocess.Popen', side_effect=lambda *args, **kwargs: create_mock_process()):
            with patch('core.scrapers.factory.tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = str(output_file)

                with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                    result = await _run_subprocess_with_retry(
                        script_path=Path("test_script.py"),
                        args=["El Paso"],
                        timeout=60,
                        state_name="Texas"
                    )

        assert result.error_message is None
        assert result.items_found == 1
        # Verify 2 calls (1 rate limit + 1 success)
        assert call_count[0] == 2
        # Verify rate limit delay (60s) was used
        mock_sleep.assert_called_with(RATE_LIMIT_DELAY)


class TestSubprocessRetryTimeout:
    """Tests for timeout scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_timeout_triggers_retry(self, tmp_path):
        """Subprocess timeout triggers retry."""
        output_file = tmp_path / "output.json"
        properties = [{"parcel_id": "AL-MOBILE-321", "amount": 750.0}]

        call_count = [0]
        timeout_process = None

        def create_mock_process():
            nonlocal timeout_process
            call_count[0] += 1
            mock_process = MagicMock()
            if call_count[0] == 1:
                # First attempt times out
                mock_process.communicate.side_effect = subprocess.TimeoutExpired(
                    cmd="python test.py", timeout=60
                )
                mock_process.terminate = MagicMock()
                mock_process.kill = MagicMock()
                mock_process.wait = MagicMock()  # Graceful termination succeeds
                timeout_process = mock_process
            else:
                # Second attempt succeeds
                mock_process.communicate.return_value = ("", "")
                mock_process.returncode = EXIT_SUCCESS
                output_file.write_text(json.dumps(properties))
            return mock_process

        with patch('core.scrapers.factory.subprocess.Popen', side_effect=lambda *args, **kwargs: create_mock_process()):
            with patch('core.scrapers.factory.tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = str(output_file)

                with patch('asyncio.sleep', new_callable=AsyncMock):
                    result = await _run_subprocess_with_retry(
                        script_path=Path("test_script.py"),
                        args=["Mobile"],
                        timeout=60,
                        state_name="Alabama"
                    )

        assert result.error_message is None
        assert result.items_found == 1
        # Verify process was gracefully terminated on timeout (terminate before kill)
        assert timeout_process is not None
        timeout_process.terminate.assert_called_once()
        # kill() should NOT be called if terminate() + wait() succeeds
        timeout_process.kill.assert_not_called()


class TestSubprocessRetryExhausted:
    """Tests for max retries exhaustion."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_max_retries_exceeded(self):
        """Returns error after MAX_RETRIES attempts."""
        with patch('core.scrapers.factory.subprocess.Popen') as mock_popen:
            # All attempts fail with transient error
            mock_process = MagicMock()
            mock_process.communicate.return_value = ("", "Network error")
            mock_process.returncode = EXIT_TRANSIENT
            mock_popen.return_value = mock_process

            with patch('core.scrapers.factory.tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = "/tmp/test.json"

                with patch('asyncio.sleep', new_callable=AsyncMock):
                    result = await _run_subprocess_with_retry(
                        script_path=Path("test_script.py"),
                        args=["Harris"],
                        timeout=60,
                        state_name="Texas"
                    )

        assert result.error_message is not None
        assert f"{MAX_RETRIES} attempts" in result.error_message
        assert result.items_found == 0
        # Verify MAX_RETRIES calls
        assert mock_popen.call_count == MAX_RETRIES


class TestSubprocessStderrLogging:
    """Tests for stderr capture and logging."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_stderr_logged_on_failure(self):
        """Subprocess stderr is captured and logged."""
        error_message = "Specific error: selector not found"

        with patch('core.scrapers.factory.subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.communicate.return_value = ("", error_message)
            mock_process.returncode = EXIT_PERMANENT
            mock_popen.return_value = mock_process

            with patch('core.scrapers.factory.tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = "/tmp/test.json"

                with patch('core.scrapers.factory.logger') as mock_logger:
                    result = await _run_subprocess_with_retry(
                        script_path=Path("test_script.py"),
                        args=["Tarrant"],
                        timeout=60,
                        state_name="Texas"
                    )

        # Verify error message contains stderr
        assert error_message in result.error_message


class TestSubprocessCleanup:
    """Tests for temp file cleanup."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_temp_file_cleaned_up_on_success(self):
        """Temp file is cleaned up even on success."""
        with patch('core.scrapers.factory.subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.communicate.return_value = ("", "")
            mock_process.returncode = EXIT_SUCCESS
            mock_popen.return_value = mock_process

            with patch('core.scrapers.factory.tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = "/tmp/test_cleanup.json"

                with patch('core.scrapers.factory.os.path.exists', return_value=True):
                    with patch('json.load', return_value=[]):
                        with patch('core.scrapers.factory.os.unlink') as mock_unlink:
                            result = await _run_subprocess_with_retry(
                                script_path=Path("test_script.py"),
                                args=["Harris"],
                                timeout=60,
                                state_name="Texas"
                            )

        # Verify temp file cleanup was attempted
        mock_unlink.assert_called()


class TestArkansasRateLimitError:
    """Tests for Arkansas COSL RateLimitError handling."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_rate_limit_error_with_retry_after(self):
        """RateLimitError respects Retry-After header."""
        from aioresponses import aioresponses
        from core.scrapers.arkansas_cosl import ArkansasCOSLScraper, RateLimitError

        scraper = ArkansasCOSLScraper(max_retries=2, base_delay=0.01)

        with aioresponses() as mocked:
            # First request returns 429 with Retry-After header
            mocked.post(
                f"{scraper.BASE_URL}{scraper.GRID_ENDPOINT}",
                status=429,
                headers={'Retry-After': '30'}
            )
            # Second request succeeds
            mocked.post(
                f"{scraper.BASE_URL}{scraper.GRID_ENDPOINT}",
                payload={'Data': [], 'Total': 0}
            )

            async with scraper:
                with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                    result = await scraper._fetch_grid_page(scraper.GRID_ENDPOINT)

            # Verify longer delay was used (30s from Retry-After)
            # The first call should be with 30 seconds
            calls = mock_sleep.call_args_list
            assert len(calls) >= 1
            # First sleep should be the rate limit delay
            assert calls[0][0][0] == 30

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_rate_limit_error_default_delay(self):
        """RateLimitError uses default 60s when no Retry-After header."""
        from aioresponses import aioresponses
        from core.scrapers.arkansas_cosl import ArkansasCOSLScraper

        scraper = ArkansasCOSLScraper(max_retries=2, base_delay=0.01)

        with aioresponses() as mocked:
            # First request returns 429 without Retry-After header
            mocked.post(
                f"{scraper.BASE_URL}{scraper.GRID_ENDPOINT}",
                status=429
            )
            # Second request succeeds
            mocked.post(
                f"{scraper.BASE_URL}{scraper.GRID_ENDPOINT}",
                payload={'Data': [], 'Total': 0}
            )

            async with scraper:
                with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                    result = await scraper._fetch_grid_page(scraper.GRID_ENDPOINT)

            # Verify default rate limit delay (60s) was used
            calls = mock_sleep.call_args_list
            assert len(calls) >= 1
            assert calls[0][0][0] == 60
