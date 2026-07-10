from __future__ import annotations

import argparse
import json

from .config import AppConfig
from .model_manager import ModelManager


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare the local CosyVoice2 Korean model cache.")
    parser.add_argument("--force", action="store_true", help="Download and verify again.")
    args = parser.parse_args()
    status = ModelManager(AppConfig.from_env()).prepare(force=args.force)
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
