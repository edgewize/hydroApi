from django.shortcuts import render, redirect
from django.http import HttpResponse
import pandas as pd
import monitor.utils as utils
from monitor.models import Screenshot, Detection, Detector
from django.db.models import Q
from django.http import JsonResponse
import datetime
from monitor.models import Screenshot, Detection, Detector, do_detection


def index(request):
    screenshots = Screenshot.objects.filter(~Q(human_mode="invalid")).order_by(
        "-timestamp"
    )
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
            "error": detector.calc_error(),
        },
    }
    return render(request, "detector.html", context=context)


def detection(request, timestamp, name):
    detector_function = utils.lookup_detector(name)
    detector = Detector(name, detector_function)
    redo = bool(request.GET.get("redo"))
    detection = Detection.objects.filter(model=name, timestamp=timestamp)
    if detection.count() > 0:
        detection = detection.first()
        screenshot = detection.get_screenshot()
        if redo:
            detection = detector.detect(screenshot, update=True)
    else:
        screenshot = Screenshot.objects.filter(timestamp=timestamp).first()
        detection = detector.detect(screenshot)
    context = {"screenshot": screenshot, "detection": detection}
    return render(request, "detection.html", context)


async def screenshot_wave(request) -> JsonResponse:
    temp_path = "temp.png"
    await utils.screenshot_wave(temp_path)
    timestamp = datetime.datetime.now()
    slug = str(timestamp)
    save_path = r"images/wave/" + slug + ".png"
    utils.ScreenshotStore().upload(temp_path, save_path)
    screenshot = Screenshot(timestamp=timestamp, url=save_path)
    detection_model = "gamma"
    detect_function = utils.lookup_detector(detection_model)
    detection = await do_detection(detection_model, screenshot, detect_function)
    context = dict(slug=slug, screenshot=screenshot, detection=detection)
    return render(request, "recur.html", context=context)


def batch_detect(request):
    detection_model = "gamma"
    screenshots = Screenshot.objects.filter(~Q(human_mode="invalid")).order_by(
        "-timestamp"
    )
    for screenshot in screenshots:
        detections = screenshot.get_detections()
        done = False
        for detection in detections:
            if detection.model == detection_model:
                done = True
        if screenshot.timestamp.date() > datetime.date(2024, 1, 1) and not done and screenshot.reviewed:
            detect_function = utils.lookup_detector(detection_model)
            screenshot_detector = Detector(detection_model, detect_function)
            detection = screenshot_detector.detect(screenshot)
            print("Detected: " + detection.imgsrc)
    return redirect("/detector/" + detection_model)


def load(request):
    Screenshot.objects.all().delete()
    Detection.objects.all().delete()
    print("Processing Images")
    data = pd.read_csv("screenshots.csv")
    detectors = [
        Detector(name, detect_function)
        for name, detect_function in utils.get_detectors().items()
    ]
    for index, row in data.iterrows():
        timestamp = utils.str_to_datetime(row["timestamp"])
        count = int(row["human_count"])
        reviewed = bool(row["reviewed"])
        screenshot = Screenshot(
            timestamp=timestamp,
            url=row["url"],
            human_count=count,
            human_mode=row["human_mode"],
            reviewed=reviewed,
        )
        screenshot.save()
        detections = []
        for detector in detectors:
            detection = detector.detect(screenshot)
            detections.append(detection)
        print(
            f"[{index}] Detections {screenshot.timestamp.date()} {screenshot.timestamp.time()} - {', '.join([': '.join([i.model, str(i.count)]) for i in detections])}"
        )
    return redirect("screenshots")
