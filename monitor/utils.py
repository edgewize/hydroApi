import cv2
import os
import io
import boto3
import datetime
import pandas as pd
import numpy as np
import mediapipe as mp
from dotenv import load_dotenv
from matplotlib import pyplot as plt
from PIL import Image
from django.utils import timezone
import pytz
from django.db import models


def visualize_detections(image, detections) -> np.ndarray:
    """Draws bounding boxes on the input image and return it.
    Args:
        image: The input RGB image.
        detection_result: The list of all "Detection" entities to be visualize.
    Returns:
        Image with bounding boxes.
    """
    image = np.copy(image)
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
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return image


def detect_objects(img, options=None):
    BaseOptions = mp.tasks.BaseOptions
    ObjectDetector = mp.tasks.vision.ObjectDetector
    ObjectDetectorOptions = mp.tasks.vision.ObjectDetectorOptions
    VisionRunningMode = mp.tasks.vision.RunningMode
    if options:
        options = options
    else:
        options = ObjectDetectorOptions(
            base_options=BaseOptions(model_asset_path="efficientdet_lite0.tflite"),
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


class ScreenshotStore:
    def __init__(self):
        load_dotenv()
        s3 = boto3.resource(
            "s3",
            endpoint_url="https://s3.us-west-1.wasabisys.com",
            aws_access_key_id=os.getenv("WASABI_ACCESS"),
            aws_secret_access_key=os.getenv("WASABI_SECRET"),
        )
        self.bucket = s3.Bucket("edginton-portfolio")
        self.imgcdn = "https://edgewize.imgix.net"

    def upload(self, img, save_path):
        temp_save_path = f"detect.png"
        plt.imsave(temp_save_path, img)
        self.bucket.upload_file(temp_save_path, save_path)
        os.remove(temp_save_path)
        # return f"Successful upload to {save_path}"

    def get_image(self, key):
        object = self.bucket.Object(key)
        img = Image.open(io.BytesIO(object.get()["Body"].read()))
        return img

    def list_files(self, path):
        return [i.key for i in self.bucket.objects.filter(Prefix=path)]

    def get_latest_timestamps(self, count=None):
        files = self.list_files("images/wave/")
        # transform file paths and filter timestamp imgs from the base directory
        date_files = [
            i.split("/")[-1].replace(".png", "").replace("_", " ")
            for i in files
            if ":" in i and len(i.split("/")) <= 3
        ]
        datetimes = [str_to_datetime(i) for i in date_files]
        datetimes.sort()
        if count:
            datetimes = datetimes[:count]
        return datetimes

    def get_latest_timestamp(self) -> datetime.datetime:
        datetimes = self.get_latest_timestamps()
        max_date = max(datetimes)
        return max_date

    def imgcdn_src(self, path):
        return self.imgcdn + path


def resize_image(image, size):
    width = size[0]
    height = size[1]
    resize = image.resize((width, height), Image.Resampling.LANCZOS)
    return resize


def alpha_detector(image):
    # Mask the image so we only look in the surf line
    img_bg = resize_image(Image.open("static/img/bg.png"), image.size)
    img_mask = resize_image(Image.open("static/img/mask.png").convert("L"), image.size)
    composite = Image.composite(image, img_bg, img_mask)
    # Use mediapipe (mp) images for image detection and annotation
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGBA, data=np.asarray(composite))
    detection_result = detect_objects(mp_image)
    filtered_detections = [
        i
        for i in detection_result.detections
        if i.bounding_box.width < 20
        and i.bounding_box.width > 10
        and i.bounding_box.height < 40
    ]
    return filtered_detections


def lookup_detector(name):
    detectors = {
        "alpha": alpha_detector
    }
    return detectors[name]


def update_detection(detection, count):
    detection.count = count
    detection.save()
    return detection


def str_to_datetime(date_str):
    timezone.now()
    d = datetime.datetime.strptime(
        date_str,
        "%Y-%m-%d %H:%M:%S.%f",
    )
    tz_aware_date = datetime.datetime(
        d.year,
        d.month,
        d.day,
        d.hour,
        d.minute,
        d.second,
        d.microsecond,
        tzinfo=pytz.UTC,
    )
    return tz_aware_date


def get_screenshot(timestamp: str) -> str:
    if "_" in timestamp:
        timestamp = timestamp.replace("_", " ")
    record = Screenshot.objects.get(pk=str_to_datetime(timestamp))
    return record


def transform_heatmap(detections):
    df = pd.DataFrame(
        [{"timestamp": i.timestamp, "count": i.count} for i in detections]
    )
    df["weekday"] = df["timestamp"].apply(lambda x: x.date().weekday())
    df["hour"] = df["timestamp"].apply(lambda x: x.time().hour)
    weekdays = list(df["weekday"].sort_values().unique())
    hours = list(df["hour"].sort_values().unique())
    transform = df.groupby([df["hour"], df["weekday"]]).mean()["count"].reset_index()
    data = []
    for hour in hours:
        hour_records = transform.query(f"hour = = {hour}")
        hour_data = []
        for weekday in weekdays:
            if weekday in hour_records["weekday"].values:
                value = hour_records.query(f"weekday == {weekday}")["count"].values[0]
            else:
                value = 0
            hour_data.append(value)
        data.append(hour_data)
    heatmap = {
        "z": data,
        "x": weekdays,
        "y": hours,
    }
    return heatmap


if __name__ == "__main__":
    from run import app
    from models import Screenshot
    import pandas as pd

# def calc_error(count_series, test_series):
#     return abs(count_series - test_series).sum() / test_series.sum()

# def getInfo(site_id):
#     data = hf.site_file(site_id).table.to_json()
#     return data

# def getTimeline(site_id, start_date, end_date):
#     data = hf.NWIS(site_id, "dv", start_date=start_date, end_date=end_date).df()
#     data = data[[data.columns[0]]]
#     data["date"] = [str(i.date()) for i in data.index]
#     data = data.set_index("date")
#     return data

# def getDelta(site_id, end_date, freq="d"):
#     # freq: d (day), w (week), y (year)
#     date_range = [
#         str(i.date()) for i in pd.date_range(end_date, periods=3, freq=f"-3{freq}")
#     ]
#     current_period = getTimeline(site_id, date_range[1], date_range[0])
#     previous_period = getTimeline(site_id, date_range[2], date_range[1])
#     current_avg = current_period.mean()
#     previous_avg = previous_period.mean()
#     data = {"current": current_avg.values[0], "previous": previous_avg.values[0]}
#     return data
