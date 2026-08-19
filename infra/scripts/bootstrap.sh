#!/usr/bin/env bash
#
# 처음 한 번 실행. 컨테이너가 쓸 폴더를 NAS 에 만들고 권한을 맞춘다.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

GREEN=$'\033[32m'; RED=$'\033[31m'; OFF=$'\033[0m'
ok()   { printf '%s✓%s %s\n' "$GREEN" "$OFF" "$*"; }
die()  { printf '%s✗%s %s\n' "$RED" "$OFF" "$*" >&2; exit 1; }

[[ -f .env ]] || die ".env 가 없습니다.  cp .env.example .env  후 값을 채우세요."

set -a
# shellcheck disable=SC1091
source <(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' .env)
set +a

DOCKER_ROOT="${DOCKER_ROOT:-/volume1/docker}"
BACKUP_ROOT="${BACKUP_ROOT:-/volume1/backup/infra}"

echo "폴더를 준비합니다."
echo "  데이터: ${DOCKER_ROOT}"
echo "  백업  : ${BACKUP_ROOT}"
echo

# 상위 볼륨이 아예 없으면 경로를 잘못 잡은 것이다. 여기서 잡아 준다.
parent="$(dirname "$DOCKER_ROOT")"
[[ -d "$parent" ]] || die \
  "상위 경로가 없습니다: ${parent}
  시놀로지는 보통 /volume1 입니다. File Station 에서 실제 경로를 확인하고
  .env 의 DOCKER_ROOT 를 고치세요."

for directory in \
  "${DOCKER_ROOT}/caddy/data" \
  "${DOCKER_ROOT}/caddy/config" \
  "${DOCKER_ROOT}/postgres" \
  "${DOCKER_ROOT}/redis" \
  "${DOCKER_ROOT}/uptime-kuma" \
  "${DOCKER_ROOT}/tailscale" \
  "${BACKUP_ROOT}"
do
  if mkdir -p "$directory" 2>/dev/null; then
    ok "$directory"
  else
    die "폴더를 만들 수 없습니다: ${directory}
  권한이 부족합니다. sudo 로 실행하거나, DSM 에서 이 계정에 해당 공유 폴더
  쓰기 권한을 주세요."
  fi
done

# Postgres 는 데이터 폴더가 남에게 열려 있으면 아예 뜨지 않는다.
chmod 700 "${DOCKER_ROOT}/postgres" 2>/dev/null || true
# 백업에는 비밀번호가 들어간 덤프가 들어가므로 좁게 잠근다.
chmod 700 "${BACKUP_ROOT}" 2>/dev/null || true

echo
ok "준비 완료"
echo
echo "다음 단계:"
echo "  ./infra doctor    설정 점검"
echo "  ./infra up        시작"
