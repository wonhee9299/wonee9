#!/usr/bin/env python3
"""
반자동 핫딜 추적 시스템
- 매일 실행하여 새로운 핫딜 감지
- 40% 이상 할인 추정 상품 추출
- CSV 형식으로 추적 기록 저장
"""

import json
import re
import csv
from datetime import datetime
from collections import defaultdict
from pathlib import Path

# 설정
PRICE_THRESHOLD = 30000  # 30,000원 이상만 추적
EXCLUDE_KEYWORDS = r'중고|이양|판매합니다|구매합니다|찾습니다|팜'
excl_re = re.compile(EXCLUDE_KEYWORDS, re.I)

# 추적 데이터 파일
TRACKER_FILE = Path('hotdeal_tracker.csv')
FILTERED_FILE = Path('hotdeals_filtered.json')

def extract_price(text):
    """텍스트에서 가격 추출"""
    match = re.search(r'(\d+(?:\.?\d+)?)\s*만원|(\d{1,3}(?:,\d{3})*)\s*원', text)
    if match:
        if match.group(1):
            return int(float(match.group(1)) * 10000)
        else:
            return int(match.group(2).replace(',', ''))
    return None

def load_dealscan():
    """dealscan.json 로드"""
    if not Path('dealscan.json').exists():
        print("❌ dealscan.json 없음. 먼저 dealscan.py 실행하세요.")
        return None

    with open('dealscan.json') as f:
        return json.load(f)

def filter_hotdeals(dealscan):
    """핫딜 필터링"""
    results = defaultdict(list)

    for site, data in dealscan.items():
        for cat, items in data['cats'].items():
            for title, date in items:
                if excl_re.search(title):
                    continue

                price = extract_price(title)
                if price and price >= PRICE_THRESHOLD:
                    results[cat].append({
                        'title': title,
                        'price': price,
                        'date': date,
                        'source': site
                    })

    return results

def load_previous_tracking():
    """이전 추적 데이터 로드"""
    if not TRACKER_FILE.exists():
        return set()

    seen = set()
    with open(TRACKER_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            seen.add(row['title'])
    return seen

def save_tracking(results):
    """추적 데이터 저장"""
    mode = 'a' if TRACKER_FILE.exists() else 'w'

    with open(TRACKER_FILE, mode, encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['title', 'price', 'date', 'source', 'added_date'])

        if mode == 'w':
            writer.writeheader()

        for cat, items in results.items():
            for item in items:
                writer.writerow({
                    'title': item['title'],
                    'price': f"{item['price']:,d}원",
                    'date': item['date'],
                    'source': item['source'],
                    'added_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })

def print_summary(new_items, all_items):
    """결과 출력"""
    print("\n" + "=" * 130)
    print("🔥 핫딜 모니터링 결과")
    print("=" * 130)
    print(f"\n📊 총 {len(all_items)}개 상품 | 새로운 상품 {len(new_items)}개\n")

    cats_order = ['등산', '러닝', '수영', '골프', '자전거', '트레일러닝', '놀이동산', '키즈카페']

    for cat in cats_order:
        new_in_cat = [item for item in new_items if item.get('cat') == cat]
        all_in_cat = [item for item in all_items if item.get('cat') == cat]

        if all_in_cat:
            print(f"📌 {cat}: {len(all_in_cat)}개 (새로운 {len(new_in_cat)}개) 🆕" if new_in_cat else f"📌 {cat}: {len(all_in_cat)}개")

            # 새 상품만 표시
            for item in sorted(new_in_cat, key=lambda x: -x['price']):
                print(f"   ✨ {item['title'][:75]}")
                print(f"      💰 {item['price']:,d}원 | 📅 {item['date']} | 📍 {item['source']}")

def main():
    print("🚀 핫딜 자동 모니터링 시작...")

    # 1. dealscan.json 로드
    dealscan = load_dealscan()
    if not dealscan:
        return

    # 2. 필터링
    results = filter_hotdeals(dealscan)

    # 3. 이전 데이터와 비교
    previous = load_previous_tracking()

    all_items = []
    new_items = []

    for cat, items in results.items():
        for item in items:
            item_with_cat = {**item, 'cat': cat}
            all_items.append(item_with_cat)

            if item['title'] not in previous:
                new_items.append(item_with_cat)

    # 4. 결과 출력
    print_summary(new_items, all_items)

    # 5. 추적 데이터 저장
    if new_items:
        save_tracking(results)
        print(f"\n✅ {len(new_items)}개 새로운 상품 저장됨")
    else:
        print("\nℹ️  새로운 상품 없음")

    # 6. JSON 저장
    output = {
        'generated_at': datetime.now().isoformat(),
        'total': len(all_items),
        'new': len(new_items),
        'categories': results
    }

    with open(FILTERED_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"📁 {FILTERED_FILE} 저장됨")
    print("=" * 130)

if __name__ == '__main__':
    main()
