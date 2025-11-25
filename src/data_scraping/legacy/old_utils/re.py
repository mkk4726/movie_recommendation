import re

# 2시간22 -> 144
def time_to_minutes(time_str: str) -> int:
    # '시간'과 '분' 앞에 있는 숫자를 추출하는 정규식
    hours_match = re.search(r'(\d+)시간', time_str)
    minutes_match = re.search(r'(\d+)분', time_str)

    # 추출한 '시간'과 '분' 값을 int로 변환 (없을 경우 0으로 처리)
    hours = int(hours_match.group(1)) if hours_match else 0
    minutes = int(minutes_match.group(1)) if minutes_match else 0

    # 시간을 분으로 변환한 값과 분을 더해줌
    total_minutes = hours * 60 + minutes
    
    return total_minutes

def extract_number(text: str) -> float:
    # 쉼표를 제거하여 숫자 부분만 남김
    text = text.replace(',', '')
    # 정규식을 이용해 숫자 부분만 추출
    match = re.search(r'(\d+\.\d+|\d+)', text)
    
    if match:
        return float(match.group(0))
    else:
        return None
    
def extract_movie_age(text: str) -> str:
    if '전체' == text:
        return '12'
    elif '청불' == text:
        return "19"
    else:
        return extract_number(text)
    

def remove_emojis(string):
    emoji_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F" # emoticons
        u"\U0001F300-\U0001F5FF" # symbols & pictographs
        u"\U0001F680-\U0001F6FF" # transport & map symbols
        u"\U0001F1E0-\U0001F1FF" # flags (iOS)
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+", 
        flags=re.UNICODE
    )
    
    return emoji_pattern.sub(r'', string)