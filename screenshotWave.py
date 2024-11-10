import os
import time
import boto3
import datetime
import asyncio
import requests
import io
import nest_asyncio
import replicate
import json
import ast
import urllib
import numpy as np
import cv2
from PIL.ExifTags import TAGS
from PIL import Image
import piexif
from collections import defaultdict
from pyppeteer import launch
from dotenv import load_dotenv

load_dotenv()

nest_asyncio.apply()
windows_chrome_path = "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
pi_chrome_path = "/usr/bin/chromium"
if os.path.isfile(windows_chrome_path):
    chrome_path = windows_chrome_path
elif os.path.isfile(pi_chrome_path):
    chrome_path = pi_chrome_path

IMG_CDN = "https://edgewize.imgix.net/"

async def screenshot_wave(save_path) -> str:
    browser = await launch(
        executablePath=chrome_path,
        headless=False,
        handleSIGINT=False,
        handleSIGTERM=False,
        handleSIGHUP=False,
    )
    page = await browser.newPage()
    await page.setViewport({"width": 1700, "height": 1000})
    await page.goto("https://www.boisewhitewaterpark.com/waveshaper-cam")
    time.sleep(20)
    element = await page.querySelector("iframe")
    await element.screenshot({"path": save_path})
    await browser.close()
    print(f"Screenshot {datetime.datetime.now()} complete")


class ScreenshotStore:
    def __init__(self):
        s3 = boto3.resource(
            "s3",
            endpoint_url="https://s3.us-west-1.wasabisys.com",
        )
        print(os.getenv("WASABI_ACCESS"))
        print(os.getenv("WASABI_SECRET"))
        self.bucket = s3.Bucket("edginton-portfolio")
        self.imgcdn = "https://edgewize.imgix.net"

    def upload_image(self, local_path, upload_path=None):
        if upload_path:
            save_path = upload_path
        else:
            timestamp = datetime.datetime.now()
            slug = str(timestamp).replace(" ", "_")
            base_dir = r"wave/"
            save_path = base_dir  + slug + ".jpg"
        self.bucket.upload_file(local_path, save_path)
        print(f"Successful upload to {save_path}")
        return save_path

    def list_files(self, path):
        return [i.key for i in self.bucket.objects.filter(Prefix=path)]

def yolo_detector(image_url):
    input = {
        "input_image": image_url,
        "nms": 0.9,
        "conf": 0.05,
        "tsize": 640,
        "model_name": "yolox-s",
        "return_json": True,
    }
    output = replicate.run(
        "daanelson/yolox:ae0d70cebf6afb2ac4f5e4375eb599c178238b312c8325a9a114827ba869e3e9",
        input=input,
    )
    try:
        detections = json.loads(ast.literal_eval(output["json_str"]).replace("'", '"'))
    except json.decoder.JSONDecodeError:
        detections = {}
    return detections


def read_image_from_url(image_url):
    req = urllib.request.urlopen(image_url)
    arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
    img = cv2.imdecode(arr, -1)
    return img

def read_png_from_url(image_url):
    """
    Reads an image from a URL and returns it as a NumPy array.

    Args:
        image_url (str): URL of the image.

    Returns:
        numpy.ndarray: Image array.
    """
    response = requests.get(image_url)
    response.raise_for_status()  # Raise an exception for bad responses

    img = Image.open(io.BytesIO(response.content))

    # Convert to RGB if it has an alpha channel (RGBA)
    if img.mode == 'RGBA':
        img = img.convert('RGB') 

    # Convert PIL Image to NumPy array
    img_array = np.array(img)

    # OpenCV expects BGR format, so convert if necessary
    if img_array.shape[2] == 3:  # Check if it's a 3-channel image
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

    return img_array

def label_yolo_image(image_url, detections):
    """
    Labels a detected image with bounding boxes and class labels.

    Args:
        img (numpy.ndarray): Image array.
        detections (dict): Dictionary containing detection results.
    """ 
    img_array = read_png_from_url(image_url)
    for det_key, det_info in detections.items():
        x0, y0, x1, y1 = det_info["x0"], det_info["y0"], det_info["x1"], det_info["y1"]
        score = det_info["score"]
        cls = det_info["cls"]

        # Draw bounding box
        cv2.rectangle(
            img_array, (int(x0), int(y0)), (int(x1), int(y1)), (0, 255, 0), 2
        )  # Green box

        # Add label with class and score
        label = f"{cls}: {score:.2f}"

        # Get text size for the black box
        (text_width, text_height), _ = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
        )

        # Draw black box
        cv2.rectangle(
            img_array,
            (int(x0), int(y0 - 2 - text_height)),
            (int(x0 + text_width), int(y0 - 2)),
            (0, 0, 0),
            -1,
        )

        # Put text on top of the black box
        cv2.putText(
            img_array,
            label,
            (int(x0), int(y0 - 2)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1,
        )
    img = Image.fromarray(img_array, "RGB")

    try:
        exif_dict = piexif.load(img.info["exif"])
    except KeyError:
        exif_dict = defaultdict(dict)

    exif_ifd = {piexif.ExifIFD.UserComment: f"count:{len(detections)}".encode()}

    exif_dict = {"0th": {}, "Exif": exif_ifd, "1st": {}, "thumbnail": None, "GPS": {}}

    exif_dat = piexif.dump(exif_dict)
    temp_path = "detect_temp.jpg"
    img.save(temp_path, exif=exif_dat)
    slug = image_url.split("/")[-1]
    ScreenshotStore().upload_image(temp_path, upload_path="wave/gamma/"+slug)
    return img

async def batch():
    store = ScreenshotStore()
    files = store.list_files("images/wave")
    for slug in files:
        if "yolo" not in slug and "." in slug:
            d = [int(i) for i in slug.split("/")[-1].split(" ")[0].split("-")]
            date = datetime.date(d[0],d[1],d[2])
            if date == datetime.date(2024, 8, 24):
                src_img_url = IMG_CDN + slug
                print(f"Detecting {slug}...")
                detections = yolo_detector(src_img_url.replace(" ", "%20"))
                print(f"Detected {len(detections)} objects in {src_img_url}")
                if len(detections) > 0:
                    detect_img = label_yolo_image(src_img_url, detections)
                    detect_img.show()

async def main():
    temp_path = "temp.jpg"
    await screenshot_wave(temp_path)
    upload_path = ScreenshotStore().upload_image(temp_path)
    img_src = IMG_CDN+upload_path
    detections = yolo_detector(img_src)
    print(f"Detected {len(detections)} objects in {img_src}")
    detect_img = label_yolo_image(img_src, detections)
    detect_img.show()
    time.sleep(60 * 15)
    await main()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
    # asyncio.run(batch())