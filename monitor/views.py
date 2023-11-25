from django.shortcuts import render
from django.http import HttpResponse
from datetime import datetime, timedelta
from django.utils import timezone
import pandas as pd
import monitor.utils as utils
from monitor.models import Screenshot, Detection, Detector


def index(request):
    detection_model = "delta"
    detect_function = utils.lookup_detector(detection_model)
    screenshot_detector = Detector(detection_model, detect_function)
    screenshot = screenshot_detector.detect_latest_screenshot()
    detection = screenshot.get_detections(model=detection_model).first()
    error_range = screenshot_detector.error_range(detection)
    timeline = screenshot_detector.timeline(10)
    context = {
        "screenshot": screenshot,
        "detection": detection,
        "error": error_range,
        "timeline": timeline,
    }
    return render(request, "index.html", context)


def screenshots(request):
    screenshots = Screenshot.objects.all().order_by("-timestamp")
    review_count = Screenshot.objects.filter(reviewed=True).count()
    context = {"screenshots": screenshots, "review_count": review_count}
    return render(request, "screenshots.html", context)


def screenshot(request, timestamp):
    timestamp = utils.str_to_datetime(timestamp.replace("_", " "))
    screenshots = Screenshot.objects.all()
    for index, s in enumerate(screenshots):
        if s.timestamp == timestamp:
            screenshot = s
            try:
                prev_screenshot = screenshots[index - 1]
            except:
                prev_screenshot = None
            try:
                next_screenshot = screenshots[index + 1]
            except IndexError:
                next_screenshot = None
            break
        else:
            screenshot = None
    if screenshot:
        detections = screenshot.get_detections()
        potential_detectors = screenshot.get_potential_detectors()
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
        "next_screenshot": next_screenshot,
        "detectors": potential_detectors,
    }
    return render(request, "screenshot.html", context)


def detector(request, name):
    detector_function = utils.lookup_detector(name)
    detector = Detector(name, detector_function)
    detections = detector.valid_detections
    refresh_count = request.GET.get("count")
    if refresh_count:
        detector.refresh(int(refresh_count))
    detect_reviewed = request.GET.get("reviewed")
    if detect_reviewed:
        detector.detect_reviewed()
    clear = request.GET.get("clear")
    if clear:
        detector.detections.delete()
    context = {
        "name": name,
        "detections": detections,
        "data": {
            "total": len(detector.detections),
            "valid": len(detector.valid_detections),
            "reviewed": len(detector.reviewed_screenshots),
            "error": detector.error(),
        },
    }
    return render(request, "detector.html", context=context)


def detection(request, timestamp, name):
    detection = Detection.objects.filter(model=name, timestamp=timestamp)
    if detection.count() == 0:
        screenshot = Screenshot.objects.filter(timestamp=timestamp).first()
        detector_function = utils.lookup_detector(name)
        detector = Detector(name, detector_function)
        detection = detector.detect(screenshot)
    else:
        detection = detection.first()
        screenshot = detection.get_screenshot()
    context = {"screenshot": screenshot, "detection": detection}
    return render(request, "detection.html", context)


def load(request):
    Screenshot.objects.all().delete()
    Detection.objects.all().delete()
    print("Processing Images")
    data = pd.read_csv("screenshots.csv")
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
        detections = []
        for name, detect_function in utils.get_detectors().items():
            detector = Detector(name, detect_function)
            detection = detector.detect(screenshot)
            detections.append(detection)
        print(
            f"Detections {screenshot.timestamp.date()} {screenshot.timestamp.time()} - {', '.join([': '.join([i.model, str(i.count)]) for i in detections])}"
        )
    return HttpResponse("Done")
