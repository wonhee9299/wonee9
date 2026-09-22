# ⚡ 로컬 환경 빠른 시작 (5분)

## 🎯 목표
컴퓨터에서 매일 자동으로 핫딜을 추적하도록 설정

## 📦 준비물
- Python 3.8 이상 (설치 여부 확인: `python3 --version`)
- 인터넷 연결
- 5분의 시간

---

## 🚀 Step 1: 파일 다운로드 (1분)

### 방법 A: GitHub에서 다운로드 (추천)
```bash
# Terminal/PowerShell에서
cd ~
git clone https://github.com/wonhee9299/wonee9.git
cd wonee9
git checkout claude/korean-sports-communities-ranking-1ngisr
```

### 방법 B: 수동 다운로드
1. GitHub 방문: https://github.com/wonhee9299/wonee9
2. 브랜치 전환: `claude/korean-sports-communities-ranking-1ngisr`
3. 다음 4개 파일 다운로드:
   - `dealscan.py`
   - `hotdeal_tracker.py`
   - `run_tracker.bat` (Windows) 또는 `run_tracker.sh` (Mac/Linux)
4. 폴더 만들기: `~/hotdeal_tracker/` 또는 `C:\hotdeal_tracker\`
5. 파일들을 그 폴더에 저장

---

## ✅ Step 2: 테스트 실행 (3분)

### Windows 사용자
```powershell
# PowerShell 또는 명령 프롬프트에서
cd C:\hotdeal_tracker
run_tracker.bat
```

### Mac/Linux 사용자
```bash
# Terminal에서
cd ~/hotdeal_tracker
bash run_tracker.sh

# 또는 (권한이 필요한 경우)
chmod +x run_tracker.sh
./run_tracker.sh
```

**예상 결과:**
```
📥 Step 1: 핫딜 수집 중... (2~5분 소요)
✅ dealscan.py 완료
🔍 Step 2: 필터링 및 추적 중...
✅ hotdeal_tracker.py 완료
📊 Step 3: 결과 생성 확인...
✅ CSV 파일 생성됨

✅ 완료! 결과를 확인하세요:
   - hotdeal_tracker.csv (16개 상품)
```

---

## 📊 Step 3: 결과 확인 (1분)

### CSV 파일 열기
```bash
# Windows
hotdeal_tracker.csv 더블클릭 (자동으로 Excel 열림)

# Mac
open hotdeal_tracker.csv

# Linux
cat hotdeal_tracker.csv
```

**파일 구조:**
```
title,price,date,source,added_date
"[등산/캠핑] [롯데온] 신일...",501270,09-17,딜바다,2026-09-22
"[의류/잡화] [지마켓]...",137640,09-18,딜바다,2026-09-22
...
```

---

## ⏰ Step 4: 자동화 설정 (1분)

### Windows: Task Scheduler
1. **시작** → "작업 스케줄러" 검색 → 열기
2. **오른쪽 패널** → **"기본 작업 만들기"**
3. **이름**: "Daily Hotdeal"
4. **트리거**: 매일 8:00 AM
5. **작업**: 프로그램 실행
   ```
   프로그램: C:\hotdeal_tracker\run_tracker.bat
   ```
6. **확인** → 저장

### Mac: crontab
```bash
crontab -e
```

다음 라인 추가 (매일 8시):
```cron
0 8 * * * cd ~/hotdeal_tracker && bash run_tracker.sh >> logs/cron.log 2>&1
```

저장: `Ctrl+O` → `Enter` → `Ctrl+X`

### Linux: crontab (Mac과 동일)
```bash
crontab -e
```

다음 라인 추가:
```cron
0 8 * * * cd ~/hotdeal_tracker && bash run_tracker.sh >> logs/cron.log 2>&1
```

---

## ✨ 완료!

**이제:**
- ✅ 매일 자동으로 핫딜 수집
- ✅ 새로운 상품만 CSV에 저장
- ✅ Excel에서 쉽게 분석

**내일 아침 8시에:**
- `hotdeal_tracker.csv` 업데이트됨
- 새 상품 확인 가능
- 각 상품 링크 확인

---

## 🔧 문제 해결

### "Python not found"
```bash
python3 --version
# 설치되지 않으면:
# Windows: python.org에서 다운로드
# Mac: brew install python3
# Linux: sudo apt install python3
```

### "권한 부족" (Mac/Linux)
```bash
chmod +x run_tracker.sh
```

### "인터넷 연결 실패"
- 방화벽 설정 확인
- VPN 활성화 여부 확인
- 인터넷 속도 테스트

### 로그 확인
```bash
# Windows
type logs\hotdeal_20260922.log

# Mac/Linux
cat logs/hotdeal_20260922.log
```

---

## 📱 팁

### 엑셀에서 필터링
1. CSV 파일 열기
2. **데이터** → **자동필터**
3. "source" 열에서 포럼 선택
4. "date" 열에서 최신순 정렬

### 매주 백업
```bash
# CSV 파일 복사
cp hotdeal_tracker.csv hotdeal_backup_$(date +%Y%m%d).csv
```

### 조건 커스터마이징
**파일**: `hotdeal_tracker.py` 상단
```python
PRICE_THRESHOLD = 30000  # 30,000원 이상만
# → 변경해서 세 번 저장

# 다시 실행
bash run_tracker.sh  # Mac/Linux
run_tracker.bat      # Windows
```

---

## 📞 자주 묻는 질문

**Q: 매일 꼭 해야 하나?**
- A: 아니오. 자동 설정하면 자동으로 실행됨.

**Q: CSV 파일은 계속 누적되나?**
- A: 예. `hotdeal_tracker.csv`에 계속 추가됨.

**Q: 포함 항목은?**
- A: 새 제품 (중고 제외), 30,000원 이상, 가격 정보 있음

**Q: 커뮤니티는?**
- A: 현재는 일반 포럼만 지원. 커뮤니티는 별도 설정 필요.

**Q: 언제 결과를 확인할 수 있나?**
- A: 설정 후 다음 날 아침 또는 수동 실행 후 5분

---

## 🎯 다음 단계

**지금**: 이 가이드 따라 하기 (5분)  
**내일 아침**: `hotdeal_tracker.csv` 확인  
**매일**: 새 상품 모니터링  
**선택**: 정가 데이터베이스 추가 (더 정확한 할인율)  

---

**문제 발생 시**: `LOCAL_SETUP_GUIDE.md` 참고

**마지막 업데이트**: 2026-09-22  
**시간 소요**: 5분 (처음), 0분 (자동 후)
