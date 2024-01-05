from plotly.offline import plot
import plotly.graph_objs as go
import pandas as pd
from django.db import models
import monitor.utils as utils
import numpy


class Detection(models.Model):
    id = models.AutoField(primary_key=True)
    model = models.CharField(max_length=99)
    timestamp = models.DateTimeField()
    count = models.IntegerField()

    @property
    def url_timestamp(self):
        return str(self.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")).replace(" ", "_")

    @property
    def imgpath(self):
        return f"images/wave/{self.model}/{self.url_timestamp}.png"

    @property
    def imgsrc(self):
        return utils.ScreenshotStore().imgcdn_src("/" + self.imgpath)

    @property
    def usage_rating(self):
        if self.count > 12:
            usage = "high"
        elif self.count > 5:
            usage = "medium"
        else:
            usage = "low"
        return usage

    @property
    def error(self):
        screenshot = self.get_screenshot()
        if screenshot:
            if type(screenshot.human_count) == int and type(self.count) == int:
                error = self.count - screenshot.human_count
            else:
                error = None
        return error

    def to_dict(self):
        timestamp = f"{self.timestamp.date()} {self.timestamp.time()}"
        return dict(timestamp=timestamp, imgsrc=self.imgsrc, count=self.count)

    def get_screenshot(self):
        screenshots = Screenshot.objects.filter(timestamp=self.timestamp)
        if screenshots.count() == 0:
            screenshot = Screenshot(timestamp=self.timestamp)
            screenshot.save()
        else:
            screenshot = screenshots.first()
        return screenshot

    def is_invalid(self):
        screenshot = self.get_screenshot()
        if screenshot.human_mode == "invalid":
            return True
        else:
            return False

    def __dict__(self):
        return self.__attrs__


class Screenshot(models.Model):
    timestamp = models.DateTimeField(primary_key=True)
    url = models.CharField(max_length=99, null=True)
    human_count = models.IntegerField(null=True)
    human_mode = models.CharField(max_length=9, null=True)
    reviewed = models.BooleanField(null=True)

    @property
    def url_timestamp(self):
        return str(self.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")).replace(" ", "_")

    @property
    def imgpath(self):
        return f"images/wave/{self.url_timestamp.replace('_', ' ')}.png"

    @property
    def imgsrc(self):
        return utils.ScreenshotStore().imgcdn_src("/" + self.imgpath)

    def get_detections(self, model=None):
        if model:
            detections = Detection.objects.filter(timestamp=self.timestamp, model=model)
        else:
            detections = Detection.objects.filter(timestamp=self.timestamp)
        return detections

    def get_potential_detectors(self):
        done_detectors = [i.model for i in self.get_detections()]
        all_detectors = utils.get_detectors().keys()
        potential_detectors = [i for i in all_detectors if i not in done_detectors]
        if len(potential_detectors) == 0:
            potential_detectors = None
        return potential_detectors


class Detector(object):
    def __init__(self, name, detect_function):
        self.name = name
        self.storage = utils.ScreenshotStore()
        self.detect_function = detect_function
        self.detections = Detection.objects.filter(model=name).order_by("timestamp")
        self.valid_detections = [i for i in self.detections if not i.is_invalid()]
        self.screenshots = [
            s for s in [i.get_screenshot() for i in self.valid_detections] if s
        ]
        self.reviewed_screenshots = [i for i in self.screenshots if i.reviewed]

    def detect(self, screenshot, update=False):
        image = self.storage.get_image(screenshot.imgpath)
        img_detections = self.detect_function(image)
        rgb_annotated_image = utils.visualize_detections(image, img_detections)
        self.storage.upload(
            rgb_annotated_image,
            f"images/wave/{self.name}/{screenshot.url_timestamp}.png",
        )
        detection_count = len(img_detections)
        detections = Detection.objects.filter(
            timestamp=screenshot.timestamp, model=self.name
        )
        if detections and update:
            detection = detections.first()
            detection.count = detection_count
            purge_cdn = utils.purge_imgcdn(detection.imgsrc)
        else:
            detection = Detection(
                timestamp=screenshot.timestamp, model=self.name, count=detection_count
            )
        print(f"Detected {detection.count} objects in {screenshot.timestamp}")
        detection.save()
        return detection

    def refresh(self, count):
        timestamps = self.storage.get_latest_timestamps(count=count)
        for timestamp in timestamps:
            screenshot = Screenshot(timestamp=timestamp)
            screenshot.save()
            detection = self.detect(screenshot, update=True)
            print(f"Detected {detection.count} objects in {screenshot.timestamp}")

    def detect_reviewed(self):
        screenshots = Screenshot.objects.filter(reviewed=True)
        for screenshot in screenshots:
            detection = self.detect(screenshot, update=True)
            print(f"Detected {detection.count} objects in {screenshot.timestamp}")

    def get_screenshot(self, timestamp):
        screenshots = [i for i in self.screenshots if i.timestamp == timestamp]
        if len(screenshots) == 0:
            # new timstammp in storage and it needs a db record here
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
        for screenshot in self.reviewed_screenshots:
            human_count = screenshot.human_count
            if human_count:
                detections = screenshot.get_detections(model=self.name)
                for detection in detections:
                    error = detection.error
                    human_counts.append(human_count)
                    errors.append((abs(error)))
        try:
            model_error = sum(errors) / sum(human_counts)
        except ZeroDivisionError:
            model_error = None
        return model_error

    def error_range(self, detection: Detection) -> set:
        """
        returns set(low, high)
        """
        count = detection.count
        error = self.error()
        if count and error:
            error_amount = count * error
            low = count - error_amount
            high = count + error_amount
            payload = (low, high)
        else:
            payload = None
        return payload

    def timeline_data(self, sample_count):
        detections = sorted(self.detections, key=lambda x: x.timestamp)[-sample_count:]
        df = (
            (
                pd.DataFrame(
                    {
                        "timestamp": [i.timestamp for i in detections],
                        "count": [i.count for i in detections],
                    }
                )
                .set_index("timestamp")
                .groupby(pd.Grouper(freq="d"))
                .mean()
            )
            .reset_index()
            .dropna()
        )
        x = list(df["timestamp"].apply(lambda x: str(x.date())))
        y = list(df["count"].values)
        data = dict(x=x, y=y)
        return data

    def timeline(self, sample_count):
        data = self.timeline_data(sample_count)
        fig = go.Figure()
        scatter = go.Bar(x=data["x"], y=data["y"], name="Usage Timeline")
        fig.add_trace(scatter)
        fig.update_layout(
            template="plotly_dark",
            height=200,
            margin=dict(l=20, r=20, t=40, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        plt_div = plot(fig, output_type="div")
        return plt_div

    def heatmap(self):
        df = pd.DataFrame(
            [
                {"timestamp": i.timestamp, "count": int(i.count)}
                for i in self.valid_detections
            ]
        )
        df["hour"] = df["timestamp"].apply(lambda x: x.hour)
        df["weekday"] = df["timestamp"].apply(lambda x: x.weekday)
        transform = df.drop(columns=["timestamp"]).groupby(["hour", "weekday"]).mean()
        transform = transform.unstack().fillna(0).values.tolist()
        payload = {
            "x": df["weekday"].unique().tolist(),
            "y": df["hour"].unique().tolist(),
            "z": transform,
        }
        return payload
