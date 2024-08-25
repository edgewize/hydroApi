import os
import time
import boto3
import datetime
import asyncio
import nest_asyncio
from pyppeteer import launch

nest_asyncio.apply()
chrome_path = "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

async def screenshot_wave() -> str:
    browser = await launch(
        executablePath=chrome_path,
        headless=True,
        handleSIGINT=False,
        handleSIGTERM=False,
        handleSIGHUP=False,
    )
    page = await browser.newPage()
    await page.setViewport({"width": 1700, "height": 1000})
    await page.goto("https://www.boisewhitewaterpark.com/waveshaper-cam")
    time.sleep(5)
    element = await page.querySelector("iframe")
    await element.screenshot({"path": name})
    await browser.close()
    print(f"Screenshot {datetime.datetime.now()} complete")


async def run():
    temp_path = "temp.png"
    await screenshot_wave(temp_path)
    timestamp = datetime.datetime.now()
    print(timestamp)
    slug = str(timestamp)
    save_path = r"images/wave/" + slug + ".png"
    s3 = boto3.resource(
        "s3",
        endpoint_url="https://s3.us-west-1.wasabisys.com",
        aws_access_key_id=os.getenv("WASABI_ACCESS"),
        aws_secret_access_key=os.getenv("WASABI_SECRET"),
    )
    bucket = s3.Bucket("edginton-portfolio")
    bucket.upload_file(temp_path, save_path)
    print(f"Successful upload to {save_path}")
    time.sleep(60*15)
    run()


if __name__ == "__main_":
    run()