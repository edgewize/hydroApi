from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
import pandas as pd
import monitor.utils as utils
from monitor.models import Screenshot, Detection

class Detector(object):
    def __init__(self, name, detect_function):
        self.name = name
        self.storage = utils.ScreenshotStore()
        self.detect_function = detect_function
        self.detections = Detection.objects.filter(model=name)
        self.screenshots = [s for s in [i.get_screenshot() for i in self.detections] if s]

    def detect(self, screenshot, update=False):
        image = self.storage.get_image(screenshot.imgpath)
        detections = self.detect_function(image)
        rgb_annotated_image = utils.visualize_detections(image, detections)
        self.storage.upload(
            rgb_annotated_image,
            f"images/wave/{self.name}/{screenshot.url_timestamp}.png",
        )
        detection_count = len(detections)
        if detections and update:
            detection = detections[0]
            detection.count = detection_count
        else:
            detection = Detection(timestamp=screenshot.timestamp, model=self.name, count=detection_count)
        detection.save()
        return detections
    
    def detect_all(self):
        for screenshot in self.screenshots():
            if screenshot.get_detections(model=self.name).count() == 0:
                detection = self.detect.screenshot()
                print(f"Detected {detection.count} objects in {screenshot.timestamp}")
            else:
                print(f"{screenshot.timestamp} already processed")

    def get_screenshot(self, timestamp):
        screenshots = [i for i in self.screenshots if i.timestamp == timestamp]
        if len(screenshots) == 0:
            #  new timstammp in storage and it needs a db record here
            screenshot = Screenshot(timestamp=timestamp)
            screenshot.save()
        else:
            screenshot = screenshots[0]
        detections = screenshot.get_detections(model=self.name)
        if detections.count() == 0:
            self.detect(screenshot)
        return screenshot

    def detect_latest_screenshot(self):
        latest_timestamp = self.storage.get_latest_timestamp()
        screenshot = self.get_screenshot(latest_timestamp)
        return screenshot
    
    def error(self):
        human_counts = []
        errors = []
        reviewed_screenshots = [i for i in self.screenshots if i.reviewed]
        for screenshot in reviewed_screenshots:
            human_count = screenshot.human_count
            human_counts.append(human_count)
            detections = screenshot.get_detections()
            for detection in detections:
                error = detection.error()
                errors.append((abs(error)))
        model_error = sum(errors) / sum(human_counts)
        return model_error
    
    def error_range(self, detection: Detection)->set:
        """
        returns set(low, high)
        """
        count = detection.count
        error = self.error()
        error_amount = count * error
        low = count - error_amount
        high = count + error_amount
        payload = (low,  high)
        return payload
    
    def timeline(self, start_date):
        screenshots = [i for i in self.screenshots if i.timestamp >= start_date]
        detections = [i.get_detections()[0] for i in screenshots]
        x = [i.timestamp for i in detections]
        y = [i.count for i in detections] 
        payload = {
            "x": x,
            "y": y
        }
        return payload

from datetime import datetime, timedelta

def index(request):
    detection_model = "alpha"
    # heatmap = utils.transform_heatmap(detections)
    screenshot_detector = Detector(detection_model, utils.alpha_detector) 
    screenshot = screenshot_detector.detect_latest_screenshot()
    detection = screenshot.get_detections()[0]
    error_range = screenshot_detector.error_range(detection)
    # timeline = screenshot_detector.timeline(datetime.now() - timedelta(days=1))
    context = {
        "screenshot": screenshot,
        "detection": detection,
        "error": error_range
    }
    return render(request, "index.html", context)

def load(request):
    Screenshot.objects.all().delete()
    Detection.objects.all().delete()
    print("Processing Images")
    data = pd.read_csv("screenshots.csv")
    screenshot_detector = Detector("alpha", utils.alpha_detector)
    for index, row in data.iterrows():
        timestamp = utils.str_to_datetime(row["timestamp"])
        screenshot = Screenshot(
            timestamp=timestamp,
            url=row["url"],
            human_count=row["human_count"],
            human_mode=row["human_mode"],
            reviewed=row["reviewed"],
        )
        screenshot.save()
        detection = screenshot_detector.detect(screenshot)
        print(
            f"{screenshot_detector.name} detected {detection.count} objects in {screenshot.timestamp}"
        )
    return HttpResponse("Done")
