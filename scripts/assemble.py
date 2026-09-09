"""컷별 (clips/epN/cut_XX.mp4 있으면 영상, 없으면 cards/epN/cut_XX.png 켄번즈) + 나레이션 → output/epN.mp4
사용: python3 scripts/assemble.py ep1 [--limit N]
"""
import json, os, subprocess, sys
ep = sys.argv[1]; limit = int(sys.argv[sys.argv.index("--limit")+1]) if "--limit" in sys.argv else 999
import imageio_ffmpeg; FF = imageio_ffmpeg.get_ffmpeg_exe()
cuts = json.load(open(f"work/{ep}/cuts.json", encoding="utf-8"))
timing = {t["n"]: t for t in json.load(open(f"audio/{ep}/timing.json"))}
os.makedirs(f"work/{ep}/seg", exist_ok=True); segs = []
for c in cuts[:limit]:
    n = c["n"]; d = timing[n]["dur"]; seg = f"work/{ep}/seg/cut_{n:02d}.mp4"
    clip = f"clips/{ep}/cut_{n:02d}.mp4"; card = f"cards/{ep}/cut_{n:02d}.png"; aud = f"audio/{ep}/cut_{n:02d}.mp3"
    frames = int(d * 30)
    if os.path.exists(clip):
        vf = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1"
        vin = ["-stream_loop", "-1", "-i", clip]
    else:
        # 켄번즈: 1.0 → 1.06 줌, 30fps
        vf = f"scale=2400:1350,zoompan=z='1+0.06*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps=30,setsar=1"
        vin = ["-loop", "1", "-i", card]
    cmd = [FF, "-y", "-loglevel", "error", *vin, "-i", aud, "-filter_complex", f"[0:v]{vf}[v];[1:a]apad=pad_dur=0.6[a]",
           "-map", "[v]", "-map", "[a]", "-t", f"{d:.3f}", "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "44100", seg]
    subprocess.run(cmd, check=True); segs.append(seg); print("seg", n, f"{d:.1f}s", "clip" if os.path.exists(clip) else "card")
with open(f"work/{ep}/concat.txt", "w") as f:
    for s in segs: f.write(f"file '{os.path.abspath(s)}'\n")
out = f"output/{ep}.mp4"; os.makedirs("output", exist_ok=True)
subprocess.run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"work/{ep}/concat.txt", "-c", "copy", out], check=True)
print("->", out)
