from lxml import html
from assets.utils.re import extract_number
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from lxml import etree

def get_data(movie_id):
    movie_url = f"https://pedia.watcha.com/ko-KR/contents/{movie_id}"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        page = context.new_page()
        page.goto(movie_url, timeout=600000)

        content = page.content()
        
        browser.close()
     
    # 3. BeautifulSoup으로 HTML 파싱
    soup = BeautifulSoup(content, 'html.parser')

    # 4. BeautifulSoup 객체를 lxml로 변환
    tree = etree.HTML(str(soup))

    # XPath를 사용해 데이터 추출
    try:
        title = tree.xpath('//*[@id="root"]/div[1]/section/div/div[2]/div/div/div[1]/div[2]/div/h1/text()')[0].replace('/', ' ')
    except Exception as e:
        title = None
    try:
        movie_info = tree.xpath('//*[@id="root"]/div[1]/section/div/div[2]/div/div/div[1]/div[2]/div/div[2]/text()')[0].split('·')
        year, genre, country = [item.strip().replace('/', ' ') for item in movie_info]
    except:
        year, genre, country = None, None, None
    
    try:
        movie_info2 = tree.xpath('//*[@id="root"]/div[1]/section/div/div[2]/div/div/div[1]/div[2]/div/div[3]/text()')[0].split('·')
        if len(movie_info2) == 1:
            runtime = [item.strip().replace('/', ' ') for item in movie_info2][0]
            age = None
        else:
            runtime, age = [item.strip() for item in movie_info2]
    except:
        runtime, age = None, None
            
    # 출연/제작 정보
    i = 1
    cast_production_info_list = []

    while True:
        try:
            name = tree.xpath(f'//*[@id="content_credits"]/section/div[1]/ul/li[{i}]/a/div[2]/div[1]/div[1]/text()')[0].replace('/', ' ')
            role = tree.xpath(f'//*[@id="content_credits"]/section/div[1]/ul/li[{i}]/a/div[2]/div[1]/div[2]/text()')[0].replace('/', ' ')
            
            cast_production_info_list.append((name, role))
            i += 1
        except Exception as e:
            break
    
    try:
        synopsis = tree.xpath('//*[@id="root"]/div[1]/section/div/div[2]/div/div/div[2]/section[1]/div[2]/section[3]/p/text()')[0].replace('\n', ' ').replace('/', ' ')
    except:
        synopsis = None
    try:
        avg_rating = tree.xpath('//*[@id="root"]/div[1]/section/div/div[2]/div/div/div[2]/section[1]/div[2]/section[1]/div[2]/div/div[1]/text()')[0]
    except:
        avg_rating = None
    try:
        n_rating = extract_number(tree.xpath('//*[@id="root"]/div[1]/section/div/div[2]/div/div/div[2]/section[1]/div[2]/section[1]/div[2]/div/div[2]/text()')[1])
    except:
        n_rating = None
    try:
        n_comments = tree.xpath('/html/body/div[1]/div[1]/section/div/div[2]/section/section[2]/header/span/text()')[0]
    except:
        n_comments = None
    return [title, year, genre, country, runtime, age, cast_production_info_list, synopsis, avg_rating, n_rating, n_comments]


if __name__ == "__main__":
    import pandas as pd
    from assets.utils.txt import append_to_txt, read_txt
    import time

    # print(get_data("m2djnad"))
    
    column_names = ["CustomID", "MovieID", "MovieName", "Rating"]
    row = read_txt('./data/custom_movie_rating.txt')
    custom_movie_rating_df = pd.DataFrame(row, columns=column_names)
    
    column_names = ["MovieID", "Title", "Year", "Genre", "Country", "Runtime", "Age", "Cast_Production_Info_List", "Synopsis", "Avg_Rating", "N_Rating(만명)","N_Comments"]
    row = read_txt('./data/movie_info_watcha.txt')
    movie_info = pd.DataFrame(row, columns=column_names)
    
    # 뽑아야하는 movie id값
    movie_ids = list(set(custom_movie_rating_df['MovieID']) - set(movie_info.loc[movie_info['Title']!='None', 'MovieID']))
    
    for i, movie_id in enumerate(movie_ids):
        movie_info = get_data(movie_id)
        if movie_info[0] != 'None':
            append_to_txt("./data/movie_info_watcha.txt", [movie_id, *movie_info])
            print(f"complete {i} / {len(movie_ids)}", end='\r')  # '\r'로 줄을 덮어씀

        time.sleep(2)
