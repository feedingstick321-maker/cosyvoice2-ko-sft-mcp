from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

import soundfile

from .config import AppConfig

_VOICE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_AUDIO_SUFFIXES = {".wav", ".flac", ".m4a", ".mp3", ".ogg"}


@dataclass(frozen=True)
class VoiceProfile:
    name: str
    prompt_text: str
    audio_path: str
    duration_sec: float
    sample_rate: int


class VoiceStore:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.config.ensure_directories()

    def register(self, name: str, prompt_text: str, audio_path: str) -> VoiceProfile:
        safe_name = self._validate_name(name)
        normalized_text = prompt_text.strip()
        if not normalized_text:
            raise ValueError("prompt_text must not be empty.")
        if len(normalized_text) > self.config.max_text_chars:
            raise ValueError("prompt_text is too long.")

        source = self.validate_audio(audio_path)
        info = soundfile.info(str(source))
        profile_dir = self.config.voices_dir / safe_name
        profile_dir.mkdir(parents=True, exist_ok=True)
        destination = profile_dir / f"prompt{source.suffix.lower()}"
        shutil.copy2(source, destination)
        profile = VoiceProfile(
            name=safe_name,
            prompt_text=normalized_text,
            audio_path=str(destination.resolve()),
            duration_sec=float(info.duration),
            sample_rate=int(info.samplerate),
        )
        self._write_json(profile_dir / "profile.json", asdict(profile))
        return profile

    def list(self) -> list[VoiceProfile]:
        profiles: list[VoiceProfile] = []
        for metadata_path in sorted(self.config.voices_dir.glob("*/profile.json")):
            try:
                payload = json.loads(metadata_path.read_text(encoding="utf-8"))
                profiles.append(VoiceProfile(**payload))
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                continue
        return profiles

    def get(self, name: str) -> VoiceProfile:
        safe_name = self._validate_name(name)
        metadata_path = self.config.voices_dir / safe_name / "profile.json"
        if not metadata_path.is_file():
            raise KeyError(f"Unknown voice profile: {safe_name}")
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        return VoiceProfile(**payload)

    def remove(self, name: str) -> bool:
        safe_name = self._validate_name(name)
        profile_dir = (self.config.voices_dir / safe_name).resolve()
        if profile_dir.parent != self.config.voices_dir.resolve():
            raise ValueError("Invalid voice profile path.")
        if not profile_dir.exists():
            return False
        shutil.rmtree(profile_dir)
        return True

    def validate_audio(self, audio_path: str) -> Path:
        source = Path(audio_path).expanduser().resolve(strict=True)
        if not source.is_file():
            raise ValueError("prompt_audio_path must point to a file.")
        if source.suffix.lower() not in _AUDIO_SUFFIXES:
            raise ValueError(f"Unsupported audio format: {source.suffix}")
        if source.stat().st_size > self.config.max_prompt_audio_bytes:
            raise ValueError("Reference audio exceeds the maximum file size.")
        try:
            info = soundfile.info(str(source))
        except RuntimeError as exc:
            raise ValueError("Reference audio could not be decoded.") from exc
        if info.frames <= 0 or info.samplerate <= 0:
            raise ValueError("Reference audio is empty or invalid.")
        if info.duration > self.config.max_prompt_audio_seconds:
            raise ValueError(
                f"Reference audio must be <= {self.config.max_prompt_audio_seconds:.0f} seconds."
            )
        return source

    @staticmethod
    def _validate_name(name: str) -> str:
        candidate = name.strip()
        if not _VOICE_NAME.fullmatch(candidate):
            raise ValueError(
                "Voice name must be 1-64 ASCII letters, digits, underscores, or hyphens."
            )
        return candidate

    @staticmethod
    def _write_json(path: Path, payload: dict[str, object]) -> None:
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)
