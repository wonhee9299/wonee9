"""SK하이닉스 5년 재무 추이 차트 생성 (1920x1080, 영상용 다크 배경).
데이터: data/hynix_financials_2021_2026H1.json (DART 연결재무제표)
실행: python3 scripts/make_charts.py
"""
import json, glob, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for f in glob.glob(os.path.expanduser("~/.fonts/*.ttf")):
    fm.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans KR"
plt.rcParams["axes.unicode_minus"] = False

d = json.load(open(os.path.join(ROOT, "data/hynix_financials_2021_2026H1.json"), encoding="utf-8"))
P = d["periods"]
T = lambda k: [v / 1e6 for v in d[k]]  # 백만원 -> 조원

# 팔레트 (dataviz 기본 팔레트, 다크 모드 값 - 검증 통과: #3987e5,#d95926,#199e70)
SURF, INK, INK2, GRID = "#1a1a19", "#ffffff", "#c3c2b7", "#383835"
BLUE, ORANGE, AQUA, RED, BLUE_L = "#3987e5", "#d95926", "#199e70", "#e66767", "#86b6ef"
x = np.arange(len(P))
labels = ["2021", "2022", "2023", "2024", "2025", "2026.6\n(상반기)"]


def fig():
    f, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100)
    f.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=20, length=0)
    ax.yaxis.grid(True, color=GRID, linewidth=1); ax.set_axisbelow(True)
    return f, ax


def finish(f, ax, title, sub, fn, unit="조 원"):
    f.text(0.06, 0.93, title, color=INK, fontsize=40, fontweight="bold", ha="left")
    f.text(0.06, 0.885, sub, color=INK2, fontsize=22, ha="left")
    f.text(0.06, 0.835, f"단위: {unit}", color=INK2, fontsize=18, ha="left")
    f.text(0.94, 0.025, "출처: DART 연결재무제표 (2026.6은 반기 누적)", color=INK2, fontsize=16, ha="right")
    plt.subplots_adjust(left=0.06, right=0.94, top=0.80, bottom=0.13)
    out = os.path.join(ROOT, fn)
    f.savefig(out, facecolor=SURF); plt.close(f); print("saved", fn)


def lab(ax, xs, ys, fmt="{:+.1f}", dy=1.5, color=INK, fs=20):
    for xi, yi in zip(xs, ys):
        ax.text(xi, yi + (dy if yi >= 0 else -dy), fmt.format(yi), ha="center",
                va="bottom" if yi >= 0 else "top", color=color, fontsize=fs)


# 1. 매출·영업이익
f, ax = fig(); w = 0.38
ax.bar(x - w / 2, T("매출액"), w, color=BLUE, label="매출액")
ax.bar(x + w / 2, T("영업이익"), w, color=ORANGE, label="영업이익")
lab(ax, x - w / 2, T("매출액"), "{:.1f}"); lab(ax, x + w / 2, T("영업이익"), "{:.1f}")
ax.axhline(0, color=INK2, linewidth=1); ax.set_xticks(x, labels)
ax.legend(loc="upper left", frameon=False, fontsize=20, labelcolor=INK)
finish(f, ax, "5년 손익 추이: 사이클의 바닥에서 반기 98조까지",
       "매출액과 영업이익 · 2023년 영업손실 −7.7조 → 2026년 상반기 영업이익 98.2조", "charts/01_손익추이.png")

# 2. 자산 구성 (부채 / 이익잉여금 / 기타자본)
f, ax = fig()
re_ = T("이익잉여금"); other = [a - b for a, b in zip(T("자본총계"), re_)]; debt = T("부채총계")
ax.bar(x, re_, 0.6, color=BLUE, label="이익잉여금")
ax.bar(x, other, 0.6, bottom=re_, color=BLUE_L, label="자본금·자본잉여금 등")
ax.bar(x, debt, 0.6, bottom=[a + b for a, b in zip(re_, other)], color=ORANGE, label="부채총계")
for xi, (r, o, dd) in enumerate(zip(re_, other, debt)):
    ax.text(xi, r / 2, f"{r:.0f}", ha="center", va="center", color=INK, fontsize=22, fontweight="bold")
    ax.text(xi, r + o + dd / 2, f"{dd:.0f}", ha="center", va="center", color=INK, fontsize=20)
    ax.text(xi, r + o + dd + 4, f"자산 {r + o + dd:.0f}", ha="center", va="bottom", color=INK2, fontsize=18)
ax.set_xticks(x, labels); ax.legend(loc="upper left", frameon=False, fontsize=20, labelcolor=INK)
finish(f, ax, "자산은 어떻게 채워졌나: 빚이 아니라 벌어서 쌓은 잉여금",
       "자산총계 = 부채 + 자본 · 이익잉여금 55.8조(2021) → 46.7조(2023, 적자로 감소) → 242.3조(2026.6)",
       "charts/02_자산구성_이익잉여금.png")

# 3. 재무구조 비율
f, ax = fig()
debt_ratio = [b / c * 100 for b, c in zip(T("부채총계"), T("자본총계"))]
borrow = [a + b for a, b in zip(T("차입금_유동"), T("차입금_비유동"))]
dep = [b / a * 100 for b, a in zip(borrow, T("자산총계"))]
eqr = [c / a * 100 for c, a in zip(T("자본총계"), T("자산총계"))]
for ys, c, name in [(debt_ratio, ORANGE, "부채비율 (부채÷자본)"), (eqr, BLUE, "자기자본비율 (자본÷자산)"),
                    (dep, AQUA, "차입금의존도 (차입금÷자산)")]:
    ax.plot(x, ys, color=c, linewidth=3, marker="o", markersize=10, label=name)
    ax.text(x[-1] + 0.12, ys[-1], f"{ys[-1]:.0f}%", color=INK, fontsize=22, va="center")
    ax.text(x[0] - 0.12, ys[0], f"{ys[0]:.0f}%", color=INK2, fontsize=20, va="center", ha="right")
ax.text(x[2], debt_ratio[2] + 3, f"{debt_ratio[2]:.0f}% (2023 적자 정점)", color=INK, fontsize=20, ha="center")
ax.set_ylim(0, 108); ax.set_xticks(x, labels); ax.set_xlim(-0.6, 5.7)
ax.legend(loc="upper right", frameon=False, fontsize=20, labelcolor=INK, ncol=1)
finish(f, ax, "재무구조 추이: 2023년을 정점으로 빚은 줄고 자기자본은 커졌다",
       "부채비율 87.5% → 32.8%, 차입금의존도 29.4% → 5.3%, 자기자본비율 53.3% → 75.3%",
       "charts/03_재무구조비율.png", unit="%")

# 4. 현금흐름
f, ax = fig(); w = 0.27
ocf = T("영업활동현금흐름")
capex = [-(a + b) for a, b in zip(T("유형자산취득"), T("무형자산취득"))]
fcf = [o + c for o, c in zip(ocf, capex)]
ax.bar(x - w, ocf, w, color=BLUE, label="영업활동현금흐름")
ax.bar(x, capex, w, color=ORANGE, label="설비투자(유형+무형 취득)")
ax.bar(x + w, fcf, w, color=AQUA, label="잉여현금흐름 (FCF)")
lab(ax, x - w, ocf, "{:.1f}"); lab(ax, x, capex, "{:.1f}"); lab(ax, x + w, fcf, "{:+.1f}")
ax.axhline(0, color=INK2, linewidth=1); ax.set_xticks(x, labels)
ax.legend(loc="upper left", frameon=False, fontsize=20, labelcolor=INK)
finish(f, ax, "현금 렌즈: 번 현금에서 공장에 쓴 돈을 빼면",
       "영업활동현금흐름 − 설비투자 = 잉여현금흐름 · 2022~2023 두 해 연속 마이너스 → 2026년 상반기 +72.7조",
       "charts/04_현금흐름_FCF.png")

# 5. 순현금 (DART 기준)
f, ax = fig()
cash = [a + b + c for a, b, c in zip(T("현금및현금성자산"), T("단기금융상품"), T("장기금융상품"))]
net = [c - b for c, b in zip(cash, borrow)]
ax.bar(x, net, 0.55, color=[BLUE if v >= 0 else RED for v in net])
lab(ax, x, net, "{:+.1f}", dy=1.0)
ax.axhline(0, color=INK2, linewidth=1); ax.set_xticks(x, labels)
finish(f, ax, "순현금 전환: 빚이 현금보다 많던 회사에서 현금이 빚보다 많은 회사로",
       "현금·금융상품 − 차입금 (DART 기준·리스 제외) · 회사 발표 기준 순현금은 2026.6말 69.4조",
       "charts/05_순현금.png")
