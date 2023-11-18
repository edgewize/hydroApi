from django.shortcuts import render
from django.http import HttpResponse
from datetime import datetime, timedelta
from django.utils import timezone

# Create your views here.
import pandas as pd
import monitor.utils as utils
from monitor.models import Screenshot, Detection, Detector

def index(request):
    detection_model = "alpha"
    # heatmap = utils.transform_heatmap(detections)
    screenshot_detector = Detector(detection_model, utils.alpha_detector) 
    screenshot = screenshot_detector.detect_latest_screenshot()
    detection = screenshot.get_detections(model=detection_model)[0]
    now = timezone.now()
    error_range = screenshot_detector.error_range(detection)
    timeline = screenshot_detector.timeline(now - timedelta(days=3))
    context = {
        "screenshot": screenshot,
        "detection": detection,
        "error": error_range,
        "timeline": timeline
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
