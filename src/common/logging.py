import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """
    Configure global application logging settings.

    This function initializes Python's built-in logging system using
    `logging.basicConfig()`. It sets:

    - The logging level (INFO by default)
    - A standardized log message format
    - A stream handler that outputs logs to stdout

    This is typically called once at the beginning of the application
    to ensure all modules use consistent logging behavior.

    Args:
        level (str, optional):
            Logging level as a string (case-insensitive).
            Common values:
                - "DEBUG"
                - "INFO"
                - "WARNING"
                - "ERROR"
                - "CRITICAL"

            If an invalid value is provided, it falls back to INFO.

    Returns:
        None
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
