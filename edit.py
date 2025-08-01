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
    return sub


def generate_video_from_json(srt_path, json_path, intro_video, trim_video, output_path, font_path):
    # — 전체 쇼츠 해상도 및 레이아웃 설정
    FRAME_W, FRAME_H = 720, 1280
    VID_W, VID_H = 720, 480  #(직사각 모양)

    # 중앙 배치할 y좌표(본문 영상을 세로 방향으로 어디에 배치할지를 결)
    video_y = (FRAME_H - VID_H) / 2
    

    def auto_linebreak(text, font, max_width):
        """
        text: 입력 문자열 (여러 개의 단락을 '\n'로 구분 가능)
        font: PIL.ImageFont 인스턴스
        max_width: 한 줄의 최대 픽셀 너비
        """
        lines = []

        paragraphs = text.split('\n')

        for para in paragraphs:
            if not para:
                # 빈 단락(연속된 \n 등)이면 빈 줄 추가
                lines.append('')
            else:
                words = para.split()
                line = ""
                for word in words:
                    test_line = f"{line} {word}".strip()
                    w, _ = font.getsize(test_line)
                    if w <= max_width:
                        line = test_line
                    else:
                        # 현재 line 확정 후 새 줄 시작
                        lines.append(line)
                        line = word
                # 해당 단락 마지막 줄 추가
                lines.append(line)

        return lines

    # — 멀티라인 중앙 정렬 텍스트 생성 유틸
    def make_textclip(text, fontsize, color, box_size, y_offset, line_spacing=10, duration=1):
        # ① 빈 RGBA 이미지 생성
        img = Image.new("RGBA", box_size, (0,0,0,0))
        font = ImageFont.truetype(font_path, fontsize)
        draw = ImageDraw.Draw(img)

        # 자동 줄바꿈 처리: 최대 width 기준
        wrapped_lines = auto_linebreak(text, font, max_width=box_size[0] - 40)

        # ② 줄별 텍스트 크기 측정 & 중앙 정렬
        lines = wrapped_lines    
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
    def make_shaped_textclip(
        text,
        box_size,
        fontsize,
        text_color,
        bg_color,
        padding,
        y_pos,
        line_spacing=10,
        duration=1
    ):
        font = ImageFont.truetype(font_path, fontsize)

        # 1) 단어 단위 & '\n' 처리해서 줄 리스트 생성
        wrapped_lines = auto_linebreak(text, font, max_width=box_size[0] - 2*padding)

        # 2) 각 줄별 마스크와 크기 계산
        line_masks = []
        line_sizes = []
        for line in wrapped_lines:
            mask = font.getmask(line, mode="L")
            w, h = mask.size
            mask_img = Image.new("L", (w, h))
            mask_img.putdata(list(mask))
            line_masks.append((line, mask_img))
            line_sizes.append((w, h))

        # 3) 전체 캔버스 크기 계산
        max_w = max(w for w, h in line_sizes)
        total_w = max_w + 2*padding
        total_h = sum(h for w, h in line_sizes) \
                + line_spacing*(len(line_sizes)-1) \
                + 2*padding

        canvas = Image.new("RGBA", (total_w, total_h), (0,0,0,0))
        draw = ImageDraw.Draw(canvas)

        # 4) 줄별로 가운데정렬된 배경(patch) + 텍스트 드로잉
        y = padding
        for (line, mask_img), (w, h) in zip(line_masks, line_sizes):
            # 줄마다 좌우 여백을 동일하게 두어 가운데정렬
            x_offset = padding + (max_w - w) // 2

            # 배경 패치: bg_color 사각형을 mask로 찍어내기
            patch = Image.new("RGBA", (w, h), bg_color)
            canvas.paste(patch, (x_offset, y), mask_img)

            # 텍스트 (stroke 포함) 그리기
            draw.text(
                (x_offset, y),
                line,
                font=font,
                fill=text_color,
                stroke_width=2,
                stroke_fill="black"
            )
            y += h + line_spacing

        # 5) ImageClip 생성 (가로 중앙정렬, y_pos 고정)
        clip = ImageClip(np.array(canvas)).set_duration(duration)

        # 화면 밖/안 위치에 따라 위아래 배치
        if y_pos <= video_y + VID_H:
            clip = clip.set_position(((FRAME_W - total_w)//2, y_pos - total_h))
        else:
            clip = clip.set_position(((FRAME_W - total_w)//2, y_pos))

        return clip


    # 1) JSON 로드
    with open(json_path, "r", encoding="utf-8") as f:
        info = json.load(f)
    
    title, subtitle, cuts = info["title"], info.get("subtitle", ""), info["cuts"]

    subtitles = srt_to_json(srt_path)    

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
    vid_resized = intro_raw.resize(height=VID_H)
    vid_crop = vid_resized.crop(width=VID_W, height=VID_H, x_center=vid_resized.w / 2, y_center=vid_resized.h / 2)
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
        vid_resized = sub.resize(height=VID_H)
        vid_crop = vid_resized.crop(width=VID_W, height=VID_H, x_center=vid_resized.w / 2, y_center=vid_resized.h / 2)
        vid = vid_crop.set_position(("center", video_y))

        over = [
            bg, vid,
            make_textclip(title, fontsize=50, color="white",
                        box_size=(FRAME_W, FRAME_H), y_offset=150, duration=dur),
            # subtitle y_offset를 100으로 내려 충돌 방지
            make_textclip(subtitle, fontsize=35, color="white",
                        box_size=(FRAME_W, FRAME_H), y_offset=300, duration=dur)
        ]

        # editor_note
        note = cut.get("editor_note", "").strip()
        if note:
            over.append(make_shaped_textclip(
                note, fontsize=18, box_size=(FRAME_W, FRAME_H), text_color="white", bg_color=(0,0,0,255),
                padding=8, y_pos=video_y + VID_H - 200, duration=dur
            ))

        # caption (글자 모양 배경)
        subtitle_ids = cut["subtitle_ids"]
        for id in subtitle_ids:
            try:
                subinfo = subtitles[str(id)]
            except:
                continue
            cap_s, cap_e, text = (subinfo["start"],
                                subinfo["end"],
                                subinfo["text"])
            cap_dur = cap_e - cap_s
            cap_s_in_clip = max(0, cap_s - o_s)
            print(id, s, o_s, cap_s, cap_s_in_clip, cap_dur, text)
            over.append(make_shaped_textclip(
                text, fontsize=32, box_size=(FRAME_W, FRAME_H), text_color="white", bg_color=(0,0,0,255),
                padding=10, y_pos=video_y + VID_H - 10, duration=cap_dur
            ).set_start(cap_s_in_clip))

        # narration (글자 모양 배경)
        narr = cut.get("narration", "").strip()
        tts_audio = None

        if narr:
            # ① TTS 음성 생성 및 로딩
            tts_path = f"output/tts/tts_{i}.mp3"
            gTTS(text=narr, lang='ko').save(tts_path)
            tts_audio = AudioFileClip(tts_path)
            tts_duration = tts_audio.duration

            # ② 자막 생성 (TTS 길이만큼만 표시)
            over.append(make_shaped_textclip(
                narr, fontsize=32, box_size=(FRAME_W, FRAME_H), text_color="yellow", bg_color="black",
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
