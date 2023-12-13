from selenium import webdriver
from selenium.webdriver.chrome import service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import jpholiday
from datetime import datetime,timedelta
import json
import csv

# chromedriverを指定
CHROMEDRIVER_PATH  = "./chromedriver/chromedriver.exe"
# configファイル指定
CONFIG_FILE = "./config.json"
# csvファイル指定
CSV_FILE = "./input.csv"
# ジョブカンログインページ
JOBCAN_URL = "https://id.jobcan.jp/users/sign_in?app_key=atd"
# 工数管理ページ
MAN_HOURS_URL = "https://ssl.jobcan.jp/employee/man-hour-manage"

def find_elements_with_retry(driver, type, selector, max_retries=10, interval=0.5):
    retries = 0
    while retries < max_retries:
        try:
            elements = WebDriverWait(driver, interval).until(
                EC.presence_of_all_elements_located((type, selector))
            )
            return elements
        except TimeoutException:
            retries += 1
            print(f"Retry {retries}/{max_retries}. Waiting for elements...")
    
    print(f"Failed to find elements after {max_retries} retries. Stopping the application.")
    raise Exception("Element not found after multiple retries.")

def find_element_with_retry(driver, type, selector, max_retries=10, interval=0.5):
    retries = 0
    while retries < max_retries:
        try:
            element = WebDriverWait(driver, interval).until(
                EC.presence_of_element_located((type, selector))
            )
            return element
        except TimeoutException:
            retries += 1
            print(f"Retry {retries}/{max_retries}. Waiting for element...")
        except NoSuchElementException:
            retries += 1
            print(f"Retry {retries}/{max_retries}. Element not found.")
    
    print(f"Failed to find element after {max_retries} retries. Stopping the application.")
    raise Exception("Element not found after multiple retries.")

# 月選択
def select_months_ago(driver, num):
    if num == 0:
        return
    select_obj = Select(find_element_with_retry(driver, By.NAME, "month"))
    selected_option_value = select_obj.first_selected_option.get_attribute("value")
    value = int(selected_option_value) - num
    if value == 0:
        # 去年にする？
        value = 12
    select_obj.select_by_value(str(value))

# config
def load_config(file_path):
    with open(file_path) as f:
        return json.load(f)

# csv
def load_csv(csv_file_path):
    try:
        last_items = []
        with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
            csv_reader = csv.reader(csvfile)
            # 1行目スキップ
            next(csv_reader, None)
            for row in csv_reader:
                if row:
                    last_item = row[-1]
                    last_items.append(last_item if last_item else None)
        return last_items
    except FileNotFoundError:
        print("csv not found")
        return None
    
# ログイン
def login(driver, config):
    # ジョブカンログインページ
    driver.get(JOBCAN_URL)
    # ID
    find_element_with_retry(driver, By.ID, "user_email").send_keys(config["id"].strip())
    # PASS
    find_element_with_retry(driver, By.ID, "user_password").send_keys(config["pass"].strip())
    # ログインボタンクリック
    find_element_with_retry(driver, By.ID, "login_button").click()

def main():
    # intput
    config = load_config(CONFIG_FILE)
    # csv
    csv_items = load_csv(CSV_FILE)
    # chrome起動
    chrome_service = service.Service(executable_path=CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=chrome_service)

    try:
        # ログイン
        login(driver, config)
        # 工数管理ページ
        driver.get(MAN_HOURS_URL)
        # 月選択
        select_months_ago(driver, config["months_ago"])

        buttons_ = find_elements_with_retry(driver, By.CSS_SELECTOR, ".btn.jbc-btn-primary")

        for i in range(len(buttons_)):
            # 編集ボタン
            buttons = find_elements_with_retry(driver, By.CSS_SELECTOR, ".btn.jbc-btn-primary")
            buttons[i].click()
            # 時間取得
            time_element = find_element_with_retry(driver, By.ID, "edit-menu-title").accessible_name.split('＝')[1]
            # 曜日取得
            date_text = find_element_with_retry(driver, By.ID, "edit-menu-title").accessible_name.split('＝')[0]
            # 年月日取得
            date = datetime.strptime(date_text.split('日')[0], "%Y年%m月%d")

            if "(土)" in date_text or "(日)" in date_text or jpholiday.is_holiday(datetime(date.year, date.month, date.day)):
                # 何もしない
                pass
            else:
                # 時間入力
                selectIndex = 1
                if csv_items is not None and csv_items[i] is not None:
                    # cvs入力あり
                    # テンプレート2選択
                    selectIndex = 2
                    # 時刻計算
                    time1 = datetime.strptime(time_element, "%H:%M")
                    try:
                        time2 = datetime.strptime(csv_items[i], "%H:%M")
                    except ValueError:
                        time2 = datetime.strptime("00:00", "%H:%M")
                    result = time1 - time2
                    if result.total_seconds() < 0:
                        result = timedelta(0)
                    # 文字列に変換
                    hours, remainder = divmod(result.total_seconds(), 3600)
                    minutes = remainder // 60
                    time_element = f"{int(hours)}:{int(minutes)}"

                # テンプレート選択
                select = Select(find_element_with_retry(driver, By.NAME, "template"))
                select.select_by_index(selectIndex)
                time.sleep(0.5)

                # 時間入力
                minutes_inputs = find_elements_with_retry(driver, By.NAME, "minutes[]")
                minutes_inputs[0].clear()
                minutes_inputs[0].send_keys(time_element)
                if csv_items is not None and csv_items[i] is not None:
                    minutes_inputs[1].clear()
                    minutes_inputs[1].send_keys(csv_items[i])

                # フォーカスアウト
                find_element_with_retry(driver, By.CSS_SELECTOR, ".modal-dialog.modal-lg").click()

            # 保存
            find_element_with_retry(driver, By.ID, "save").click()

            # 月選択
            select_months_ago(driver, config["months_ago"])

    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        # ブラウザ閉じる
        driver.quit()

if __name__ == "__main__":
    main()
