from __future__ import annotations

import re
import subprocess
from pathlib import Path

FORBIDDEN_SUFFIXES = {".pt", ".wav", ".flac", ".parquet", ".tar"}
ALLOWED_UPSTREAM_ARTIFACTS = {
    "asset/cross_lingual_prompt.wav",
    "asset/zero_shot_prompt.wav",
}
SECRET_PATTERNS = (
    re.compile(r"hf_[A-Za-z0-9]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
)
PRIVATE_PATHS = ("C:\\Users\\User", "D:\\영상연습", "/mnt/d/영상연습", "/root/")
REQUIRED = (
    "LICENSE",
    "NOTICE",
    "README.md",
    "pyproject.toml",
    "src/cosyvoice_ko_mcp/server.py",
    "examples/ko_sft/conf/cosyvoice2_ko_sft.yaml",
)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    tracked = [root / line for line in result.stdout.splitlines() if line]
    errors: list[str] = []

    for relative in REQUIRED:
        if not (root / relative).is_file():
            errors.append(f"missing required file: {relative}")

    for path in tracked:
        relative = path.relative_to(root).as_posix()
        if (
            path.suffix.lower() in FORBIDDEN_SUFFIXES
            and relative not in ALLOWED_UPSTREAM_ARTIFACTS
        ):
            errors.append(f"forbidden tracked artifact: {relative}")
        if path.is_file() and path.stat().st_size > 50 * 1024 * 1024:
            errors.append(f"tracked file exceeds 50 MiB: {relative}")
        if not path.is_file() or path.suffix.lower() in {".png", ".jpg", ".jpeg", ".onnx"}:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                errors.append(f"possible secret in {relative}: {pattern.pattern}")
        if relative != "scripts/validate_release.py":
            for private_path in PRIVATE_PATHS:
                if private_path in content:
                    errors.append(f"private absolute path in {relative}: {private_path}")

    if errors:
        raise SystemExit("\n".join(errors))
    print(f"release validation passed: {len(tracked)} tracked files")


if __name__ == "__main__":
    main()
