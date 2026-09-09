"""cuts.json → 컷별 mp3 + 길이(timing.json) + SRT.  edge-tts 사용.
사용: python3 scripts/build_narration.py work/ep1/cuts.json audio/ep1 [voice]
"""
import json, sys, os, subprocess, asyncio
import edge_tts
cuts = json.load(open(sys.argv[1], encoding="utf-8"))
outdir = sys.argv[2]; voice = sys.argv[3] if len(sys.argv) > 3 else "ko-KR-InJoonNeural"
os.makedirs(outdir, exist_ok=True)
import imageio_ffmpeg; FF = imageio_ffmpeg.get_ffmpeg_exe()
def dur(p):
    r = subprocess.run([FF, "-i", p], capture_output=True, text=True).stderr
    import re; m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r)
    return int(m[1])*3600 + int(m[2])*60 + float(m[3])
async def main():
    timing = []; t = 0.0
    for c in cuts:
        mp3 = os.path.join(outdir, f"cut_{c['n']:02d}.mp3")
        if not os.path.exists(mp3):
            await edge_tts.Communicate(c["narration"], voice, rate="+3%").save(mp3)
        d = dur(mp3) + 0.6  # 컷 사이 여백
        timing.append({"n": c["n"], "start": round(t, 3), "dur": round(d, 3)}); t += d
    json.dump(timing, open(os.path.join(outdir, "timing.json"), "w"), indent=1)
    def ts(s): h=int(s//3600); m=int(s%3600//60); sec=s%60; return f"{h:02d}:{m:02d}:{sec:06.3f}".replace(".", ",")
    with open(os.path.join(outdir, "narration.srt"), "w", encoding="utf-8") as f:
        for c, tm in zip(cuts, timing):
            f.write(f"{c['n']}\n{ts(tm['start'])} --> {ts(tm['start']+tm['dur']-0.3)}\n{c['narration']}\n\n")
    print(f"{len(cuts)} cuts, total {t/60:.1f} min")
asyncio.run(main())
