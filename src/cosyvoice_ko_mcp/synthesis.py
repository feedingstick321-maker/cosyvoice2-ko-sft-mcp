from __future__ import annotations

import random
import time
import uuid
from pathlib import Path
from threading import Lock
from typing import Any

import soundfile

from .config import AppConfig
from .model_manager import ModelManager
from .voice_store import VoiceStore


class SynthesisService:
    def __init__(
        self,
        config: AppConfig,
        model_manager: ModelManager,
        voice_store: VoiceStore,
    ) -> None:
        self.config = config
        self.model_manager = model_manager
        self.voice_store = voice_store
        self._synthesis_lock = Lock()

    def synthesize_registered(
        self,
        text: str,
        voice: str,
        speed: float = 1.0,
        seed: int = 1234,
    ) -> dict[str, object]:
        profile = self.voice_store.get(voice)
        return self.synthesize_zero_shot(
            text=text,
            prompt_text=profile.prompt_text,
            prompt_audio_path=profile.audio_path,
            speed=speed,
            seed=seed,
        )

    def synthesize_zero_shot(
        self,
        text: str,
        prompt_text: str,
        prompt_audio_path: str,
        speed: float = 1.0,
        seed: int = 1234,
    ) -> dict[str, object]:
        normalized_text = self._validate_text(text, "text")
        normalized_prompt = self._validate_text(prompt_text, "prompt_text")
        prompt_path = self.voice_store.validate_audio(prompt_audio_path)
        if not 0.5 <= speed <= 2.0:
            raise ValueError("speed must be between 0.5 and 2.0.")
        if not 0 <= seed <= 2_147_483_647:
            raise ValueError("seed must be between 0 and 2147483647.")

        with self._synthesis_lock:
            self._seed_everything(seed)
            model = self.model_manager.load()
            output_path = self._new_output_path()
            started = time.perf_counter()
            output: Any | None = None
            for model_output in model.inference_zero_shot(
                normalized_text,
                normalized_prompt,
                str(prompt_path),
                stream=False,
                speed=speed,
            ):
                output = model_output["tts_speech"].detach().cpu()
                break
            if output is None or output.numel() == 0:
                raise RuntimeError("The model returned no audio.")

            import torchaudio

            torchaudio.save(str(output_path), output, model.sample_rate)
            audio_info = soundfile.info(str(output_path))
            if audio_info.frames <= 0:
                output_path.unlink(missing_ok=True)
                raise RuntimeError("The generated audio file is empty.")
            return {
                "path": str(output_path.resolve()),
                "uri": output_path.resolve().as_uri(),
                "duration_sec": round(float(audio_info.duration), 3),
                "sample_rate": int(audio_info.samplerate),
                "seed": seed,
                "speed": speed,
                "elapsed_sec": round(time.perf_counter() - started, 3),
            }

    def _validate_text(self, value: str, field_name: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field_name} must not be empty.")
        if len(normalized) > self.config.max_text_chars:
            raise ValueError(
                f"{field_name} must be <= {self.config.max_text_chars} characters."
            )
        return normalized

    def _new_output_path(self) -> Path:
        self.config.outputs_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        return self.config.outputs_dir / f"tts-{timestamp}-{uuid.uuid4().hex[:8]}.wav"

    @staticmethod
    def _seed_everything(seed: int) -> None:
        random.seed(seed)
        try:
            import numpy
            import torch

            numpy.random.seed(seed)
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(seed)
        except ImportError:
            return
