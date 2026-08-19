#!/usr/bin/env bash
#
# 백업에서 복원한다. 되돌릴 수 없는 작업이라 반드시 확인을 받는다.
#
#   ./scripts/restore.sh                    가장 최근 백업으로
#   ./scripts/restore.sh 20260819-040000    특정 시점으로
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

GREEN=$'\033[32m'; RED=$'\033[31m'; YELLOW=$'\033[33m'; OFF=$'\033[0m'
ok()   { printf '%s✓%s %s\n' "$GREEN" "$OFF" "$*"; }
warn() { printf '%s!%s %s\n' "$YELLOW" "$OFF" "$*" >&2; }
die()  { printf '%s✗%s %s\n' "$RED" "$OFF" "$*" >&2; exit 1; }

[[ -f .env ]] || die ".env 가 없습니다."
set -a
# shellcheck disable=SC1091
source <(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' .env)
set +a

DOCKER_ROOT="${DOCKER_ROOT:-/volume1/docker}"
BACKUP_ROOT="${BACKUP_ROOT:-/volume1/backup/infra}"

# ── 복원할 백업 고르기 ──────────────────────────────────────────────────
if [[ $# -ge 1 ]]; then
  SOURCE="${BACKUP_ROOT}/$1"
  [[ -d "$SOURCE" ]] || die "그런 백업이 없습니다: $1
  쓸 수 있는 백업:
$(find "$BACKUP_ROOT" -maxdepth 1 -mindepth 1 -type d -name '20*' -printf '    %f\n' 2>/dev/null | sort -r | head -20)"
else
  SOURCE="$(find "$BACKUP_ROOT" -maxdepth 1 -mindepth 1 -type d -name '20*' | sort | tail -1)"
  [[ -n "$SOURCE" ]] || die "${BACKUP_ROOT} 에 백업이 없습니다."
fi

echo "복원할 백업: $(basename "$SOURCE")  ($(du -sh "$SOURCE" | cut -f1))"
echo "복원 대상  : ${DOCKER_ROOT}"
echo
warn "지금 있는 데이터를 백업 시점의 것으로 덮어씁니다. 되돌릴 수 없습니다."
read -rp "정말 진행하려면 '복원' 이라고 입력하세요: " answer
[[ "$answer" == "복원" ]] || { echo "취소했습니다."; exit 0; }

# ── 서비스 정지 ─────────────────────────────────────────────────────────
echo
echo "서비스를 내립니다..."
docker compose --profile data --profile monitor --profile remote --profile full down || true

# ── 볼륨 복원 ───────────────────────────────────────────────────────────
if [[ -f "${SOURCE}/volumes.tar.gz" ]]; then
  echo "볼륨 복원..."
  mkdir -p "$DOCKER_ROOT"
  tar -xzf "${SOURCE}/volumes.tar.gz" -C "$DOCKER_ROOT"
  ok "볼륨 복원 완료"
else
  warn "volumes.tar.gz 없음 - 건너뜀"
fi

# ── 데이터베이스 복원 ───────────────────────────────────────────────────
if [[ -f "${SOURCE}/postgres.sql.gz" ]]; then
  echo "Postgres 복원..."
  # 덤프를 넣으려면 DB 가 떠 있어야 하므로 postgres 만 먼저 올린다.
  docker compose --profile data up -d postgres
  echo "  기동 대기..."
  for _ in $(seq 1 60); do
    if docker exec infra-postgres pg_isready -U "${POSTGRES_USER:-app}" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  docker exec infra-postgres pg_isready -U "${POSTGRES_USER:-app}" >/dev/null 2>&1 \
    || die "Postgres 가 기동하지 않았습니다. './infra logs postgres' 로 확인하세요."
  if gunzip -c "${SOURCE}/postgres.sql.gz" \
      | docker exec -i infra-postgres psql -U "${POSTGRES_USER:-app}" -d postgres >/dev/null; then
    ok "Postgres 복원 완료"
  else
    die "Postgres 복원 실패"
  fi
fi

echo
ok "복원 완료"
echo "  './infra up' 으로 나머지 서비스를 올리세요."
