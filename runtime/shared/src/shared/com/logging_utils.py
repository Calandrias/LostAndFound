"""Logging utilities for Lost & Found platform."""

import os
import logging
import re

SENSITIVE_PATTERN = re.compile(r'\b([a-fA-F0-9]{8,}|[A-Za-z0-9\-_]{12,}|eyJ[A-Za-z0-9\-_]{20,})\b')
PROTECTED_PREFIXES = ("owner_", "tag_", "sessiontok_")


def mask_sensitive_patterns(text: str) -> str:
    """Mask sensitive patterns in a given text string."""

    def replacer(match):
        """Replace matched sensitive pattern with a mask."""
        word = match.group(0)
        for prefix in PROTECTED_PREFIXES:
            if word.startswith(prefix):
                suffix = word[len(prefix):]
                if len(suffix) > 3:
                    masked_suffix = f"{suffix[0]}>len={len(suffix)}<{suffix[-1]}"
                    return prefix + masked_suffix
                return word
        if len(word) < 4:
            return word
        return f"{word[0]}>len={len(word)}<{word[-1]}"

    return SENSITIVE_PATTERN.sub(replacer, text)


class SanitizingFormatter(logging.Formatter):
    """ Custom formatter that sanitizes sensitive information in log messages."""

    def __init__(self, pattern=None, *args, **kwargs):
        """Initialize logger with optional pattern and arguments."""
        self.sensitive_pattern = re.compile(pattern) if pattern else SENSITIVE_PATTERN
        super().__init__(*args, **kwargs)

    def sanitize(self, text: str) -> str:
        """Sanitize text by masking sensitive information."""
        return mask_sensitive_patterns(text)

    def format(self, record):
        """Format log record for output."""
        # Mask message and args
        if record.args:
            record.msg = self.sanitize(str(record.msg))
            record.args = tuple(self.sanitize(str(a)) for a in record.args)
        else:
            record.msg = self.sanitize(str(record.msg))
        return super().format(record)


class ProjectLogger:
    """Custom logger for Lost & Found platform."""
    _instances = {}

    def __new__(cls, name="LostAndFound"):
        """Create a new logger instance."""
        if name not in cls._instances:
            instance = super().__new__(cls)
            instance._init_logger(name)
            cls._instances[name] = instance
        return cls._instances[name]

    def _init_logger(self, name):
        """Initialize the logger backend."""
        self.logger = logging.getLogger(name)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = SanitizingFormatter('[%(levelname)s] %(asctime)s %(name)s: %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.propagate = False

            # Env-based config
            stage = os.getenv("STAGE", "prod").lower()
            log_level = os.getenv("LOG_LEVEL", "INFO").upper()
            # In prod, enforce at least INFO (never DEBUG/TRACE!)

            allowed_levels = {"INFO", "WARNING", "ERROR", "CRITICAL"}
            # Dev: allow ANY level
            if stage == "dev":
                self.logger.setLevel(getattr(logging, log_level, logging.INFO))
            # All others: only allow INFO or stricter (no DEBUG or lower)
            else:
                if log_level in allowed_levels:
                    self.logger.setLevel(getattr(logging, log_level))
                else:
                    self.logger.setLevel(logging.INFO)

    def get_logger(self):
        """Return the logger instance."""
        return self.logger

    @staticmethod
    def sanitize(text: str) -> str:
        """Sanitize text by masking sensitive information (standalone function)."""
        return mask_sensitive_patterns(text)
