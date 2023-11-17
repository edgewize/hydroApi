from django.db import models
import monitor.utils as utils

class Detection(models.Model):
    id =  models.AutoField(primary_key=True)
    model = models.CharField(max_length=99)
    timestamp = models.DateTimeField()
    count = models.IntegerField()

    @property
    def url_timestamp(self):
        return str(self.timestamp.strftime( "%Y-%m-%d %H:%M:%S.%f")).replace(" ", "_") 

    @property
    def imgpath(self):
        return f"images/wave/{self.model}/{self.url_timestamp}.png"

    @property
    def imgsrc(self):
        return utils.ScreenshotStore().imgcdn_src("/"+self.imgpath)

    @property
    def usage_rating(self):
        if self.count > 12:
            usage = "high"
        elif self.count > 5:
            usage = "medium"
        else:
            usage = "low"
        return usage
    
    def get_screenshot(self):
        screenshots = Screenshot.objects.filter(timestamp=self.timestamp)
        if screenshots.count() == 0:
            screenshot = None
        else:
            screenshot = screenshots[0]
        return screenshot
 
    def error(self):
        screenshot = self.get_screenshot()
        if screenshot:
            if type(screenshot.human_count) == int and type(self.count) == int:
                error = screenshot.human_count - self.count
            else:
                error = None
        return error


class Screenshot(models.Model):
    timestamp = models.DateTimeField(primary_key=True)
    url = models.CharField(max_length=99, null=True)
    human_count = models.IntegerField(null=True)
    human_mode = models.CharField(max_length=9, null=True)
    reviewed = models.BooleanField(null=True)
    
    @property
    def url_timestamp(self):
        return str(self.timestamp.strftime( "%Y-%m-%d %H:%M:%S.%f")).replace(" ", "_")

    @property
    def imgpath(self):
        return f"images/wave/{self.url_timestamp.replace('_', ' ')}.png"

    @property
    def imgsrc(self):
        return utils.ScreenshotStore().imgcdn_src("/"+self.imgpath)

    def get_detections(self, model=None):
        if model:
            detections = Detection.objects.filter(timestamp=self.timestamp, model=model)
        else:
            detections = Detection.objects.filter(timestamp=self.timestamp) 
        return detections 
        
    # use utils.detect() instead
    # def process(self, screenshot_detector, update=False):
    #     detections = self.get_detections(model=screenshot_utils.name)
    #     detection_count = len(screenshot_utils.detect(self))
    #     if detections and update:
    #         detection = detections[0]
    #         detection.count = detection_count 
    #     else:
    #         detection = Detection(timestamp=self.timestamp, model=screenshot_utils.name, count=detection_count)
    #     detection.save()
    #     return detection