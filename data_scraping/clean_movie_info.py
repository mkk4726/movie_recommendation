input_file = './data/movie_info_watcha.txt'
output_file = './data/movie_info_watcha_cleaned.txt'

# 파일 읽고 조건에 따라 줄 삭제
with open(input_file, 'r', encoding='utf-8') as infile, open(output_file, 'w', encoding='utf-8') as outfile:
    for line_number, line in enumerate(infile, start=1):
        try:
            # 조건: 두 번째 필드가 'None'인 경우 해당 줄 건너뜀
            if line.split('/')[1] != 'None':
                outfile.write(line)  # 조건에 맞지 않으면 줄을 그대로 저장
        except IndexError:
            # 줄이 잘못된 경우 (예: 구분자가 부족한 경우)도 건너뜀
            continue

print(f"Filtered file saved to {output_file}")