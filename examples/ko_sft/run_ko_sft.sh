#!/usr/bin/env bash
set -euo pipefail

: "${QWEN_PRETRAIN_PATH:?Set QWEN_PRETRAIN_PATH to CosyVoice-BlankEN}"
: "${ONNX_PATH:?Set ONNX_PATH to the CosyVoice2 base model directory}"
: "${TRAIN_DATA:?Set TRAIN_DATA to the training data.list}"
: "${CV_DATA:?Set CV_DATA to the validation data.list}"

NUM_GPUS="${NUM_GPUS:-1}"
DIST_BACKEND="${DIST_BACKEND:-nccl}"
OUTPUT_DIR="${OUTPUT_DIR:-exp/ko_sft/llm/torch_ddp}"
TENSORBOARD_DIR="${TENSORBOARD_DIR:-tensorboard/ko_sft/llm/torch_ddp}"
CHECKPOINT="${CHECKPOINT:-${ONNX_PATH}/llm.pt}"

torchrun --standalone --nnodes=1 --nproc_per_node="${NUM_GPUS}" +  cosyvoice/bin/train.py +  --train_engine torch_ddp +  --config examples/ko_sft/conf/cosyvoice2_ko_sft.yaml +  --train_data "${TRAIN_DATA}" +  --cv_data "${CV_DATA}" +  --qwen_pretrain_path "${QWEN_PRETRAIN_PATH}" +  --onnx_path "${ONNX_PATH}" +  --model llm +  --checkpoint "${CHECKPOINT}" +  --model_dir "${OUTPUT_DIR}" +  --tensorboard_dir "${TENSORBOARD_DIR}" +  --ddp.dist_backend "${DIST_BACKEND}" +  --num_workers "${NUM_WORKERS:-2}" +  --prefetch "${PREFETCH:-16}" +  --pin_memory +  --use_amp
