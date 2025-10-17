import json


# JSON 파일 읽기
def read_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        # print("JSON 데이터 읽기 성공:", data)
        return data
    except FileNotFoundError:
        print("파일을 찾을 수 없습니다.")
        return {}
    except json.JSONDecodeError:
        print("JSON 파일 형식 오류입니다.")
        return {}

# JSON 파일 쓰기
def write_json(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
        # print("JSON 파일 쓰기 성공")
    except Exception as e:
        print("JSON 파일 쓰기 중 오류 발생:", e)