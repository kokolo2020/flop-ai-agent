#!/usr/bin/env bash
# Run only on the provisioned VM after installation is authorized.
set -euo pipefail
umask 077
if [[ $# != 3 || "$1" != "--authorized-vm" ]]; then
  echo 'Usage: download-qwen.sh --authorized-vm OPERATOR_APPROVED_40_HEX_REV NEW_ABSOLUTE_DIRECTORY' >&2
  exit 1
fi
revision=$2
checkpoint_dir=$3
[[ "$revision" =~ ^[0-9a-f]{40}$ ]] || { echo 'Exact operator-approved HF commit required' >&2; exit 1; }
[[ "$checkpoint_dir" == /* && ! -e "$checkpoint_dir" && ! -L "$checkpoint_dir" ]] || { echo 'Use a fresh absolute checkpoint directory' >&2; exit 1; }
[[ "$(uname -s)" == Linux && "$(uname -m)" == x86_64 ]] || { echo 'Linux x86_64 VM required' >&2; exit 1; }
command -v uvx >/dev/null || { echo 'Install approved uv tooling on the authorized VM first' >&2; exit 1; }
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
mkdir -m 700 "$checkpoint_dir"
uvx --from huggingface_hub hf download Qwen/Qwen2.5-0.5B-Instruct \
  --revision "$revision" --local-dir "$checkpoint_dir"
python3 - "$checkpoint_dir" <<'PY'
import json, shutil, sys
from pathlib import Path
p = Path(sys.argv[1])
# Only download metadata in the freshly created checkpoint directory is removed.
cache = p / '.cache'
if cache.is_symlink():
    raise SystemExit('Refusing unexpected metadata symlink')
if cache.exists():
    shutil.rmtree(cache)
cfg = json.loads((p / 'config.json').read_text())
if cfg.get('model_type') != 'qwen2' or not list(p.glob('*.safetensors')):
    raise SystemExit('Checkpoint structure is unexpected; do not serve')
print('Checkpoint downloaded. Official backend model-root verification is still required.')
PY
