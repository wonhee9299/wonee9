#!/usr/bin/env python3
"""
scenes.json + 이미지/클립 → 나레이션(TTS) + 자막 + 편집 → 완성 mp4

사용법 (프로젝트 폴더 기준):
    python pipeline/make_video.py project/scenes.json
    python pipeline/make_video.py project/scenes.json --vertical      # 쇼츠(9:16)
    python pipeline/make_video.py project/scenes.json --no-tts        # 음성 없이 미리보기
    python pipeline/make_video.py project/scenes.json --bgm music.mp3 # 배경음악 추가

폴더 규칙 (scenes.json이 있는 폴더 기준):
    media/01.png  또는 media/01.mp4   ← 장면 1의 그림/클립 (없으면 임시 카드로 대체)
    audio/01.mp3                      ← 직접 녹음한 나레이션이 있으면 TTS 대신 사용
    work/                             ← 중간 파일 (자동 생성, 지워도 됨)
    output.mp4                        ← 결과물
"""

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ----------------------------------------------------------------------------
# ffmpeg 찾기: 시스템에 설치돼 있으면 그것을, 없으면 imageio-ffmpeg에 딸려온 것을 사용
# ----------------------------------------------------------------------------
def find_ffmpeg() -> str:
    from shutil import which
    if which("ffmpeg"):
        return "ffmpeg"
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit("ffmpeg를 찾지 못했습니다. `pip install imageio-ffmpeg` 또는 ffmpeg 설치가 필요합니다.")


FFMPEG = find_ffmpeg()


def run(cmd: list[str]) -> None:
    """ffmpeg 명령 실행. 실패하면 마지막 에러 줄을 보여주고 종료."""
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-15:])
        sys.exit(f"ffmpeg 실패:\n{' '.join(cmd)}\n\n{tail}")


def media_duration(path: Path) -> float:
    """ffprobe 없이 ffmpeg 출력에서 길이(초)를 읽는다."""
    proc = subprocess.run([FFMPEG, "-i", str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", proc.stderr)
    if not m:
        sys.exit(f"길이를 읽을 수 없습니다: {path}")
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


# ----------------------------------------------------------------------------
# 한글 폰트 찾기 (자막·임시 카드용)
# ----------------------------------------------------------------------------
FONT_CANDIDATES = [
    "C:/Windows/Fonts/malgunbd.ttf",                       # Windows 맑은 고딕 Bold
    "C:/Windows/Fonts/malgun.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",           # macOS
    "/Library/Fonts/AppleSDGothicNeo.ttc",
    "/usr/share/fonts/truetype/nanum/NanumSquareRoundEB.ttf",  # Linux (fonts-nanum)
    "/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
]


def find_font(user_font: str | None) -> str | None:
    if user_font:
        if Path(user_font).exists():
            return user_font
        sys.exit(f"폰트 파일이 없습니다: {user_font}")
    for c in FONT_CANDIDATES:
        if Path(c).exists():
            return c
    print("경고: 한글 폰트를 찾지 못했습니다. --font 로 .ttf 경로를 지정하세요. (자막이 네모로 나올 수 있음)")
    return None


def load_font(path: str | None, size: int) -> ImageFont.ImageFont:
    if path:
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


# ----------------------------------------------------------------------------
# 그림 만들기: 자막 오버레이 PNG, 임시 카드 PNG
# ----------------------------------------------------------------------------
def make_subtitle_png(text: str, out: Path, w: int, h: int, font_path: str | None) -> None:
    """투명 배경에 하단 자막만 그린 PNG. ffmpeg overlay로 얹는다."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    size = int(min(w, h) * 0.055)
    # 화면 폭의 90%를 넘으면 글자를 줄여서 맞춘다
    while True:
        font = load_font(font_path, size)
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if tw <= w * 0.9 or size <= 20:
            break
        size -= 2
    pad = int(size * 0.5)
    x = (w - tw) // 2
    y = int(h * 0.86) - th
    draw.rounded_rectangle((x - pad, y - pad, x + tw + pad, y + th + pad), radius=pad // 2, fill=(0, 0, 0, 170))
    # 노란 글씨 + 검은 외곽선 (썸네일과 같은 느낌)
    draw.text((x - bbox[0], y - bbox[1]), text, font=font, fill=(255, 221, 0, 255),
              stroke_width=max(2, size // 14), stroke_fill=(0, 0, 0, 255))
    img.save(out)


def make_placeholder_png(scene: dict, out: Path, w: int, h: int, font_path: str | None) -> None:
    """그림이 아직 없는 장면용 임시 카드. 장면 번호와 이미지 프롬프트 요약을 보여준다."""
    img = Image.new("RGB", (w, h), (34, 36, 40))
    draw = ImageDraw.Draw(img)
    big = load_font(font_path, int(h * 0.09))
    small = load_font(font_path, int(h * 0.035))
    title = f"장면 {scene['id']:02d}  (이미지 없음)"
    draw.text((int(w * 0.06), int(h * 0.12)), title, font=big, fill=(255, 221, 0))
    prompt = scene.get("image_prompt", "")
    line, lines, maxw = "", [], int(w * 0.88)
    for word in prompt.split():
        test = (line + " " + word).strip()
        if draw.textlength(test, font=small) > maxw:
            lines.append(line)
            line = word
        else:
            line = test
    lines.append(line)
    y = int(h * 0.30)
    for ln in lines[:8]:
        draw.text((int(w * 0.06), y), ln, font=small, fill=(200, 205, 215))
        y += int(h * 0.05)
    img.save(out)


# ----------------------------------------------------------------------------
# 나레이션 만들기 (edge-tts, 무료)
# ----------------------------------------------------------------------------
def tts(text: str, voice: str, out: Path) -> None:
    try:
        import edge_tts
    except ImportError:
        sys.exit("edge-tts가 없습니다. `pip install edge-tts` 후 다시 실행하거나 --no-tts 를 쓰세요.")

    async def _go():
        await edge_tts.Communicate(text, voice, rate="+5%").save(str(out))

    asyncio.run(_go())


# ----------------------------------------------------------------------------
# 장면 하나를 mp4로
# ----------------------------------------------------------------------------
def find_media(media_dir: Path, scene_id: int) -> Path | None:
    for ext in ("mp4", "mov", "webm", "png", "jpg", "jpeg", "webp"):
        p = media_dir / f"{scene_id:02d}.{ext}"
        if p.exists():
            return p
    return None


def build_scene(scene: dict, media: Path, sub_png: Path, audio: Path | None, dur: float,
                out: Path, w: int, h: int, fps: int) -> None:
    is_video = media.suffix.lower() in (".mp4", ".mov", ".webm")
    fade = 0.3
    frames = int(dur * fps) + 1

    def fit_with_blur(cw: int, ch: int) -> str:
        """비율이 안 맞는 소스는 흐린 배경 위에 원본을 통째로 얹는다 (쇼츠에 16:9 그림을 넣을 때)."""
        return (f"split=2[bg][fg];"
                f"[bg]scale={cw}:{ch}:force_original_aspect_ratio=increase,crop={cw}:{ch},boxblur=24:4[bgb];"
                f"[fg]scale={cw}:{ch}:force_original_aspect_ratio=decrease[fgs];"
                f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2")

    if is_video:
        # 클립이 나레이션보다 짧으면 반복, 길면 자른다
        inputs = ["-stream_loop", "-1", "-i", str(media)]
        vf = f"[0:v]fps={fps},{fit_with_blur(w, h)},setsar=1[base]"
    else:
        # 정지 이미지: 천천히 확대 (Ken Burns). 2배로 키운 뒤 zoompan 해야 떨림이 적다
        inputs = ["-loop", "1", "-framerate", str(fps), "-i", str(media)]
        vf = (f"[0:v]{fit_with_blur(w * 2, h * 2)},"
              f"zoompan=z='min(zoom+0.0008,1.18)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
              f":d={frames}:s={w}x{h}:fps={fps},setsar=1[base]")

    inputs += ["-i", str(sub_png)]
    if audio:
        inputs += ["-i", str(audio)]
    else:
        inputs += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]

    filter_complex = (
        vf + ";"
        f"[base][1:v]overlay=0:0:format=auto,"
        f"fade=t=in:st=0:d={fade},fade=t=out:st={max(0, dur - fade):.2f}:d={fade},format=yuv420p[v]"
    )
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", *inputs,
           "-filter_complex", filter_complex,
           "-map", "[v]", "-map", "2:a",
           "-t", f"{dur:.3f}",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", str(fps),
           "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
           "-shortest", str(out)]
    run(cmd)


# ----------------------------------------------------------------------------
# 메인
# ----------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="scenes.json으로 설명 영상 만들기")
    ap.add_argument("scenes", help="scenes.json 경로")
    ap.add_argument("--out", help="결과 파일 (기본: scenes.json 옆의 output.mp4)")
    ap.add_argument("--vertical", action="store_true", help="쇼츠용 9:16 (1080x1920)")
    ap.add_argument("--no-tts", action="store_true", help="음성 없이 만들기 (장면당 --silent-sec 초)")
    ap.add_argument("--silent-sec", type=float, default=5.0, help="--no-tts 일 때 장면 길이")
    ap.add_argument("--font", help="자막용 한글 폰트(.ttf) 경로")
    ap.add_argument("--bgm", help="배경음악 파일 (자동으로 작게 깔림)")
    ap.add_argument("--bgm-volume", type=float, default=0.12, help="배경음악 크기 0~1")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--tail", type=float, default=0.6, help="나레이션 끝난 뒤 여유 초")
    args = ap.parse_args()

    scenes_path = Path(args.scenes).resolve()
    base = scenes_path.parent
    media_dir, audio_dir, work = base / "media", base / "audio", base / "work"
    work.mkdir(exist_ok=True)
    out_path = Path(args.out).resolve() if args.out else base / "output.mp4"

    w, h = (1080, 1920) if args.vertical else (1920, 1080)
    font_path = find_font(args.font)

    data = json.loads(scenes_path.read_text(encoding="utf-8"))
    voice = data.get("voice", "ko-KR-InJoonNeural")
    scenes = data["scenes"]
    print(f"제목: {data.get('title', '')}\n장면 {len(scenes)}개, 해상도 {w}x{h}, ffmpeg: {FFMPEG}\n")

    clip_files: list[Path] = []
    for scene in scenes:
        sid = scene["id"]
        tag = f"{sid:02d}"

        # 1) 나레이션 오디오
        audio: Path | None = None
        user_audio = next((audio_dir / f"{tag}.{e}" for e in ("mp3", "wav", "m4a")
                           if (audio_dir / f"{tag}.{e}").exists()), None)
        if user_audio:
            audio = user_audio
        elif not args.no_tts:
            audio = work / f"{tag}_tts.mp3"
            if not audio.exists():
                print(f"[{tag}] 음성 생성 중: {scene['narration'][:30]}…")
                tts(scene["narration"], voice, audio)
        dur = (media_duration(audio) + args.tail) if audio else args.silent_sec

        # 2) 그림 또는 클립
        media = find_media(media_dir, sid)
        if media is None:
            media = work / f"{tag}_placeholder.png"
            make_placeholder_png(scene, media, w, h, font_path)
            print(f"[{tag}] media/{tag}.png 가 없어 임시 카드를 사용합니다")

        # 3) 자막 → 4) 장면 mp4
        sub_png = work / f"{tag}_sub.png"
        make_subtitle_png(scene.get("subtitle", ""), sub_png, w, h, font_path)
        clip = work / f"{tag}.mp4"
        print(f"[{tag}] {media.name} + 자막 → {clip.name} ({dur:.1f}초)")
        build_scene(scene, media, sub_png, audio, dur, clip, w, h, args.fps)
        clip_files.append(clip)

    # 5) 이어붙이기
    list_file = work / "concat.txt"
    list_file.write_text("".join(f"file '{p.as_posix()}'\n" for p in clip_files), encoding="utf-8")
    joined = work / "joined.mp4"
    run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
         "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(joined)])

    # 6) 배경음악 (선택)
    if args.bgm:
        print("배경음악 섞는 중…")
        run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
             "-i", str(joined), "-stream_loop", "-1", "-i", args.bgm,
             "-filter_complex",
             f"[1:a]volume={args.bgm_volume}[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[a]",
             "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
             "-shortest", str(out_path)])
    else:
        joined.replace(out_path)

    print(f"\n완성: {out_path}  (총 {media_duration(out_path):.1f}초)")


if __name__ == "__main__":
    main()
