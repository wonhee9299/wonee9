# ai-video-studio 규칙 문서 반입 안내

영상 제작 착수 전 필독인 아래 3개 문서는 **아직 이 저장소에 없다.**
원본은 로컬 workspace 의 `ai-video-studio/` 에 있으며, 클라우드 세션에서는 접근할 수 없다.

- `ai-video-studio/VIDEO_PRODUCTION_MASTER_RULES.md`
- `ai-video-studio/MANDATORY_VIDEO_PRODUCTION_CHARTER.md`
- `ai-video-studio/INSTAGRAM_REELS_PRODUCTION_GATE.md`

## 반입 방법

로컬 PC에서 이 저장소를 클론한 뒤 복사해 커밋한다.

```bash
git clone https://github.com/wonhee9299/wonee9.git
cd wonee9
git checkout claude/reels-task-migration-toc5i8
mkdir -p docs/reels/rules
cp <workspace>/ai-video-studio/VIDEO_PRODUCTION_MASTER_RULES.md docs/reels/rules/
cp <workspace>/ai-video-studio/MANDATORY_VIDEO_PRODUCTION_CHARTER.md docs/reels/rules/
cp <workspace>/ai-video-studio/INSTAGRAM_REELS_PRODUCTION_GATE.md docs/reels/rules/
git add -A && git commit -m "docs(reels): import ai-video-studio production rules"
git push
```

반입 후 `CLAUDE.md` 의 "영상 제작 전 필독" 섹션 경로를 `docs/reels/rules/` 로 갱신하고
이 파일은 삭제한다.

## 반입 전까지의 임시 기준

규칙 원본이 없는 동안에는 `CLAUDE.md` 의 "릴스 제작 기준" 과
`docs/reels/WORKFLOW.md` 의 게이트 체크리스트를 최소 기준으로 사용한다.
원본 규칙과 충돌하면 **원본 규칙이 우선**한다.
