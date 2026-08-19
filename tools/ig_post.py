#!/usr/bin/env python3
"""Instagram Graph API CLI — 댓글 조회/답글, 스토리 게시, 릴스 인사이트 수집.

환경변수
  IG_ACCESS_TOKEN   장기 액세스 토큰 (필수)
  IG_USER_ID        인스타 프로페셔널 계정의 IG User ID (story/media 명령에 필요)
  IG_API_BASE       기본값 https://graph.instagram.com/v23.0

설정 방법: docs/reels/IG_API_SETUP.md

사용 예
  python tools/ig_post.py media --limit 10
  python tools/ig_post.py comments --media 17900000000000000
  python tools/ig_post.py reply --comment 17900000000000000 --message "답글 내용"
  python tools/ig_post.py reply --comment 17900000000000000 --message-file draft.txt --dry-run
  python tools/ig_post.py insights --media 17900000000000000
  python tools/ig_post.py story --image-url https://example.com/story.jpg
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import requests

DEFAULT_BASE = "https://graph.instagram.com/v23.0"
TIMEOUT = 30

# 릴스에서 의미 있는 지표. 계정 유형/미디어 유형에 따라 일부는 거부될 수 있으므로
# 하나씩 요청해 실패한 지표는 건너뛴다.
REEL_METRICS = [
    "reach",
    "saved",
    "shares",
    "comments",
    "likes",
    "total_interactions",
    "views",
    "ig_reels_avg_watch_time",
    "ig_reels_video_view_total_time",
]


class ApiError(RuntimeError):
    pass


def _token() -> str:
    token = os.environ.get("IG_ACCESS_TOKEN")
    if not token:
        raise ApiError(
            "IG_ACCESS_TOKEN 이 설정되지 않았습니다. docs/reels/IG_API_SETUP.md 참고."
        )
    return token


def _user_id() -> str:
    uid = os.environ.get("IG_USER_ID")
    if not uid:
        raise ApiError(
            "IG_USER_ID 가 설정되지 않았습니다. docs/reels/IG_API_SETUP.md 참고."
        )
    return uid


def _base() -> str:
    return os.environ.get("IG_API_BASE", DEFAULT_BASE).rstrip("/")


def _request(method: str, path: str, **params) -> dict:
    url = f"{_base()}/{path.lstrip('/')}"
    params["access_token"] = _token()
    resp = requests.request(method, url, params=params, timeout=TIMEOUT)
    try:
        body = resp.json()
    except ValueError:
        raise ApiError(f"{method} {path} → HTTP {resp.status_code}, 응답이 JSON 이 아님:\n{resp.text[:500]}")
    if resp.status_code >= 400 or "error" in body:
        err = body.get("error", {})
        raise ApiError(
            f"{method} {path} → HTTP {resp.status_code}\n"
            f"  type: {err.get('type')}\n"
            f"  code: {err.get('code')} (subcode {err.get('error_subcode')})\n"
            f"  message: {err.get('message')}"
        )
    return body


def _print(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


# --- 명령 ---------------------------------------------------------------


def cmd_media(args) -> int:
    """최근 게시물 목록. 릴스 URL 의 shortcode 를 permalink 로 대조해 media id 를 찾는다."""
    body = _request(
        "GET",
        f"{_user_id()}/media",
        fields="id,media_type,media_product_type,permalink,caption,timestamp,like_count,comments_count",
        limit=args.limit,
    )
    for item in body.get("data", []):
        caption = (item.get("caption") or "").replace("\n", " ")
        if len(caption) > 60:
            caption = caption[:60] + "…"
        print(
            f"{item['id']}  {item.get('timestamp','')}  "
            f"{item.get('media_product_type') or item.get('media_type','')}  "
            f"♥{item.get('like_count','-')} 💬{item.get('comments_count','-')}"
        )
        print(f"    {item.get('permalink','')}")
        if caption:
            print(f"    {caption}")
    return 0


def cmd_comments(args) -> int:
    """댓글과 각 댓글의 답글까지 조회. 미응답 질문을 찾는 용도."""
    body = _request(
        "GET",
        f"{args.media}/comments",
        fields="id,text,username,timestamp,like_count,replies{id,text,username,timestamp}",
        limit=args.limit,
    )
    comments = body.get("data", [])
    if not comments:
        print("댓글 없음")
        return 0
    for c in comments:
        replies = c.get("replies", {}).get("data", [])
        mark = "  " if replies else "❗"  # 답글 없는 댓글 표시
        print(f"{mark} {c['id']}  @{c.get('username','?')}  {c.get('timestamp','')}")
        print(f"     {c.get('text','')}")
        for r in replies:
            print(f"     └ @{r.get('username','?')}  {r.get('timestamp','')}  {r.get('text','')}")
    print("\n❗ = 답글이 달리지 않은 댓글")
    return 0


def cmd_reply(args) -> int:
    """댓글에 답글 게시. 새 댓글이 아니라 답글이어야 질문자에게 알림이 간다."""
    message = args.message
    if args.message_file:
        with open(args.message_file, encoding="utf-8") as fh:
            message = fh.read().strip()
    if not message:
        raise ApiError("--message 또는 --message-file 로 답글 내용을 지정하세요.")

    print(f"대상 댓글: {args.comment}")
    print(f"답글 내용 ({len(message)}자):\n{message}\n")
    if args.dry_run:
        print("[dry-run] 게시하지 않고 종료합니다.")
        return 0

    body = _request("POST", f"{args.comment}/replies", message=message)
    _print(body)
    print("답글 게시 완료. 실제로 달렸는지 comments 명령으로 재확인하세요.")
    return 0


def cmd_story(args) -> int:
    """스토리 게시.

    주의: Graph API 로는 이미지/영상만 올라간다. @멘션 스티커, 링크 스티커,
    질문 스티커를 붙이는 파라미터는 없다. 멘션 알림이 목적이라면 폰에서 올려야 한다.
    image_url 은 공개적으로 접근 가능한 URL 이어야 한다 (로컬 파일 업로드 불가).
    """
    print("주의: API 스토리에는 멘션/링크 스티커를 붙일 수 없습니다.", file=sys.stderr)
    if args.dry_run:
        print(f"[dry-run] story image_url={args.image_url}")
        return 0

    created = _request(
        "POST", f"{_user_id()}/media", media_type="STORIES", image_url=args.image_url
    )
    container = created["id"]
    print(f"컨테이너 생성: {container}")

    # 컨테이너가 FINISHED 될 때까지 대기 후 게시
    for attempt in range(args.max_wait):
        status = _request("GET", container, fields="status_code,status")
        code = status.get("status_code")
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise ApiError(f"컨테이너 처리 실패: {status}")
        print(f"  대기 중… ({code}, {attempt + 1}/{args.max_wait})")
        time.sleep(2)
    else:
        raise ApiError("컨테이너가 제한 시간 내에 준비되지 않았습니다.")

    published = _request("POST", f"{_user_id()}/media_publish", creation_id=container)
    _print(published)
    return 0


def cmd_insights(args) -> int:
    """릴스 인사이트. 계정/미디어 유형에 따라 거부되는 지표는 건너뛴다."""
    results, skipped = {}, {}
    for metric in REEL_METRICS:
        try:
            body = _request("GET", f"{args.media}/insights", metric=metric)
        except ApiError as exc:
            skipped[metric] = str(exc).splitlines()[-1].strip()
            continue
        for row in body.get("data", []):
            values = row.get("values") or [{}]
            results[row.get("name", metric)] = values[0].get("value")

    print("=== 지표 ===")
    for name, value in results.items():
        print(f"{name:34} {value}")
    if skipped:
        print("\n=== 조회 불가 ===")
        for name, why in skipped.items():
            print(f"{name:34} {why}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("media", help="최근 게시물 목록 (media id 찾기)")
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(func=cmd_media)

    p = sub.add_parser("comments", help="댓글·답글 조회 (미응답 댓글 표시)")
    p.add_argument("--media", required=True)
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=cmd_comments)

    p = sub.add_parser("reply", help="댓글에 답글 게시")
    p.add_argument("--comment", required=True)
    p.add_argument("--message")
    p.add_argument("--message-file", help="답글 내용을 담은 텍스트 파일")
    p.add_argument("--dry-run", action="store_true", help="게시하지 않고 내용만 출력")
    p.set_defaults(func=cmd_reply)

    p = sub.add_parser("story", help="스토리 게시 (스티커 불가)")
    p.add_argument("--image-url", required=True, help="공개 접근 가능한 이미지 URL")
    p.add_argument("--max-wait", type=int, default=30, help="컨테이너 준비 대기 횟수 (2초 간격)")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_story)

    p = sub.add_parser("insights", help="릴스 인사이트 조회")
    p.add_argument("--media", required=True)
    p.set_defaults(func=cmd_insights)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ApiError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"네트워크 오류: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
