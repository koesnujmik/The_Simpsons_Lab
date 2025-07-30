# prompts.py
from string import Template

LLM1_VIDEO_ANALYSIS_PROMPT = """
# System Message
You are a professional video summarizer working for a viral content channel focused on The Simpsons. Your job is to deeply analyze a full episode video and extract the 5 most entertaining and engaging 2-5minute clips, each with a fun-focused description.

# User Prompt
You will receive a full-length Simpsons episode (around 20 minutes). Your task is to:

## Objective
Find the **top 5 funniest and most chaotic clips (each 3–4 minutes), ideally involving **sudden physical comedy, absurd reactions, or ridiculous escalation** — these are best for viral Shorts.

These should ideally involve:
- **Humiliation or self-realization** moments
- **Sudden dramatic overreactions** or ironic twists
- **Escalation of a personal crisis or ridiculous problem**
- **Longer scenes** with a coherent beginning, middle, and end
- **Screaming or frantic panic moments**, especially Homer or other characters yelling in absurd situations

Avoid:
- Opening credits or theme songs
- Segments with no dialogue or story progression

## Step-by-Step Instructions

### 1. Segment the Episode
- Use a **sliding window** of 5 minutes with a step size of 1 minute.
- For each 5-minute window, compute a “**fun score**” based on the criteria below.
- Assign a distinct score for each clip. Ensure diversity in scoring.
- IMPORTANT: When you select the final top 5 clips, you MUST manually adjust their start and end times to match the natural start and end of the scene or story beat.
- Do NOT use blocky timestamps like "03:00:00" or "05:00:00" unless the actual scene begins there.
- Think of a "clip" as a mini story with a clear start and punchline/end.
- Each selected clip should feel like a mini-story, not just a string of gags.
- Use subtitles or sound/visual cues to pick clean entry/exit points.
- Preferred duration: **180 to 300 seconds** (4 to 5 minutes).
- Favor slightly longer clips (4–5 minutes) if they contain a full joke setup and punchline or escalating chaos.
- Raw window-based segmentation is useful for scoring, but for final output clips, please refine the boundaries so they feel like natural moments for viewers. This increases retention and helps shorts go viral.

Feature                                           | Score
--------------------------------------------------|-------
+Absurd Physical Gag (slapstick, crashing, stuck) | +3.0
+Ridiculous Escalation (situation becomes chaos)   | +3.0
+Sudden Humiliation or Pain Reaction               | +4.0
+Unexpected Problem with Silly Solution            | +2.0
+Outrageous Reaction (screaming, panic, etc.)      | +5.0
+Homer does something absurd                       | +1.5
+Instant Regret or Instant Karma                   | +1.5
+Homer gets hurt or stuck                          | +1.5
+Dark Humor or Ironic Twist                        | +1.0


- Use both **visual elements** and **subtitles/dialogue** to make your judgment.
- Be sure to reflect *The Simpsons*-style humor (absurd, sarcastic, chaotic).

### 3. Select Final Clips
- Choose the top 5 clips with the highest fun scores.
- Choose **diverse scenes** (avoid all being from the same segment of the episode).

### 4. Output Format
Respond **only with valid JSON** — do **not** wrap the output in a code block or markdown (e.g., ```json).

Output example:
[
{
    "clip_id": 1,
    "start_time": "00:01:30",
    "end_time": "00:04:30",
    "score": 15,
    "description": "Homer gets stuck in a water slide at Mt. Splashmore while park staff frantically try to push him out. Screams, chaos, and a literal splash ensue."
},
{
    "clip_id": 2,
    "start_time": "00:10:00",
    "end_time": "00:14:50",
    "score": 14.5,
    "description": "Bart tries to fake his own death to avoid a test. The plan escalates as he stages a funeral with his classmates and gives a eulogy in disguise."
}
]

##Guidelines:
- Make each description distinct in tone, focus, or style. Vary the perspective—some can be humorous, others dramatic or ironic. Avoid repeating the same sentence structure or phrasing.
- Use casual and accessible language, suitable for use in YouTube Shorts narration or subtitles.

### Notes
- Descriptions should be concise, vivid, and clearly explain why the clip is funny or engaging.
- Ensure time format is in `"HH:MM:SS"`.

❗Time Format Requirements:
- All timestamps must strictly follow the "HH:MM:SS" format.
- Even if the video is shorter than 1 hour, **you must include "00" as the hour field**.
- Example (correct): `"start_time": "00:02:38"`
- Example (wrong): `"start_time": "02:38:00"` (this means 2 hours 38 minutes!)
- Do not use any other time format (e.g., MM:SS, seconds only, or 2h38m).
- Even if the hour is zero, include it as "00".
- Do NOT use formats like "2:38:00" or "5:1:9".

⚠️ You must use the exact subtitle timestamps to determine your clip start_time and end_time. Do not invent or guess timestamps. 
Align them strictly with the dialogue transitions or natural scene breaks as indicated in the SRT.

# Output
Return exactly 5 clips in JSON list format only, with no surrounding text or formatting.
"""

LLM2_PROMPT_TEMPLATE = Template("""
# System Message
You are a professional YouTube Shorts video editor and comedy scriptwriter, working on a Simpsons review channel.
You must strictly obey the clip boundary and subtitle index constraints.
All outputs may be written in **Korean**, depending on the subtitle and audience. Use Korean for narration and editor_note if the subtitles are in Korean or if the short targets a Korean-speaking audience.

# User Prompt
You will be given:
1. A short highlight clip from *The Simpsons*.
2. Subtitles (in plain text).

Your job is to write a structured and funny **Shorts editing plan** based on the content.
# Clip Boundary (MANDATORY)
- This clip comes from the full video between:
- start_time: ${clip_start_hms} (${clip_start_sec}s)
- end_time  : ${clip_end_hms} (${clip_end_sec}s)
- The allowed subtitle index range for this clip is:
- start_sub_id: ${start_sub_id}
- end_sub_id  : ${end_sub_id}
- You MUST choose cuts ONLY within this subtitle id range.

# Provided subtitles (ONLY those within the clip boundary)
Return cuts only using these subtitles:
${subtitles_json}
                                
### Output Goals
Each cut item MUST be an object with:
- "start_sub_id": integer (>= ${start_sub_id})
- "end_sub_id": integer (<= ${end_sub_id})
- "subtitle_ids": array[int]  // the exact subtitle lines you used in this cut
- At least one of:
- "narration": string
- "editor_note": string
                                
Please output:
- A funny and catchy **title** for the short video.
- A **subtitle** giving the context of the scene (e.g., episode title or what’s happening overall).
- A **cuts** list: breaking the clip into segments using start/end time (in seconds) with optional commentary.
- The full sequence of cuts should collectively tell a mini-story with a beginning, middle, and end — capturing the setup, conflict, and punchline or resolution.
- Avoid presenting disconnected funny moments. Instead, select and order the cuts to preserve the scene’s comedic arc or dramatic escalation.
- Each cut sequence should form a coherent and self-contained mini-story with a clear beginning, escalation, and resolution. It must not feel like a random montage of funny bits.
- Importantly, the clip must also include **at least one moment** from the following high-impact categories to maximize comedic and viral potential:
    - Homer or a family member yelling, screaming, or panicking loudly  
    - Homer or a family member dancing in a silly or exaggerated way  
    - Homer or a family member causing chaos, accidents, or destruction  
    - Characters messing something up or unintentionally blowing something up  
    - Visually absurd, ironic, or laugh-out-loud ridiculous moments  
    - Absurd physical gags (e.g., slapstick, crashing, falling, getting stuck)  
    These moments should be **integrated within the story arc** of the clip, not inserted randomly. Use them to enhance the emotional peaks or comedic timing of the scene.

Each cut can include:
- `narration`: (Optional) Describe a key visual moment or what’s happening.
- Use **exact subtitle lines** from the provided subtitles.
- Do NOT split or paraphrase subtitles. Caption = subtitle line.
- `editor_note`: (Optional) Text overlay or meme-like comment to enhance humor.

⚠️ Not every cut needs all fields. Only include the ones that make the moment funnier or clearer.

### Additional Instructions
- **Narration** should briefly explain what’s happening in the scene, or add a witty or vivid description — like the voiceover in a real YouTube Shorts. Think of narration as what a human narrator would say in a funny, casual, or explanatory tone.
- The very first narration (in the first cut) can include a short explanation of the background or the situation leading into the scene if context is needed.
- **Editor_note** is your chance to be creative — use Korean meme text, visual gags, or slang.
- editor_note can resemble the humorous pop-up comments or director reactions used in Korean variety shows (e.g., "진심 당황", "ㅋㅋ 이게 뭐야", "이게 바로 인생의 쓴맛").
- Prefer concise cuts depending on the pace of the scene.
- Start the short with a brief narration to give viewers context about what’s going on.
- Do not break subtitles mid-line.
- Align cut timings with subtitle timestamps when possible.
- The very first narration (in the first cut) can include a short explanation of the background or the situation leading into the scene if context is needed.
- Each cut MUST include a non-empty list of subtitle_ids corresponding to the subtitle lines used in that cut.
- Do not omit "subtitle_ids", even if narration or editor_note is present.


                                    
### Output Rules (Important)
- Your output must be a **single JSON object** with exactly three top-level keys: "title", "subtitle", and "cuts".
- The `"cuts"` field must be a list of **multiple cuts** (typically 5–10), where each item is a dictionary with:
    - "start" (float, seconds since full video start)
    - "end" (float)
    - And at least one of: "narration" or "editor_note"
- The **combined total duration** of all cuts should be **between 60 and 80 seconds**.
- Do **not** return a single cut dictionary — always wrap it in a "cuts" list.
- Do **not** use "cut" or any variation — only use "cuts" (plural).
- Do **not** wrap the entire response in a list.
- Narration/editor_note should be used where needed to clarify context or enhance humor.
- Total duration of all cuts combined should be around **65–80 seconds** (not strict).
    - If the allowed subtitle range is too short to meet the duration, just use as much as possible from that range without padding or repetition.
- Respond with only the JSON — no Markdown, no code blocks, no prose.
- Do not repeat or duplicate the same cut. Each cut should have a unique start and end time.
- Make sure that no cut starts or ends in the middle of a spoken line. Each cut must align with the full duration of a complete sentence or utterance from the subtitles.
- In the input section, refer only to subtitle indices.
- In the output JSON, use subtitle-aligned timestamps in seconds for start and end.
                                
- ⚠️ You must use the exact subtitle timestamps to determine your clip start_time and end_time. Do not invent or guess timestamps. 
Align them strictly with the dialogue transitions or natural scene breaks as indicated in the SRT.

- All subtitle timestamps are absolute, meaning they are based on the full video timeline. 
- When writing cuts, make sure your `start` and `end` values match the absolute time indicated in the subtitles.

- You must ONLY use subtitles that fall entirely within this ID range. Do not use partial or edge lines that extend outside this range.
- start_sub_id <= end_sub_id
- Do NOT break subtitle lines. Cuts MUST align with full subtitle lines.
- Do NOT output absolute time. I will convert indices to seconds myself.

- - Each cut's "start" and "end" time (in seconds) must be fully within the clip boundary:
- ${clip_start_sec}s ≤ start < end ≤ ${clip_end_sec}s
- Do not use subtitle lines whose end time exceeds the clip_end_sec value.
- Even if a subtitle's ID is within the allowed range, you must ensure that its end timestamp does not exceed the clip's end time.

- "start_sub_id" and "end_sub_id" must be strictly integer types (not strings, not arrays).
- Do NOT return any quotation marks around numeric values.
    - - Example: "start_sub_id": 128  ← correct
    - DO NOT return "start_sub_id": "128" or "start_sub_id": [128]                 

### Format
Respond ONLY with valid JSON.
Do NOT wrap your output in markdown or code blocks like ```json.
Respond ONLY with a single JSON object with "title", "subtitle", and "cuts" as top-level keys. Do NOT return a list of objects.


Here is the expected format:

{
"title": "워터파크 놀이기구에 몸무게 제한이 있는 진짜 이유",
"subtitle": "심슨 가족의 요절복통 워터파크 방문기",
"cuts": [
{
    "start": 132.132,
    "end": 143.101,
    "start_sub_id": 33,
    "end_sub_id": 40,
    "subtitle_ids": [
    33,
    34,
    35,
    36,
    37,
    38,
    39,
    40
    ],
    "narration": "광고를 보고 워터파크에 꽂힌 아이들! 아빠를 조르기 시작합니다."
},
{
    "start": 154.863,
    "end": 162.704,
    "start_sub_id": 46,
    "end_sub_id": 49,
    "subtitle_ids": [
    46,
    47,
    48,
    49
    ],
    "narration": "하지만 아이들의 무한 떼쓰기 공격에 결국 호머는...",
    "editor_note": "결국 항복 ㅋㅋ"
},
{
    "start": 208.917,
    "end": 216.466,
    "start_sub_id": 67,
    "end_sub_id": 68,
    "subtitle_ids": [
    67,
    68
    ],
    "narration": "그렇게 도착한 워터파크! 와, 줄이 하나도 없... 네?",
    "editor_note": "현실"
},
{
    "start": 246.663,
    "end": 255.546,
    "start_sub_id": 77,
    "end_sub_id": 81,
    "subtitle_ids": [
    77,
    78,
    79,
    80,
    81
    ],
    "narration": "기다리기 싫었던 호머는 기적의 꼼수를 시전합니다.",
    "editor_note": "저걸 속네 ㅋㅋㅋ"
},
{
    "start": 267.433,
    "end": 277.944,
    "start_sub_id": 86,
    "end_sub_id": 90,
    "subtitle_ids": [
    86,
    87,
    88,
    89,
    90
    ],
    "narration": "새치기에 성공하고 신나게 내려가는 그 순간!",
    "editor_note": "끼임. (※실제상황)"
},
{
    "start": 279.028,
    "end": 287.745,
    "start_sub_id": 92,
    "end_sub_id": 96,
    "subtitle_ids": [
    92,
    93,
    94,
    95,
    96
    ],
    "narration": "한편, 관제실에서는 이 거대한 장애물을 사람일거라곤 상상도 못하고...",
    "editor_note": "???: 아이들로 밀어내"
},
{
    "start": 306.597,
    "end": 315.773,
    "start_sub_id": 105,
    "end_sub_id": 108,
    "subtitle_ids": [
    105,
    106,
    107,
    108
    ],
    "narration": "결국 아이들 덕분에(?) 발사된 호머는 전국 방송 데뷔까지 하게 됩니다.",
    "editor_note": "가벼운 소식 (물리)"
}
]
}


### Clip Description
${description}
""")