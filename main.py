# main.py
import os
import json

# 설정 및 모듈 임포트
import config
from prompts import LLM1_VIDEO_ANALYSIS_PROMPT
from utils import load_srt_with_indices, extract_json_from_code_block
from gemini_agent import analyze_video, create_edit_plan
from edit import trim_video_only_from_json, trim_intro, generate_video_from_json


def run_pipeline(llm1_output, srt_path, video_path, output_folder, top_k=3):
    os.makedirs(output_folder, exist_ok=True)

    # 1. 자막 로딩
    print("[SRT 로딩 중...]")
    srt_rows = load_srt_with_indices(srt_path)

    # 2. LLM1 출력 → JSON 변환
    print("[LLM1 응답 파싱 중...]")
    clip_list = extract_json_from_code_block(llm1_output)
    clip_list = sorted(clip_list, key=lambda x: x.get("score", 0), reverse=True)

    # 3. 상위 클립 처리 및 영상 생성
    results = []
    for rank, clip_data in enumerate(clip_list[:top_k], start=1):
        print(f"\n========== [TOP {rank}] clip_id={clip_data.get('clip_id')} ==========")
        try:
            # 편집 계획 생성
            plan = create_edit_plan(clip_data, srt_rows)
            print("\n📄 편집 계획 (plan) 출력 완료")
            
            # 계획을 JSON 파일로 저장
            json_path = os.path.join(output_folder, "json", f"final_result_{rank}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(plan, f, ensure_ascii=False, indent=2)
            
            trimmed_video = trim_video_only_from_json(video_path, json_path)
            print("trimmed_video 완료")
            intro_clip = trim_intro(video_path)
            print("intro 완료")

            # 최종 쇼츠 영상 생성
            final_shorts_path = os.path.join(output_folder, "video", f"final_shorts_{rank}.mp4")
            generate_video_from_json(
                json_path=json_path,
                intro_video=intro_clip,
                trim_video=trimmed_video,
                output_path=final_shorts_path,
                font_path=config.FONT_PATH
            )
            print(f"✅ [TOP {rank}] 쇼츠 영상 생성 완료: {final_shorts_path}")

        except Exception as e:
            print(f"[에러] TOP {rank} 클립 처리 실패: {e}")
            continue

if __name__ == "__main__":
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.API_JSON_PATH

    # 1단계: 영상 분석 (LLM1)
    llm1_output = analyze_video(
        config.PROJECT_ID, 
        config.LOCATION, 
        config.GCS_URI, 
        LLM1_VIDEO_ANALYSIS_PROMPT
    )

    # 2단계: 분석 결과를 바탕으로 파이프라인 실행
    if llm1_output:
        run_pipeline(
            llm1_output, 
            config.SRT_PATH, 
            config.VIDEO_PATH, 
            config.OUTPUT_FOLDER, 
            top_k=config.TOP_K
        )
