from hydroApp import db
import datetime
import hydroApp.detector as detector


class Detection(db.Model):
    __tablename__ = "detections"
    __table_args__ = {"extend_existing": True}
    id = db.Column("id", db.Integer, primary_key=True, autoincrement=True)
    screenshot_timestamp = db.Column("screenshot_timestamp", db.DateTime)
    model = db.Column("model", db.String(100))
    count = db.Column("count", db.Integer)

    def __init__(self, screenshot_timestamp: str, model: str, count: int):
        self.screenshot_timestamp = screenshot_timestamp
        self.model = model
        self.count = count

    def get_screenshot(self):
        return Screenshot.query.filter(Screenshot.timestamp == self.screenshot_timestamp).first()

    def error(self):
        screenshot = Screenshot.query.get(self.screenshot_timestamp)
        if type(screenshot.human_count) == int and type(self.count) == int:
            error = screenshot.human_count - self.count
        else:
            error = None
        return error
    
    def usage_rating(self):
        if self.count > 12:
            usage = "high"
        elif self.count > 5:
            usage = "medium"
        else:
            usage = "low"
        return usage
        

    def imgsrc(self):
        return detector.ScreenshotStore().imgcdn_src(f"/images/wave/{self.model}/{self.screenshot_timestamp}.png") 


class Screenshot(db.Model):
    __tablename__ = "screenshots"
    __table_args__ = {"extend_existing": True}
    timestamp = db.Column("timestamp", db.DateTime, primary_key=True, nullable=False)
    url = db.Column("url", db.String(100), nullable=False)
    human_count = db.Column("human_count", db.Integer)
    human_mode = db.Column("human_mode", db.String(100))
    reviewed = db.Column("reviewed", db.Boolean)

    def __init__(
        self,
        timestamp: datetime.datetime.timestamp,
        url: str,
        human_count: int,
        human_mode: str,
        reviewed: bool,
    ):
        self.timestamp = timestamp
        self.url = url
        self.human_count = human_count
        self.human_mode = human_mode
        self.reviewed = reviewed

    def get_detections(self, model=None):
        if model:
            detections = Detection.query.filter(
                self.timestamp == Detection.screenshot_timestamp
                and model == Detection.model
            )
        else:
            detections = Detection.query.filter(
                self.timestamp == Detection.screenshot_timestamp
            )
        return detections

    def url_timestamp(self):
        return str(self.timestamp).replace(" ", "_")
        
    def imgsrc(self):
        return detector.ScreenshotStore().imgcdn_src(f"/images/wave/{self.timestamp}.png")

    def process(self, screenshot_detector, update=False):
        detections = self.get_detections(model=screenshot_detector.name).all()
        detection_count = len(screenshot_detector.detect(self))
        if len(detections) > 0 and update:
            result = detector.update_detection(detections, detection_count)
        else:
            result = detector.create_detection(
                self.timestamp, screenshot_detector.name, detection_count
            )
        return result
        # detections = self.get_detections(model=scr.name).all()
        # return detections


if __name__ == "__main__":
    from run import appp

    # Run this file directly to create the database tables.
    print("Creating database tables...")
    with app.app_context():
        db.drop_all()
        db.create_all()
    print("Tables created")
