"""분기 실적과 주가 연동 차트 (1920x1080, 영상용 다크 배경).
데이터: data/hynix_quarterly_2021_2026.json (DART), data/hynix_price_daily.csv (네이버 금융 일별 종가)
실행: python3 scripts/make_charts_quarterly.py
"""
import json, csv, glob, os
from datetime import datetime, timedelta
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager as fm
from matplotlib.ticker import FixedLocator, FuncFormatter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for f in glob.glob(os.path.expanduser("~/.fonts/*.ttf")):
    fm.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans KR"; plt.rcParams["axes.unicode_minus"] = False
SURF, INK, INK2, GRID = "#1a1a19", "#ffffff", "#c3c2b7", "#383835"
BLUE, ORANGE, AQUA, RED = "#3987e5", "#d95926", "#199e70", "#e66767"

q = json.load(open(os.path.join(ROOT, "data/hynix_quarterly_2021_2026.json"), encoding="utf-8"))
qend = [datetime.strptime(d, "%Y-%m-%d") for d in q["quarter_end"]]
qmid = [d - timedelta(days=45) for d in qend]
op = [v / 1e6 for v in q["영업이익"]]
px = [(datetime.strptime(r["date"], "%Y-%m-%d"), int(r["close"])) for r in csv.DictReader(open(os.path.join(ROOT, "data/hynix_price_daily.csv")))]
px = [(d, c) for d, c in px if d >= datetime(2021, 1, 1)]
pd_, pc = zip(*px)

def style(ax):
    ax.set_facecolor(SURF)
    for s in ["top", "right", "left"]: ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID); ax.tick_params(colors=INK2, labelsize=18, length=0)
    ax.yaxis.grid(True, color=GRID, linewidth=1); ax.set_axisbelow(True)

# ---------- 06. 주가 vs 분기 영업이익 (두 패널, x축 공유) ----------
f, (a1, a2) = plt.subplots(2, 1, figsize=(19.2, 10.8), dpi=100, sharex=True, gridspec_kw={"height_ratios": [1.15, 1], "hspace": 0.08})
f.patch.set_facecolor(SURF); style(a1); style(a2)
a1.plot(pd_, pc, color=BLUE, linewidth=2.2)
a1.set_yscale("log")
ticks = [70000, 100000, 150000, 200000, 300000, 500000, 1000000, 2000000, 3000000]
a1.yaxis.set_major_locator(FixedLocator(ticks)); a1.yaxis.set_minor_locator(FixedLocator([]))
a1.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v/10000:.0f}만"))
a1.set_ylim(65000, 4800000)
colors = [BLUE if v >= 0 else RED for v in op]
a2.bar(qmid, op, width=70, color=colors)
a2.axhline(0, color=INK2, linewidth=1)
for d, v in zip(qmid, op):
    a2.text(d, v + (1.2 if v >= 0 else -1.2), f"{v:.1f}", ha="center", va="bottom" if v >= 0 else "top", color=INK, fontsize=15)
a2.set_ylim(-8, 70)
a2.xaxis.set_major_locator(mdates.YearLocator()); a2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
a2.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=[4, 7, 10]))
a1.set_xlim(datetime(2021, 1, 1), datetime(2027, 1, 15))

def mark(date, label, y_frac, color=ORANGE, ax=a1, dy=0):
    for ax_ in (a1, a2): ax_.axvline(date, color=color, linewidth=1.2, linestyle="--", alpha=0.9)
    a1.text(date, 3300000 * (1 - y_frac * 0.0), label, color=color, fontsize=16, ha="center", va="top", transform=a1.get_xaxis_transform() if False else a1.transData)
# 이벤트
events = [
    (datetime(2021, 2, 25), "① 주가 고점 14.9만\n(2021.2)", 0),
    (datetime(2021, 11, 15), "② 영업이익 고점\n4Q21~2Q22", 0),
    (datetime(2022, 12, 29), "③ 주가 저점 7.5만\n(2022.12)", 0),
    (datetime(2023, 2, 15), "④ 영업이익 저점\n1Q23 −3.4조", 0),
    (datetime(2026, 6, 22), "⑤ 주가 고점 292만\n(2026.6)", 0),
    (datetime(2026, 7, 29), "⑥ 2Q 발표일 −9.6%", 0),
]
pos = {0: (4600000, "center", 0), 1: (1700000, "center", 0), 2: (4600000, "center", 0), 3: (1700000, "center", 0), 4: (300000, "right", -8), 5: (300000, "left", 8)}
for i, (d, label, _) in enumerate(events):
    c = ORANGE if ("주가" in label or "발표" in label) else AQUA
    for ax_ in (a1, a2): ax_.axvline(d, color=c, linewidth=1.2, linestyle="--", alpha=0.9)
    y, ha, dx = pos[i]
    a1.text(d + timedelta(days=dx), y, label, color=c, fontsize=15, ha=ha, va="top", bbox=dict(facecolor=SURF, edgecolor="none", pad=2))
a1.text(datetime(2021, 1, 10), 80000, "주가 (종가, 원 · 로그 눈금)", color=INK2, fontsize=17, va="bottom")
a2.text(datetime(2021, 1, 10), 62, "분기 영업이익 (조 원)", color=INK2, fontsize=17, va="top")
f.text(0.06, 0.94, "분기 실적과 주가를 겹쳐 보면: 주가가 먼저 움직인다", color=INK, fontsize=38, fontweight="bold")
f.text(0.06, 0.895, "위: SK하이닉스 일별 종가 (2021.1~2026.9)  ·  아래: 분기 영업이익 (조 원, 분기 중간에 표시)  ·  주황 = 주가 전환점, 초록 = 이익 전환점", color=INK2, fontsize=19)
f.text(0.94, 0.02, "출처: DART 분기·사업보고서 (영업이익), 네이버 금융 (종가)", color=INK2, fontsize=15, ha="right")
plt.subplots_adjust(left=0.06, right=0.94, top=0.86, bottom=0.07)
f.savefig(os.path.join(ROOT, "charts/06_주가_분기영업이익_연동.png"), facecolor=SURF); plt.close(f); print("saved 06")

# ---------- 07. 실적 발표 당일 주가 반응 ----------
ann = [  # (분기, 잠정실적 발표일)
    ("4Q21", "2022-01-28"), ("1Q22", "2022-04-27"), ("2Q22", "2022-07-27"), ("3Q22", "2022-10-26"),
    ("4Q22", "2023-02-01"), ("1Q23", "2023-04-26"), ("2Q23", "2023-07-26"), ("3Q23", "2023-10-26"),
    ("4Q23", "2024-01-25"), ("1Q24", "2024-04-25"), ("2Q24", "2024-07-25"), ("3Q24", "2024-10-24"),
    ("4Q24", "2025-01-23"), ("1Q25", "2025-04-24"), ("2Q25", "2025-07-24"), ("3Q25", "2025-10-29"),
    ("4Q25", "2026-01-28"), ("1Q26", "2026-04-23"), ("2Q26", "2026-07-29"),
]
allpx = [(r["date"], int(r["close"])) for r in csv.DictReader(open(os.path.join(ROOT, "data/hynix_price_daily.csv")))]
def reaction(day):
    i = next(k for k, (d, _) in enumerate(allpx) if d >= day)
    return (allpx[i][1] / allpx[i - 1][1] - 1) * 100
labels = [a for a, _ in ann]; rx = [reaction(d) for _, d in ann]
opmap = dict(zip(q["periods"], op)); ops = [opmap[a] for a in labels]
f, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100); f.patch.set_facecolor(SURF); style(ax)
x = range(len(labels))
ax.bar(x, rx, 0.6, color=[BLUE if v >= 0 else RED for v in rx])
ax.axhline(0, color=INK2, linewidth=1)
for xi, v, o in zip(x, rx, ops):
    ax.text(xi, v + (0.3 if v >= 0 else -0.3), f"{v:+.1f}%", ha="center", va="bottom" if v >= 0 else "top", color=INK, fontsize=17)
    ax.text(xi, -12.3, f"{o:.1f}조", ha="center", va="top", color=INK2, fontsize=15)
ax.text(-0.5, -11.0, "분기 영업이익 →", ha="right", va="top", color=INK2, fontsize=14)
ax.set_xticks(list(x), labels, fontsize=16); ax.set_ylim(-13.5, 9.5)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:+.0f}%"))
notes = {"4Q25": "①", "1Q26": "②", "2Q26": "③", "2Q24": "④"}
for xi, a in zip(x, labels):
    if a in notes:
        v = rx[xi]; yy = v + (1.6 if v >= 0 else -1.6)
        ax.text(xi, yy, notes[a], ha="center", va="bottom" if v >= 0 else "top", color=ORANGE, fontsize=24, fontweight="bold")
box = ("① 4Q25 (2026.1.28): 19.2조, 예상 크게 상회 → +5.1%\n"
       "② 1Q26 (2026.4.23): 컨센서스 36.4조 vs 실제 37.6조, 상회 → +0.2% (이미 반영)\n"
       "③ 2Q26 (2026.7.29): 컨센서스 63.7조 vs 실제 60.5조, 미달 → 역대 최대인데 −9.6%\n"
       "④ 2Q24 (2024.7.25): 실적은 예상 수준, 하락은 실적 외 요인(글로벌 반도체 급락일)")
ax.text(1.0, 8.6, box, ha="left", va="top", color=INK, fontsize=16, linespacing=1.6, bbox=dict(facecolor=SURF, edgecolor=GRID, pad=8))
ax.set_yticks([-10, -8, -5, -2, 0, 2, 5, 8])
f.text(0.06, 0.94, "실적 발표 당일 주가는 '얼마나 벌었나'가 아니라 '기대와의 차이'에 반응한다", color=INK, fontsize=36, fontweight="bold")
f.text(0.06, 0.895, "분기 잠정실적 발표일 종가 등락률 (전일 대비) · 아래 회색 숫자는 해당 분기 영업이익", color=INK2, fontsize=19)
f.text(0.94, 0.02, "출처: 네이버 금융 일별 종가, DART · 발표일은 회사 잠정실적 공시일 기준", color=INK2, fontsize=15, ha="right")
plt.subplots_adjust(left=0.08, right=0.94, top=0.85, bottom=0.12)
f.savefig(os.path.join(ROOT, "charts/07_실적발표일_주가반응.png"), facecolor=SURF); plt.close(f); print("saved 07")
