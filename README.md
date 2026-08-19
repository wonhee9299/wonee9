# wonee9 — 시놀로지 NAS 작업 저장소

모든 작업을 시놀로지 NAS에 **저장(save)** 하고 다시 **추출(extract)** 하기 위한 도구입니다.
DSM의 File Station 웹 API를 통해 동작하며, 파이썬 표준 라이브러리만 사용하므로
`pip install` 없이 파이썬 3.8+ 만 있으면 바로 씁니다.

```
./nas snapshot          # 지금 작업 폴더 전체를 NAS에 통째로 저장
./nas restore           # NAS의 가장 최근 스냅샷으로 되돌리기
```

## 왜 이 방식인가

NAS는 보통 집·사무실 네트워크 안에 있어 외부 서비스가 직접 접근할 수 없습니다.
그래서 이 저장소는 **여러분의 PC에서 실행되어 NAS와 직접 통신하는 클라이언트**입니다.
자격 증명은 로컬 `.env`에만 남고 어디에도 전송되지 않습니다.

## 설치

```bash
git clone <이 저장소> && cd wonee9
cp .env.example .env
$EDITOR .env          # NAS 주소, 계정, 비밀번호 입력
./nas check           # 연결 확인
```

`./nas check` 가 성공하면 준비 끝입니다. 실패하면 [docs/SETUP.md](docs/SETUP.md)의
문제 해결 표를 보세요.

## 명령어

| 명령 | 하는 일 |
|------|---------|
| `./nas check` | 연결·로그인·기준 경로를 확인 |
| `./nas ls [경로]` | NAS 폴더 내용 보기 |
| `./nas save <파일\|폴더>` | 파일이나 폴더를 NAS에 올리기 |
| `./nas extract <NAS경로>` | NAS에서 파일이나 폴더 내려받기 |
| `./nas snapshot [폴더]` | 작업 폴더 전체를 tar.gz로 묶어 저장 |
| `./nas snapshots` | 저장된 스냅샷 목록 (최신순) |
| `./nas restore` | 스냅샷 되돌리기 (기본: 최신) |

전역 옵션: `-v` 파일 단위 진행 표시, `--env-file` 다른 설정 파일 사용.

### 저장하기

```bash
./nas save ./보고서.pdf                # 기준 경로 바로 아래에
./nas save ./보고서.pdf --to 문서/2026  # 원하는 하위 폴더에
./nas save ./src --to 코드             # 폴더는 구조를 유지한 채 통째로
```

### 추출하기

```bash
./nas extract 문서/2026/보고서.pdf              # 현재 폴더로
./nas extract 코드 --to ~/작업/받은코드          # 폴더째로
./nas extract snapshots/myapp/myapp-20260819-030000.tar.gz
# tar.gz 는 받은 뒤 자동으로 풀립니다 (--no-unpack 으로 끌 수 있음)
```

### 스냅샷 — "모든 작업"을 한 덩어리로

`snapshot` 은 작업 폴더 전체를 타임스탬프가 붙은 tar.gz 하나로 묶어 올립니다.
`.git`, `node_modules`, `__pycache__`, `.venv`, `*.log`, `.env` 등 재생성 가능하거나
민감한 항목은 기본으로 빠집니다. 더 뺄 것은 작업 폴더의 `.nasignore` 에 적으세요.

```bash
cd ~/작업/myapp
./나스경로/nas snapshot                 # myapp-20260819-143000.tar.gz 로 저장
./나스경로/nas snapshots                # 목록 확인
./나스경로/nas restore --to ~/새폴더     # 다른 PC에서 그대로 복원
```

NAS 안에는 이렇게 쌓입니다:

```
/home/work/                       ← NAS_BASE_PATH
├── snapshots/
│   └── myapp/
│       ├── myapp-20260818-030000.tar.gz
│       └── myapp-20260819-030000.tar.gz   ← restore 가 고르는 최신본
├── 문서/
└── 코드/
```

특정 시점으로 돌아가려면 `--snapshot` 에 파일 이름을 주면 됩니다.
복원 대상 폴더가 비어 있지 않으면 실수 방지를 위해 멈추며, `--force` 로만 덮어씁니다.

### 자동 저장

```bash
# 매일 새벽 3시에 자동 스냅샷
crontab -e
0 3 * * * /경로/wonee9/scripts/auto-snapshot.sh /경로/내작업폴더 >> /tmp/nas-snapshot.log 2>&1
```

일시적 네트워크 오류에 대비해 3회까지 재시도합니다.

## 보안

- 비밀번호는 `.env` 에만 두며, 이 파일은 `.gitignore` 에 등록되어 있습니다.
- 스냅샷은 `.env` 를 기본 제외하므로 자격 증명이 NAS로 새어 나가지 않습니다.
- 2단계 인증을 쓴다면 실행할 때마다 넘기는 편이 안전합니다: `SYNOLOGY_OTP=123456 ./nas snapshot`
- 외부망 접속은 정식 인증서(Let's Encrypt)를 발급받아 `SYNOLOGY_VERIFY_SSL=true` 를 유지하세요.
  DSM 기본 자체 서명 인증서에서만 `false` 를 쓰고, 그때는 내부망에서만 쓰는 것을 권합니다.
- 복원 시 tar 안의 `../` 경로 탈출 시도는 차단됩니다.

## 테스트

실제 NAS 없이도 전 과정을 검증합니다. 가짜 DSM 서버를 띄워 로그인, 목록,
멀티파트 업로드, 다운로드, 스냅샷 왕복까지 확인합니다.

```bash
python3 -m unittest discover -s tests -v
```

## 구조

```
nas                     실행 진입점
nascloud/
├── cli.py              명령어 정의
├── client.py           DSM FileStation API 클라이언트
├── archive.py          tar.gz 스냅샷 생성/복원
├── config.py           .env·환경변수 로딩
└── errors.py           DSM 오류 코드 → 한국어 설명
scripts/auto-snapshot.sh  cron 자동 백업
tests/                  가짜 DSM 서버 기반 통합 테스트
docs/SETUP.md           DSM 설정과 문제 해결
```
