import re

def clean_srt_file(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    cleaned_lines = []
    for line in lines:
        # 괄호와 괄호 안의 내용 제거
        line = re.sub(r'\([^)]*\)', '', line)

        # <i> 및 </i> 제거
        line = re.sub(r'</?i>', '', line)

        # 불필요한 공백 제거
        line = line.strip()

        # 줄 내용이 남아 있으면 저장
        if line == '':
            cleaned_lines.append('\n')  # 빈 줄 유지 (srt 구분용)
        else:
            cleaned_lines.append(line + '\n')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(cleaned_lines)

    print(f"✅ 완료: 정리된 SRT 저장됨 → {output_path}")

input_path = 'input/s0218_kor.srt'
output_path = 'output/srt/s0218_kor_cleaned.srt'
clean_srt_file(input_path, output_path)

