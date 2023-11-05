
import time
import datetime
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

import hydroApp.report as report

def screenshot_wave(img_name):
    # service = Service(executable_path="/usr/bin/chromedriver")
    service = Service(executable_path="C:/Users/taylor/Documents/chromedriver-win64/chromedriver.exe")
    op = webdriver.ChromeOptions()
    # op.add_argument('headless')
    driver = webdriver.Chrome(service=service, options=op)
    driver.get("https://www.boisewhitewaterpark.com/waveshaper-cam/")
    time.sleep(20)
    iframe = driver.find_element(By.TAG_NAME, "iframe")
    iframe.screenshot(img_name)
    driver.close()


def repeat_screenshot(interval):
    store = report.ScreenshotStore()
    now = datetime.datetime.now()
    if now.hour >= 8 and now.hour <=20:
        slug = str(now).replace(" ", "_") + ".png"
        img_name = os.path.join("screenshots", slug)
        screenshot_wave(img_name)
        img_name = r"images/wave/"+ slug
        upload = store.upload_file(img_name, img_name)


        
        print(upload)
    else:
        print(f"Skipping screenshot at {now}")
    time.sleep(interval)
    repeat_screenshot(interval)


if __name__ == "__main__":
    repeat_screenshot(3600)
