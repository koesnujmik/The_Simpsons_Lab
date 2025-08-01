import srt
import os
import re
import vertexai
from vertexai.generative_models import GenerativeModel
from prompts import TRANSLATOR_PROMPT
from pathlib import Path
from config import PROJECT_ID, LOCATION, API_JSON_PATH

def translate_srt_to_korean(input_path: str, output_path: str):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = API_JSON_PATH

    # 1. 원본 SRT 읽기
    input_path = Path(input_path)
    with input_path.open('r', encoding='utf-8-sig') as f:
        srt_content = f.read()

    # 2. SRT 파싱
    subtitles = list(srt.parse(srt_content))

    # 3. 번역 모델 초기화
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    model = GenerativeModel(
        "gemini-2.5-pro",
        system_instruction=TRANSLATOR_PROMPT
    )
    chat = model.start_chat()

    # 4. 각 자막을 번역하고, 새로운 Subtitle 객체에 반영
    translated_subs = []
    for sub in subtitles:
        # 줄바꿈을 제거하고 번역 요청
        src = sub.content.replace('\n', ' ')
        src = src.replace('<i>', '')
        src = src.replace('</i>', '')
        src = src.replace('-', '\n')
        src = re.sub(r'\(.*?\)', '', src)
        print("원본:", src)
        
        if re.search(r'\w', src):
            response = chat.send_message(src)
            kr_text = response.text
            print("번역:", kr_text)
        else:
            kr_text = "None_None"

        # 새 Subtitle 생성
        translated_subs.append(
            srt.Subtitle(
                index=sub.index,
                start=sub.start,
                end=sub.end,
                content=kr_text
            )
        )

    # 5. 한국어 자막으로 조합
    output_srt = srt.compose(translated_subs)

    # 6. 결과 SRT 파일로 저장
    output_path = Path(output_path)
    with output_path.open('w', encoding='utf-8') as f:
        f.write(output_srt)

    print(f"Saved translated SRT to: {output_path}")

# 사용 예시
if __name__ == "__main__":
    translate_srt_to_korean(
        "input/s0218_modified.srt",
        "input/s0218_kor.srt"
    )
