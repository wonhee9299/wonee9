#!/usr/bin/env python3
"""인스타 스토리용 1080x1920 이미지 생성.

차량 화면 사진은 가로로 찍히는 경우가 많아 그대로 올리면 화면이 작아진다.
이 스크립트는 상단 훅 / 사진 / 하단 본문 3단으로 배치하고, 사진 속 작은 UI 요소
(예: 경고 팝업)를 확대 삽입해 스토리 크기에서도 읽히게 만든다.

EXIF 는 저장 시 제거된다 (기기명·촬영시각·GPS 유출 방지).

사용 예
  # 사진 전체를 한 장으로
  python tools/make_story_image.py --src photo.jpg --out story.jpg \\
      --hook "FSD 끌 때마다" --hook "테슬라가 묻는 것" \\
      --body "직접 학습은 아니고," --body "해제할 때마다 이렇게 물어봅니다"

  # 팝업 영역을 확대 삽입 (좌표는 --probe 로 먼저 확인)
  python tools/make_story_image.py --src photo.jpg --out story.jpg \\
      --context-box 600,640,2980,2447 --popup-box 830,2150,2020,2440 \\
      --hook "FSD 끌 때마다" --hook "테슬라가 묻는 것" \\
      --body "직접 학습은 아니고, 해제할 때마다 이렇게" --body "익명으로 상황을 물어봅니다" \\
      --footnote "국내 표기는 '어시스티드 드라이빙'"

  # 정방향 크기와 축소 미리보기를 먼저 확인해 좌표를 잡는다
  python tools/make_story_image.py --src photo.jpg --probe
"""
from __future__ import annotations

import argparse
import sys

from PIL import Image, ImageDraw, ImageFont, ImageOps

W, H = 1080, 1920
BG = (10, 10, 12)
WHITE = (255, 255, 255)
DIM = (170, 172, 178)
QUOTE = (150, 152, 158)
MUTED = (128, 130, 136)

# 컨테이너에 한글 지원 폰트가 제한적이다. 앞쪽부터 존재하는 것을 쓴다.
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]


def resolve_font() -> str:
    import os

    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    raise SystemExit(
        "한글을 렌더링할 폰트를 찾지 못했습니다. FONT_CANDIDATES 에 경로를 추가하세요."
    )


def parse_box(value: str) -> tuple[int, int, int, int]:
    parts = [int(v) for v in value.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("좌표는 left,top,right,bottom 네 개여야 합니다.")
    return tuple(parts)  # type: ignore[return-value]


def draw_block(draw, font_path, lines, top):
    """lines: [(text, size, fill, stroke, gap_after)] — 가운데 정렬로 쌓는다."""
    y = top
    for text, size, fill, stroke, gap in lines:
        font = ImageFont.truetype(font_path, size)
        box = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
        draw.text(
            ((W - (box[2] - box[0])) // 2, y),
            text,
            font=font,
            fill=fill,
            stroke_width=stroke,
            stroke_fill=fill,
        )
        y += (box[3] - box[1]) + gap
    return y


def probe(src: str) -> int:
    """정방향 크기를 출력하고 1/4 축소 미리보기를 저장한다 (좌표 잡기용)."""
    image = ImageOps.exif_transpose(Image.open(src))
    print(f"정방향 크기: {image.width} x {image.height}")
    print("미리보기 좌표에 4를 곱하면 원본 좌표가 됩니다.")
    out = "probe_preview.jpg"
    image.resize((image.width // 4, image.height // 4)).save(out, quality=90)
    print(f"미리보기 저장: {out}")
    return 0


def build(args) -> int:
    font_path = resolve_font()
    src = ImageOps.exif_transpose(Image.open(args.src))
    canvas = Image.new("RGB", (W, H), BG)

    context_box = args.context_box or (0, 0, src.width, src.height)

    if args.popup_box:
        # 확대 삽입 구성: 맥락 사진(위) + 확대 패널(아래)
        ctx_top, ctx_h = 352, 820
        inset_top, inset_w = 1206, 1000
        pw = args.popup_box[2] - args.popup_box[0]
        ph = args.popup_box[3] - args.popup_box[1]
        canvas.paste(src.crop(context_box).resize((W, ctx_h), Image.LANCZOS), (0, ctx_top))
        inset = src.crop(args.popup_box).resize((inset_w, round(inset_w * ph / pw)), Image.LANCZOS)
        inset = ImageOps.expand(inset, border=3, fill=(92, 95, 102))
        canvas.paste(inset, ((W - inset.width) // 2, inset_top))
        body_top = 1530
    else:
        photo_top, photo_h = 360, 1120
        canvas.paste(src.crop(context_box).resize((W, photo_h), Image.LANCZOS), (0, photo_top))
        body_top = 1524

    draw = ImageDraw.Draw(canvas)

    hook = []
    for index, text in enumerate(args.hook):
        last = index == len(args.hook) - 1
        # 마지막 줄을 크고 밝게 — 훅의 무게중심
        hook.append((text, 96 if last else 74, WHITE if last else DIM, 1 if last else 0, 0 if last else 20))
    if hook:
        draw_block(draw, font_path, hook, top=72)

    body = []
    if args.quote:
        body.append((args.quote, 38, QUOTE, 0, 24))
    for index, text in enumerate(args.body):
        last = index == len(args.body) - 1
        body.append((text, 54, WHITE, 1, 22 if last else 12))
    if args.footnote:
        body.append((args.footnote, 32, MUTED, 0, 0))
    end = draw_block(draw, font_path, body, top=body_top) if body else body_top

    # exif 인자를 넘기지 않으면 메타데이터가 저장되지 않는다
    canvas.save(args.out, quality=94, optimize=True)
    print(f"저장: {args.out} ({W}x{H}, EXIF 제거)")
    print(f"하단 여백 {H - end}px — @멘션 스티커를 여기에 두면 텍스트를 가리지 않습니다.")
    if H - end < 100:
        print("경고: 하단 여백이 좁습니다. 본문 줄 수를 줄이세요.", file=sys.stderr)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--src", required=True, help="원본 사진")
    parser.add_argument("--out", help="출력 파일 (--probe 가 아니면 필수)")
    parser.add_argument("--probe", action="store_true", help="좌표 잡기용 미리보기만 생성")
    parser.add_argument("--context-box", type=parse_box, help="사진에서 사용할 영역 left,top,right,bottom")
    parser.add_argument("--popup-box", type=parse_box, help="확대 삽입할 영역 left,top,right,bottom")
    parser.add_argument("--hook", action="append", default=[], help="상단 훅 (여러 번 지정 = 여러 줄)")
    parser.add_argument("--quote", help="본문 위에 붙는 작은 인용/라벨 한 줄")
    parser.add_argument("--body", action="append", default=[], help="하단 본문 (여러 번 지정 = 여러 줄)")
    parser.add_argument("--footnote", help="본문 아래 작은 주석 한 줄")
    args = parser.parse_args(argv)

    if args.probe:
        return probe(args.src)
    if not args.out:
        parser.error("--out 이 필요합니다 (또는 --probe 를 쓰세요).")
    return build(args)


if __name__ == "__main__":
    sys.exit(main())
