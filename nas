#!/usr/bin/env bash
# nascloud CLI 진입점.
# 현재 작업 디렉터리를 바꾸지 않으므로, 저장소 밖에서 상대 경로를 넘겨도 그대로 동작한다.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
exec "${PYTHON:-python3}" -m nascloud "$@"
