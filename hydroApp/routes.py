from flask import Blueprint, jsonify, request
import datetime
from dateutil.relativedelta import relativedelta
import hydroApp.report as report

import models
from hydroApp import db
import datetime

# 13206000 - Boise River


bp = Blueprint("main", __name__)


@bp.route("/")
def home():
    # TODO: Document the API and show it here
    return "Hydrofunctions API"

@bp.route("/report/<site_id>", methods=["GET"])
def get_report(site_id):
    global request
    end_date = request.args.get("end_date", default=datetime.date.today())

    start_date = request.args.get(
        "start_date", default=end_date - relativedelta(days=7)
    )
    info = report.getInfo(site_id)
    timeline = report.getTimeline(site_id, start_date, end_date).to_json()
    weekly_delta = report.getDelta(site_id, end_date, freq="w")
    monthly_delta = report.getDelta(site_id, end_date, freq="m")
    screenshot = report.getLatestScreenshot()
    process_img = report.process_image(screenshot)
    data = {
        "info": info,
        "screenshot": screenshot,
        "detections": process_img,
        "timeline": timeline,
        "delta": {
            "week": weekly_delta,
            "month": monthly_delta
        }
    }
    return jsonify(data)



@bp.route("/create/screenshot", methods=["GET","POST"])
def create_screenshot():
    screenshot = models.Screenshot(
        datetime.datetime.strptime("2023-08-14 10:03:30.744708", "%Y-%m-%d %H:%M:%S.%f"),
        "/images/wave/2023-08-14 10:03:30.744708.png",
        4,
        6
    )
    db.session.add(screenshot)
    db.session.commit()
    return "True"


@bp.route("/count/screenshots", methods=["GET","POST"])
def count_screenshots():
    count = len(models.Screenshot.query.all())
    return jsonify({"count": count})


@bp.route("/load/screenshots", methods=["GET","POST"])
def load_screenshots():
    files = [i for i in report.WasabiStore().list_files("images/wave") if ":" in i]
    data = []
    for key in files[:10]:
        detections = report.process_image(key)
        timestamp = datetime.datetime.strptime(
            key.split("/")[-1].replace(".png", ""),
            "%Y-%m-%d %H:%M:%S.%f"
        )
        check_record = db.session.query(models.Screenshot).get(timestamp) 
        if  check_record is None:
            count = detections["count"]
            test_count = 0
            screenshot = models.Screenshot(
                timestamp,
                key,
                count,
                test_count
            )
            db.session.add(screenshot)
            db.session.commit()
            data.append(screenshot)
        else:
            print(f"{key} already in Database")
    return f"Added {len(data)} screenshots"

# @bp.route("/get/screenshots", methods=["GET","POST"])
# def get_screenshot():
#     screenshots = models.Screenshot.query.all()
#     import pdb
#     pdb.set_trace()
#     return jsonify(screenshots)

# @bp.route("/add/screenshot", methods=["GET", "POST"])
# def add_screenshot():
#     models.create_screenshot()
#     return jsonify({"result": True})  

# screenshot = db.Screenshot(
#     "2023-08-14 10:03:30.744708",
#     "/images/wave/2023-08-14 10:03:30.744708.png"
# )