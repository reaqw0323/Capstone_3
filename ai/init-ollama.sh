#!/bin/sh
set -eu

OLLAMA_URL="${OLLAMA_HOST:-http://ollama:11434}"
BASE_MODEL="${BASE_MODEL:-qwen3:4b}"
SHOP_MODEL="${SHOP_MODEL:-easypick-ai}"

echo "[ollama-init] Waiting for Ollama server at ${OLLAMA_URL}..."
until ollama list >/dev/null 2>&1; do
  sleep 3
  echo "[ollama-init] Ollama is not ready yet. Retrying..."
done

echo "[ollama-init] Pulling base model: ${BASE_MODEL}"
ollama pull "${BASE_MODEL}"

echo "[ollama-init] Creating EasyPick model: ${SHOP_MODEL}"
ollama create "${SHOP_MODEL}" -f /ai/Modelfile

echo "[ollama-init] Available models:"
ollama list

echo "[ollama-init] EasyPick AI model is ready."
