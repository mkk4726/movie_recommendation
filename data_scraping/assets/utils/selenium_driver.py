import selenium.webdriver
from selenium.webdriver.chrome.service import Service
import selenium.webdriver.remote
import selenium.webdriver.remote.webelement
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options   
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from typing import Literal
import selenium
import time

 
def get_driver(use_headless:bool=True, proxy_server:bool=None, chrome_driver_path:str=None) -> webdriver.Chrome:
    chrome_options = Options()
    chrome_options.add_argument('--disable-gpu')  # GPU 비활성화
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-extensions')  # 확장 프로그램 비활성화
    chrome_options.add_experimental_option("prefs", {
        "profile.managed_default_content_settings.images": 2,  # 이미지 비활성화
        "profile.default_content_setting_values.notifications": 2,  # 알림 비활성화
        "profile.default_content_setting_values.media_stream": 2,  # 미디어 스트림 비활성화
    })
    chrome_options.add_argument("--disable-build-check")
    
    if use_headless:
        chrome_options.add_argument('--headless=new')  # 최신 Chrome에서 안정적으로 작동
    
    if proxy_server:
        chrome_options.add_argument(f'--proxy-server={proxy_server}')

    if chrome_driver_path is None:
        # Chrome 드라이버를 자동으로 설정
        driver = Service(ChromeDriverManager.install())
    else:
        service = Service(chrome_driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
    return driver

def get_text_by_xpath(driver:webdriver.Chrome, xpath:str):
    try:
        element = driver.find_element(By.XPATH, xpath)
        return element.text
    except:
        return 'None'
    
def get_button(driver:webdriver.Chrome, path:str, by:Literal["xpath", "class_name"]):
    if by == "xpath":
        try:
            button = driver.find_element(By.XPATH, path)
        except:
            button = "None"
        return button
    elif by == "class_name":
        try:
            button = driver.find_element(By.CLASS_NAME, path)
        except:
            button = "None"
        return button


def open_new_tab(driver:webdriver.Chrome, button:selenium.webdriver.remote.webelement):
    ActionChains(driver).key_down(Keys.CONTROL).click(button).key_up(Keys.CONTROL).perform()


def scroll_to_end(driver: webdriver.Chrome, verbose=False, max_n_retries=5, delay=2):
    """
    Scrolls to the end of the page, ensuring dynamic content is fully loaded.

    Args:
        driver (webdriver.Chrome): Selenium WebDriver instance.
        verbose (bool): If True, prints scroll progress.
        max_n_retries (int): Maximum number of attempts to check for new content.
        delay (float): Delay in seconds to wait for content to load.
    """
    last_height = driver.execute_script("return document.body.scrollHeight")
    attempts = 0
    i = 0
    
    while attempts < max_n_retries:
        # Scroll down
        if verbose:
            print(f"Scroll down {i}", end='\r')  # '\r'로 줄을 덮어씀
            i += 1
        
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(delay)  # Delay to wait for new content to load
        
        # Check for new content
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            attempts += 1  # Increment attempt count if no new content is loaded
        else:
            attempts = 0  # Reset attempt count if new content is detected
        
        last_height = new_height

    if verbose:
        print("Scroll down end")
