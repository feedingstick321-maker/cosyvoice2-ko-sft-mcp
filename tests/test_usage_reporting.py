from __future__ import annotations

import json
from pathlib import Path

import pytest

from cosyvoice_ko_mcp.config import AppConfig
from cosyvoice_ko_mcp.usage_reporting import UsageReporter


def make_config(tmp_path: Path, endpoint: str = "") -> AppConfig:
    return AppConfig("base", "rev", "fine", "rev", tmp_path / "data", endpoint)


def test_reporting_is_disabled_by_default(tmp_path: Path) -> None:
    reporter = UsageReporter(make_config(tmp_path))

    status = reporter.status()

    assert status["enabled"] is False
    assert status["endpoint_configured"] is False


def test_release_endpoint_is_configured_without_enabling_reporting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COSYVOICE_KO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("COSYVOICE_USAGE_ENDPOINT", raising=False)

    reporter = UsageReporter(AppConfig.from_env())

    assert reporter.status()["enabled"] is False
    assert reporter.status()["endpoint_configured"] is True
    assert reporter.config.usage_endpoint.startswith("https://34-64-223-17.sslip.io/")


def test_enabling_requires_distribution_endpoint(tmp_path: Path) -> None:
    reporter = UsageReporter(make_config(tmp_path))

    with pytest.raises(ValueError, match="COSYVOICE_USAGE_ENDPOINT"):
        reporter.configure(True, "community-tester")


def test_explicit_consent_is_persisted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = make_config(tmp_path, "https://usage.example.invalid/events")
    reporter = UsageReporter(config)
    monkeypatch.setattr(reporter, "report", lambda event, properties: None)

    status = reporter.configure(True, "school-lab")
    stored = json.loads(config.usage_settings_path.read_text(encoding="utf-8"))

    assert status["enabled"] is True
    assert stored["enabled"] is True
    assert stored["participant_id"] == "school-lab"
    assert UsageReporter(config).status()["enabled"] is True


def test_feedback_requires_consent(tmp_path: Path) -> None:
    reporter = UsageReporter(make_config(tmp_path, "https://usage.example.invalid/events"))

    with pytest.raises(ValueError, match="disabled"):
        reporter.report_feedback(5, "prosody")
