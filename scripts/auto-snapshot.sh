#!/usr/bin/env bash
#
# 작업 폴더를 주기적으로 NAS 에 스냅샷으로 올린다.
#
# cron 등록 예 (매일 오전 3시):
#   0 3 * * * /경로/wonee9/scripts/auto-snapshot.sh /경로/내작업폴더 >> /tmp/nas-snapshot.log 2>&1
#
# macOS launchd 나 Windows 작업 스케줄러(WSL) 에서도 같은 방식으로 씁니다.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-$PWD}"
KEEP_LOCAL="${KEEP_LOCAL:-}"   # 값을 주면 그 폴더에 로컬 사본도 남긴다

if [[ ! -d "$TARGET" ]]; then
  echo "대상 폴더가 없습니다: $TARGET" >&2
  exit 1
fi

echo "[$(date '+%F %T')] 스냅샷 시작: $TARGET"

args=(snapshot "$TARGET")
if [[ -n "$KEEP_LOCAL" ]]; then
  args+=(--keep "$KEEP_LOCAL")
fi

# 일시적인 네트워크 문제로 백업을 통째로 놓치지 않도록 재시도한다.
delay=5
for attempt in 1 2 3; do
  if "$ROOT/nas" "${args[@]}"; then
    echo "[$(date '+%F %T')] 완료"
    exit 0
  fi
  echo "시도 ${attempt} 실패 - ${delay}초 후 재시도" >&2
  sleep "$delay"
  delay=$(( delay * 2 ))
done

echo "[$(date '+%F %T')] 3회 모두 실패" >&2
exit 1
