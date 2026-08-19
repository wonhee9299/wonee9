#!/usr/bin/env bash
#
# 인프라 백업. 데이터베이스는 덤프로, 나머지 볼륨은 tar 로 묶는다.
#
# cron 등록 예 (매일 새벽 4시):
#   0 4 * * * /volume1/docker/wonee9/infra/scripts/backup.sh >> /var/log/infra-backup.log 2>&1
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
KEEP="${BACKUP_KEEP:-14}"
STAMP="$(date +%Y%m%d-%H%M%S)"
DESTINATION="${BACKUP_ROOT}/${STAMP}"

mkdir -p "$DESTINATION" || die "백업 폴더를 만들 수 없습니다: ${DESTINATION}"
echo "[$(date '+%F %T')] 백업 시작 → ${DESTINATION}"

failures=0

# ── 1. Postgres 논리 백업 ───────────────────────────────────────────────
# 파일을 그대로 복사하면 쓰는 중인 상태가 섞여 깨질 수 있으므로 덤프를 뜬다.
if docker ps --format '{{.Names}}' | grep -qx 'infra-postgres'; then
  echo "  Postgres 덤프..."
  if docker exec infra-postgres pg_dumpall -U "${POSTGRES_USER:-app}" \
      | gzip > "${DESTINATION}/postgres.sql.gz"; then
    ok "  postgres.sql.gz ($(du -h "${DESTINATION}/postgres.sql.gz" | cut -f1))"
  else
    warn "  Postgres 덤프 실패"; failures=$((failures+1))
  fi
else
  echo "  Postgres 미실행 - 건너뜀"
fi

# ── 2. Redis 스냅샷 ─────────────────────────────────────────────────────
if docker ps --format '{{.Names}}' | grep -qx 'infra-redis'; then
  echo "  Redis 저장 지시..."
  # BGSAVE 는 비동기라, 끝날 때까지 기다린 뒤 파일을 복사해야 한다.
  if docker exec infra-redis redis-cli --no-auth-warning -a "${REDIS_PASSWORD:-}" BGSAVE >/dev/null; then
    for _ in $(seq 1 30); do
      status="$(docker exec infra-redis redis-cli --no-auth-warning -a "${REDIS_PASSWORD:-}" \
                INFO persistence 2>/dev/null | tr -d '\r' | grep '^rdb_bgsave_in_progress:' | cut -d: -f2)"
      [[ "$status" == "0" ]] && break
      sleep 1
    done
    ok "  Redis 스냅샷 준비됨"
  else
    warn "  Redis BGSAVE 실패"; failures=$((failures+1))
  fi
fi

# ── 3. 볼륨 아카이브 ────────────────────────────────────────────────────
# postgres 데이터 디렉터리는 위에서 덤프를 떴으므로 제외한다.
echo "  볼륨 압축..."
if tar -czf "${DESTINATION}/volumes.tar.gz" \
     -C "$DOCKER_ROOT" \
     --exclude='postgres' \
     --exclude='caddy/data/caddy/locks' \
     . 2>/dev/null; then
  ok "  volumes.tar.gz ($(du -h "${DESTINATION}/volumes.tar.gz" | cut -f1))"
else
  warn "  볼륨 압축 실패"; failures=$((failures+1))
fi

# ── 4. 설정 파일 ────────────────────────────────────────────────────────
# .env 에는 비밀번호가 들어 있으므로 백업 폴더 권한을 좁게 유지한다.
cp docker-compose.yml "${DESTINATION}/" 2>/dev/null || true
cp -r caddy "${DESTINATION}/" 2>/dev/null || true
if [[ -f .env ]]; then
  cp .env "${DESTINATION}/env.backup"
  chmod 600 "${DESTINATION}/env.backup"
fi
chmod 700 "$DESTINATION"
ok "  설정 파일 복사"

# ── 5. 오래된 백업 정리 ─────────────────────────────────────────────────
# 이름이 타임스탬프라 사전순 정렬 = 시간순 정렬이다.
mapfile -t old < <(find "$BACKUP_ROOT" -maxdepth 1 -mindepth 1 -type d -name '20*' | sort | head -n -"$KEEP")
if (( ${#old[@]} > 0 )); then
  for directory in "${old[@]}"; do
    rm -rf "$directory"
    echo "  오래된 백업 삭제: $(basename "$directory")"
  done
fi

total="$(du -sh "$DESTINATION" | cut -f1)"
echo
if (( failures == 0 )); then
  ok "[$(date '+%F %T')] 백업 완료 (${total}) - 보관 중인 백업 $(find "$BACKUP_ROOT" -maxdepth 1 -mindepth 1 -type d -name '20*' | wc -l)개"
else
  die "[$(date '+%F %T')] 백업이 ${failures}건 실패했습니다. 위 메시지를 확인하세요."
fi
