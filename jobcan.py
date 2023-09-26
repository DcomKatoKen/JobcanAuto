from selenium import webdriver
from selenium.webdriver.chrome import service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
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

# 月選択
def select_months_ago(driver, num):
    if num == 0:
        return
    select_obj = Select(driver.find_element(By.NAME, "month"))
    selected_option_value = select_obj.first_selected_option.get_attribute("value")
    value = int(selected_option_value) - num
    if value == 0:
        # 去年にする？
        value = 12
    select_obj.select_by_value(str(value))
    time.sleep(3)

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
    driver.find_element(By.ID, "user_email").send_keys(config["id"].strip())
    time.sleep(1)
    # PASS
    driver.find_element(By.ID, "user_password").send_keys(config["pass"].strip())
    time.sleep(1)
    # ログインボタンクリック
    driver.find_element(By.ID, "login_button").click()
    time.sleep(3)

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
        time.sleep(3)
        # 月選択
        select_months_ago(driver, config["months_ago"])

        buttons_ = driver.find_elements(By.CSS_SELECTOR, ".btn.jbc-btn-primary")

        for i in range(len(buttons_)):
            # 編集ボタン
            buttons = driver.find_elements(By.CSS_SELECTOR, ".btn.jbc-btn-primary")
            buttons[i].click()
            time.sleep(1)
            # 時間取得
            time_element = driver.find_element(By.ID, "edit-menu-title").accessible_name.split('＝')[1]
            # 曜日取得
            date_text = driver.find_element(By.ID, "edit-menu-title").accessible_name.split('＝')[0]
            # 年月日取得
            date = datetime.strptime(date_text.split('日')[0], "%Y年%m月%d")

            if "(土)" in date_text or "(日)" in date_text or jpholiday.is_holiday(datetime(date.year, date.month, date.day)):
                # 何もしない
                pass
            else:
                # 時間入力
                template_value = "2"
                if csv_items is not None and csv_items[i] is not None:
                    # cvs入力あり
                    # テンプレート2選択
                    template_value = "3"
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
                select = Select(driver.find_element(By.NAME, "template"))
                select.select_by_value(template_value)
                time.sleep(1)

                # 時間入力
                minutes_inputs = driver.find_elements(By.NAME, "minutes[]")
                minutes_inputs[0].clear()
                minutes_inputs[0].send_keys(time_element)
                if csv_items is not None and csv_items[i] is not None:
                    minutes_inputs[1].clear()
                    minutes_inputs[1].send_keys(csv_items[i])

                # フォーカスアウト
                driver.find_element(By.CSS_SELECTOR, ".modal-dialog.modal-lg").click()
                time.sleep(1)

            # 保存
            driver.find_element(By.ID, "save").click()
            time.sleep(3)

            # 月選択
            select_months_ago(driver, config["months_ago"])

    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        # ブラウザ閉じる
        driver.quit()

if __name__ == "__main__":
    main()
