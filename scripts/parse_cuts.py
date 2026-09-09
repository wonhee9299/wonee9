"""컷 대본(md) → cuts.json  (컷 번호, 파트, 나레이션, 화면, 프롬프트, 강조어, 차트 참조)"""
import re, json, sys, os
def parse(path):
    txt = open(path, encoding="utf-8").read()
    part = ""
    cuts = []
    for block in re.split(r"\n(?=\*\*#\d+\*\*)", txt):
        m = re.match(r"\*\*#(\d+)\*\*", block)
        if not m: continue
        # part header may appear before the block; find last '## ' heading before it
        idx = txt.index(block)
        heads = re.findall(r"^## (.+?) \(", txt[:idx], re.M)
        part = heads[-1] if heads else part
        g = lambda k: (re.search(r"^- %s: (.+)$" % k, block, re.M) or [None, ""])[1].strip()
        chart = re.search(r"charts/light/(\d+)", g("화"))
        cuts.append({"n": int(m.group(1)), "part": part, "narration": g("나"), "screen": g("화"),
                     "prompt": g("P"), "emph": g("강"), "chart": chart.group(1) if chart else None})
    return cuts
if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    cuts = parse(src)
    json.dump(cuts, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(cuts), "cuts ->", out)
