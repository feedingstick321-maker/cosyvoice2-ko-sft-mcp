from __future__ import annotations

import logging
import sys
from dataclasses import asdict

from mcp.server.fastmcp import FastMCP

from .config import AppConfig
from .model_manager import ModelManager
from .synthesis import SynthesisService
from .usage_reporting import UsageReporter
from .voice_store import VoiceStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)

config = AppConfig.from_env()
voice_store = VoiceStore(config)
model_manager = ModelManager(config)
usage_reporter = UsageReporter(config)
synthesis = SynthesisService(config, model_manager, voice_store, usage_reporter)

mcp = FastMCP(
    "CosyVoice2 Korean SFT",
    instructions=(
        "Generate Korean speech locally. Register only reference voices the user has rights to use. "
        "Generated WAV files remain on the local machine."
    ),
)


@mcp.tool()
def model_status() -> dict[str, object]:
    """Check local model files, GPU availability, CUDA, VRAM, and revisions."""
    return model_manager.status()


@mcp.tool()
def usage_reporting_status() -> dict[str, object]:
    """Show whether optional usage reporting is enabled and what it excludes."""
    return usage_reporter.status()


@mcp.tool()
def configure_usage_reporting(
    enabled: bool,
    participant_id: str = "",
) -> dict[str, object]:
    """Explicitly opt in or out; participant_id is optional and user supplied."""
    return usage_reporter.configure(enabled, participant_id)


@mcp.tool()
def report_feedback(score: int, category: str = "", comment: str = "") -> dict[str, object]:
    """Send an optional 1-5 quality score after usage reporting is enabled."""
    return usage_reporter.report_feedback(score, category, comment)


@mcp.tool()
def prepare_model(force: bool = False) -> dict[str, object]:
    """Download the pinned base model and Korean SFT weights, then verify them."""
    return model_manager.prepare(force=force)


@mcp.tool()
def register_voice(name: str, prompt_text: str, prompt_audio_path: str) -> dict[str, object]:
    """Register a user-owned local reference voice for later synthesis."""
    return asdict(voice_store.register(name, prompt_text, prompt_audio_path))


@mcp.tool()
def list_voices() -> list[dict[str, object]]:
    """List local voice profiles. No voice data is sent over the network."""
    return [asdict(profile) for profile in voice_store.list()]


@mcp.tool()
def synthesize(
    text: str,
    voice: str,
    speed: float = 1.0,
    seed: int = 1234,
) -> dict[str, object]:
    """Generate Korean speech with a registered local voice and return the WAV path."""
    return synthesis.synthesize_registered(text, voice, speed=speed, seed=seed)


@mcp.tool()
def synthesize_zero_shot(
    text: str,
    prompt_text: str,
    prompt_audio_path: str,
    speed: float = 1.0,
    seed: int = 1234,
) -> dict[str, object]:
    """Generate Korean speech from one user-owned local reference audio file."""
    return synthesis.synthesize_zero_shot(
        text,
        prompt_text,
        prompt_audio_path,
        speed=speed,
        seed=seed,
    )


@mcp.tool()
def remove_voice(name: str) -> dict[str, object]:
    """Remove one named profile from the local voice store."""
    return {"name": name, "removed": voice_store.remove(name)}


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
