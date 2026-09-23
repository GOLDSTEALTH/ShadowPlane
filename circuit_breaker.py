"""
Circuit Breaker for Terraform Deployment Tools.

Prevents runaway retry loops by tracking consecutive failures per Terraform
directory within a sliding time window. When the failure threshold is reached,
the breaker "trips" and returns a hard-stop message that breaks the LLM
feedback loop.

Usage:
    from circuit_breaker import circuit_breaker, SYSTEM_OVERRIDE_MESSAGE

    # Before executing:
    if circuit_breaker.is_tripped(tf_dir):
        return SYSTEM_OVERRIDE_MESSAGE.format(...)

    # On failure:
    tripped = circuit_breaker.check_and_record_failure(tf_dir)

    # On success:
    circuit_breaker.record_success(tf_dir)
"""

import logging
import os
import threading
import time

class CircuitBreakerError(Exception):
    """Raised when the circuit breaker is tripped and execution is blocked."""
    pass

logger = logging.getLogger("ShadowPlane-Gateway.CircuitBreaker")

# ──────────────────────────────────────────────────────────────────────────────
# Hard-stop message returned to the LLM when the circuit breaker trips.
# This must be strong enough to break the agent out of its retry loop.
# ──────────────────────────────────────────────────────────────────────────────
SYSTEM_OVERRIDE_MESSAGE = (
    "SYSTEM OVERRIDE: MAX RETRIES EXCEEDED. YOU MUST STOP EXECUTING.\n"
    "\n"
    "Terraform apply has failed {failure_count} consecutive times "
    "for directory '{terraform_dir}' within the last {window}s.\n"
    "\n"
    "The circuit breaker has TRIPPED. This tool will NOT execute Terraform "
    "until a human operator resets it.\n"
    "\n"
    "ACTION REQUIRED:\n"
    "1. Do NOT call clone_and_deploy again for this directory.\n"
    "2. Report this failure to the user immediately.\n"
    "3. Wait for human intervention.\n"
    "4. A human can reset the breaker by calling the reset_circuit_breaker tool.\n"
)


class CircuitBreaker:
    """
    Per-directory circuit breaker that tracks consecutive Terraform failures
    within a sliding time window.

    Attributes:
        max_failures:   Maximum allowed failures before tripping (default: 4).
                        This means 1 initial attempt + 3 retries.
        window_seconds: Sliding window in seconds; failures older than this
                        are pruned (default: 300 = 5 minutes).
    """

    def __init__(self, max_failures: int = 4, window_seconds: int = 300):
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        # _failures: { normalized_dir: [timestamp, timestamp, ...] }
        self._failures: dict[str, list[float]] = {}
        # _tripped: { normalized_dir: True } — latched until manual reset
        self._tripped: dict[str, bool] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _normalize_dir(terraform_dir: str) -> str:
        """Normalize a directory path for consistent keying."""
        return os.path.abspath(terraform_dir).replace("\\", "/").lower()

    def _prune(self, key: str) -> None:
        """Remove failure timestamps outside the sliding window."""
        cutoff = time.time() - self.window_seconds
        if key in self._failures:
            self._failures[key] = [
                ts for ts in self._failures[key] if ts > cutoff
            ]

    def is_tripped(self, terraform_dir: str) -> bool:
        """
        Check if the circuit breaker is currently tripped for a directory.

        A tripped breaker stays tripped until explicitly reset via
        ``reset(terraform_dir)`` — it does NOT auto-reset after the window.
        This ensures a human must intervene.
        """
        key = self._normalize_dir(terraform_dir)
        with self._lock:
            return self._tripped.get(key, False)

    def check_and_record_failure(self, terraform_dir: str) -> bool:
        """
        Record a failure and check if the breaker should trip.

        Returns:
            True  — the circuit breaker has just tripped (threshold reached).
            False — failure recorded but threshold not yet reached.
        """
        key = self._normalize_dir(terraform_dir)
        now = time.time()
        with self._lock:
            # If already tripped, don't bother recording
            if self._tripped.get(key, False):
                return True

            self._failures.setdefault(key, []).append(now)
            self._prune(key)

            failure_count = len(self._failures[key])
            logger.warning(
                "CircuitBreaker: failure %d/%d for '%s'",
                failure_count,
                self.max_failures,
                terraform_dir,
            )

            if failure_count >= self.max_failures:
                self._tripped[key] = True
                logger.error(
                    "CircuitBreaker TRIPPED for '%s' after %d failures in %ds window. "
                    "Terraform execution is now BLOCKED for this directory.",
                    terraform_dir,
                    failure_count,
                    self.window_seconds,
                )
                return True

            return False

    def record_success(self, terraform_dir: str) -> None:
        """
        Record a successful deployment — resets the failure counter
        for the directory (but not a tripped state, which requires
        explicit ``reset()``).
        """
        key = self._normalize_dir(terraform_dir)
        with self._lock:
            self._failures.pop(key, None)
            # Note: tripped state is NOT cleared on success.
            # A tripped breaker requires explicit reset() by a human operator.
            logger.info("CircuitBreaker: cleared failures for '%s' on success", terraform_dir)

    def reset(self, terraform_dir: str) -> str:
        """
        Manually reset the circuit breaker for a directory.
        Called by the reset_circuit_breaker MCP tool after human intervention.

        Returns:
            A confirmation message string.
        """
        key = self._normalize_dir(terraform_dir)
        with self._lock:
            was_tripped = self._tripped.pop(key, False)
            cleared_count = len(self._failures.pop(key, []))
            logger.info(
                "CircuitBreaker: manual reset for '%s' (was_tripped=%s, cleared_failures=%d)",
                terraform_dir,
                was_tripped,
                cleared_count,
            )
            if was_tripped:
                return (
                    f"Circuit breaker RESET for '{terraform_dir}'. "
                    f"Cleared {cleared_count} recorded failures. "
                    f"Terraform deployments are now unblocked for this directory."
                )
            return (
                f"Circuit breaker was not tripped for '{terraform_dir}'. "
                f"Cleared {cleared_count} recorded failures."
            )

    def get_status(self, terraform_dir: str) -> dict:
        """Return the current breaker status for a directory."""
        key = self._normalize_dir(terraform_dir)
        with self._lock:
            self._prune(key)
            return {
                "directory": terraform_dir,
                "normalized_key": key,
                "is_tripped": self._tripped.get(key, False),
                "failure_count": len(self._failures.get(key, [])),
                "max_failures": self.max_failures,
                "window_seconds": self.window_seconds,
            }

    def get_all_status(self) -> list[dict]:
        """Return status for all tracked directories."""
        with self._lock:
            all_keys = set(list(self._failures.keys()) + list(self._tripped.keys()))
            statuses = []
            for key in all_keys:
                self._prune(key)
                statuses.append({
                    "directory": key,
                    "is_tripped": self._tripped.get(key, False),
                    "failure_count": len(self._failures.get(key, [])),
                    "max_failures": self.max_failures,
                    "window_seconds": self.window_seconds,
                })
            return statuses


# ──────────────────────────────────────────────────────────────────────────────
# Module-level singleton — shared across the MCP server
# ──────────────────────────────────────────────────────────────────────────────
circuit_breaker = CircuitBreaker(max_failures=4, window_seconds=300)
