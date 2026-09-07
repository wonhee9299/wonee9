# 로컬 Claude Code / Codex 세션에 붙여넣는 프롬프트

아래 내용을 통째로 복사해서 PC의 Claude Code(또는 Codex) 세션에 붙여넣으세요.

---

C:\ 에서 작업해줘. 나는 코딩 초보자야. 명령을 실행하기 전에 한 줄로 뭘 하는지 설명해줘.

## 1. 저장소 준비
- https://github.com/wonhee9299/wonee9.git 를 C:\wonee9 에 clone 하고
  브랜치 claude/youtube-video-analysis-k4clq0 로 checkout 해줘.
- Python 3.10 이상과 git이 없으면 설치 방법을 먼저 알려줘.
- pip install -r requirements.txt 실행.
- python pipeline\make_video.py project\scenes.json --no-tts 를 실행해서
  project\output.mp4 가 만들어지는지 확인해줘. (이미지가 없어서 임시 카드로 나오는 게 정상)

## 2. 저장소 설명 (먼저 README.md 를 읽어줘)
- 유튜브 "AI건축 영상 10분만에 만드는 방법" 스타일의 공학 설명 영상을 만드는 키트야.
- project\scenes.json : 5개 장면의 나레이션, 자막, 이미지 프롬프트 (예시 주제: 도심 인공호수 빗물 침투)
- project\flow_prompts.md : Google Flow에 붙여넣을 장면별 이미지 프롬프트 5개와 영상화 프롬프트 2개
- pipeline\make_video.py : media 폴더의 이미지/클립 + TTS 나레이션 + 자막을 합쳐 mp4를 만드는 스크립트
- project\media\01.png ~ 05.png 에 이미지를 넣으면 자동으로 사용됨. 같은 번호에 mp4가 있으면 mp4 우선.

## 3. Google Flow에서 이미지 만들기
- 브라우저로 https://labs.google/fx/tools/flow 를 열어줘.
- 로그인과 휴대폰 인증은 내가 직접 할게. 로그인 화면이 나오면 멈추고 나에게 알려줘.
  비밀번호나 인증번호를 나에게 묻지 마.
- 로그인이 끝나면 새 프로젝트 → "텍스트를 이미지로" 모드에서
  project\flow_prompts.md 의 장면 1~5 프롬프트를 순서대로 넣고 생성해줘.
- 각 장면마다 숫자 라벨("150 m", "2.5 m", "15,000 m3", "50 m", "-40%")이 깨지지 않은 이미지를 골라
  다운로드하고 C:\wonee9\project\media\01.png ~ 05.png 로 저장해줘.
- 라벨이 3번 넘게 깨지면 프롬프트에서 labeled "..." 부분을 빼고 다시 생성해. 숫자는 자막이 대신 보여줘.
- 무료 계정은 하루 50크레딧이야. 크레딧이 부족하다는 메시지가 나오면 멈추고 알려줘.
- 브라우저를 직접 조작할 수 없으면, 내가 할 일을 한 번에 하나씩 알려주고 파일이 media 폴더에 들어왔는지 확인해줘.

## 4. 완성
- 5장이 다 모이면 python pipeline\make_video.py project\scenes.json 을 실행해서
  나레이션(edge-tts)과 자막이 붙은 project\output.mp4 를 만들어줘.
- TTS가 네트워크 문제로 실패하면 --no-tts 로 먼저 만들고 원인을 알려줘.
- 자막이 네모로 나오면 --font C:\Windows\Fonts\malgunbd.ttf 옵션을 붙여줘.
- 완성되면 output.mp4 경로와 총 길이를 알려줘.
