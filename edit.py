# edit.py
import json
import numpy as np
from moviepy.editor import *
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
from utils import srt_to_json

def trim_intro(extract_path):

    intro = VideoFileClip(extract_path, audio=True)

    intro_clip = intro.subclip(0, 1)

    intro.close()

    return intro_clip


def trim_video_only_from_json(extract_path, json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        cuts = json.load(f)["cuts"]

    min_start = min(c["start"] for c in cuts)
    max_end   = max(c["end"]   for c in cuts)
    print(f"⏱ 잘라낼 구간: {min_start}초 ~ {max_end}초")

    # 클립 로드 (오디오 포함)
    clip = VideoFileClip(extract_path, audio=True)
    sub  = clip.subclip(min_start, max_end)

    print("subclip 완료")
    clip.close()
    return sub


def generate_video_from_json(json_path, intro_video, trim_video, output_path, font_path):
    # — 전체 쇼츠 해상도 및 레이아웃 설정
    FRAME_W, FRAME_H = 720, 1280
    VID_W, VID_H = 720, 480  #(직사각 모양)

    # 중앙 배치할 y좌표(본문 영상을 세로 방향으로 어디에 배치할지를 결)
    video_y = (FRAME_H - VID_H) / 2

    # — 멀티라인 중앙 정렬 텍스트 생성 유틸
    def make_textclip(text, fontsize, color, box_size, y_offset, line_spacing=10, duration=1):
        # ① 빈 RGBA 이미지 생성
        img = Image.new("RGBA", box_size, (0,0,0,0))
        font = ImageFont.truetype(font_path, fontsize)
        draw = ImageDraw.Draw(img)

        # ② 줄별 텍스트 크기 측정 & 중앙 정렬
        lines = text.split("\n")
        sizes = [draw.textbbox((0,0), line, font=font)[2:] for line in lines]

        y = y_offset
        for (line, (w,h)) in zip(lines, sizes):
            x = (box_size[0] - w) // 2
            draw.text(
                (x, y), line, font=font,
                fill=color,
                stroke_width=2,
                stroke_fill="black"
                )
            y += h + line_spacing

        # ③ numpy 배열로 변환 후 ImageClip 생성
        return ImageClip(np.array(img)).set_duration(duration).set_position(("center", 0))

    # — 글자 모양 배경 텍스트 생성 유틸 (editor_note, caption용)
    def make_shaped_textclip(text, fontsize, text_color, bg_color, padding, y_pos, duration=1):
        font = ImageFont.truetype(font_path, fontsize)

        # 흰색 글자 형태의 그레이스케일 마스크
        mask = font.getmask(text, mode="L") # 글자 윤곽 마스크
        w, h = mask.size

        # ① 마스크를 PIL 이미지로 변환
        mask_img = Image.new("L", (w, h))
        mask_img.putdata(list(mask))

        # ② bg_color로 된 캔버스에 마스크를 씌워 배경 패치
        canvas = Image.new("RGBA", (w + padding*2, h + padding*2), (0,0,0,0))
        canvas.paste(Image.new("RGBA", (w, h), bg_color), (padding, padding), mask_img)
        draw = ImageDraw.Draw(canvas)
        draw.text((padding, padding), text, font=font, fill=text_color)

        # ④ ImageClip 생성 (가로 가운데 정렬, y_pos 절대 위치)
        return ImageClip(np.array(canvas))\
               .set_duration(duration)\
               .set_position(((FRAME_W - (w + padding*2)) // 2, y_pos))

    # 1) JSON 로드
    with open(json_path, "r", encoding="utf-8") as f:
        info = json.load(f)
    
    title, subtitle, cuts = info["title"], info.get("subtitle", ""), info["cuts"]

    subtitles = srt_to_json(json_path)    

    # JSON의 첫 컷 start를 오프셋으로 사용
    offset = cuts[0]["start"]

    # 2) 영상 로드
    intro_raw = intro_video
    video     = trim_video
    final_clips = []

    # 3) 인트로 처리
    dur = intro_raw.duration

    #전체 배경
    bg  = ColorClip((FRAME_W, FRAME_H), color=(0,0,0)).set_duration(dur)
    vid_crop = intro_raw.crop(x_center=intro_raw.w/2, y_center=intro_raw.h/2,width=VID_W, height=VID_H)
    vid = vid_crop.set_position(("center", video_y))

    # (3) 타이틀/서브타이틀 오버레이
    over = [
        bg, vid,
        make_textclip(title, fontsize=50, color="white",
                      box_size=(FRAME_W, FRAME_H), y_offset=150, duration=dur),
        # subtitle y_offset를 100으로 내려 충돌 방지
        make_textclip(subtitle, fontsize=35, color="white",
                      box_size=(FRAME_W, FRAME_H), y_offset=300, duration=dur)
    ]
    final_clips.append(CompositeVideoClip(over).set_audio(intro_raw.audio))

    # 4) 본문 컷 처리
    for i, cut in enumerate(cuts, start=1):
        o_s, o_e = cut["start"], cut["end"]
        s = max(0, o_s - offset)
        e = min(video.duration, o_e - offset)
        dur = e - s
        if dur <= 0:
            continue

        sub = video.subclip(s, e)
        bg  = ColorClip((FRAME_W, FRAME_H), color=(0,0,0)).set_duration(dur)


        # 본문도 동일한 크롭 & 중앙 배치(중심 좌표를 기준으로 좌우로 360픽셀, 상하로 240픽셀씩 잘라서 -> 720*480 영역만 추출함)
        vid_crop = sub.crop(x_center=sub.w/2, y_center=sub.h/2,width=VID_W, height=VID_H)
        vid = vid_crop.set_position(("center", video_y))

        over = [
            bg, vid,
            make_textclip(title,    fontsize=50, color="white",
                          box_size=(FRAME_W, FRAME_H), y_offset=100, duration=dur),
            # 본문에서도 subtitle y_offset=100으로 조정
            make_textclip(subtitle, fontsize=30, color="lightgray",
                          box_size=(FRAME_W, FRAME_H), y_offset=300, duration=dur)
        ]

        # editor_note
        note = cut.get("editor_note", "").strip()
        if note:
            over.append(make_shaped_textclip(
                note, fontsize=28, text_color="white", bg_color=(0,0,0,255),
                padding=8, y_pos=video_y + VID_H - 200, duration=dur
            ))

        # caption (글자 모양 배경)
        subtitle_ids = cut["subtitle_ids"]
        for id in subtitle_ids:
            subinfo = subtitles[str(id)]    # JSON 키는 문자열이므로 str(id) 사용
            cap_s, cap_e, text = (subinfo["start"],
                                subinfo["end"],
                                subinfo["text"])
            cap_dur = cap_e - cap_s
            cap_s_in_clip = max(0, cap_s - o_s)
            over.append(make_shaped_textclip(
                text, fontsize=32, text_color="white", bg_color=(0,0,0,255),
                padding=10, y_pos=video_y + VID_H - 60, duration=cap_dur
            ).set_start(cap_s_in_clip))

        # narration (글자 모양 배경)
        narr = cut.get("narration", "").strip()
        tts_audio = None

        if narr:
            # ① TTS 음성 생성 및 로딩
            tts_path = f"tts_{i}.mp3"
            gTTS(text=narr, lang='ko').save(tts_path)
            tts_audio = AudioFileClip(tts_path)
            tts_duration = tts_audio.duration

            # ② 자막 생성 (TTS 길이만큼만 표시)
            over.append(make_shaped_textclip(
                narr, fontsize=32, text_color="yellow", bg_color="black",
                padding=8, y_pos=video_y + VID_H + 40, duration=tts_duration
            ))

            # ③ sub.audio에서 남은 부분 잘라내기
            remaining_dur = dur - tts_duration
            if remaining_dur > 0:
                sub_trimmed = sub.audio.subclip(tts_duration, dur)
            else:
                sub_trimmed = None

            # ④ 오디오 이어붙이기: TTS + 남은 sub.audio
            audio_parts = [tts_audio.volumex(1.2)]
            if sub_trimmed:
                audio_parts.append(sub_trimmed.volumex(0.5))

            mixed_audio = concatenate_audioclips(audio_parts)

        else:
            mixed_audio = sub.audio

        # 최종 클립 구성
        clip = CompositeVideoClip(over).set_duration(dur).set_audio(mixed_audio)
        final_clips.append(clip)


    # 5) 합치고 저장
    if final_clips:
        final = concatenate_videoclips(final_clips, method="compose")
        final.write_videofile(
            output_path,
            fps=30,
            audio=True,                       # 오디오 포함
            audio_codec="aac",                # 사용할 오디오 코덱
            temp_audiofile="temp-audio.m4a",  # 임시 오디오 파일 지정
            remove_temp=True                  # 렌더 후 임시 파일 삭제
        )
        print("✅ 쇼츠용 영상 저장 완료:", output_path)
    else:
        print("🚫 처리할 클립이 없습니다.")