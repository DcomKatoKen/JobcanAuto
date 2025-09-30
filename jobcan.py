from selenium import webdriver
from selenium.webdriver.chrome import service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException,
    StaleElementReferenceException,
    ElementNotInteractableException,
    ElementClickInterceptedException
)
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
# 出席簿ページ
ATTENDANCE_URL = "https://ssl.jobcan.jp/employee/attendance"
# 休み
VACATION = {"有", "ア休", "夏休"} # "欠" はいらなそう

def find_element_with_retry(driver, by, selector, single=True, max_retries=10, interval=0.5):
    retries = 0
    while retries < max_retries:
        try:
            if single:
                elements = WebDriverWait(driver, interval).until(
                    EC.presence_of_element_located((by, selector))
                )
            else:
                elements = WebDriverWait(driver, interval).until(
                    EC.presence_of_all_elements_located((by, selector))
                )
        except (TimeoutException, NoSuchElementException) as e:
            retries += 1
            print(f"Retry {retries}/{max_retries} due to {e.__class__.__name__}...")
            time.sleep(interval)
            continue

        try:
            if single:
                _ = elements.is_displayed()
            else:
                for element in elements:
                    _ = element.is_displayed()
            return elements
        except StaleElementReferenceException:
            retries += 1
            print(f"Retry {retries}/{max_retries} due to stale element reference...")
            time.sleep(interval)
        except Exception as e:
            print(f"Unexpected error on retry {retries}/{max_retries}: {str(e)}")
            retries += 1

    print(f"Failed to find element(s) after {max_retries} retries. Stopping the application.")
    raise Exception("Element(s) not found after multiple retries.")

def retry_action(action, max_retries=10, interval=0.5):
    retries = 0
    while retries < max_retries:
        try:
            action()
            return
        except (StaleElementReferenceException, ElementNotInteractableException, ElementClickInterceptedException) as e:
            retries += 1
            print(f"Retry {retries}/{max_retries} due to {e.__class__.__name__}...")
            time.sleep(interval)
    raise Exception(f"Action failed after {max_retries} retries.")

# 月選択
def select_months_ago(driver, num):
    if num == 0:
        return
    elif num > 12:
        return
    select_obj = Select(find_element_with_retry(driver, By.NAME, "month"))
    selected_option_value = select_obj.first_selected_option.get_attribute("value")
    value = int(selected_option_value) - num
    if value <= 0:
        select_obj_year = Select(find_element_with_retry(driver, By.NAME, "year"))
        selected_option_year_value = select_obj_year.first_selected_option.get_attribute("value")
        yaer_value = int(selected_option_year_value) - 1
        select_obj_year.select_by_value(str(yaer_value))
        select_obj = Select(find_element_with_retry(driver, By.NAME, "month"))
        value = value + 12
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

# 休み取得
def getAttendance(driver, num):
    # 出席簿ページ
    driver.get(ATTENDANCE_URL)
    if num != 0:
        # 月を変更
        select_obj = Select(find_element_with_retry(driver, By.NAME, "month"))
        selected_option_value = select_obj.first_selected_option.get_attribute("value")
        value = int(selected_option_value) - num
        if value == 0:
            # 去年にする？
            value = 12
        select_obj.select_by_value(str(value))
        find_element_with_retry(driver, By.XPATH, '//input[@value="表示"]').click()
        
    # 勤怠状況取得
    td_elements = find_element_with_retry(driver, By.XPATH,'//td[div[@data-toggle="tooltip"]]', False)
    result_list = []
    for td_element in td_elements:
        try:
            font_element = td_element.find_element(By.XPATH, './/font')
            result_list.append(font_element.text)
        except:
            result_list.append('')

    return result_list

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
        # 休暇を取得
        attendanceList = getAttendance(driver, config["months_ago"])
        # 工数管理ページ
        driver.get(MAN_HOURS_URL)
        # 月選択
        select_months_ago(driver, config["months_ago"])

        buttons_ = find_element_with_retry(driver, By.CSS_SELECTOR, ".btn.jbc-btn-primary", False)

        for i in range(len(buttons_)):
            # 編集ボタン
            buttons = find_element_with_retry(driver, By.CSS_SELECTOR, ".btn.jbc-btn-primary", False)
            retry_action(lambda: buttons[i].click())

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
                elif attendanceList[i] in VACATION:
                    # 休み
                    selectIndex = 3
                else:
                    # 普通
                    selectIndex = 1

                # テンプレート選択
                select = Select(find_element_with_retry(driver, By.NAME, "template"))
                select.select_by_index(selectIndex)
                time.sleep(0.5)

                # 時間入力
                minutes_inputs = find_element_with_retry(driver, By.NAME, "minutes[]", False)
                minutes_inputs[0].clear()
                minutes_inputs[0].send_keys(time_element)
                if csv_items is not None and csv_items[i] is not None:
                    minutes_inputs[1].clear()
                    minutes_inputs[1].send_keys(csv_items[i])

                # フォーカスアウト
                retry_action(lambda: find_element_with_retry(driver, By.CSS_SELECTOR, ".modal-dialog.modal-lg").click())

            # 保存
            retry_action(lambda: find_element_with_retry(driver, By.ID, "save").click())

            # 月選択
            select_months_ago(driver, config["months_ago"])

    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        # ブラウザ閉じる
        driver.quit()

if __name__ == "__main__":
    main()
