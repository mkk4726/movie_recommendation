from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from lxml import etree
from assets.utils.re import extract_number
import time

def fetch_with_scroll(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)

        # JavaScript로 스크롤을 끝까지 내리기
        previous_height = 0
        i = 1
        while True:
            current_height = page.evaluate("document.body.scrollHeight")
            if current_height == previous_height:
                break
            previous_height = current_height
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            # print(f"scroll down {i}", end='\r'); i += 1  # '\r'로 줄을 덮어씀

            time.sleep(2)  # 콘텐츠 로딩을 기다림
            
        # 모든 스크롤이 완료된 후 콘텐츠 가져오기
        content = page.content()
        browser.close()
        return content

def get_data(custom_id):
    html_source = fetch_with_scroll(f'https://pedia.watcha.com/ko-KR/users/{custom_id}/contents/movies/ratings')

    # 3. BeautifulSoup으로 HTML 파싱
    soup = BeautifulSoup(html_source, 'html.parser')

    # 4. BeautifulSoup 객체를 lxml로 변환
    tree = etree.HTML(str(soup))
    
    data_list = []

    i = 1

    while True:
        try:
            # print(f"movie {i}", end='\r')  # '\r'로 줄을 덮어씀
            movie_id = tree.xpath(f'//*[@id="root"]/div[1]/section/section/div[1]/section/div[1]/div/ul/li[{i}]/a/@href')[0].split('/')[-1]
            movie_name = tree.xpath(f'//*[@id="root"]/div[1]/section/section/div[1]/section/div[1]/div/ul/li[{i}]/a/div[2]/div[1]/text()')[0].replace('/', '')
            movie_rate = extract_number(tree.xpath(f'//*[@id="root"]/div[1]/section/section/div[1]/section/div[1]/div/ul/li[{i}]/a/div[2]/div[2]/text()')[0])
            
            data = [movie_id, movie_name, movie_rate]
            data_list.append(data)
            i += 1
        except Exception as e:
            # print(e)
            break
        
    return data_list

if __name__ == "__main__":
    from assets.utils.txt import append_to_txt, read_txt
    import pandas as pd
    
    column_names = ["MovieID", "CustomID", "Comment", "Rating", "N_Likes"]
    row = read_txt("./data/movie_comments.txt")
    movie_comments_df = pd.DataFrame(row, columns=column_names)
        
    row = read_txt('./data/custom_movie_rating.txt')
    column_names = ["CustomID", "MovieID", "MovieName", "Rating"]
    custom_movie_rating_df = pd.DataFrame(row, columns=column_names)
    
    custom_id_list = list(set(movie_comments_df['CustomID']) - set(custom_movie_rating_df['CustomID']))
    
    for i, custom_id in enumerate(custom_id_list):
        print(f"{i} / {len(custom_id_list)}", end='\r')  # '\r'로 줄을 덮어씀
        data_list = get_data(custom_id)
        
        for data in data_list:
            append_to_txt("./data/custom_movie_rating.txt", [custom_id, *data])
