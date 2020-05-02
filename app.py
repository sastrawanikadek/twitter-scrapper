import os
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, NoSuchElementException
from pymongo import MongoClient

client = MongoClient(os.environ.get('MONGODB_URI'))
db = client['big-data']
collection = db['tweets']
total_documents = collection.count_documents({})
queries = ['pekerjaan saya sebagai', 'saya bekerja sebagai', 'saya mendapatkan pekerjaan sebagai',
           'karir saya sebagai']
query_index = 0
retry = 0
max_retry = 3

chrome_options = ChromeOptions()
chrome_options.binary_location = os.environ.get('GOOGLE_CHROME_BIN')
chrome_options.add_argument('--headless')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--no-sandbox')

driver = Chrome(executable_path=os.environ.get('CHROMEDRIVER_PATH'), chrome_options=chrome_options)
wait = WebDriverWait(driver, 15)
driver.get('https://twitter.com/login')
driver.implicitly_wait(15)

form = driver.find_element_by_css_selector('form[action="/sessions"]')
input_username = driver.find_element_by_name('session[username_or_email]')
input_password = driver.find_element_by_name('session[password]')

input_username.send_keys(os.environ.get('TWITTER_EMAIL'))
input_password.send_keys(os.environ.get('TWITTER_PASSWORD'))
form.submit()

try:
    explore_button = wait.until(lambda drv: drv.find_element_by_css_selector('a[href="/explore"]'))
    explore_button.click()
    input_search = wait.until(
        lambda drv: drv.find_element_by_css_selector('input[data-testid="SearchBox_Search_Input"]'))
    input_search.send_keys(f'"{queries[query_index]}" lang:id{Keys.ENTER}')
except TimeoutException:
    form = wait.until(lambda drv: drv.find_element_by_css_selector('form[action="/account/login_challenge"]'))
    input_phone = wait.until(lambda drv: drv.find_element_by_css_selector('input[name="challenge_response"]'))
    input_phone.send_keys(os.environ.get('TWITTER_PHONE'))
    form.submit()

    explore_button = wait.until(lambda drv: drv.find_element_by_css_selector('a[href="/explore"]'))
    explore_button.click()
    input_search = wait.until(
        lambda drv: drv.find_element_by_css_selector('input[data-testid="SearchBox_Search_Input"]'))
    input_search.send_keys(f'"{queries[query_index]}" lang:id{Keys.ENTER}')

latest_button = wait.until(lambda drv: drv.find_element_by_link_text('Latest'))
latest_button.click()

while True:
    temp_total_documents = collection.count_documents({})

    if temp_total_documents == total_documents:
        if retry == max_retry:
            retry = 0
            query_index = query_index + 1 if query_index < len(queries) - 1 else 0
            input_search = wait.until(
                lambda drv: drv.find_element_by_css_selector('input[data-testid="SearchBox_Search_Input"]'))
            input_search.send_keys(f'"{queries[query_index]}" lang:id{Keys.ENTER}')
        else:
            retry += 1

    tweets = wait.until(lambda drv: drv.find_elements_by_css_selector('div[data-testid="tweet"]'))

    for tweet in tweets:
        try:
            url_element = tweet.find_element_by_css_selector('a.r-3s2u2q')
            time_element = tweet.find_element_by_css_selector('a.r-3s2u2q time')
            avatar_element = tweet.find_element_by_css_selector('img.css-9pa8cd')
            name_element = tweet.find_element_by_css_selector('a span span.css-901oao')
            username_element = tweet.find_element_by_css_selector('a div.r-1f6r7vd span')
            caption_element = tweet.find_element_by_css_selector('div.r-bnwqim')

            tweet_avatar = avatar_element.get_attribute('src')
            tweet_name = name_element.text
            tweet_username = username_element.text
            tweet_caption = caption_element.text
            tweet_datetime = time_element.get_attribute('datetime')
            tweet_url = url_element.get_attribute('href')
            tweet_id = tweet_url[tweet_url.rfind('/') + 1:]

            if not collection.find_one({'tweet_id': tweet_id}):
                tweet_data_dict = {
                    'tweet_id': tweet_id,
                    'avatar': tweet_avatar,
                    'name': tweet_name,
                    'username': tweet_username,
                    'caption': tweet_caption,
                    'datetime': tweet_datetime,
                    'url': tweet_url
                }
                collection.insert_one(tweet_data_dict)
        except (StaleElementReferenceException, NoSuchElementException):
            continue

    total_documents = temp_total_documents
    driver.find_element_by_tag_name('body').send_keys(Keys.PAGE_DOWN)
