import os
import io
import cv2
import os
import boto3
import hydrofunctions as hf
import pandas as pd
from dotenv import load_dotenv
import datetime
from PIL import Image
import numpy as np
import mediapipe as mp
from matplotlib import pyplot as plt

def getInfo(site_id):
    data = hf.site_file(site_id).table.to_json()
    return data


def getTimeline(site_id, start_date, end_date):
    data = hf.NWIS(site_id, "dv", start_date=start_date, end_date=end_date).df()
    data = data[[data.columns[0]]]
    data["date"] = [str(i.date()) for i in data.index]
    data = data.set_index("date")
    return data


def getDelta(site_id, end_date, freq="d"):
    # freq: d (day), w (week), y (year)
    date_range = [
        str(i.date()) for i in pd.date_range(end_date, periods=3, freq=f"-3{freq}")
    ]
    current_period = getTimeline(site_id, date_range[1], date_range[0])
    previous_period = getTimeline(site_id, date_range[2], date_range[1])
    current_avg = current_period.mean()
    previous_avg = previous_period.mean()
    data = {"current": current_avg.values[0], "previous": previous_avg.values[0]}
    return data

class WasabiStore():
    def __init__(self):
        load_dotenv()
        s3 = boto3.resource('s3',
            endpoint_url = 'https://s3.us-west-1.wasabisys.com',
            aws_access_key_id =  os.getenv("WASABI_ACCESS"),
            aws_secret_access_key =  os.getenv("WASABI_SECRET")
        )
        self.bucket = s3.Bucket('edginton-portfolio')

    def upload_file(self, upload_file_path, destination_path):
        self.bucket.upload_file(upload_file_path, destination_path)
        return f"{upload_file_path} successfully uploaded to {destination_path}"

    def list_files(self, path):
        return [i.key for i in self.bucket.objects.filter(Prefix=path)]
    
def getLatestScreenshot():
    files = WasabiStore().list_files("images/wave/")
    date_files = [i.split("/")[-1].replace(".png", "") for i in files if ":" in i]
    datetimes = [datetime.datetime.strptime(i, "%Y-%m-%d %H:%M:%S.%f") for i in date_files]
    max_date = max(datetimes)
    latest_file = [i for i in files if str(max_date) in i]
    return latest_file[0]

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
            model_asset_path="efficientdet_lite0.tflite"
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

def upload_processed_img(img, img_name):
    save_dir = "images/wave/processed"
    s = WasabiStore()
    files = s.list_files(save_dir)
    save_path = f"{save_dir}/{img_name.replace('images/wave/', '')}"
    if save_path not in files:
        temp_save_path = f"detect.png"
        plt.imsave(temp_save_path, img)
        upload = s.upload_file(temp_save_path, save_path)
        os.remove(temp_save_path)
    else:
        upload = f"Skipped {img_name} upload"
    print(upload)
    return save_path


def process_image(key):
    # Read image from cloud
    s = WasabiStore()
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
    img_name = key.split('/')[-1]
    print(f"Detected {len(filtered_detections)} objects in {img_name}")
    image_copy = np.copy(mp_img.numpy_view())
    annotated_image = visualize_detections(image_copy, filtered_detections)
    rgb_annotated_image = cv2.cvtColor(annotated_image, cv2.COLOR_BGR2RGB)
    upload = upload_processed_img(rgb_annotated_image, key)
    return {
        "key": key,
        "count": len(filtered_detections),
        "processed_key": upload
    }


if __name__ == "__main__":
    s = WasabiStore()
    files = s.list_files("images/wave")
    image = Image.open(f"https://edgewize.imgix.net/{files[0]}")
    display(image)