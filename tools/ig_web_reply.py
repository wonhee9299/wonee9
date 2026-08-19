#!/usr/bin/env python3
"""로컬 PC에서 인스타그램 웹에 댓글 답글을 게시한다.

**로컬 전용.** 클라우드 컨테이너에서는 로그인 세션이 없고 데이터센터 IP 로그인은
보안 체크포인트에 걸리므로 쓰지 않는다. 집 PC에서 실행할 것.

로그인은 사람이 직접 한 번만 한다. 비밀번호를 이 스크립트에 넣지 않는다 —
브라우저 프로필(`.ig-profile/`)에 세션이 남아 이후 실행은 로그인 없이 동작한다.

    pip install playwright && playwright install chromium

    # 1회: 브라우저가 열리면 직접 로그인한 뒤 터미널에서 Enter
    python tools/ig_web_reply.py --login

    # 답글 게시 (먼저 --dry-run 으로 대상 댓글이 맞는지 확인)
    python tools/ig_web_reply.py \\
        --url https://www.instagram.com/wonhee929/reel/DcM0pGiPsN-/ \\
        --reply-to shrah84 --message-file draft.txt --dry-run

참고: 웹 자동화로는 **스토리 @멘션·링크 스티커를 붙일 수 없다** (폰 앱 전용 기능).
공식 경로인 Graph API 도 마찬가지다 — `tools/ig_post.py` 와 docs/reels/IG_API_SETUP.md 참고.
자동화 게시는 인스타그램 이용약관상 제약이 있을 수 있으니 본인 계정·본인 콘텐츠에만 쓴다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROFILE_DIR = Path(__file__).resolve().parent.parent / ".ig-profile"
SHOT_DIR = Path(__file__).resolve().parent.parent / ".ig-shots"


def launch(playwright, headless: bool, args=None):
    """브라우저 컨텍스트를 얻는다.

    이미 인스타에 로그인된 크롬이 있으면 그걸 쓰는 게 가장 빠르다. 우선순위:

    1. `--cdp <url>` — 원격 디버깅이 켜진 채 **실행 중인** 크롬에 붙는다.
       크롬을 닫을 필요가 없고 로그인 세션을 그대로 쓴다. 권장.
       크롬을 이렇게 띄워둔다: `chrome --remote-debugging-port=9222`
    2. `--chrome-user-data-dir <path>` — 실제 크롬 프로필로 띄운다.
       **크롬을 완전히 종료한 뒤** 실행해야 한다 (프로필 잠금).
    3. 기본 — 이 저장소의 `.ig-profile/` 전용 프로필. 최초 1회 `--login` 필요.
    """
    cdp = getattr(args, "cdp", None)
    if cdp:
        browser = playwright.chromium.connect_over_cdp(cdp)
        contexts = browser.contexts
        return contexts[0] if contexts else browser.new_context(locale="ko-KR")

    chrome_dir = getattr(args, "chrome_user_data_dir", None)
    if chrome_dir:
        return playwright.chromium.launch_persistent_context(
            user_data_dir=chrome_dir,
            channel="chrome",
            headless=headless,
            viewport={"width": 1280, "height": 1000},
            locale="ko-KR",
        )

    PROFILE_DIR.mkdir(exist_ok=True)
    return playwright.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=headless,
        viewport={"width": 1280, "height": 1000},
        locale="ko-KR",
    )


def save_shot(page, name: str) -> Path:
    SHOT_DIR.mkdir(exist_ok=True)
    path = SHOT_DIR / f"{name}.png"
    page.screenshot(path=str(path))
    return path


def do_login(playwright, args=None) -> int:
    ctx = launch(playwright, headless=False, args=args)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
    print("브라우저에서 직접 로그인하세요. 2단계 인증까지 끝내고 피드가 보이면,")
    input("여기서 Enter 를 누르세요... ")
    page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    logged_in = page.locator('svg[aria-label="새 게시물"], svg[aria-label="New post"]').count() > 0
    print("로그인 상태로 보입니다." if logged_in else "로그인이 확인되지 않았습니다. 다시 시도하세요.")
    print(f"세션 저장 위치: {PROFILE_DIR}")
    ctx.close()
    return 0 if logged_in else 1


def find_comment(page, username: str):
    """대상 사용자의 댓글 블록을 찾아 반환한다."""
    # 댓글은 li/div 구조가 자주 바뀌므로 사용자명 링크에서 위로 올라가 컨테이너를 잡는다.
    link = page.locator(f'a[href="/{username}/"]').last
    if link.count() == 0:
        return None
    return link.locator("xpath=ancestor::*[self::li or self::div][.//span][1]")


def do_reply(playwright, args) -> int:
    message = args.message
    if args.message_file:
        message = Path(args.message_file).read_text(encoding="utf-8").strip()
    if not message:
        print("답글 내용이 비어 있습니다.", file=sys.stderr)
        return 1

    ctx = launch(playwright, headless=False, args=args)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(4000)

    if "login" in page.url:
        print("로그인이 필요합니다. 먼저 --login 을 실행하세요.", file=sys.stderr)
        ctx.close()
        return 1

    # 댓글이 접혀 있으면 펼친다
    for label in ["댓글 더 보기", "Load more comments"]:
        button = page.locator(f'[aria-label="{label}"]')
        for _ in range(5):
            if button.count() == 0:
                break
            button.first.click()
            page.wait_for_timeout(1200)

    block = find_comment(page, args.reply_to)
    if block is None or block.count() == 0:
        shot = save_shot(page, "comment-not-found")
        print(f"@{args.reply_to} 의 댓글을 찾지 못했습니다. 화면: {shot}", file=sys.stderr)
        ctx.close()
        return 1

    print(f"대상 댓글 (@{args.reply_to}):")
    print("  " + block.inner_text().replace("\n", " | ")[:300])
    print(f"\n답글 ({len(message)}자):\n{message}\n")

    if args.dry_run:
        shot = save_shot(page, "dry-run")
        print(f"[dry-run] 게시하지 않았습니다. 화면: {shot}")
        ctx.close()
        return 0

    reply_button = block.locator('text=/^답글 달기$|^Reply$/').first
    if reply_button.count() == 0:
        shot = save_shot(page, "reply-button-not-found")
        print(f"'답글 달기' 버튼을 찾지 못했습니다. 화면: {shot}", file=sys.stderr)
        ctx.close()
        return 1
    reply_button.click()
    page.wait_for_timeout(1200)

    box = page.locator('textarea[aria-label*="댓글"], textarea[aria-label*="comment"]').first
    if box.count() == 0:
        shot = save_shot(page, "comment-box-not-found")
        print(f"댓글 입력창을 찾지 못했습니다. 화면: {shot}", file=sys.stderr)
        ctx.close()
        return 1

    # 답글 달기를 누르면 "@사용자명 " 이 미리 채워진다. 뒤에 이어 쓴다.
    box.click()
    page.wait_for_timeout(400)
    box.type(message, delay=25)
    page.wait_for_timeout(600)

    submit = page.locator('div[role="button"]:has-text("게시"), button:has-text("게시"), button:has-text("Post")').first
    if submit.count() == 0:
        shot = save_shot(page, "submit-not-found")
        print(f"게시 버튼을 찾지 못했습니다. 화면: {shot}", file=sys.stderr)
        ctx.close()
        return 1
    submit.click()
    page.wait_for_timeout(4000)

    shot = save_shot(page, "after-post")
    posted = args.reply_to in page.inner_text("body") and message[:12] in page.inner_text("body")
    print(f"게시 후 화면: {shot}")
    print("답글이 화면에 보입니다." if posted else "답글이 화면에서 확인되지 않았습니다. 화면을 직접 확인하세요.")
    ctx.close()
    return 0 if posted else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--login", action="store_true", help="브라우저를 띄워 직접 로그인 (1회)")
    parser.add_argument("--url", help="릴스/게시물 URL")
    parser.add_argument("--reply-to", help="답글을 달 대상 사용자명 (@ 제외)")
    parser.add_argument("--message", help="답글 내용")
    parser.add_argument("--message-file", help="답글 내용을 담은 텍스트 파일")
    parser.add_argument("--dry-run", action="store_true", help="대상 댓글만 확인하고 게시하지 않음")
    parser.add_argument(
        "--cdp",
        help="실행 중인 크롬에 붙는다 (예: http://localhost:9222). "
             "크롬을 --remote-debugging-port=9222 로 띄워두면 로그인 세션을 그대로 쓴다. 권장",
    )
    parser.add_argument(
        "--chrome-user-data-dir",
        help="실제 크롬 프로필 경로로 띄운다. 크롬을 완전히 종료한 뒤 실행할 것",
    )
    args = parser.parse_args(argv)

    # 브라우저를 띄우기 전에 인자를 검증한다
    if not args.login and not (args.url and args.reply_to):
        parser.error("--url 과 --reply-to 가 필요합니다 (또는 --login).")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright 가 필요합니다: pip install playwright && playwright install chromium", file=sys.stderr)
        return 1

    with sync_playwright() as playwright:
        return do_login(playwright, args) if args.login else do_reply(playwright, args)


if __name__ == "__main__":
    sys.exit(main())
