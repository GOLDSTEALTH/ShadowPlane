"""
Unit tests for the CircuitBreaker module.

Tests cover:
  - Failure counting and threshold tripping
  - Pre-check blocking after trip
  - Success resets
  - Manual reset via reset()
  - Sliding window expiry
  - Per-directory isolation
  - Thread safety
  - SYSTEM_OVERRIDE_MESSAGE formatting
"""

import sys
import os
import time
import threading
import unittest

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from circuit_breaker import CircuitBreaker, SYSTEM_OVERRIDE_MESSAGE


class TestCircuitBreakerBasic(unittest.TestCase):
    """Core functionality: counting, tripping, resetting."""

    def setUp(self):
        self.cb = CircuitBreaker(max_failures=4, window_seconds=300)

    def test_not_tripped_initially(self):
        self.assertFalse(self.cb.is_tripped("/some/dir"))

    def test_trips_after_max_failures(self):
        """4 consecutive failures should trip the breaker."""
        for i in range(3):
            tripped = self.cb.check_and_record_failure("/infra")
            self.assertFalse(tripped, f"Should not trip on failure {i+1}")

        # 4th failure trips it
        tripped = self.cb.check_and_record_failure("/infra")
        self.assertTrue(tripped)
        self.assertTrue(self.cb.is_tripped("/infra"))

    def test_is_tripped_blocks_before_execution(self):
        """Once tripped, is_tripped returns True on subsequent checks."""
        for _ in range(4):
            self.cb.check_and_record_failure("/infra")

        # Multiple subsequent checks should all return True
        for _ in range(10):
            self.assertTrue(self.cb.is_tripped("/infra"))

    def test_already_tripped_returns_true(self):
        """check_and_record_failure on an already-tripped breaker returns True."""
        for _ in range(4):
            self.cb.check_and_record_failure("/infra")

        # 5th call should still return True without adding more failures
        self.assertTrue(self.cb.check_and_record_failure("/infra"))

    def test_success_resets_counter(self):
        """A successful deployment clears failures and tripped state."""
        # Record 3 failures (not yet tripped)
        for _ in range(3):
            self.cb.check_and_record_failure("/infra")

        self.cb.record_success("/infra")

        # Should be fully reset
        self.assertFalse(self.cb.is_tripped("/infra"))
        status = self.cb.get_status("/infra")
        self.assertEqual(status["failure_count"], 0)

    def test_success_clears_tripped_state(self):
        """If somehow a success occurs after tripping, it clears the trip."""
        for _ in range(4):
            self.cb.check_and_record_failure("/infra")
        self.assertTrue(self.cb.is_tripped("/infra"))

        self.cb.record_success("/infra")
        self.assertFalse(self.cb.is_tripped("/infra"))

    def test_manual_reset(self):
        """reset() clears both failures and tripped state."""
        for _ in range(4):
            self.cb.check_and_record_failure("/infra")
        self.assertTrue(self.cb.is_tripped("/infra"))

        result = self.cb.reset("/infra")
        self.assertIn("RESET", result)
        self.assertFalse(self.cb.is_tripped("/infra"))
        self.assertEqual(self.cb.get_status("/infra")["failure_count"], 0)

    def test_manual_reset_not_tripped(self):
        """reset() on a non-tripped breaker returns appropriate message."""
        self.cb.check_and_record_failure("/infra")
        result = self.cb.reset("/infra")
        self.assertIn("was not tripped", result)


class TestCircuitBreakerIsolation(unittest.TestCase):
    """Per-directory isolation: one dir tripping doesn't affect others."""

    def setUp(self):
        self.cb = CircuitBreaker(max_failures=4, window_seconds=300)

    def test_directories_are_independent(self):
        """Failures in /dir-a should not affect /dir-b."""
        # Trip /dir-a
        for _ in range(4):
            self.cb.check_and_record_failure("/dir-a")
        self.assertTrue(self.cb.is_tripped("/dir-a"))

        # /dir-b should be fine
        self.assertFalse(self.cb.is_tripped("/dir-b"))
        self.assertFalse(self.cb.check_and_record_failure("/dir-b"))

    def test_path_normalization(self):
        """Different representations of the same path should share state."""
        self.cb.check_and_record_failure("E:\\ShadowPlane\\demo-infra")
        self.cb.check_and_record_failure("e:/shadowplane/demo-infra")
        # Both should be normalized to the same key
        status = self.cb.get_status("E:\\ShadowPlane\\demo-infra")
        self.assertEqual(status["failure_count"], 2)


class TestCircuitBreakerSlidingWindow(unittest.TestCase):
    """Sliding window: old failures expire."""

    def test_failures_expire_after_window(self):
        """Failures older than window_seconds are pruned."""
        # Use a tiny window for testing
        cb = CircuitBreaker(max_failures=4, window_seconds=1)

        # Record 3 failures
        for _ in range(3):
            cb.check_and_record_failure("/infra")

        # Wait for them to expire
        time.sleep(1.5)

        # New failure should be counted as #1, not #4
        tripped = cb.check_and_record_failure("/infra")
        self.assertFalse(tripped)
        self.assertFalse(cb.is_tripped("/infra"))


class TestCircuitBreakerStatus(unittest.TestCase):
    """get_status and get_all_status."""

    def setUp(self):
        self.cb = CircuitBreaker(max_failures=4, window_seconds=300)

    def test_status_fields(self):
        self.cb.check_and_record_failure("/infra")
        status = self.cb.get_status("/infra")
        self.assertEqual(status["failure_count"], 1)
        self.assertEqual(status["max_failures"], 4)
        self.assertFalse(status["is_tripped"])
        self.assertEqual(status["window_seconds"], 300)

    def test_get_all_status(self):
        self.cb.check_and_record_failure("/dir-a")
        self.cb.check_and_record_failure("/dir-b")
        statuses = self.cb.get_all_status()
        self.assertEqual(len(statuses), 2)


class TestCircuitBreakerThreadSafety(unittest.TestCase):
    """Concurrent access should not corrupt state."""

    def test_concurrent_failures(self):
        cb = CircuitBreaker(max_failures=100, window_seconds=300)
        errors = []

        def hammer():
            try:
                for _ in range(50):
                    cb.check_and_record_failure("/infra")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=hammer) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        status = cb.get_status("/infra")
        # 10 threads * 50 failures = 500, but it should be tripped at 100
        self.assertTrue(cb.is_tripped("/infra"))


class TestSystemOverrideMessage(unittest.TestCase):
    """SYSTEM_OVERRIDE_MESSAGE formatting."""

    def test_message_contains_placeholders(self):
        msg = SYSTEM_OVERRIDE_MESSAGE.format(
            failure_count=4,
            terraform_dir="/my/infra",
            window=300,
        )
        self.assertIn("SYSTEM OVERRIDE", msg)
        self.assertIn("MAX RETRIES EXCEEDED", msg)
        self.assertIn("YOU MUST STOP EXECUTING", msg)
        self.assertIn("4", msg)
        self.assertIn("/my/infra", msg)
        self.assertIn("300", msg)
        self.assertIn("reset_circuit_breaker", msg)


if __name__ == "__main__":
    unittest.main()
