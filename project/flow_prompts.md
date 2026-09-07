# Flow에서 붙여넣기만 하면 되는 프롬프트 (예시 대본 5장면)

## Flow 여는 법

1. 브라우저에서 https://labs.google/fx/tools/flow 접속 → wonhee9299 계정으로 로그인
2. 왼쪽 위 **새 프로젝트** 클릭
3. 아래쪽 입력창 왼쪽 메뉴에서 **텍스트를 이미지로(Text to Image)** 선택
4. 아래 프롬프트를 복사해 붙여넣고 실행 → 나온 이미지 중 라벨(숫자)이 깨지지 않은 것을 다운로드
5. 파일 이름을 장면 번호로 바꿔 `project/media/` 폴더에 넣기 (`01.png`, `02.png` …)
6. 5장 다 모이면 터미널에서 `python pipeline/make_video.py project/scenes.json`

무료 계정은 하루 50크레딧입니다. 이미지 생성은 크레딧이 적게 들어서 5장면 × 2~3회 시도는 하루 안에 가능합니다.
한 장면에서 라벨이 자꾸 깨지면 프롬프트 맨 끝의 `labeled "..."` 부분을 지우고 다시 뽑으세요. 숫자는 자막이 대신 보여 줍니다.

---

## 장면 1 → `01.png`

```
16:9 aspect ratio. 3D isometric cutaway infographic, clean gray low-poly city blocks, soft studio lighting, dark gray background. A 150 m wide artificial lake in the center of a dense gray city, seen from a high angle. Below the lake, a cutaway reveals layered soil: sand-colored top soil, gray gravel, dark bedrock. Dozens of glowing cyan arrows point downward from the lake bed into the ground. Thin white dimension lines. Bottom 25% of the frame left empty. No people, no logos, no watermark, no Korean text.
```

## 장면 2 → `02.png`

```
16:9 aspect ratio. 3D isometric cutaway infographic, clean gray low-poly city blocks, soft studio lighting, dark gray background. Close cross-section of an artificial lake bed: the lake sits in a sand-colored porous soil layer full of small dark holes, below it gray gravel, then dark bedrock. Thin white horizontal dimension line across the lake labeled "150 m", thin white vertical dimension line beside the top soil labeled "2.5 m". Bottom 25% of the frame left empty. No people, no logos, no watermark, no Korean text.
```

## 장면 3 → `03.png`

```
16:9 aspect ratio. 3D isometric cutaway infographic, clean gray low-poly city blocks, soft studio lighting, dark gray background. Rain falling on an artificial lake in a gray city. In the cutaway below, dozens of glowing cyan arrows flow down through a porous sand-colored lake bed into a gray gravel layer. A small white label reads "15,000 m3 / day". Bottom 25% of the frame left empty. No people, no logos, no watermark, no Korean text.
```

## 장면 4 → `04.png`

```
16:9 aspect ratio. 3D isometric cutaway infographic, clean gray low-poly city blocks, soft studio lighting, dark gray background. Deep vertical cutaway under a city lake showing sand-colored top soil, gray gravel, and a thick dark bedrock layer. At 50 m depth a glowing cyan aquifer band runs horizontally. Cyan arrows converge from above into the aquifer. Thin white vertical dimension line labeled "50 m". Bottom 25% of the frame left empty. No people, no logos, no watermark, no Korean text.
```

## 장면 5 → `05.png`

```
16:9 aspect ratio. 3D isometric infographic, clean gray low-poly city blocks, soft studio lighting, dark gray background. Split comparison side by side. Left: a city block during heavy rain with storm drains overflowing, red arrows rushing along the streets. Right: the same block with an artificial lake, calm glowing cyan arrows sinking into the ground, dry streets. A white label between them reads "-40%". Bottom 25% of the frame left empty. No people, no logos, no watermark, no Korean text.
```

---

## (선택) 이미지를 움직이게 만들기

크레딧이 남으면 장면 1과 3만 영상으로 만들어 보세요. 나머지는 정지 이미지로 충분합니다.

1. 입력창 메뉴에서 **프레임을 동영상으로(Frames to Video)** 선택
2. 위에서 받은 이미지를 첫 프레임으로 업로드
3. 아래 프롬프트 붙여넣기 → 다운로드 → `01.mp4`, `03.mp4` 로 저장 (같은 번호의 png보다 mp4가 우선 사용됨)

장면 1:
```
Animate this infographic. Keep every building, label and dimension line exactly as in the image; do not add or remove text. Slow push-in from the wide city shot toward the lake. The cyan arrows flow continuously downward, water surface ripples subtly. Smooth camera, no people, no sudden cuts, no flicker.
```

장면 3:
```
Animate this infographic. Keep every building, label and dimension line exactly as in the image; do not add or remove text. Static camera. Rain keeps falling, the cyan arrows pulse downward through the soil, and the lake water level drops slowly. No people, no sudden cuts, no flicker.
```
