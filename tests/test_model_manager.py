from __future__ import annotations

from pathlib import Path

from cosyvoice_ko_mcp.config import AppConfig
from cosyvoice_ko_mcp.model_manager import ModelManager


def test_ready_requires_complete_model(tmp_path: Path) -> None:
    config = AppConfig("base", "rev", "fine", "rev", tmp_path / "data")
    manager = ModelManager(config)

    assert manager.is_ready() is False
    for name in (
        "cosyvoice2.yaml",
        "llm.safetensors",
        "flow.pt",
        "hift.pt",
        "campplus.onnx",
        "speech_tokenizer_v2.onnx",
    ):
        (config.model_dir / name).touch()

    assert manager.is_ready() is True
