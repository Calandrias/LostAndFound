import os
import logging
import re

SENSITIVE_PATTERN = re.compile(r'\b([a-fA-F0-9]{8,}|[A-Za-z0-9\-_]{12,}|eyJ[A-Za-z0-9\-_]{20,})\b')


class SanitizingFormatter(logging.Formatter):
    """ Custom formatter that sanitizes sensitive information in log messages."""

    def __init__(self, pattern=None, *args, **kwargs):

        self.sensitive_pattern = re.compile(pattern) if pattern else SENSITIVE_PATTERN
        super().__init__(*args, **kwargs)

    def sanitize(self, text: str) -> str:
        """ Replace sensitive patterns in the text with a masked version."""

        def replacer(match):
            word = match.group(0)
            if len(word) < 4:
                return word
            return f"{word[0]}>len={len(word)}<{word[-1]}"

        return self.sensitive_pattern.sub(replacer, text)

    def format(self, record):
        # Mask message and args
        if record.args:
            record.msg = self.sanitize(str(record.msg))
            record.args = tuple(self.sanitize(str(a)) for a in record.args)
        else:
            record.msg = self.sanitize(str(record.msg))
        return super().format(record)


class ProjectLogger:
    _instances = {}

    def __new__(cls, name="LostAndFound"):
        if name not in cls._instances:
            instance = super().__new__(cls)
            instance._init_logger(name)
            cls._instances[name] = instance
        return cls._instances[name]

    def _init_logger(self, name):
        self.logger = logging.getLogger(name)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = SanitizingFormatter('[%(levelname)s] %(asctime)s %(name)s: %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.propagate = False

            # Env-based config
            stage = os.getenv("STAGE", "prod").lower()
            debug_env = os.getenv("LOG_LEVEL", "INFO").upper()
            if debug_env == "DEBUG" and stage == "dev":
                self.logger.setLevel(logging.DEBUG)
            else:
                self.logger.setLevel(getattr(logging, debug_env, logging.INFO))

    def get_logger(self):
        return self.logger

    @staticmethod
    def sanitize(text: str) -> str:
        pattern = SENSITIVE_PATTERN

        def replacer(match):
            word = match.group(0)
            if len(word) < 4:
                return word
            return f"{word[0]}>len={len(word)}<{word[-1]}"

        return pattern.sub(replacer, text)
