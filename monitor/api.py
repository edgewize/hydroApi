from django.http import JsonResponse
from monitor.models import Screenshot, Detection, Detector
import monitor.utils as utils
import json


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
            error=detection.error,
            imgsrc=detection.imgsrc,
            usage_rating=detection.usage_rating,
        )
    else:
        payload = dict()
    return JsonResponse(payload, content_type="application/json")


def detector(request, name) -> JsonResponse:
    detect_function = utils.lookup_detector(name)
    detector = Detector(name, detect_function)
    payload = dict(
        name=detector.name,
        detection_count=len(detector.detections),
        valid_detection_count=len(detector.valid_detections),
        error=detector.error(),
        timeline=detector.timeline_data(24)
    )
    return JsonResponse(payload, content_type="application/json")