from django.db import models
import monitor.detector as detector


class Detection(models.Model):
    id =  models.AutoField(primary_key=True)
    model = models.CharField(max_length=99)
    timestamp = models.DateTimeField()
    count = models.IntegerField()

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
    def url_timestamp(self):
        return str(self.timestamp.strftime( "%Y-%m-%d %H:%M:%S.%f")).replace(" ", "_") 

    @property
    def imgpath(self):
        return f"images/wave/{self.model}/{self.url_timestamp}.png"

    @property
    def imgsrc(self):
        return detector.ScreenshotStore().imgcdn_src("/"+self.imgpath)

    def get_screenshot(self):
        return Screenshot.objects.filter(timestamp=self.timestamp)[0]

    def error(self):
        screenshot = Screenshot.objects.filter(timestamp=self.timestamp)[0]
        if type(screenshot.human_count) == int and type(self.count) == int:
            error = screenshot.human_count - self.count
        else:
            error = None
        return error


class Screenshot(models.Model):
    timestamp = models.DateTimeField(primary_key=True)
    url = models.CharField(max_length=99)
    human_count = models.IntegerField()
    human_mode = models.CharField(max_length=9)
    reviewed = models.BooleanField()
    
    @property
    def url_timestamp(self):
        return str(self.timestamp.strftime( "%Y-%m-%d %H:%M:%S.%f")).replace(" ", "_")

    @property
    def imgpath(self):
        return f"images/wave/{self.url_timestamp.replace('_', ' ')}.png"

    @property
    def imgsrc(self):
        return detector.ScreenshotStore().imgcdn_src("/"+self.imgpath)

    def get_detections(self, model=None):
        detection_count = Detection.objects.count()
        if detection_count > 0:
            detections = Detection.objects.filter(timestamp=self.timestamp, model=model)
        if detection_count == 0 or detections.count() == 0:
            detections = None
        return detections 
        
    def process(self, screenshot_detector, update=False):
        detections = self.get_detections(model=screenshot_detector.name)
        detection_count = len(screenshot_detector.detect(self))
        if detections and update:
            detection = detections[0]
            detection.count = detection_count 
        else:
            detection = Detection(timestamp=self.timestamp, model=screenshot_detector.name, count=detection_count)
        detection.save()
        return detection