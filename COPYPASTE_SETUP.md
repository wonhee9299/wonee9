# 📋 한 번에 복사-붙여넣기 설정

**선택한 OS의 코드를 **전체 복사 → 터미널에 붙여넣기** 하면 됩니다.**

---

## 🪟 Windows 사용자

### 1️⃣ PowerShell에 다음을 복사-붙여넣기
```powershell
mkdir C:\hotdeal_tracker; cd C:\hotdeal_tracker; curl -o dealscan.py https://raw.githubusercontent.com/wonhee9299/wonee9/claude/korean-sports-communities-ranking-1ngisr/dealscan.py; curl -o hotdeal_tracker.py https://raw.githubusercontent.com/wonhee9299/wonee9/claude/korean-sports-communities-ranking-1ngisr/hotdeal_tracker.py; curl -o run_tracker.bat https://raw.githubusercontent.com/wonhee9299/wonee9/claude/korean-sports-communities-ranking-1ngisr/run_tracker.bat; mkdir logs; echo "✅ 파일 다운로드 완료!"; dir
```

### 2️⃣ 테스트 실행 (아래 명령어 복사-붙여넣기)
```powershell
cd C:\hotdeal_tracker; python3 dealscan.py; python3 hotdeal_tracker.py
```

### 3️⃣ 결과 확인
```powershell
cd C:\hotdeal_tracker; type hotdeal_tracker.csv
```

### 4️⃣ 자동 실행 설정 (Task Scheduler)

**PowerShell을 관리자 권한으로 실행 후:**
```powershell
$taskName = "Daily Hotdeal Tracker"
$taskPath = "\\"
$action = New-ScheduledTaskAction -Execute "C:\hotdeal_tracker\run_tracker.bat"
$trigger = New-ScheduledTaskTrigger -Daily -At 8:00AM
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -RunLevel Highest
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Force
Write-Host "✅ 매일 8시에 자동 실행 설정 완료!"
Get-ScheduledTask -TaskName $taskName
```

---

## 🍎 Mac 사용자

### 1️⃣ Terminal에 다음을 복사-붙여넣기
```bash
mkdir -p ~/hotdeal_tracker/logs && cd ~/hotdeal_tracker && curl -o dealscan.py https://raw.githubusercontent.com/wonhee9299/wonee9/claude/korean-sports-communities-ranking-1ngisr/dealscan.py && curl -o hotdeal_tracker.py https://raw.githubusercontent.com/wonhee9299/wonee9/claude/korean-sports-communities-ranking-1ngisr/hotdeal_tracker.py && curl -o run_tracker.sh https://raw.githubusercontent.com/wonhee9299/wonee9/claude/korean-sports-communities-ranking-1ngisr/run_tracker.sh && chmod +x run_tracker.sh && echo "✅ 파일 다운로드 완료!" && ls -la
```

### 2️⃣ 테스트 실행
```bash
cd ~/hotdeal_tracker && bash run_tracker.sh
```

### 3️⃣ 결과 확인
```bash
cd ~/hotdeal_tracker && cat hotdeal_tracker.csv
```

### 4️⃣ 자동 실행 설정 (crontab)

**Terminal에 복사-붙여넣기:**
```bash
crontab -e
```

**에디터가 열리면 마지막 줄에 다음을 추가:**
```cron
0 8 * * * cd ~/hotdeal_tracker && bash run_tracker.sh >> logs/cron_$(date +\%Y\%m\%d).log 2>&1
```

**저장:** `Control+X` → `Y` → `Enter`

**설정 확인:**
```bash
crontab -l
```

---

## 🐧 Linux 사용자 (Ubuntu/Debian)

### 1️⃣ Terminal에 다음을 복사-붙여넣기
```bash
mkdir -p ~/hotdeal_tracker/logs && cd ~/hotdeal_tracker && wget -O dealscan.py https://raw.githubusercontent.com/wonhee9299/wonee9/claude/korean-sports-communities-ranking-1ngisr/dealscan.py && wget -O hotdeal_tracker.py https://raw.githubusercontent.com/wonhee9299/wonee9/claude/korean-sports-communities-ranking-1ngisr/hotdeal_tracker.py && wget -O run_tracker.sh https://raw.githubusercontent.com/wonhee9299/wonee9/claude/korean-sports-communities-ranking-1ngisr/run_tracker.sh && chmod +x run_tracker.sh && echo "✅ 파일 다운로드 완료!" && ls -la
```

(curl이 없으면 wget 사용됨)

### 2️⃣ Python3 설치 확인
```bash
python3 --version
```

**설치 안 되어 있으면:**
```bash
sudo apt update && sudo apt install python3 python3-pip -y
```

### 3️⃣ 테스트 실행
```bash
cd ~/hotdeal_tracker && bash run_tracker.sh
```

### 4️⃣ 결과 확인
```bash
cd ~/hotdeal_tracker && cat hotdeal_tracker.csv
```

### 5️⃣ 자동 실행 설정 (crontab)

**Terminal에 복사-붙여넣기:**
```bash
crontab -e
```

**에디터가 열리면 마지막 줄에 다음을 추가:**
```cron
0 8 * * * cd ~/hotdeal_tracker && bash run_tracker.sh >> logs/cron_$(date +\%Y\%m\%d).log 2>&1
```

**저장:** `Control+X` → `Y` → `Enter`

**설정 확인:**
```bash
crontab -l
```

---

## 📱 모든 OS 공통

### 매일 수동 실행
```bash
# Mac/Linux
cd ~/hotdeal_tracker && bash run_tracker.sh

# Windows (PowerShell)
cd C:\hotdeal_tracker; python3 dealscan.py; python3 hotdeal_tracker.py
```

### 결과 확인
```bash
# CSV 열기
cd ~/hotdeal_tracker && cat hotdeal_tracker.csv  # 터미널에서 보기

# 또는 Excel/Numbers/Google Sheets에서 열기
```

### 로그 확인
```bash
# 최신 로그 보기
cd ~/hotdeal_tracker && tail logs/hotdeal_*.log

# 또는
cd ~/hotdeal_tracker && cat logs/hotdeal_*.log
```

---

## ✅ 체크리스트

- [ ] OS 선택 (Windows / Mac / Linux)
- [ ] 1️⃣ 파일 다운로드 명령어 복사-붙여넣기
- [ ] 2️⃣ 테스트 실행 명령어 복사-붙여넣기
- [ ] ✅ "완료!" 메시지 확인
- [ ] 3️⃣ 결과 확인 명령어 복사-붙여넣기
- [ ] CSV 파일에서 상품 보임
- [ ] 4️⃣ 자동 실행 설정 (선택사항)
- [ ] 내일 아침 자동 실행 확인

---

## 🆘 문제 해결

### "명령어를 찾을 수 없음"
```bash
# Python 경로 확인
which python3  # Mac/Linux
where python   # Windows (PowerShell)

# 설치되지 않음 → LOCAL_SETUP_GUIDE.md 참고
```

### "권한 거부" (Mac/Linux)
```bash
chmod +x ~/hotdeal_tracker/run_tracker.sh
```

### "인터넷 연결 실패"
```bash
# 네트워크 테스트
ping github.com

# 또는 수동으로 파일 다운로드
# https://github.com/wonhee9299/wonee9 방문
# 브랜치: claude/korean-sports-communities-ranking-1ngisr
# 파일: dealscan.py, hotdeal_tracker.py, run_tracker.sh (또는 .bat)
```

### "CSV 파일이 안 보임"
```bash
# 생성 확인
cd ~/hotdeal_tracker && ls -la hotdeal_tracker.csv

# 내용 확인
cat hotdeal_tracker.csv

# Excel에서 열기
open hotdeal_tracker.csv  # Mac
```

---

## 🎯 다음 단계

**Step 1**: 이 파일에서 OS에 맞는 코드 복사  
**Step 2**: 터미널/PowerShell에 붙여넣기  
**Step 3**: Enter 키 누르기  
**Step 4**: "✅ 완료!" 메시지 확인  
**Step 5**: CSV 파일에서 상품 확인  

---

**소요 시간**: 5분  
**복잡도**: ⭐ (매우 간단)  
**보상**: 매일 자동으로 핫딜 추적 🎉

