import re

def clean_line(line):
    # 괄호 내 지시문 제거
    line = re.sub(r'\([^)]*\)', '', line)
    # <i>, </i> 태그 제거
    line = re.sub(r'<[^>]+>', '', line)
    return line.strip()

def clean_srt_blocks(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    output = []
    block = []
    
    for line in lines:
        if line.strip() == '':
            # 블록 종료 처리
            if block:
                cleaned_block = [clean_line(l) for l in block]
                text_lines = [l for l in cleaned_block[2:] if l.strip()]
                if text_lines:
                    output.extend(cleaned_block)
                    output.append('')  # 블록 구분 빈 줄
                # text 없으면 번호+시간 포함한 블록 전체 제거
                block = []
        else:
            block.append(line.rstrip('\n'))

    # 마지막 블록 누락 방지
    if block:
        cleaned_block = [clean_line(l) for l in block]
        text_lines = [l for l in cleaned_block[2:] if l.strip()]
        if text_lines:
            output.extend(cleaned_block)

    # 파일 저장
    with open(output_path, 'w', encoding='utf-8') as f:
        for line in output:
            f.write(line + '\n')

# === 실행 파트 ===
if __name__ == "__main__":
    input_file = "input/s0218_kor.srt"          # 여기에 원본 SRT 파일 이름
    output_file = "output/srt/s0218_kor_clean.srt"  # 저장할 새 SRT 파일 이름

    clean_srt_blocks(input_file, output_file)
    print(f"✅ 정제가 완료되었습니다: {output_file}")
