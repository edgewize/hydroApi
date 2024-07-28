from django.http import JsonResponse
from monitor.models import Screenshot, Detection, Detector, do_detection
import monitor.utils as utils
import asyncio
import datetime
import os
from django.shortcuts import render, redirect


def screenshot(request, url_timestamp: str) -> JsonResponse:
    timestamp = utils.str_to_datetime(url_timestamp)
    screenshot = Screenshot.objects.filter(timestamp=timestamp).first()
    if screenshot:
        payload = dict(
            timestamp=screenshot.timestamp.timestamp(),
            url=screenshot.url,
            count=screenshot.human_count,
            mode=screenshot.human_mode,
            url_timestamp=screenshot.url_timestamp,
            imgsrc=screenshot.imgsrc,
        )
    else:
        payload = dict()
    return JsonResponse(payload, content_type="application/json")


def detection(request, model: str, url_timestamp: str) -> JsonResponse:
    timestamp = utils.str_to_datetime(url_timestamp)
    detection = Detection.objects.filter(model=model, timestamp=timestamp).first()
    if detection:
        payload = dict(
            timestamp=detection.timestamp.timestamp(),
            model=detection.model,
            count=detection.count,
            error=detection.calc_error,
            imgsrc=detection.imgsrc,
            usage_rating=detection.usage_rating,
        )
    else:
        payload = dict()
    return JsonResponse(payload, content_type="application/json")


def detector(request, name: str) -> JsonResponse:
    detect_function = utils.lookup_detector(name)
    detector = Detector(name, detect_function)
    latest_detection = (
        detector.detect_latest_screenshot().get_detections(model=name)[0].to_dict()
    )
    detections = detector.valid_detections[:12]
    timeline_data = dict(
        x=[i.timestamp for i in detections], y=[i.count for i in detections]
    )
    detections = [i.to_dict() for i in detections]
    payload = dict(
        name=detector.name,
        latest_detection=latest_detection,
        detections=detections,
        detection_count=len(detector.detections),
        valid_detection_count=len(detector.valid_detections),
        error=detector.calc_error(),
        timeline=timeline_data,
        heatmap=detector.heatmap(),
    )
    return JsonResponse(payload, content_type="application/json")


def flow(request) -> JsonResponse:
    flow = utils.get_river_flow("D", 150)
    flow.columns = ["cfs", "P"]
    latest = flow.loc[flow.index.max()]
    last_week = flow.loc[flow.index[-7]]
    payload = dict(
        latest=dict(timestamp=str(latest.name.date()), cfs=latest["cfs"]),
        last_week=dict(timestamp=str(last_week.name.date()), cfs=last_week["cfs"]),
        timeline=dict(
            x=[str(i.date()) for i in flow.index], y=flow["cfs"].values.tolist()
        ),
    )
    return JsonResponse(payload, content_type="application/json")



async def screenshot_wave(request) -> JsonResponse:
    temp_path = "temp.png"
    await utils.screenshot_wave(temp_path)
    timestamp = datetime.datetime.now()
    slug = str(timestamp)
    save_path = r"images/wave/" + slug + ".png"
    utils.ScreenshotStore().upload(temp_path, save_path)
    screenshot = Screenshot(timestamp=timestamp, url=save_path)
    detection_model = "beta"
    detect_function = utils.lookup_detector(detection_model)
    detection = await do_detection(detection_model, screenshot, detect_function)
    context = dict(slug=slug, screenshot=screenshot, detection=detection)
    return render(request, "recur.html", context=context)

