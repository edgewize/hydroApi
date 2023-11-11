from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
import pandas as pd
import monitor.detector as detector
from monitor.models import Screenshot, Detection


def index(request):
    detection_model = "alpha"
    screenshot_detector = detector.Detector(detection_model, detector.alpha_detector)
    detections = Detection.objects.filter(model=detection_model)
    # heatmap = detector.transform_heatmap(detections)
    latest_timestamp = detector.ScreenshotStore().get_latest_timestamp()
    screenshot = Screenshot.objects.filter(
        timestamp=latest_timestamp
    )
    if screenshot.count() == 0:
        screenshot = Screenshot(
            timestamp=latest_timestamp)
    else:
        screenshot = screenshot[0]
    # screenshot = max(
    #     Screenshot.objects.filter(human_mode="surf"),
    #     key=lambda x: x.timestamp
    # )
    if screenshot.get_detections():
        detection = Detection.objects.filter(timestamp=screenshot.timestamp)[0]
    else:
        detection = screenshot.process(screenshot_detector, update=True)
    # human_counts = []
    # errors = []
    # for d in detections:
    #     human_count = d.get_screenshot().human_count
    #     error = d.error()
    #     if human_count and error:
    #         human_counts.append(human_count)
    #         errors.append(abs(error))
    # model_error = sum(errors) / sum(human_counts)
    # error_count = detection.count * model_error
    # error_range = (
    #     int(detection.count - error_count),
    #     int(detection.count + error_count),
    # )
    context = {
        "screenshot": screenshot,
        "detection": detection,
        # "model_error": model_error,
        # "error_range": {"low": error_range[0], "high": error_range[1]},
    }
    return render(request, "index.html", context)


def load(request):
    Screenshot.objects.all().delete()
    Detection.objects.all().delete()
    print("Processing Images")
    data = pd.read_csv("screenshots.csv")
    screenshot_detector = detector.Detector("alpha", detector.alpha_detector)
    for index, row in data.iterrows():
        timestamp = detector.str_to_datetime(row["timestamp"])
        screenshot = Screenshot(
            timestamp=timestamp,
            url=row["url"],
            human_count=row["human_count"],
            human_mode=row["human_mode"],
            reviewed=row["reviewed"],
        )
        screenshot.save()
        detection = screenshot.process(screenshot_detector)
        print(
            f"{screenshot_detector.name} detected {detection.count} objects in {screenshot.timestamp}"
        )
    return HttpResponse("Done")
