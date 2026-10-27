from __future__ import annotations

import logging
import re
import sys

PHONE_MASK_REGEX = re.compile(r"(?:\+91[\s\-]?)?(?:0)?([6-9]\d{1,4})[\s\-]?(\d{1,4})[\s\-]?(\d{4})\b")


class SensitiveDataFilter(logging.Filter):
    """Masks phone numbers and ensures sensitive patient PII is redacted from technical logs."""

    @staticmethod
    def mask_phone_string(text: str) -> str:
        def _repl(m: re.Match[str]) -> str:
            raw = m.group(0)
            digits = re.sub(r"\D", "", raw)
            if digits.startswith("91") and len(digits) == 12:
                digits = digits[2:]
            elif digits.startswith("0") and len(digits) == 11:
                digits = digits[1:]
            if len(digits) == 10:
                return f"+91 {digits[:2]}****{digits[-4:]}"
            return raw

        return PHONE_MASK_REGEX.sub(_repl, text)

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.mask_phone_string(record.msg)
        return True


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("clinicvoice")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(SensitiveDataFilter())
        logger.addHandler(handler)

    return logger


logger = setup_logging()
