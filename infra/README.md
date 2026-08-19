# NAS 인프라

시놀로지 NAS를 **여러 서비스를 돌리는 서버**로 쓰기 위한 구성입니다.
도커 컨테이너로 서비스를 올리고, 하나의 출입구(Caddy)를 통해 접근합니다.

## 무엇이 들어 있나

```
        인터넷 / 내부망
              │
              ▼  포트 8080 하나만 열림
        ┌───────────┐
        │   Caddy   │  ← 출입구. 이름으로 서비스를 찾아준다
        └─────┬─────┘
    ┌─────────┼─────────┐
    ▼         ▼         ▼
 상태감시   로그뷰어   (내 앱)      ← edge 망
                          │
                    ┌─────┴─────┐
                    ▼           ▼
                Postgres      Redis     ← data 망 (외부와 완전 차단)
```

| 계층 | 서비스 | 프로필 | 하는 일 |
|------|--------|--------|---------|
| 출입구 | Caddy | (항상) | 바깥과 통하는 유일한 문. 이름으로 서비스 연결, HTTPS 처리 |
| 데이터 | Postgres, Redis | `data` | 앱이 쓰는 데이터베이스. 외부에 포트를 열지 않음 |
| 관측 | Uptime Kuma, Dozzle | `monitor` | 서비스 생사 감시 + 알림, 컨테이너 로그 열람 |
| 원격 | Tailscale | `remote` | 공유기 포트를 열지 않고 외부에서 접속 |

**설계 원칙:** 바깥에 열리는 포트는 Caddy 하나뿐입니다. 데이터베이스는
`internal` 네트워크에 있어 컨테이너 밖으로 나갈 수 없습니다.

## 시작하기

NAS에 SSH로 접속한 상태에서 진행합니다
(DSM → 제어판 → 터미널 및 SNMP → SSH 서비스 활성화).

```bash
# 1. 코드 받기
cd /volume1/docker
git clone https://github.com/wonhee9299/wonee9
cd wonee9/infra

# 2. 설정 채우기
cp .env.example .env
vi .env                    # DOCKER_ROOT, 비밀번호 등

# 3. 폴더 준비
./scripts/bootstrap.sh

# 4. 점검  ← 문제가 있으면 여기서 다 알려줍니다
./infra doctor

# 5. 시작
./infra up
```

`http://NAS주소:8080` 에서 첫 화면이 보이면 성공입니다.

## 매일 쓰는 명령

```bash
./infra up              # 진입점만 (가장 가벼움)
./infra up monitor      # + 상태감시, 로그뷰어
./infra up full         # 전부
./infra status          # 지금 뭐가 돌고 있나
./infra logs caddy      # 로그 보기 (Ctrl+C 로 종료)
./infra down            # 정지 (데이터는 남습니다)
./infra doctor          # 문제 생기면 먼저 이것부터
```

## 이름으로 접속하기

`status.nas.local` 같은 주소가 열리려면 PC가 그 이름을 NAS 주소로 알아야 합니다.
방법은 두 가지입니다.

**방법 1 — PC의 hosts 파일에 등록** (간단, PC마다 해야 함)

- 윈도우: `C:\Windows\System32\drivers\etc\hosts` (관리자 권한 메모장)
- 맥/리눅스: `/etc/hosts` (`sudo vi /etc/hosts`)

```
192.168.0.10  nas.local status.nas.local logs.nas.local
```

**방법 2 — 공유기나 DNS 서버에 등록** (한 번만, 모든 기기에 적용)

공유기 관리 페이지의 DNS 설정에서 `*.nas.local` 을 NAS 주소로 지정합니다.
Pi-hole이나 AdGuard Home을 쓴다면 거기서 와일드카드로 등록하는 편이 편합니다.

주소가 안 열릴 때는 IP로 먼저 확인해 보세요: `http://192.168.0.10:8080`

## 새 서비스 추가하기

앱 하나를 올린다고 해봅시다. 두 파일만 고치면 됩니다.

**1) `docker-compose.yml` 에 서비스 추가**

```yaml
  myapp:
    <<: *common
    image: 내이미지:태그
    container_name: infra-myapp
    environment:
      TZ: ${TZ:-Asia/Seoul}
      DATABASE_URL: postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
    networks:
      - edge      # Caddy 가 닿아야 하므로
      - data      # DB 를 쓴다면 추가
```

포트는 열지 마세요. Caddy를 통해서만 접근하는 것이 이 구성의 핵심입니다.

**2) `caddy/Caddyfile` 에 경로 추가**

```
{$SITE_SCHEME:http}://myapp.{$BASE_DOMAIN:nas.local} {
	import common
	reverse_proxy myapp:3000
}
```

그리고 `./infra up` 하면 끝입니다.

## 백업

```bash
./infra backup                    # 지금 바로
./infra restore                   # 가장 최근 백업으로 복원
./infra restore 20260819-040000   # 특정 시점으로
```

데이터베이스는 파일을 그대로 복사하지 않고 **덤프**를 뜹니다. 쓰는 도중의
파일을 복사하면 깨질 수 있기 때문입니다. 나머지 볼륨은 tar로 묶습니다.

자동 백업은 cron에 등록하세요:

```bash
# 매일 새벽 4시
0 4 * * * /volume1/docker/wonee9/infra/scripts/backup.sh >> /var/log/infra-backup.log 2>&1
```

오래된 백업은 `BACKUP_KEEP` 개수만 남기고 자동으로 지웁니다(기본 14개).

> NAS 한 대는 백업이 아니라 저장소입니다. 디스크가 통째로 죽으면 백업도
> 같이 죽습니다. DSM의 **Hyper Backup**으로 외부에 한 벌 더 복사해 두세요.

## 외부에서 접속하기

안전한 순서대로입니다.

**1순위 — Tailscale** (권장). 공유기 포트를 하나도 열지 않습니다.

```bash
# .env 에 TS_AUTHKEY 를 채운 뒤
./infra up remote
```
인증키는 https://login.tailscale.com/admin/settings/keys 에서 발급합니다.
DSM 패키지 센터에도 Tailscale이 있어 그쪽이 더 편할 수 있습니다.

**2순위 — 진짜 도메인 + HTTPS.** 도메인이 있다면:

```bash
# .env
BASE_DOMAIN=nas.example.com
SITE_SCHEME=https
ACME_EMAIL=본인@메일주소
CADDY_HTTP_PORT=80
CADDY_HTTPS_PORT=443
```

공유기에서 80, 443 포트를 NAS로 포워딩해야 인증서가 발급됩니다.
Caddy가 Let's Encrypt 인증서를 자동으로 받고 갱신합니다.

**하지 말 것:** 포트만 열고 HTTP로 노출하는 것. 비밀번호가 평문으로 오갑니다.

## 보안 메모

- `.env` 에만 비밀번호가 있고, 이 파일은 `.gitignore` 에 등록되어 있습니다
- Postgres와 Redis는 `internal` 네트워크에 있어 **컨테이너 밖에서 접속 불가**입니다
- Dozzle은 도커 소켓을 **읽기 전용**으로 붙입니다. 그래도 모든 컨테이너 로그를
  볼 수 있으니 외부에 노출하지 마세요
- 백업 폴더는 `700` 으로 잠급니다 (덤프에 데이터가 들어 있음)
- 비밀번호는 `openssl rand -base64 24` 로 만드세요. `doctor` 가 12자 미만이면 잡아냅니다

## 문제 해결

| 증상 | 해결 |
|------|------|
| `docker 를 찾을 수 없습니다` | DSM 패키지 센터에서 **Container Manager** 설치 |
| `도커 데몬에 연결할 수 없습니다` | Container Manager 실행 확인. SSH 계정이 관리자 그룹인지 확인 |
| `DOCKER_ROOT 폴더 없음` | `./scripts/bootstrap.sh` 실행. 그래도 안 되면 `.env` 의 경로 확인 |
| 첫 화면이 안 열림 | `./infra status` 로 caddy 가 `healthy` 인지 확인 → `./infra logs caddy` |
| 포트 충돌 | DSM이 5000/5001을, Web Station이 80/443을 씁니다. `.env` 에서 다른 포트로 |
| 이름 주소만 안 열림 | hosts 파일 등록 확인. IP:포트로는 되는지 먼저 확인 |
| `상위 경로가 없습니다` | 시놀로지 볼륨 이름 확인. `/volume1` 이 아니라 `/volume2` 일 수 있음 |

무엇이든 막히면 **`./infra doctor` 를 먼저 실행**하세요. 도커 설치 여부, 설정
파일, 폴더 권한, 비밀번호 길이, 포트 충돌, compose 문법까지 한 번에 점검합니다.

## 검증 상태

이 구성은 다음까지 실제로 확인했습니다:

- `docker compose config` 로 compose 파일 문법 검증 (full 프로필 포함)
- Postgres/Redis가 외부 포트를 열지 않고 `internal` 망에만 있음을 자동 검사
- `caddy validate` 로 Caddy 설정 검증 (내부망 http / 도메인 https 두 모드)
- Caddy를 실제 기동해 첫 화면, 라우팅, 보안 헤더, 헬스체크 응답 확인
- 헬스체크가 **망가진 설정을 실제로 잡아내는지** 역방향 검증

확인하지 **못한** 것: 시놀로지 실제 하드웨어에서의 기동. 이 환경에는 도커
데몬이 없어 컨테이너를 띄울 수 없었습니다. NAS에서 `./infra doctor` 를
돌려 보시고 문제가 나오면 알려주세요.
