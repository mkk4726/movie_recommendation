import pickle

def save_file_to_pickle(file:str, file_path:str):
    """
    file: 저장할 파일
    file_path: 저장할 이름 (~.pkl)
    """
    # pickle 파일로 저장
    with open(file_path, 'wb') as f:  # 'wb'는 write binary의 약자
        pickle.dump(file, f)
        
def load_file_from_pickle(file_path:str):
    # pickle 파일에서 데이터 불러오기
    with open(file_path, 'rb') as f:  # 'rb'는 read binary의 약자
        file = pickle.load(f)
        
    return file