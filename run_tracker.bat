@echo off
REM Windows 배치 파일 - 핫딜 추적 자동 실행
REM 사용법: run_tracker.bat

cd /d %~dp0

echo.
echo ================================================================================
echo 🔥 핫딜 추적 시스템 시작 (Windows)
echo ================================================================================
echo.
echo 현재 시간: %date% %time%
echo 현재 위치: %cd%
echo.

REM 로그 파일 생성
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a%%b)
set logfile=logs\hotdeal_%mydate%.log

REM logs 폴더가 없으면 생성
if not exist logs mkdir logs

echo [%date% %time%] === 핫딜 추적 시작 === >> %logfile%

REM Step 1: dealscan.py 실행
echo.
echo 📥 Step 1: 핫딜 수집 중... (2~5분 소요)
echo [%date% %time%] Step 1: dealscan.py 시작 >> %logfile%

python3 dealscan.py >> %logfile% 2>&1

if errorlevel 1 (
    echo ❌ 오류 발생! dealscan.py 실행 실패
    echo [%date% %time%] ERROR: dealscan.py 실패 >> %logfile%
    goto error
)

echo ✅ dealscan.py 완료
echo [%date% %time%] Step 1 완료 >> %logfile%

REM Step 2: hotdeal_tracker.py 실행
echo.
echo 🔍 Step 2: 필터링 및 추적 중...
echo [%date% %time%] Step 2: hotdeal_tracker.py 시작 >> %logfile%

python3 hotdeal_tracker.py >> %logfile% 2>&1

if errorlevel 1 (
    echo ❌ 오류 발생! hotdeal_tracker.py 실행 실패
    echo [%date% %time%] ERROR: hotdeal_tracker.py 실패 >> %logfile%
    goto error
)

echo ✅ hotdeal_tracker.py 완료
echo [%date% %time%] Step 2 완료 >> %logfile%

REM Step 3: 결과 확인
echo.
echo 📊 Step 3: 결과 생성 확인...
echo [%date% %time%] Step 3: 결과 확인 >> %logfile%

if exist hotdeal_tracker.csv (
    echo ✅ CSV 파일 생성됨: hotdeal_tracker.csv
    echo [%date% %time%] 결과 파일 생성 확인 >> %logfile%
) else (
    echo ⚠️  CSV 파일이 없습니다
    echo [%date% %time%] WARNING: CSV 파일 없음 >> %logfile%
)

REM 완료
echo.
echo ================================================================================
echo ✅ 완료! 결과를 확인하세요:
echo ================================================================================
echo.
echo 📁 생성된 파일:
echo   - hotdeal_tracker.csv (추적 기록)
echo   - hotdeals_filtered.json (필터링된 데이터)
echo   - logs\hotdeal_%mydate%.log (실행 로그)
echo.
echo 📖 다음 단계:
echo   1. hotdeal_tracker.csv를 Excel에서 열기
echo   2. 각 상품의 링크 확인
echo   3. 마음에 드는 상품 구매!
echo.
echo 로그 확인: type logs\hotdeal_%mydate%.log
echo.
echo [%date% %time%] === 핫딜 추적 완료 === >> %logfile%

timeout /t 5
exit /b 0

:error
echo.
echo ================================================================================
echo ❌ 오류 발생!
echo ================================================================================
echo.
echo 📋 로그 확인: type %logfile%
echo.
echo 💡 일반적인 문제:
echo   1. Python이 설치되지 않음 → python3 --version 확인
echo   2. 인터넷 연결 끊김 → 네트워크 상태 확인
echo   3. 방화벽 차단 → 방화벽 설정 확인
echo.
timeout /t 10
exit /b 1
