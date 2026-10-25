"""Application logging configuration."""

import logging
import sys


def configure_logging() -> None:
    """Configure standard library logging for the application.

    Kept intentionally minimal. A future phase can route logs to structured
    sinks (e.g. JSON) without changing call sites.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        stream=sys.stdout,
    )


logger = logging.getLogger("careertwin")
