from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import torch
from safetensors.torch import load_file, save_file


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert a CosyVoice state dict to safetensors.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--dtype", choices=("float32", "bfloat16"), default="float32")
    args = parser.parse_args()

    source = torch.load(args.input, map_location="cpu", weights_only=True)
    dtype = torch.float32 if args.dtype == "float32" else torch.bfloat16
    tensors = {
        key: value.detach().to(dtype=dtype).contiguous().clone()
        for key, value in source.items()
        if isinstance(value, torch.Tensor)
    }
    if not tensors:
        raise RuntimeError("No tensors were found in the checkpoint.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    save_file(
        tensors,
        str(args.output),
        metadata={
            "format": "pt",
            "source": args.input.name,
            "dtype": args.dtype,
            "epoch": str(source.get("epoch", "unknown")),
            "step": str(source.get("step", "unknown")),
        },
    )

    reloaded = load_file(str(args.output), device="cpu")
    if set(reloaded) != set(tensors):
        raise RuntimeError("Converted checkpoint keys do not match the source checkpoint.")
    for key, tensor in tensors.items():
        if not torch.equal(tensor, reloaded[key]):
            raise RuntimeError(f"Converted tensor mismatch: {key}")

    digest = sha256(args.output)
    checksum_path = args.output.parent / "checksums.sha256"
    checksum_path.write_text(f"{digest}  {args.output.name}\n", encoding="utf-8")
    print(f"saved={args.output}")
    print(f"sha256={digest}")
    print(f"tensors={len(tensors)}")
    print(f"parameters={sum(tensor.numel() for tensor in tensors.values())}")


if __name__ == "__main__":
    main()
