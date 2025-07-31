import re
import pysrt
import srt
import json
from datetime import datetime
from dataclasses import dataclass

# JSON 정리 함수
# : LLM이 출력한 JSON 형태 문자열을 깨끗하게 정리하고 파싱해서 파이썬에서 쓸 수 있는 형태로 변환
def extract_json_from_code_block(text):

    # 코드 블록 제거 및 스마트 따옴표 제거
    cleaned = re.sub(r"```(?:json)?", "", text.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"```", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace('“', '"').replace('”', '"')
    cleaned = cleaned.replace("‘", "'").replace("’", "'")

    # 1차: 앞의 정리 과정을 거친 후, 전체 문자열을 JSON으로 직접 파싱 시도
    try:
        return json.loads(cleaned.strip())
    except json.JSONDecodeError:
        pass

    # 2차: 앞의 정리 과정이 가능한 모든 출력 형태를 100% 모두 커버할 순 없어서, 2차 정리 과정 적용(정규식으로 JSON 객체나 리스트 추출)
    json_match = re.search(r"(\[\s*{[\s\S]+?}\s*\])", cleaned)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_match = re.search(r"({[\s\S]+})", cleaned)
        json_str = json_match.group(1) if json_match else cleaned.strip()

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print("[JSON 파싱 실패]:", e)
        print("[파싱 대상 문자열]:", json_str)
        with open("debug_llm_output_cleaned_failed.json", "w", encoding="utf-8") as f:
            f.write(json_str)
        raise

def hms_to_sec(hms):
    parts = hms.strip().split(":")
    if len(parts) == 2:
        parts = ["00"] + parts
    parts = [p.zfill(2) for p in parts]
    hms = ":".join(parts)
    t = datetime.strptime(hms, "%H:%M:%S")
    return t.hour * 3600 + t.minute * 60 + t.second

# ------------------------------
# 자막 정보를 담는 데이터 구조
# ------------------------------
@dataclass
class SrtRow:
    id: int
    start_sec: float
    end_sec: float
    text: str

# ------------------------------
# SRT 파일에서 subtitle ID, 시작/끝 시간, 텍스트 추출
# ------------------------------
def load_srt_with_indices(srt_path):
    subs = pysrt.open(srt_path)
    rows = []
    for s in subs:
        rows.append(SrtRow(
            id=s.index,
            start_sec=s.start.ordinal / 1000.0,
            end_sec=s.end.ordinal / 1000.0,
            text=s.text.replace("\n", " ").strip()
        ))
    return rows

# ------------------------------
# 특정 초(sec) 범위에 해당하는 SRT 자막 라인 추출
# ------------------------------
def slice_srt_by_seconds(srt_rows, start_sec, end_sec):
    inside = [r for r in srt_rows if r.end_sec >= start_sec and r.start_sec <= end_sec]
    if not inside:
        raise ValueError("해당 범위에 포함되는 자막 라인이 없습니다.")
    return inside, inside[0].id, inside[-1].id

# ------------------------------
# 응답의 각 cut이 subtitle ID 범위를 벗어나지 않았는지 검증
# ------------------------------
def validate_plan_indices(plan, start_sub_id, end_sub_id):
    if not isinstance(plan, dict):
        raise ValueError("LLM2 응답이 dict가 아님")

    cuts = plan.get("cuts")
    if not isinstance(cuts, list) or not cuts:
        raise ValueError("cuts가 없거나 비어있음")

    allowed_ids = set(range(start_sub_id, end_sub_id + 1))

    for i, cut in enumerate(cuts):
        s_id = cut.get("start_sub_id")
        e_id = cut.get("end_sub_id")
        sids = cut.get("subtitle_ids")

        if not isinstance(s_id, int) or not isinstance(e_id, int):
            raise ValueError(f"cut[{i}] start_sub_id/end_sub_id 타입 오류")
        if s_id < start_sub_id or e_id > end_sub_id or s_id > e_id:
            raise ValueError(f"cut[{i}] subtitle id 범위 오류: {s_id}~{e_id}")
        if not isinstance(sids, list) or not sids:
            raise ValueError(f"cut[{i}] subtitle_ids 누락/비어있음")
        if any(not isinstance(x, int) for x in sids):
            raise ValueError(f"cut[{i}] subtitle_ids 내 타입 오류")
        if any(x not in allowed_ids for x in sids):
            raise ValueError(f"cut[{i}] subtitle_ids가 허용 범위 벗어남")
        if min(sids) < s_id or max(sids) > e_id:
            raise ValueError(f"cut[{i}] subtitle_ids가 start_sub_id~end_sub_id 밖")


def debug_and_fix_cut_ids(parsed_json, clip_start=None, clip_end=None):
    if "cuts" not in parsed_json:
        print("[에러] cuts 필드 없음")
        return parsed_json

    for idx, cut in enumerate(parsed_json["cuts"]):
        try:
            # --- start_sub_id ---
            sid = cut.get("start_sub_id")
            if sid is None:
                print(f"[보정] cut[{idx}] start_sub_id 누락 → subtitle_ids에서 추론")
                sid = min(subtitle_ids)
                cut["start_sub_id"] = sid
            if isinstance(sid, str) and sid.isdigit():
                print(f"[디버그] cut[{idx}] start_sub_id 문자열 → int 변환")
                cut["start_sub_id"] = int(sid)
            elif isinstance(sid, list) and len(sid) == 1:
                print(f"[디버그] cut[{idx}] start_sub_id 리스트 → 첫 원소 int 변환")
                cut["start_sub_id"] = int(sid[0])
            elif not isinstance(sid, int):
                raise ValueError(f"start_sub_id가 정수가 아님: {sid}")

            # --- end_sub_id ---
            eid = cut.get("end_sub_id")
            if eid is None:
                print(f"[보정] cut[{idx}] end_sub_id 누락 → subtitle_ids에서 추론")
                eid = max(subtitle_ids)
                cut["end_sub_id"] = eid
            if isinstance(eid, str) and eid.isdigit():
                print(f"[디버그] cut[{idx}] end_sub_id 문자열 → int 변환")
                cut["end_sub_id"] = int(eid)
            elif isinstance(eid, list) and len(eid) == 1:
                print(f"[디버그] cut[{idx}] end_sub_id 리스트 → 첫 원소 int 변환")
                cut["end_sub_id"] = int(eid[0])
            elif not isinstance(eid, int):
                raise ValueError(f"end_sub_id가 정수가 아님: {eid}")

            # --- subtitle_ids 확인 ---
            subtitle_ids = cut.get("subtitle_ids", [])
            if not isinstance(subtitle_ids, list) or len(subtitle_ids) == 0:
                raise ValueError("subtitle_ids가 비어있거나 리스트가 아님")

            # --- clip 범위 초과 확인
            if cut.get("start", 0) < clip_start or cut.get("end", 99999) > clip_end:
                print(f"[경고] cut[{idx}]이 clip 시간 범위를 벗어남")

        except Exception as e:
            print(f"[에러] cut[{idx}] 검사 실패: {e}")
            raise


# ------------------------------
# subtitle ID → 초 단위(start, end)로 변환
# ------------------------------
def attach_seconds(plan, srt_rows):
    id2row = {r.id: r for r in srt_rows}
    for i, cut in enumerate(plan["cuts"]):
        s_id = cut["start_sub_id"]
        e_id = cut["end_sub_id"]

        if s_id not in id2row or e_id not in id2row:
            raise ValueError(f"cut[{i}]의 자막 ID가 존재하지 않음: {s_id}, {e_id}")

        cut["start"] = id2row[s_id].start_sec
        cut["end"]   = id2row[e_id].end_sec
    return plan

# ------------------------------
# 변환된 초 단위가 클립 전체 범위 내에 있는지 검증
# ------------------------------
def validate_plan_seconds(plan, clip_start_sec, clip_end_sec):
    for i, cut in enumerate(plan["cuts"]):
        if cut["start"] < clip_start_sec or cut["end"] > clip_end_sec:
            raise ValueError(
                f"cut[{i}]의 시간 범위({cut['start']}~{cut['end']})가 clip 전체 범위({clip_start_sec}~{clip_end_sec})를 벗어남."
            )
        if cut["start"] >= cut["end"]:
            raise ValueError(f"cut[{i}]의 start가 end보다 크거나 같음.")


def srt_to_json(srt_path: str):
    # 1. SRT 파일 읽기
    with open(srt_path, 'r', encoding='utf-8-sig') as f:
        srt_content = f.read()

    # 2. SRT 파싱
    subtitles = list(srt.parse(srt_content))

    # 3. 원하는 JSON 구조로 변환
    json_data = {}
    for sub in subtitles:
        # key: index (문자열), value: start/end/text 정보
        json_data[str(sub.index)] = {
            "start": sub.start.total_seconds(),
            "end":   sub.end.total_seconds(),
            "text":  sub.content.replace('\n', ' ')
        }

    return json_data