def append_to_txt(file_name, data):
    """
    데이터를 /로 구분하여 txt 파일에 추가합니다.
    """
    line = "/".join(map(str, data)) + "\n"  # 데이터를 /로 구분하여 한 줄 생성
    with open(file_name, "a", encoding="utf-8") as file:
        file.write(line)
    # print(f"'{line.strip()}'이 {file_name}에 추가되었습니다.")
    
def read_txt(file_name) -> list:
    row = []
    
    # 특정 줄 확인
    with open(file_name, 'r', encoding='utf-8') as file:
        for line_number, line in enumerate(file, start=1):
            row.append(line.split('/'))
            
    return row