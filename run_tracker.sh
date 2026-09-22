#!/bin/bash
# Mac/Linux 셸 스크립트 - 핫딜 추적 자동 실행
# 사용법: bash run_tracker.sh
#        또는 chmod +x run_tracker.sh && ./run_tracker.sh

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 현재 디렉토리
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 로그 파일
LOGDIR="logs"
LOGFILE="$LOGDIR/hotdeal_$(date +%Y%m%d).log"

# 시작
clear
echo ""
echo "================================================================================"
echo -e "${BLUE}🔥 핫딜 추적 시스템 시작 (Mac/Linux)${NC}"
echo "================================================================================"
echo ""
echo "📅 현재 시간: $(date '+%Y-%m-%d %H:%M:%S')"
echo "📁 현재 위치: $SCRIPT_DIR"
echo ""

# logs 폴더 생성
mkdir -p "$LOGDIR"

# 함수: 로그 기록
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOGFILE"
}

log "=== 핫딜 추적 시작 ==="

# 함수: 오류 처리
error_exit() {
    echo ""
    echo "================================================================================"
    echo -e "${RED}❌ 오류 발생!${NC}"
    echo "================================================================================"
    echo ""
    echo "📋 로그 확인:"
    echo "   cat $LOGFILE"
    echo ""
    echo "💡 일반적인 문제:"
    echo "   1. Python이 설치되지 않음"
    echo "      → python3 --version 확인"
    echo "   2. 인터넷 연결 끊김"
    echo "      → 네트워크 상태 확인"
    echo "   3. 권한 부족"
    echo "      → chmod +x run_tracker.sh 실행"
    echo ""
    log "ERROR: $1"
    exit 1
}

# Python 확인
if ! command -v python3 &> /dev/null; then
    error_exit "Python3가 설치되지 않음"
fi

echo -e "${BLUE}✓ Python 확인: $(python3 --version)${NC}"
log "Python 확인: $(python3 --version)"

# Step 1: dealscan.py 실행
echo ""
echo "📥 Step 1: 핫딜 수집 중... (2~5분 소요)"
log "Step 1: dealscan.py 시작"

if python3 dealscan.py >> "$LOGFILE" 2>&1; then
    echo -e "${GREEN}✅ dealscan.py 완료${NC}"
    log "Step 1 완료"
else
    error_exit "dealscan.py 실행 실패"
fi

# Step 2: hotdeal_tracker.py 실행
echo ""
echo "🔍 Step 2: 필터링 및 추적 중..."
log "Step 2: hotdeal_tracker.py 시작"

if python3 hotdeal_tracker.py >> "$LOGFILE" 2>&1; then
    echo -e "${GREEN}✅ hotdeal_tracker.py 완료${NC}"
    log "Step 2 완료"
else
    error_exit "hotdeal_tracker.py 실행 실패"
fi

# Step 3: 결과 확인
echo ""
echo "📊 Step 3: 결과 생성 확인..."
log "Step 3: 결과 확인"

if [ -f hotdeal_tracker.csv ]; then
    ITEM_COUNT=$(tail -n +2 hotdeal_tracker.csv | wc -l)
    echo -e "${GREEN}✅ CSV 파일 생성됨${NC}"
    echo "   파일: hotdeal_tracker.csv"
    echo "   상품: $ITEM_COUNT개"
    log "결과 파일 생성 완료 ($ITEM_COUNT개 상품)"
else
    echo -e "${YELLOW}⚠️  CSV 파일이 없습니다${NC}"
    log "WARNING: CSV 파일 없음"
fi

# 완료 메시지
echo ""
echo "================================================================================"
echo -e "${GREEN}✅ 완료! 결과를 확인하세요:${NC}"
echo "================================================================================"
echo ""
echo -e "${BLUE}📁 생성된 파일:${NC}"
echo "   - hotdeal_tracker.csv (추적 기록)"
echo "   - hotdeals_filtered.json (필터링된 데이터)"
echo "   - $LOGFILE (실행 로그)"
echo ""
echo -e "${BLUE}📖 다음 단계:${NC}"
echo "   1. hotdeal_tracker.csv 확인:"
echo "      cat hotdeal_tracker.csv"
echo "   2. 각 상품의 링크 확인"
echo "   3. 마음에 드는 상품 구매!"
echo ""
echo -e "${BLUE}📋 로그 확인:${NC}"
echo "   tail -f $LOGFILE"
echo ""
echo "⏰ 자동 실행 설정:"
echo "   crontab -e 에 다음 추가:"
echo "   0 8 * * * cd $SCRIPT_DIR && bash run_tracker.sh"
echo ""

log "=== 핫딜 추적 완료 ==="

exit 0
