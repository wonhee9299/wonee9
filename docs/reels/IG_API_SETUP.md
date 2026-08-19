# Instagram API 설정 — 댓글 답글·인사이트 자동화

`tools/ig_post.py` 를 쓰려면 액세스 토큰이 필요하다.
토큰이 준비되면 **댓글 답글 게시와 인사이트 수집을 Claude가 직접 실행**할 수 있다.

## 되는 것 / 안 되는 것

| 작업 | API | 비고 |
|---|---|---|
| 댓글·답글 조회 | ✅ | 미응답 댓글 탐지 가능 |
| **댓글에 답글 게시** | ✅ | 질문 댓글 대응이 자동화되는 핵심 |
| 릴스 인사이트 조회 | ✅ | 도달, 저장, 공유, 평균 시청시간 등 |
| 릴스·피드 게시 | ✅ | 영상이 공개 URL 에 올라가 있어야 함 |
| 스토리 이미지/영상 게시 | ✅ | 아래 제약 참고 |
| **스토리 @멘션 스티커** | ❌ | API 파라미터가 없다 |
| **스토리 링크·질문 스티커** | ❌ | 동일 |
| 로컬 파일 직접 업로드 | ❌ | `image_url` / `video_url` 방식만 지원 |

> **결론**: 질문자에게 알림을 보내는 것이 목적인 스토리는 **폰에서 올려야 한다.**
> 댓글 답글과 인사이트 수집은 API 로 전부 대체된다.

## 준비 절차

1. **계정을 프로페셔널로 전환** — 개인 계정은 API 대상이 아니다.
   인스타 앱 → 설정 → 계정 유형 → 프로페셔널(비즈니스 또는 크리에이터)
2. **Meta 앱 생성** — https://developers.facebook.com/apps → 앱 만들기
3. **Instagram 제품 추가** → Instagram 로그인 설정
4. **권한(스코프) 요청** — 앱 대시보드에서 아래를 추가한다.
   이름은 Meta 가 개편하는 경우가 있으니 **대시보드에 표시된 실제 이름을 확인**할 것.
   - `instagram_business_basic`
   - `instagram_business_manage_comments` ← 답글 게시에 필요
   - `instagram_business_content_publish` ← 게시에 필요
   - `instagram_business_manage_insights` ← 인사이트에 필요
5. **장기 토큰 발급** — 단기 토큰을 장기 토큰(약 60일)으로 교환한다.
   만료되므로 주기적 갱신이 필요하다.
6. **IG User ID 확인** — 앱 대시보드 또는 `GET /me?fields=id,username` 로 확인

## 이 저장소에서 쓰기

`.env` 파일을 만든다. **`.env` 는 `.gitignore` 에 있으므로 커밋되지 않는다.**

```bash
IG_ACCESS_TOKEN=<장기 토큰>
IG_USER_ID=<IG User ID>
```

```bash
pip install -r requirements.txt
set -a && . ./.env && set +a

python tools/ig_post.py media --limit 10                    # media id 찾기
python tools/ig_post.py comments --media <media-id>         # ❗ 표시가 미응답 댓글
python tools/ig_post.py reply --comment <comment-id> \
    --message-file draft.txt --dry-run                      # 내용 확인
python tools/ig_post.py reply --comment <comment-id> \
    --message-file draft.txt                                # 실제 게시
python tools/ig_post.py insights --media <media-id>
```

## 토큰 취급 원칙

- **토큰을 채팅에 붙여넣지 말 것.** 이 저장소는 퍼블릭이고, 채팅 기록에 남는다.
  `.env` 파일에 직접 넣고, 클라우드 세션에서 실행이 필요하면 환경변수로 주입한다.
- 토큰이 노출됐다고 판단되면 Meta 앱 대시보드에서 즉시 무효화한다.
- `reply` 는 항상 `--dry-run` 으로 문안을 먼저 확인한 뒤 게시한다.
  게시 전 사용자 승인은 `CLAUDE.md` 의 작업 방식 규칙을 따른다.
