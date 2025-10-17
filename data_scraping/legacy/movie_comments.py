from playwright.sync_api import sync_playwright
import time


def fetch_with_scroll(page):
    # JavaScript로 스크롤을 끝까지 내리기
    previous_height = 0
    i = 1
    while True:
        current_height = page.evaluate("document.body.scrollHeight")
        if current_height == previous_height:
            break
        previous_height = current_height
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        # print(f"scroll down {i}", end='\r')
        i += 1
        time.sleep(2)  # 콘텐츠 로딩을 기다림


def get_data(movie_id):
    # 왓챠피디아 코멘트 더보기 url
    url = f'https://pedia.watcha.com/ko-KR/contents/{movie_id}/comments'
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)

        # 스크롤 끝까지 내리기
        fetch_with_scroll(page)
        # print("\nScroll end")

        data_list = []
        i = 1

        while True:
            try:
                # 더보기 버튼 찾기
                comment_button_xpath = f'//*[@id="root"]/div[1]/section/section/div/div/div/ul/div[{i}]/div[2]/a/div/span/button'
                more_button = page.locator(comment_button_xpath)
                if more_button.count() > 0:
                    more_button.click()
                    time.sleep(0.5)  # 로딩 대기

                # 각 코멘트 정보 수집
                custom_id_xpath = f'//*[@id="root"]/div[1]/section/section/div/div/div/ul/div[{i}]/div[1]/div[1]/a'
                comment_xpath = f'//*[@id="root"]/div[1]/section/section/div/div/div/ul/div[{i}]/div[2]/a/div/div'
                rating_xpath = f'//*[@id="root"]/div[1]/section/section/div/div/div/ul/div[{i}]/div[1]/div[2]/span'
                n_likes_xpath = f'//*[@id="root"]/div[1]/section/section/div/div/div/ul/div[{i}]/div[3]/em[1]'

                if page.locator(custom_id_xpath).count() > 0:
                    custom_id = page.locator(custom_id_xpath).get_attribute('href').split('/')[-1]
                else:
                    break

                if page.locator(comment_xpath).count() > 0:
                    comment = page.locator(comment_xpath).inner_text().replace('\n', ' ').replace('/', ' ').replace('\t', ' ').replace('\r', ' ')
                else:
                    comment = None

                if page.locator(rating_xpath).count() > 0:
                    rating = page.locator(rating_xpath).inner_text().replace('\n', ' ').replace('/', ' ')
                else:
                    rating = None

                if page.locator(n_likes_xpath).count() > 0:
                    n_likes = page.locator(n_likes_xpath).inner_text().replace('\n', ' ').replace('/', ' ')
                else:
                    n_likes = None

                data_list.append([custom_id, comment, rating, n_likes])
                # print(f"comment {i}", end='\r')
                i += 1
            except Exception as e:
                print(f"Error processing comment {i}: {e}")
                break
        # print("\n End")
        browser.close()  # Playwright 컨텍스트 내에서 브라우저 닫기
        return data_list


# 실행 예시
if __name__ == "__main__":
    import pandas as pd
    from assets.utils.txt import append_to_txt, read_txt
    
    row = read_txt('./data/custom_movie_rating.txt')
    column_names = ["CustomID", "MovieID", "MovieName", "Rating"]
    custom_movie_rating_df = pd.DataFrame(row, columns=column_names)
    
    column_names = ["MovieID", "CustomID", "Comment", "Rating", "N_Likes"]
    row = read_txt("./data/movie_comments.txt")
    movie_comments_df = pd.DataFrame(row, columns=column_names)
    
    movie_ids = list(set(custom_movie_rating_df['MovieID']) - set(movie_comments_df['MovieID']))

    for i, movie_id in enumerate(movie_ids):
        print(f"{i} / {len(movie_ids)}", end='\r')  # '\r'로 줄을 덮어씀
        data_list = get_data(movie_id)
        for data in data_list:
            append_to_txt("./data/movie_comments.txt", [movie_id, *data])
        
