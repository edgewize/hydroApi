from plotly.offline import plot
import plotly.graph_objs as go

from django.db import models
import monitor.utils as utils


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
                error = screenshot.human_count - self.count
            else:
                error = None
        return error

    def get_screenshot(self):
        screenshots = Screenshot.objects.filter(timestamp=self.timestamp)
        if screenshots.count() == 0:
            screenshot = None
        else:
            screenshot = screenshots[0]
        return screenshot
        


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
    
class Detector(object):
    def __init__(self, name, detect_function):
        self.name = name
        self.storage = utils.ScreenshotStore()
        self.detect_function = detect_function
        self.detections = Detection.objects.filter(model=name)
        self.screenshots = [
            s for s in [i.get_screenshot() for i in self.detections] if s
        ]

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
            detection = Detection(
                timestamp=screenshot.timestamp, model=self.name, count=detection_count
            )
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
                error = detection.error
                errors.append((abs(error)))
        model_error = sum(errors) / sum(human_counts)
        return model_error

    def error_range(self, detection: Detection) -> set:
        """
        returns set(low, high)
        """
        count = detection.count
        error = self.error
        error_amount = count * error()
        low = count - error_amount
        high = count + error_amount
        payload = (low, high)
        return payload

    def timeline(self, start_date):
        screenshots = [i for i in self.screenshots if i.timestamp >= start_date]
        detections = [i.get_detections()[0] for i in screenshots]
        x = [i.timestamp for i in detections]
        y = [i.count for i in detections]
        fig = go.Figure()
        scatter = go.Scatter(
            x=x, y=y, mode="lines", 
            name="Usage Timeline"
        )
        fig.add_trace(scatter)
        fig.update_layout(
            template='plotly_dark',
            height=200,
            margin=dict(l=20, r=20, t=40, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        plt_div = plot(fig, output_type="div")
        return plt_div
