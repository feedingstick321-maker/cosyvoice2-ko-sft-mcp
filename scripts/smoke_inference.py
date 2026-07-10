from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one local CosyVoice2 synthesis smoke test.")
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--prompt-audio", type=Path, required=True)
    parser.add_argument("--prompt-text", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fp16", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "third_party" / "Matcha-TTS"))
    sys.path.insert(0, str(repo_root))

    import soundfile
    import torchaudio

    from cosyvoice.cli.cosyvoice import CosyVoice2

    model = CosyVoice2(
        str(args.model_dir.resolve()),
        load_jit=False,
        load_trt=False,
        load_vllm=False,
        fp16=args.fp16,
    )
    import torch

    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for result in model.inference_zero_shot(
        args.text,
        args.prompt_text,
        str(args.prompt_audio.resolve()),
        stream=False,
    ):
        torchaudio.save(str(args.output), result["tts_speech"].cpu(), model.sample_rate)
        break
    info = soundfile.info(str(args.output))
    if info.frames <= 0:
        raise RuntimeError("Smoke test produced empty audio.")
    print(f"output={args.output}")
    print(f"duration_sec={info.duration:.3f}")
    print(f"sample_rate={info.samplerate}")
    if torch.cuda.is_available():
        print(f"gpu={torch.cuda.get_device_name(0)}")
        print(f"peak_allocated_gib={torch.cuda.max_memory_allocated() / 1024**3:.3f}")
        print(f"peak_reserved_gib={torch.cuda.max_memory_reserved() / 1024**3:.3f}")


if __name__ == "__main__":
    main()
