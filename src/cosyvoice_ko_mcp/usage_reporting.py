from __future__ import annotations

import json
import platform
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from importlib.metadata import PackageNotFoundError, version
from typing import Any
from urllib.request import Request, urlopen

from .config import AppConfig


@dataclass
class UsageSettings:
    enabled: bool
    install_id: str
    participant_id: str = ""


class UsageReporter:
    """Opt-in, best-effort usage reporting that never includes text or audio."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._settings = self._load_settings()

    def status(self) -> dict[str, object]:
        return {
            "enabled": self._settings.enabled,
            "endpoint_configured": bool(self.config.usage_endpoint),
            "participant_id": self._settings.participant_id or None,
            "install_id_suffix": self._settings.install_id[-8:],
            "data_policy": "No text, prompt text, audio, voice name, or file path is sent.",
        }

    def configure(self, enabled: bool, participant_id: str = "") -> dict[str, object]:
        participant_id = participant_id.strip()
        if len(participant_id) > 100:
            raise ValueError("participant_id must be <= 100 characters.")
        if enabled and not self.config.usage_endpoint:
            raise ValueError(
                "COSYVOICE_USAGE_ENDPOINT is not configured by this distribution."
            )
        self._settings.enabled = enabled
        self._settings.participant_id = participant_id
        self._save_settings()
        if enabled:
            self.report("reporting_enabled", {})
        return self.status()

    def report_synthesis(
        self,
        *,
        success: bool,
        elapsed_sec: float,
        duration_sec: float | None,
        text_chars: int,
        error_type: str | None = None,
    ) -> None:
        self.report(
            "synthesis_finished",
            {
                "success": success,
                "elapsed_sec": round(elapsed_sec, 3),
                "duration_sec": round(duration_sec, 3) if duration_sec is not None else None,
                "text_chars_bucket": self._length_bucket(text_chars),
                "error_type": error_type,
            },
        )

    def report_feedback(self, score: int, category: str = "", comment: str = "") -> dict[str, object]:
        if not 1 <= score <= 5:
            raise ValueError("score must be between 1 and 5.")
        category = category.strip()
        comment = comment.strip()
        if len(category) > 40:
            raise ValueError("category must be <= 40 characters.")
        if len(comment) > 500:
            raise ValueError("comment must be <= 500 characters.")
        if not self._settings.enabled:
            raise ValueError("Usage reporting is disabled. Enable it explicitly first.")
        self.report(
            "quality_feedback",
            {"score": score, "category": category or None, "comment": comment or None},
        )
        return {"queued": True, "score": score}

    def report(self, event: str, properties: dict[str, Any]) -> None:
        if not self._settings.enabled or not self.config.usage_endpoint:
            return
        payload = {
            "schema_version": 1,
            "event_id": str(uuid.uuid4()),
            "event": event,
            "timestamp": int(time.time()),
            "install_id": self._settings.install_id,
            "participant_id": self._settings.participant_id or None,
            "client": self._client_metadata(),
            "properties": properties,
        }
        threading.Thread(target=self._post, args=(payload,), daemon=True).start()

    def _post(self, payload: dict[str, Any]) -> None:
        try:
            body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
            request = Request(
                self.config.usage_endpoint,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "cosyvoice2-ko-sft-mcp/usage-reporting",
                },
                method="POST",
            )
            with urlopen(request, timeout=3):
                pass
        except Exception:
            # Reporting must never affect local synthesis.
            return

    def _load_settings(self) -> UsageSettings:
        try:
            data = json.loads(self.config.usage_settings_path.read_text(encoding="utf-8"))
            return UsageSettings(
                enabled=bool(data.get("enabled", False)),
                install_id=str(data["install_id"]),
                participant_id=str(data.get("participant_id", "")),
            )
        except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return UsageSettings(enabled=False, install_id=str(uuid.uuid4()))

    def _save_settings(self) -> None:
        self.config.ensure_directories()
        self.config.usage_settings_path.write_text(
            json.dumps(asdict(self._settings), ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _length_bucket(length: int) -> str:
        for upper in (20, 50, 100, 250, 500, 1000):
            if length <= upper:
                return f"1-{upper}"
        return "1001+"

    @staticmethod
    def _client_metadata() -> dict[str, object]:
        try:
            package_version = version("cosyvoice2-ko-sft-mcp")
        except PackageNotFoundError:
            package_version = "development"
        metadata: dict[str, object] = {
            "version": package_version,
            "os": platform.system(),
            "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        }
        try:
            import torch

            metadata["cuda_available"] = torch.cuda.is_available()
            if torch.cuda.is_available():
                metadata["gpu"] = torch.cuda.get_device_name(0)
                metadata["vram_gib"] = round(
                    torch.cuda.get_device_properties(0).total_memory / 1024**3, 1
                )
        except (ImportError, RuntimeError):
            metadata["cuda_available"] = False
        return metadata
