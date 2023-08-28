
import time
import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

import hydroApp.report as report

def screenshot_wave(img_name):
    service = Service(executable_path="/usr/bin/chromedriver")
    op = webdriver.ChromeOptions()
    # op.add_argument('headless')
    driver = webdriver.Chrome(service=service, options=op)
    driver.get("https://www.boisewhitewaterpark.com/waveshaper-cam/")
    time.sleep(20)
    iframe = driver.find_element(By.TAG_NAME, "iframe")
    iframe.screenshot(img_name)
    driver.close()


def repeat_screenshot(interval):
    s = report.WasabiStore()
    now = datetime.datetime.now()
    if now.hour >= 8 and now.hour <=20:
        img_name = f"screenshots/{now}.png"
        screenshot_wave(img_name)
        img_name = f"images/wave/{now}.png"
        upload = s.upload_file(img_name, img_name)
        print(upload)
    else:
        print(f"Skipping screenshot at {now}")
    time.sleep(interval)
    repeat_screenshot(interval)


if __name__ == "__main__":
    repeat_screenshot(3600)
