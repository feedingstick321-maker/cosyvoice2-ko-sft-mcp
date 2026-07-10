from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from threading import Lock
from typing import Any

from .config import AppConfig


class ModelManager:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.config.ensure_directories()
        self._model: Any | None = None
        self._load_lock = Lock()

    def status(self) -> dict[str, object]:
        llm_path = self.config.model_dir / "llm.safetensors"
        payload: dict[str, object] = {
            "ready": self.is_ready(),
            "data_dir": str(self.config.data_dir),
            "model_dir": str(self.config.model_dir),
            "base_repo": self.config.base_repo,
            "base_revision": self.config.base_revision,
            "finetune_repo": self.config.finetune_repo,
            "finetune_revision": self.config.finetune_revision,
            "llm_sha256": self._sha256(llm_path) if llm_path.is_file() else None,
            "loaded": self._model is not None,
        }
        try:
            import torch

            payload.update(
                {
                    "torch": torch.__version__,
                    "cuda_available": torch.cuda.is_available(),
                    "cuda_version": torch.version.cuda,
                    "gpu_count": torch.cuda.device_count(),
                    "gpus": [
                        {
                            "index": index,
                            "name": torch.cuda.get_device_name(index),
                            "total_vram_gib": round(
                                torch.cuda.get_device_properties(index).total_memory
                                / (1024**3),
                                2,
                            ),
                        }
                        for index in range(torch.cuda.device_count())
                    ],
                }
            )
        except ImportError:
            payload.update({"torch": None, "cuda_available": False, "gpus": []})
        return payload

    def is_ready(self) -> bool:
        required = (
            "cosyvoice2.yaml",
            "llm.safetensors",
            "flow.pt",
            "hift.pt",
            "campplus.onnx",
            "speech_tokenizer_v2.onnx",
        )
        return all((self.config.model_dir / name).is_file() for name in required)

    def prepare(self, force: bool = False) -> dict[str, object]:
        if self.is_ready() and not force:
            return self.status()

        from huggingface_hub import hf_hub_download, snapshot_download

        snapshot_download(
            repo_id=self.config.base_repo,
            revision=self.config.base_revision,
            local_dir=self.config.model_dir,
        )
        downloaded_llm = Path(
            hf_hub_download(
                repo_id=self.config.finetune_repo,
                revision=self.config.finetune_revision,
                filename="llm.safetensors",
            )
        )
        destination = self.config.model_dir / "llm.safetensors"
        shutil.copy2(downloaded_llm, destination)

        expected_hash = self._download_expected_hash(hf_hub_download)
        actual_hash = self._sha256(destination)
        if expected_hash is not None and actual_hash != expected_hash:
            destination.unlink(missing_ok=True)
            raise RuntimeError(
                f"Model checksum mismatch: expected {expected_hash}, got {actual_hash}"
            )

        manifest = {
            "base_repo": self.config.base_repo,
            "base_revision": self.config.base_revision,
            "finetune_repo": self.config.finetune_repo,
            "finetune_revision": self.config.finetune_revision,
            "llm_sha256": actual_hash,
        }
        self.config.manifest_path.write_text(
            json.dumps(manifest, indent=2),
            encoding="utf-8",
        )
        return self.status()

    def load(self) -> Any:
        with self._load_lock:
            if self._model is not None:
                return self._model
            if not self.is_ready():
                self.prepare()
            repo_root = Path(__file__).resolve().parents[2]
            matcha_root = repo_root / "third_party" / "Matcha-TTS"
            for path in (repo_root, matcha_root):
                path_text = str(path)
                if path_text not in sys.path:
                    sys.path.insert(0, path_text)
            from cosyvoice.cli.cosyvoice import CosyVoice2

            fp16 = os.environ.get("COSYVOICE_KO_FP16", "1") == "1"
            self._model = CosyVoice2(
                str(self.config.model_dir),
                load_jit=False,
                load_trt=False,
                load_vllm=False,
                fp16=fp16,
            )
            return self._model

    def _download_expected_hash(self, downloader: Any) -> str | None:
        try:
            checksum_path = Path(
                downloader(
                    repo_id=self.config.finetune_repo,
                    revision=self.config.finetune_revision,
                    filename="checksums.sha256",
                )
            )
        except Exception:
            return None
        for line in checksum_path.read_text(encoding="utf-8").splitlines():
            fields = line.strip().split()
            if len(fields) == 2 and fields[1].lstrip("*") == "llm.safetensors":
                return fields[0].lower()
        return None

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
