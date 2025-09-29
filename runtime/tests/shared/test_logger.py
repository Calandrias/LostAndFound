"""Tests for logging utilities with identifier prefix masking, strict loglevel policy and memory handler for output capturing."""

import logging
import random
import io
import pytest

from shared.com.logging_utils import ProjectLogger, SanitizingFormatter


def random_logger() -> str:
    """Return a random logger name for test isolation."""
    return "TestLogger_" + str(random.randint(0, 99999))


def attach_memory_handler(logger):
    """Attach a fresh StreamHandler(StringIO) and return its buffer for test log capture."""
    stream = io.StringIO()
    for h in list(logger.handlers):
        logger.removeHandler(h)
    handler = logging.StreamHandler(stream)
    handler.setFormatter(SanitizingFormatter('[%(levelname)s] %(asctime)s %(name)s: %(message)s'))
    logger.addHandler(handler)
    return stream


@pytest.mark.parametrize(
    "value,should_mask,prefix",
    [
        ("owner_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", True, "owner_"),
        ("tag_ABCDEFGHJKLMNOPQRSTU", True, "tag_"),
        ("sessiontok_123456789012345678901234567890ABCDEFG", True, "sessiontok_"),
        ("owner_000", False, "owner_"),  # too short
        ("tag_XYZ12", False, "tag_"),
        ("sessiontok_123", False, "sessiontok_"),
        ("notanid_ABCD1234", True, None),
        ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9abcdefghi", True, None),
        ("abcd", False, None),
        ("", False, None),
        ("12345", False, None),
    ])
def test_sanitize_identifier_patterns_and_prefixes(value, should_mask, prefix):
    """Test that ProjectLogger.sanitize correctly masks or passes values based on prefix and length."""
    masked = ProjectLogger.sanitize(value)
    if should_mask and prefix:
        assert masked.startswith(prefix)
        assert ">len=" in masked
        assert masked[len(prefix)] == value[len(prefix)]
        assert masked[-1] == value[-1]
        assert masked != value
    elif should_mask:
        assert ">len=" in masked
        assert masked != value
    else:
        assert masked == value


def test_sanitizing_formatter_unicode_and_prefix():
    """Test that SanitizingFormatter handles unicode and known prefixes."""
    formatter = SanitizingFormatter()
    examples = ["MyÜñîcødé ✨ owner_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "foo tag_ABCDEFGHJKLMNOPQRSTU", "X sessiontok_123456789012345678901234567890ABCDEFG Z"]
    for msg in examples:
        record = logging.LogRecord(name="test", level=logging.INFO, pathname=__file__, lineno=1, msg=msg, args=(), exc_info=None, func=None)
        formatted = formatter.format(record)
        assert ">len=" in formatted


def test_logger_level_dependency(monkeypatch):
    """Test logger level and output depending on environment variables."""
    logger_name = random_logger()
    monkeypatch.setenv("STAGE", "prod")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    logger = ProjectLogger(logger_name).get_logger()
    stream = attach_memory_handler(logger)
    logger.debug("hidden debug message %s", "owner_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    logger.info("public info %s", "owner_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    log_output = stream.getvalue()
    assert "public info" in log_output
    assert ">len=" in log_output
    assert "hidden debug" not in log_output

    logger_name2 = random_logger()
    monkeypatch.setenv("STAGE", "dev")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    logger2 = ProjectLogger(logger_name2).get_logger()
    stream2 = attach_memory_handler(logger2)
    logger2.debug("debug msg %s", "tag_ABCDEFGHJKLMNOPQRSTU")
    log_output2 = stream2.getvalue()
    assert "debug msg" in log_output2
    assert ">len=" in log_output2


def test_logger_sanitizer_on_args_with_prefixes():
    """Test that logger output masks sensitive args with known prefixes."""
    logger_name = random_logger()
    logger = ProjectLogger(logger_name).get_logger()
    stream = attach_memory_handler(logger)
    logger.info("Sensitive: %s %s", "owner_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "sessiontok_123456789012345678901234567890ABCDEFG")
    log_output = stream.getvalue()
    assert "Sensitive" in log_output
    assert log_output.count(">len=") >= 2
    logger.info("Safe log: %s", "short")
    safe_output = stream.getvalue()
    assert "Safe log: short" in safe_output


def test_logger_singleton_and_handler():
    """Test that ProjectLogger is a singleton and handlers can be cleared and reattached."""
    logger_name = random_logger()
    logger_a = ProjectLogger(logger_name).get_logger()
    logger_b = ProjectLogger(logger_name).get_logger()
    assert logger_a is logger_b
    logger_a.handlers.clear()
    logger_c = ProjectLogger(logger_name).get_logger()
    stream_c = attach_memory_handler(logger_c)
    logger_c.info("should show after clearing handlers: tag_ABCDEFGHJKLMNOPQRSTU")
    out_c = stream_c.getvalue()
    assert "should show after clearing handlers" in out_c
    assert ">len=" in out_c


def test_formatter_custom_pattern_for_qr_prefix():
    """Test that SanitizingFormatter can use a custom regex pattern for QR tag prefix."""
    pattern = r'\btag_[A-Za-z0-9]{8,}\b'
    formatter = SanitizingFormatter(pattern=pattern)
    teststring = "tag_ABCDEFGH tag_SHORT tag_ABCDEFGHIJKLMNOPQ"
    masked = formatter.sanitize(teststring)
    assert "tag_A>len=" in masked
    assert masked.endswith("Q") or "<Q" in masked


def test_formatter_args_tuple_with_owner_tag():
    """Test that formatter masks args tuple with owner and tag values."""
    formatter = SanitizingFormatter()
    record = logging.LogRecord(name="foo",
                               level=logging.INFO,
                               pathname=__file__,
                               lineno=1,
                               msg="tokens %s %s",
                               args=("owner_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "tag_ABCDEFGHJK"),
                               exc_info=None,
                               func=None)
    result = formatter.format(record)
    assert "owner_A>len=" in result
    assert "tag_A>len=" in result


def test_logger_propagate_behavior():
    """Test that ProjectLogger sets propagate to False."""
    logger_name = random_logger()
    logger = ProjectLogger(logger_name).get_logger()
    assert logger.propagate is False


def test_project_logger_env_setup(monkeypatch):
    """Test logger level setup based on STAGE and LOG_LEVEL environment variables."""
    logger_name = random_logger()
    monkeypatch.setenv("STAGE", "prod")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    logger = ProjectLogger(logger_name).get_logger()
    assert logger.level == logging.INFO  # INFO is 20

    logger_name2 = random_logger()
    monkeypatch.setenv("STAGE", "dev")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    logger2 = ProjectLogger(logger_name2).get_logger()
    assert logger2.level == logging.DEBUG  # DEBUG is 10


def test_sanitize_staticmethod_public_with_tag_owner():
    """Test that ProjectLogger.sanitize matches SanitizingFormatter.sanitize for known values."""
    val1 = "owner_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    val2 = "tag_ABCDEFGHJKLMNOPQRSTU"
    val3 = "sessiontok_123456789012345678901234567890ABCDEFG"
    for val in (val1, val2, val3):
        assert ProjectLogger.sanitize(val) == SanitizingFormatter().sanitize(val)
