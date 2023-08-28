import io
import cv2
import os
import time
import boto3
import datetime
import numpy as np
import mediapipe as mp
from PIL import Image
from matplotlib import pyplot as plt
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By


import hydroApp.report as report


def visualize_detections(image, detections) -> np.ndarray:
    """Draws bounding boxes on the input image and return it.
    Args:
        image: The input RGB image.
        detection_result: The list of all "Detection" entities to be visualize.
    Returns:
        Image with bounding boxes.
    """
    MARGIN = 10  # pixels
    ROW_SIZE = 10  # pixels
    FONT_SIZE = 1
    FONT_THICKNESS = 1
    TEXT_COLOR = (0, 255, 0)  # red
    for detection in detections:
        # Draw bounding_box
        bbox = detection.bounding_box
        start_point = bbox.origin_x, bbox.origin_y
        end_point = bbox.origin_x + bbox.width, bbox.origin_y + bbox.height
        cv2.rectangle(image, start_point, end_point, TEXT_COLOR, 1)
        # Draw label and score
        category = detection.categories[0]
        category_name = category.category_name
        probability = round(category.score, 2)
        # result_text = category_name + ' (' + str(probability) + ')'
        # text_location = (MARGIN + bbox.origin_x,
        #                 MARGIN + ROW_SIZE + bbox.origin_y)
        # cv2.putText(image, result_text, text_location, cv2.FONT_HERSHEY_PLAIN,
        #             FONT_SIZE, TEXT_COLOR, FONT_THICKNESS)
    return image


def detect_objects(img):
    BaseOptions = mp.tasks.BaseOptions
    ObjectDetector = mp.tasks.vision.ObjectDetector
    ObjectDetectorOptions = mp.tasks.vision.ObjectDetectorOptions
    VisionRunningMode = mp.tasks.vision.RunningMode
    
    options = ObjectDetectorOptions(
        base_options=BaseOptions(
            model_asset_path="/efficientdet_lite0.tflite"
        ),
        max_results=20,
        # category_denylist=["clock", "truck", "airplane", "bird", "frisbee", "traffic light"],
        # score_threshold=.015,
        running_mode=VisionRunningMode.IMAGE,
    )

    with ObjectDetector.create_from_options(options) as detector:
        # The detector is initialized. Use it here.
        # Perform object detection on the provided single image.
        detection_result = detector.detect(img)

    return detection_result


def process_image(key):
    # Read image from cloud
    s = report.WasabiStore()
    object = s.bucket.Object(key)
    img = Image.open(io.BytesIO(object.get()["Body"].read()))
    # Mask the image so we only look in the surf line
    img_bg = Image.open("img/bg.png")
    img_mask = Image.open("img/mask.png").convert("L")
    composite = Image.composite(img, img_bg, img_mask)

    # Use mediapipe (mp) images for image detection and annotation
    detection_result = detect_objects(
        mp.Image(image_format=mp.ImageFormat.SRGBA, data=np.asarray(composite))
    )

    mp_img = mp.Image(image_format=mp.ImageFormat.SRGBA, data=np.asarray(img))

    filtered_detections = [
        i
        for i in detection_result.detections
        # if i.categories[0].category_name == "person"
        if i.bounding_box.width < 20
        and i.bounding_box.width > 10
        and i.bounding_box.height < 40
    ]
    image_copy = np.copy(mp_img.numpy_view())
    annotated_image = visualize_detections(image_copy, filtered_detections)
    rgb_annotated_image = cv2.cvtColor(annotated_image, cv2.COLOR_BGR2RGB)
    img_name = key.split('/')[-1]
    print(f"Detected {len(filtered_detections)} objects in {img_name}")
    temp_save_path = f"detect.png"
    plt.imsave(temp_save_path, rgb_annotated_image)
    s.upload_file(temp_save_path, f"images/wave/processed/{img_name}")
    os.remove(temp_save_path)
    return {
        "key": key,
        "detections": filtered_detections,
        "img": rgb_annotated_image
    }


def upload_file(upload_file_path, destination_path):
    s3 = boto3.resource('s3',
        endpoint_url = 'https://s3.us-west-1.wasabisys.com',
        aws_access_key_id =  WASABI_ACCESS,
        aws_secret_access_key =  WASABI_SECRET
    )
    bucket = s3.Bucket('edginton-portfolio')
    bucket.upload_file(upload_file_path, destination_path)
    return f"{upload_file_path} successfully uploaded to {destination_path}"


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
        result = process_image(img_name)
        print(f"Detected {len(result['detections'])} objects in {result['key'].split('/')[-1]}")
    else:
        print(f"Skipping screenshot at {now}")
    time.sleep(interval)
    repeat_screenshot(interval)


if __name__ == "__main__":
    repeat_screenshot(3600)
