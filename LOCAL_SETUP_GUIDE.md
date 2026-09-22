# 🏠 로컬 환경 반자동 핫딜 추적 시스템 설정 가이드

## 📋 개요
이 가이드는 **로컬 컴퓨터**에서 핫딜 추적 시스템을 설정하고 자동으로 실행하도록 하는 방법을 설명합니다.

---

## 🔧 준비 사항

### 1단계: Python 설치 확인
```bash
python3 --version
# 출력: Python 3.8 이상
```

**설치되지 않았다면:**
- Windows: https://www.python.org/downloads/
- Mac: `brew install python3`
- Linux: `sudo apt install python3 python3-pip`

### 2단계: 필요한 라이브러리
이 프로젝트는 **표준 라이브러리만 사용**하므로 추가 설치 불필요!
```python
# 사용되는 라이브러리 (모두 기본 포함)
import urllib.request
import json
import re
import csv
import time
from datetime import datetime
from collections import defaultdict
from pathlib import Path
```

---

## 📁 폴더 구조 설정

로컬 컴퓨터에 다음 구조로 폴더를 만드세요:

```
C:/hotdeal_tracker/  (또는 ~/hotdeal_tracker)
├── dealscan.py           ← 핫딜 수집 스크립트
├── hotdeal_tracker.py    ← 필터링 스크립트
├── dealscan.json         ← 수집된 핫딜 데이터
├── hotdeals_filtered.json ← 필터링된 데이터
├── hotdeal_tracker.csv   ← 추적 기록
├── logs/                 ← 실행 로그 (자동 생성)
│   └── hotdeal_2026-09-22.log
└── README.md
```

### 폴더 만드는 방법

**Windows (PowerShell):**
```powershell
mkdir C:\hotdeal_tracker
cd C:\hotdeal_tracker
mkdir logs
```

**Mac/Linux (Terminal):**
```bash
mkdir -p ~/hotdeal_tracker/logs
cd ~/hotdeal_tracker
```

---

## 📥 파일 다운로드

GitHub에서 다음 파일을 다운로드하여 위 폴더에 저장:

1. **dealscan.py** → https://github.com/wonhee9299/wonee9/blob/claude/korean-sports-communities-ranking-1ngisr/dealscan.py
2. **hotdeal_tracker.py** → https://github.com/wonhee9299/wonee9/blob/claude/korean-sports-communities-ranking-1ngisr/hotdeal_tracker.py
3. **HOTDEAL_GUIDE.md** → 참고용

또는 다음 명령어로 한 번에 클론:
```bash
cd ~
git clone https://github.com/wonhee9299/wonee9.git
cd wonee9
git checkout claude/korean-sports-communities-ranking-1ngisr
```

---

## 🚀 수동 실행 (처음 테스트)

### 1단계: 핫딜 수집
```bash
# 현재 폴더에서
python3 dealscan.py
```

**예상 출력:**
```
##### 클리앙 알뜰구매  최근7일 전체 24건
  등산      1건  [K.Village] 아이더 멤버스 데이 세일 | ...
...
SCAN DONE
```

**소요 시간:** 2~5분 (네트워크 속도에 따라)

### 2단계: 필터링 및 추적
```bash
python3 hotdeal_tracker.py
```

**예상 출력:**
```
🚀 핫딜 자동 모니터링 시작...
🔥 핫딜 모니터링 결과
📊 총 16개 상품 | 새로운 상품 16개

📌 등산: 9개
   ✨ [등산/캠핑] [롯데온] 신일 에코...
...
✅ 16개 새로운 상품 저장됨
```

### 3단계: 결과 확인
```bash
# CSV 파일 열기
cat hotdeal_tracker.csv  # Linux/Mac
type hotdeal_tracker.csv  # Windows

# Excel에서 열기 (그래픽)
# Windows: hotdeal_tracker.csv 더블클릭
# Mac: open hotdeal_tracker.csv
```

---

## ⏰ 자동 실행 설정

### Windows 사용자 (Task Scheduler)

#### 1. Task Scheduler 열기
- **시작 버튼** → "작업 스케줄러" 검색 → 열기

#### 2. 작업 만들기
1. 오른쪽 패널 → **"기본 작업 만들기"** 클릭
2. **이름**: "Daily Hotdeal Tracker"
3. **설명**: "매일 핫딜 자동 추적"
4. **트리거** 탭:
   - "새로 만들기" 클릭
   - **반복**: 매일
   - **시간**: 08:00 (아침 8시)
   - **고급**: "작업을 활성화된 상태로 유지" 체크

5. **작업** 탭:
   - "새로 만들기" 클릭
   - **프로그램**: `C:\Windows\System32\cmd.exe`
   - **인수 추가**:
   ```
   /c cd C:\hotdeal_tracker && python3 dealscan.py && python3 hotdeal_tracker.py >> logs\hotdeal_%date:~-4%%date:~-10,2%%date:~-7,2%.log 2>&1
   ```
   - **시작 위치**: `C:\hotdeal_tracker`

6. **확인** → 저장

#### 3. 테스트
```powershell
# PowerShell을 관리자 권한으로 열기
cd C:\hotdeal_tracker
python3 dealscan.py
python3 hotdeal_tracker.py
```

### Mac/Linux 사용자 (crontab)

#### 1. crontab 편집
```bash
crontab -e
```

#### 2. 다음 라인 추가 (매일 아침 8시)
```cron
0 8 * * * cd ~/hotdeal_tracker && python3 dealscan.py && python3 hotdeal_tracker.py >> logs/hotdeal_$(date +\%Y\%m\%d).log 2>&1
```

#### 3. 저장 및 종료
- Nano 에디터: `Ctrl+O` → `Enter` → `Ctrl+X`
- Vi 에디터: `ESC` → `:wq` → `Enter`

#### 4. 확인
```bash
crontab -l
# 위의 라인이 보여야 함
```

#### 5. 테스트
```bash
cd ~/hotdeal_tracker
python3 dealscan.py
python3 hotdeal_tracker.py
```

---

## 📊 로그 확인

### 실행 로그 보기
```bash
# 최신 로그 보기 (Mac/Linux)
tail -f logs/hotdeal_*.log

# Windows (PowerShell)
Get-Content logs\hotdeal_*.log -Tail 20
```

### 오류 진단

**문제: "dealscan.py not found"**
```bash
# 현재 위치 확인
pwd  # Mac/Linux
cd   # Windows

# 올바른 폴더인지 확인
ls   # Mac/Linux
dir  # Windows
```

**문제: Python 명령 안 됨**
```bash
# Python 경로 확인
which python3        # Mac/Linux
where python         # Windows

# 전체 경로로 실행
/usr/bin/python3 dealscan.py     # Mac/Linux
C:\Python311\python.exe dealscan.py  # Windows
```

**문제: 네트워크 오류**
```
urllib.error.HTTPError: HTTP Error 403

→ 해결: 인터넷 연결 확인, VPN 설정 확인
```

---

## 📱 결과 활용

### 1. CSV 파일 분석
```bash
# 상위 10개 비싼 상품
sort -t',' -k2 -nr hotdeal_tracker.csv | head -10

# 포럼별 상품 수
cut -d',' -f4 hotdeal_tracker.csv | sort | uniq -c
```

### 2. Excel에서 가공
- `hotdeal_tracker.csv` 열기 → "조건부 서식" → 가격 기준으로 색칠
- 필터링: 포럼별 상품만 보기
- 정렬: 최신순, 가격순

### 3. 이메일 알림 추가 (선택)
```bash
# 새 상품이 있으면 이메일 발송
# Windows: https://github.com/HemulGM/SendMail
# Mac/Linux: mail, sendmail 명령 사용
```

---

## 🔄 매주 유지보수

### 매주 금요일 (예)
```bash
# CSV 백업
cp hotdeal_tracker.csv hotdeal_tracker_backup_$(date +%Y%m%d).csv

# 오래된 로그 정리 (30일 이상)
find logs -name "*.log" -mtime +30 -delete
```

### 월 1회
```bash
# 필터 기준 검토
# - PRICE_THRESHOLD 확인 (충분히 낮은가?)
# - 제외 키워드 업데이트
```

---

## 🎯 주요 설정 커스터마이징

### 가격 기준 변경
**파일**: `hotdeal_tracker.py` 상단
```python
PRICE_THRESHOLD = 30000  # 30,000원
# ↓ 변경
PRICE_THRESHOLD = 50000  # 50,000원 이상만
```

### 실행 시간 변경
**Windows Task Scheduler:**
- 작업 속성 → 트리거 → "시간" 변경

**Mac/Linux crontab:**
```cron
# 기존: 매일 8시
0 8 * * * ...

# 변경: 매일 6시
0 6 * * * ...

# 변경: 평일만 8시
0 8 * * 1-5 ...  (월~금)

# 변경: 매주 월요일 8시
0 8 * * 1 ...
```

### 제외 키워드 추가
**파일**: `hotdeal_tracker.py`
```python
EXCLUDE_KEYWORDS = r'중고|이양|팜|해외직배송'
# ↓ 변경
EXCLUDE_KEYWORDS = r'중고|이양|팜|해외직배송|직구|포워딩'
```

---

## 📞 자주 묻는 질문

### Q: 매일 꼭 실행해야 하나?
**A**: 매일 1회 권장. 새 상품을 놓치지 않기 위해.

### Q: 인터넷 연결이 느리면?
**A**: 자동 재시도 기능 있음. 최대 5회 시도.

### Q: 데이터는 언제 삭제되나?
**A**: 자동 삭제 없음. 수동으로 정리 필요.

### Q: 몇 개 포럼을 추적하나?
**A**: 현재 6개 포럼 (뽐뿌, 딜바다, 빠삭, 아카라이브, 클리앙, 루리웹)

### Q: 커뮤니티는 왜 없나?
**A**: 커뮤니티는 회원 인증 필요 (별도 설정 필요)

---

## 📝 트러블슈팅 체크리스트

- [ ] Python 3.8 이상 설치됨
- [ ] dealscan.py, hotdeal_tracker.py 파일 다운로드됨
- [ ] logs/ 폴더 생성됨
- [ ] 수동 실행으로 테스트 완료
- [ ] 자동 실행 스케줄 설정 완료
- [ ] 첫 번째 자동 실행 로그 확인됨

---

## 🚀 시작하기

1. **지금 바로**: 폴더 만들고 파일 다운로드
2. **첫 테스트**: `python3 dealscan.py` 실행
3. **필터링**: `python3 hotdeal_tracker.py` 실행
4. **자동화**: Task Scheduler 또는 crontab 설정
5. **확인**: 내일 아침 메일 또는 로그 확인

---

**문제 발생 시:**
1. 로그 파일 확인: `logs/hotdeal_*.log`
2. 수동 실행으로 오류 메시지 확인
3. HOTDEAL_GUIDE.md 참고

**업데이트 확인:**
```bash
cd ~/wonee9
git pull origin claude/korean-sports-communities-ranking-1ngisr
```

---

**마지막 업데이트**: 2026-09-22  
**Python 최소 버전**: 3.8+  
**소요 시간**: 2~5분/일
