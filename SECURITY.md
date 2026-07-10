# Security Policy

## Reporting

Report suspected vulnerabilities through GitHub private vulnerability reporting. Do not include
private reference audio, generated speech, access tokens, or personal filesystem paths in a public
issue.

## Local Data

The MCP server has no telemetry and no hosted inference endpoint. Voice profiles and generated WAV
files remain in the configured local data directory. The tools reject remote audio URLs and confine
managed output to that directory.

## Model Files

The installer downloads pinned Hugging Face revisions and verifies the fine-tuned LLM with SHA-256.
Never load an untrusted PyTorch pickle. This project prefers safetensors for the released LLM.
