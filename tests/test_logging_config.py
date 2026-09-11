"""Tests for centralized logging configuration (utils/logging_config.py)."""

import logging
import sys

import pytest

from egg_n_bacon_housing.utils.logging_config import (
    LEVEL_MAP,
    setup_logging,
    setup_logging_from_env,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _restore_root_logging():
    """Snapshot and restore root logger state around every test.

    setup_logging() uses ``force=True``, which replaces all existing root
    handlers (including any pytest installs) — restoring the snapshot keeps
    these tests from leaking console handlers into the rest of the suite.
    """
    handlers = logging.root.handlers[:]
    level = logging.root.level
    yield
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        handler.close()
    logging.root.handlers = handlers
    logging.root.setLevel(level)


def _stream_handlers(stream) -> list[logging.StreamHandler]:
    return [
        h
        for h in logging.root.handlers
        if isinstance(h, logging.StreamHandler) and h.stream is stream
    ]


class TestSetupLoggingForce:
    """setup_logging uses basicConfig(force=True): it replaces, not appends."""

    def test_force_replaces_pre_existing_handlers(self):
        sentinel = logging.Handler()
        logging.root.addHandler(sentinel)

        setup_logging(level=logging.INFO)

        assert sentinel not in logging.root.handlers
        assert len(logging.root.handlers) == 2  # stdout + stderr, no file

    def test_repeated_setup_does_not_accumulate_handlers(self):
        setup_logging(level=logging.INFO)
        setup_logging(level=logging.WARNING)

        assert len(logging.root.handlers) == 2

    def test_sets_root_level(self):
        setup_logging(level=logging.ERROR)
        assert logging.root.level == logging.ERROR


class TestHandlerRouting:
    """INFO and below go to stdout; WARNING and above are mirrored to stderr."""

    def test_installs_stdout_and_stderr_handlers(self):
        setup_logging(level=logging.INFO)

        stdout_handlers = _stream_handlers(sys.stdout)
        stderr_handlers = _stream_handlers(sys.stderr)
        assert len(stdout_handlers) == 1
        assert len(stderr_handlers) == 1
        assert stdout_handlers[0].level == logging.INFO
        assert stderr_handlers[0].level == logging.WARNING

    def test_info_goes_to_stdout_only(self, capsys):
        setup_logging(level=logging.INFO)
        logging.getLogger("routing.test").info("info message")

        out, err = capsys.readouterr()
        assert "info message" in out
        assert "info message" not in err

    def test_warning_and_above_go_to_stderr(self, capsys):
        setup_logging(level=logging.INFO)
        logger = logging.getLogger("routing.test")
        logger.warning("warning message")
        logger.error("error message")
        logger.critical("critical message")

        _, err = capsys.readouterr()
        assert "warning message" in err
        assert "error message" in err
        assert "critical message" in err

    def test_warning_still_mirrored_on_stdout(self, capsys):
        """The stdout handler stays at INFO, so WARNING+ appears on both streams."""
        setup_logging(level=logging.INFO)
        logging.getLogger("routing.test").warning("warn both streams")

        out, err = capsys.readouterr()
        assert "warn both streams" in out
        assert "warn both streams" in err

    def test_debug_level_preserves_debug_on_stdout(self, capsys):
        """A DEBUG run must not lose debug output to the INFO stdout handler."""
        setup_logging(level=logging.DEBUG)
        logging.getLogger("routing.test").debug("debug message")

        out, _ = capsys.readouterr()
        assert "debug message" in out

    def test_log_file_receives_all_records_and_keeps_stderr_routing(self, tmp_path, capsys):
        log_file = tmp_path / "nested" / "logs" / "run.log"  # parent dirs auto-created

        setup_logging(level=logging.INFO, log_file=log_file)
        logging.getLogger("file.test").info("file info")
        logging.getLogger("file.test").warning("file warning")

        for handler in logging.root.handlers:
            handler.flush()
        text = log_file.read_text(encoding="utf-8")
        assert "file info" in text
        assert "file warning" in text

        _, err = capsys.readouterr()
        assert "file warning" in err
        assert "file info" not in err


class TestLevelMap:
    def test_maps_every_standard_level(self):
        assert LEVEL_MAP == {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }


class TestSetupLoggingFromEnv:
    def test_reads_log_level_env(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        setup_logging_from_env()
        assert logging.root.level == logging.DEBUG

    def test_accepts_lowercase_values(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "warning")
        setup_logging_from_env()
        assert logging.root.level == logging.WARNING

    def test_invalid_value_falls_back_to_info(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "NOT_A_LEVEL")
        setup_logging_from_env()
        assert logging.root.level == logging.INFO

    def test_unset_defaults_to_info(self, monkeypatch):
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        setup_logging_from_env()
        assert logging.root.level == logging.INFO
