from playwright.sync_api import sync_playwright
import time
from assets.utils.txt import append_to_txt


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

# 왓챠피디아 코멘트 더보기 url
url = f'https://pedia.watcha.com/en-KR/contents/mO88EDO/comments'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url)

    # 스크롤 끝까지 내리기
    fetch_with_scroll(page)
    # print("\nScroll end")

    data_list = []
    i = 95

    # 각 코멘트 정보 수집
    custom_id_xpath = f'//*[@id="root"]/div[1]/section/section/div/div/div/ul/div[{i}]/div[1]/div[1]/a'
    comment_xpath = f'//*[@id="root"]/div[1]/section/section/div/div/div/ul/div[{i}]/div[2]/a/div/div'
    rating_xpath = f'//*[@id="root"]/div[1]/section/section/div/div/div/ul/div[{i}]/div[1]/div[2]/span'
    n_likes_xpath = f'//*[@id="root"]/div[1]/section/section/div/div/div/ul/div[{i}]/div[3]/em[1]'

    if page.locator(custom_id_xpath).count() > 0:
        custom_id = page.locator(custom_id_xpath).get_attribute('href').split('/')[-1]
    else:
        print('hi')

    if page.locator(comment_xpath).count() > 0:
        comment = page.locator(comment_xpath).inner_text().replace('\n', ' ').replace('\t', ' ').replace('\r', ' ').replace('/', '')
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

    # print("\n End")
    browser.close()  # Playwright 컨텍스트 내에서 브라우저 닫기
    
append_to_txt("./data/movie_comments.txt", ["test", *[custom_id, comment, rating, n_likes]])