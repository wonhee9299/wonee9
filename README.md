# AI 공학·건축 설명 영상 제작 키트

유튜브 영상 [AI건축 영상 초보자도 10분만에 만드는 방법](https://youtu.be/HlWX2GuIZXM)의
제작 방식을 재구성한 것입니다. 프롬프트 3종과 자동 조립 스크립트로 되어 있습니다.

## 전체 흐름

| 단계 | 하는 일 | 쓰는 도구 | 비용 |
|---|---|---|---|
| 1 | 주제 → 대본 + 장면표(JSON) | Codex / ChatGPT / Claude 중 하나 | 무료 가능 |
| 2 | 장면별 인포그래픽 이미지 | Google Flow, Gemini, ChatGPT 이미지 중 하나 | 무료 한도 있음 |
| 3 | (선택) 이미지 → 움직이는 클립 | Google Flow (Veo) | Google AI Pro |
| 4 | 나레이션 + 자막 + 편집 → mp4 | 이 저장소의 `make_video.py` | 무료 |

1~3단계는 사람이 웹사이트에서 직접 합니다. 4단계만 자동입니다.

## 준비 (한 번만)

Python 3.10 이상이 필요합니다. 터미널(명령 프롬프트)에서:

```
pip install -r requirements.txt
```

ffmpeg는 자동으로 같이 설치됩니다. 따로 설치할 필요 없습니다.

## 만드는 순서

1. `prompts/01_기획_대본.md`의 프롬프트를 AI에 붙여넣고 `[주제]`를 바꿉니다.
   결과 JSON을 `project/scenes.json`에 덮어씁니다. (예시 파일이 들어 있습니다)
2. `prompts/02_인포그래픽_이미지.md`를 보고 장면별 이미지를 만들어
   `project/media/01.png`, `02.png` … 로 저장합니다.
3. (선택) `prompts/03_영상화.md`를 보고 클립을 만들어 `project/media/01.mp4` 로 저장합니다.
   같은 번호에 png와 mp4가 둘 다 있으면 mp4를 씁니다.
4. 조립:

```
python pipeline/make_video.py project/scenes.json
```

`project/output.mp4`가 만들어집니다. 이미지가 아직 없는 장면은 임시 카드로 채워지므로
그림을 만들기 전에도 대본 흐름을 미리 볼 수 있습니다.

### 자주 쓰는 옵션

```
--vertical            쇼츠용 세로(9:16) 영상
--no-tts              음성 없이 빠르게 미리보기
--bgm music.mp3       배경음악 깔기 (--bgm-volume 0.12 로 크기 조절)
--font C:/Windows/Fonts/malgunbd.ttf   자막 폰트 직접 지정
```

### 나레이션 목소리

`scenes.json`의 `voice` 값을 바꾸면 됩니다. 무료 edge-tts 한국어 목소리:

- `ko-KR-InJoonNeural` (남성, 기본)
- `ko-KR-SunHiNeural` (여성)
- `ko-KR-HyunsuMultilingualNeural` (남성, 다국어)

직접 녹음한 음성을 쓰려면 `project/audio/01.mp3` 처럼 넣으세요. TTS 대신 그 파일을 씁니다.

## 폴더 구조

```
prompts/        1~3단계 프롬프트
pipeline/       make_video.py (4단계 조립 스크립트)
project/        작업 폴더 (scenes.json, media/, audio/, work/, output.mp4)
analysis/       원본 영상 분석 메모
```

## 문제가 생기면

- **자막이 네모로 나온다**: 한글 폰트를 못 찾은 것입니다. `--font`로 .ttf 경로를 지정하세요.
- **TTS가 실패한다**: 인터넷 연결을 확인하세요. 회사 네트워크(프록시)에서는 막힐 수 있습니다.
  그 경우 `--no-tts`로 만들거나 직접 녹음한 파일을 `project/audio/`에 넣으세요.
- **이미지 속 글자가 깨진다**: 라벨은 영문·숫자만 쓰고, 한글은 자막으로 처리하세요.

## 알아둘 점

- 원본 영상의 프롬프트 원문은 확보하지 못했습니다. 여기 프롬프트는 영상의 결과물 스타일을 보고
  다시 쓴 것이라 원본과 다를 수 있습니다.
- 이 포맷의 영상은 이미 많습니다. 소재(지역, 구조물, 사고 사례)를 차별화하지 않으면
  조회수를 기대하기 어렵습니다. AI가 만든 수치는 반드시 검증하세요.
