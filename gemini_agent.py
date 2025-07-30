# gemini_agent.py
import vertexai
from vertexai.generative_models import GenerativeModel, Part

from utils import extract_json_from_code_block, hms_to_sec, slice_srt_by_seconds, \
                  validate_plan_indices, debug_and_fix_cut_ids, attach_seconds, validate_plan_seconds
from prompts import LLM2_PROMPT_TEMPLATE
from json import dumps

def analyze_video(project_id: str, location: str, gcs_uri: str, prompt: str):
    # os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "C:/Users/82102/Desktop/PM_project/gen-lang-client-0545243194-669c0509e451.json"

    print("[1/5] Vertex AI 초기화 중...")
    vertexai.init(project=project_id, location=location)
    print("→ 완료")

    print("[2/5] GCS 영상 파일 불러오는 중...")
    video_file = Part.from_uri(mime_type="video/mp4", uri=gcs_uri)
    print("→ 완료")

    print("[3/5] Gemini 모델 로드 중...")
    model = GenerativeModel("gemini-2.5-flash")
    print("→ 완료")

    print("[4/5] Gemini 모델에 요청 중 (영상 + 프롬프트)...")
    response = model.generate_content([video_file, prompt], stream=False)
    print("\n→ 완료")

    print("[5/5] 결과 출력:")
    print("--------------------------------------------------")
    print(response.text if hasattr(response, "text") else "없음")
    print("--------------------------------------------------")

    return response.text if hasattr(response, "text") else None

def create_edit_plan(clip_info, srt_rows):
    """
    clip_info: dict (LLM1 output for a single clip)
      - must include "start_time", "end_time", "description"
    srt_rows: list[SrtRow]
    """
    print("[LLM2 시작] 편집 계획 생성 시작")

    # 1. LLM1에서 받은 클립 정보 → 시간 변환
    clip_start_hms = clip_info["start_time"]
    clip_end_hms = clip_info["end_time"]
    clip_start_sec = hms_to_sec(clip_start_hms)
    clip_end_sec = hms_to_sec(clip_end_hms)

    # 2. 이 구간에 해당하는 SRT 자막 범위 추출
    clip_srt_rows, start_sub_id, end_sub_id = slice_srt_by_seconds(srt_rows, clip_start_sec, clip_end_sec)

    # 3. subtitle JSON 구성
    subtitles_json = dumps([
        {
            "id": r.id,
            "start_sec": round(r.start_sec, 3),
            "end_sec": round(r.end_sec, 3),
            "text": r.text
        } for r in clip_srt_rows
    ], ensure_ascii=False)

    
    print("[프롬프트 생성 중...]")
    # 4. 프롬프트 생성
    EDIT_PROMPT = LLM2_PROMPT_TEMPLATE.substitute(
        clip_start_hms=clip_start_hms,
        clip_end_hms=clip_end_hms,
        clip_start_sec=clip_start_sec,
        clip_end_sec=clip_end_sec,
        start_sub_id=start_sub_id,
        end_sub_id=end_sub_id,
        subtitles_json=subtitles_json,
        description=clip_info["description"],
    )
    print("[프롬프트 생성 완료]")



    print("[Gemini API 호출 중...]")
    model = GenerativeModel("gemini-2.5-pro")
    response = model.generate_content(EDIT_PROMPT, stream=False)
    print("[Gemini 응답 수신 완료]")

    # JSON 파싱
    plan = extract_json_from_code_block(response.text)
    # ✅ 컷 디버깅 및 자동 수정을 여기서
    debug_and_fix_cut_ids(parsed_json=plan, clip_start=clip_start_sec, clip_end=clip_end_sec)

    # ✅ 추가: 컷 범위 체크 후 유효한 컷만 남기기
    valid_cuts = []
    for i, cut in enumerate(plan["cuts"]):
        s = cut.get("start", -1)
        e = cut.get("end", -1)
        if clip_start_sec <= s < e <= clip_end_sec:
            valid_cuts.append(cut)
        else:
            print(f"[제외] cut[{i}]이 clip 범위({clip_start_sec}~{clip_end_sec})를 벗어남 → 제거")

    if not valid_cuts:
        raise ValueError("모든 컷이 clip 범위를 벗어남")


    # 5. 응답 검증 + 초로 변환 (다음 파트에서 정의)
    validate_plan_indices(plan, start_sub_id, end_sub_id)
    plan = attach_seconds(plan, srt_rows)
    validate_plan_seconds(plan, clip_start_sec, clip_end_sec)

    return plan