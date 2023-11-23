from django.shortcuts import render
from django.http import HttpResponse
from datetime import datetime, timedelta
from django.utils import timezone
import pandas as pd
import monitor.utils as utils
from monitor.models import Screenshot, Detection, Detector

def index(request):
    detection_model = "alpha"
    # heatmap = utils.transform_heatmap(detections)
    screenshot_detector = Detector(detection_model, utils.alpha_detector) 
    # screenshot_detector.refresh(10)
    screenshot = screenshot_detector.detect_latest_screenshot()
    detection = screenshot.get_detections(model=detection_model)[0]
    now = timezone.now()
    error_range = screenshot_detector.error_range(detection)
    timeline = screenshot_detector.timeline(10)
    context = {
        "screenshot": screenshot,
        "detection": detection,
        "error": error_range,
        "timeline": timeline
    }
    return render(request, "index.html", context)

def screenshots(request):
    screenshots = Screenshot.objects.all().order_by("-timestamp")
    review_count = Screenshot.objects.filter(reviewed=True).count()
    context = {
        "screenshots": screenshots,
        "review_count": review_count
    }
    return render(request, "screenshots.html", context)

def screenshot(request, timestamp):
    timestamp = utils.str_to_datetime(timestamp.replace("_"," "))
    screenshots = Screenshot.objects.all()
    for index, s in enumerate(screenshots):
        if s.timestamp == timestamp:
            screenshot = s
            try:
                prev_screenshot = screenshots[index-1]
            except IndexError:
                prev_screenshot = None
            try:
                next_screenshot = screenshots[index+1]
            except IndexError:
                next_screenshot = None
            break
        else:
            screenshot = None
    if screenshot:
        detections = screenshot.get_detections()
        if request.POST:
            count = request.POST.get("human_count")
            mode = request.POST.get("human_mode")
            if count:
                screenshot.human_count = count
            if mode:
                screenshot.human_mode = mode
            if count or mode:
                screenshot.reviewed = True
            screenshot.save()
            screenshot = Screenshot.objects.filter(timestamp=timestamp).first()
    else:
        detections = None
    context = {
        "screenshot": screenshot,
        "detections": detections,
        "prev_screenshot": prev_screenshot,
        "next_screenshot": next_screenshot
    }
    return render(request, "screenshot.html", context)

def detection(request, timestamp, model):
    detection = Detection.objects.filter(model=model, timestamp=timestamp)
    if detection.count() == 0:
        screenshot = Screenshot.objects.filter(timestamp=timestamp).first()
        detector_function = utils.lookup_detector(model)
        detector = Detector(model, detector_function)
        detection = detector.detect(screenshot)
    else:
        detection = detection.first()
        screenshot = detection.get_screenshot()
    context = {
        "screenshot": screenshot,
        "detection": detection
    }
    return render(request, "detection.html", context)

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
