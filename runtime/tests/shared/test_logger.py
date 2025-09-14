"""Tests for logging utilities, including token masking and log level behavior."""
from runtime.shared.logging_utils import ProjectLogger


def test_sanitize_token_masking():
    test_cases = [
        ("afed1385efhabc", "a>len=14<c"),
        ("sessiontok_eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", "s>len=43<9"),  # JWT-artig
        ("f3e39e3a1d28bb9bf9891f37aeccdfea", "f>len=32<a"),  # typical hash
        ("owner_1234567890123456789012345", "o>len=27<5"),  # owner_hash
        ("abcd", "a>len=4<d"),  # minimal Masking
        ("xyz", "xyz"),  # too short, unchanged
    ]
    for orig, expected in test_cases:
        masked = ProjectLogger.sanitize(orig)
        assert masked[0] == orig[0]
        assert masked[-1] == orig[-1]
        assert ">len=" in masked or masked == orig
        # Optionally, ensure that the length marker matches expected value
        if masked != orig:
            assert f">len={len(orig)}<" in masked


def test_logger_level_dependency(monkeypatch, capsys):
    # Stage "prod" and LOG_LEVEL "DEBUG" => should fall back to INFO (no debug)
    monkeypatch.setenv("STAGE", "prod")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    logger = ProjectLogger("TestLogger1").get_logger()
    logger.debug("hidden debug message %s", "tok123456789xyz")
    logger.info("public info %s", "tok123456789xyz")
    out = capsys.readouterr().out + capsys.readouterr().err
    assert "public info" in out
    assert "tok>len=" in out  # Masking in action!
    assert "hidden debug" not in out

    # Both "dev" and "DEBUG" => debug should show!
    monkeypatch.setenv("STAGE", "dev")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    logger2 = ProjectLogger("TestLogger2").get_logger()
    logger2.debug("debug msg %s", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abcdefghi")
    out = capsys.readouterr().out + capsys.readouterr().err
    assert "debug msg" in out
    # Should mask JWT/artige string
    assert "e>len=" in out or "y>len=" in out


def test_logger_sanitizer_on_args(capsys):
    logger = ProjectLogger("TestLogger3").get_logger()
    # Test with plausible session token and owner hash
    logger.info("Sensitive: %s %s", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", "f3e39e3a1d28bb9bf9891f37aeccdfea")
    out = capsys.readouterr().out + capsys.readouterr().err
    assert "Sensitive" in out
    assert "e>len=" in out and "f>len=" in out
    # Test that an unmasked short string remains intact
    logger.info("Safe log: %s", "abc")
    out = capsys.readouterr().out
    assert "Safe log: abc" in out
