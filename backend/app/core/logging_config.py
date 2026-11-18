import logging
import re
import sys


class TokenRedactionFilter(logging.Filter):
    """Prevents accidental leakage of Bearer JWTs or sops_ agent tokens into logs."""

    TOKEN_PATTERN = re.compile(r"(Bearer\s+[A-Za-z0-9\-_\.]+|sops_[A-Za-z0-9\-_]+)")

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.TOKEN_PATTERN.sub("[REDACTED_TOKEN]", record.msg)
        if record.args:
            redacted_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    redacted_args.append(self.TOKEN_PATTERN.sub("[REDACTED_TOKEN]", arg))
                else:
                    redacted_args.append(arg)
            record.args = tuple(redacted_args)
        return True


def configure_logging(level: str = "INFO") -> None:
    log_level = getattr(logging, level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        )
    )
    handler.addFilter(TokenRedactionFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Quiet noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

