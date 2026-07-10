# Changelog

## 0.1.0 - 2026-07-10

- Publish the Korean SFT v6 Epoch 3 training recipe.
- Add safe safetensors loading for the fine-tuned LLM.
- Add a local stdio MCP server for Claude and Codex.
- Add local voice registration and zero-shot Korean synthesis tools.
- Support PyTorch 2.8/CUDA 12.8 for RTX 3060, RTX 3090, and RTX 5060 Ti-class GPUs.
- Make gradient checkpointing and dynamic batch limits recipe-controlled.
- Remove per-step CUDA cache flushes from the training loop.
- Add Windows/Linux installers, tests, release guards, and model checksums.
