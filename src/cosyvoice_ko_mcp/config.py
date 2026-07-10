from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_data_path


@dataclass(frozen=True)
class AppConfig:
    base_repo: str
    base_revision: str
    finetune_repo: str
    finetune_revision: str
    data_dir: Path
    max_text_chars: int = 2_000
    max_prompt_audio_bytes: int = 100 * 1024 * 1024
    max_prompt_audio_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> "AppConfig":
        configured_dir = os.environ.get("COSYVOICE_KO_DATA_DIR")
        data_dir = (
            Path(configured_dir).expanduser()
            if configured_dir
            else user_data_path("CosyVoice2-KO-MCP", appauthor=False)
        )
        return cls(
            base_repo=os.environ.get(
                "COSYVOICE_BASE_REPO", "FunAudioLLM/CosyVoice2-0.5B"
            ),
            base_revision=os.environ.get(
                "COSYVOICE_BASE_REVISION",
                "eec1ae6c79877dbd9379285cf8789c9e0879293d",
            ),
            finetune_repo=os.environ.get(
                "COSYVOICE_KO_MODEL_REPO",
                "feedingstick321-maker/CosyVoice2-KO-SFT-v6-epoch3",
            ),
            finetune_revision=os.environ.get("COSYVOICE_KO_MODEL_REVISION", "main"),
            data_dir=data_dir.resolve(),
        )

    @property
    def model_dir(self) -> Path:
        return self.data_dir / "model"

    @property
    def voices_dir(self) -> Path:
        return self.data_dir / "voices"

    @property
    def outputs_dir(self) -> Path:
        return self.data_dir / "outputs"

    @property
    def manifest_path(self) -> Path:
        return self.data_dir / "model-manifest.json"

    def ensure_directories(self) -> None:
        for path in (self.data_dir, self.model_dir, self.voices_dir, self.outputs_dir):
            path.mkdir(parents=True, exist_ok=True)
