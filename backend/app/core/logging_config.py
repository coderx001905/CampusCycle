import logging


def configure_logging(level: str) -> None:
    """Configure concise application logging without logging request secrets."""
    normalized_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=normalized_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger().setLevel(normalized_level)
