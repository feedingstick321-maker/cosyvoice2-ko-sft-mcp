from __future__ import annotations

import wave
from pathlib import Path

import pytest

from cosyvoice_ko_mcp.config import AppConfig
from cosyvoice_ko_mcp.voice_store import VoiceStore


def make_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16_000)
        handle.writeframes(b"\x00\x00" * 1_600)


def test_register_list_get_remove(tmp_path: Path) -> None:
    audio = tmp_path / "prompt.wav"
    make_wav(audio)
    store = VoiceStore(
        AppConfig(
            base_repo="base",
            base_revision="revision",
            finetune_repo="fine",
            finetune_revision="revision",
            data_dir=tmp_path / "data",
        )
    )

    profile = store.register("teacher", "안녕하세요.", str(audio))

    assert profile.name == "teacher"
    assert Path(profile.audio_path).is_file()
    assert store.get("teacher").prompt_text == "안녕하세요."
    assert [item.name for item in store.list()] == ["teacher"]
    assert store.remove("teacher") is True
    assert store.remove("teacher") is False


@pytest.mark.parametrize("name", ("../escape", "has space", "", "한글"))
def test_rejects_unsafe_voice_names(tmp_path: Path, name: str) -> None:
    store = VoiceStore(
        AppConfig("base", "rev", "fine", "rev", tmp_path / "data")
    )
    with pytest.raises(ValueError):
        store.remove(name)
