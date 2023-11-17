import datetime
import pandas as pd
from dateutil.relativedelta import relativedelta
from flask import Blueprint, jsonify, request, render_template, redirect

from hydroApp import db
import hydroApp.detector as detector
from models import Screenshot, Detection

# 13206000 - Boise River

bp = Blueprint("main", __name__)


@bp.route("/screenshots", methods=["GET", "POST"])
def screenshots():
    query = Screenshot.query
    records = query.all()
    reviewed_records = query.filter(Screenshot.reviewed).all()
    invalid_records = query.filter(Screenshot.human_mode == "invalid").all()
    surf_records = query.filter(Screenshot.human_mode == "surf").all()
    count = len(records)
    reviewed_count = len(reviewed_records)
    invalid_count = len(invalid_records)
    surf_count = len(surf_records)
    stats = {
        "count": count,
        "reviewed_count": reviewed_count,
        "invalid_count": invalid_count,
        "surf_count": surf_count,
    }
    record_filter = request.args.get("filter")
    show_button = True
    if record_filter == "untested":
        records = Screenshot.query.filter(Screenshot.reviewed != True).all()
        show_button = False
    elif record_filter == "invalid":
        records = invalid_records
    else:
        records = surf_records
    return render_template(
        "screenshots.html", screenshots=records, stats=stats, show_button=show_button
    )


@bp.route("/screenshots/<timestamp>", methods=["GET", "POST"])
def screenshot(timestamp):
    global request
    screenshot = detector.get_screenshot(timestamp)
    detections = screenshot.get_detections()
    if request.form:
        if request.form["human_count"].isnumeric():
            screenshot.human_count = int(request.form["human_count"])
        screenshot.human_mode = request.form["human_mode"]
        screenshot.reviewed = True
        db.session.commit()
        screenshot = detector.get_screenshot(timestamp)
        redirect_url = "/screenshots?filter=untested"
        return redirect(redirect_url)
    return render_template(
        "screenshot.html", screenshot=screenshot, detections=detections
    )


@bp.route("/report/export", methods=["GET"])
def export():
    query = db.session.query(Screenshot).filter(Screenshot.human_count)
    df = pd.DataFrame(
        [(i.timestamp, i.url, i.human_count, i.human_mode, i.reviewed) for i in query.all()]
    )
    df.columns = ["timestamp", "url", "human_count", "human_mode", "reviewed"]
    df.to_csv("screenshots.csv")
    return "Export successful"


@bp.route("/screenshots/import", methods=["GET", "POST"])
def load_screenshots():
    global request
    df = pd.read_csv("export.csv")
    img_dir = "images/wave"
    files = [
        i
        for i in detector.ScreenshotStore().list_files(img_dir)
        if ":" in i and "processed" not in i
    ]
    print(f"Loading {len(files)} images")
    added = []
    updated = []
    for file in files:
        key = file.split("/")[-1].replace(".png", "")
        timestamp = datetime.datetime.strptime(key, "%Y-%m-%d %H:%M:%S.%f")
        human_mode = None
        if str(timestamp) in df["timestamp"].values:
            reviewed = True
            human_count = df.set_index("timestamp").loc[str(timestamp)]["test_count"]
        else:
            reviewed = False
            human_count = None
        check_record = db.session.query(Screenshot).get(timestamp)
        url = file
        if check_record is None:
            screenshot = Screenshot(timestamp, url, human_count, human_mode, reviewed)
            db.session.add(screenshot)
            db.session.commit()
            added.append(1)
            print(f"added {key}")
        else:
            check_record.url = url
            check_record.human_count = human_count
            check_record.reviewed = reviewed
            db.session.commit()
            updated.append(1)
            print(f"updated {key}")

    return f"Added {len(added)} screenshots. Updated {len(updated)} screenshots."


# @bp.route("/report/<site_id>", methods=["GET"])
# def get_report(site_id):
#     global request
#     end_date = request.args.get("end_date", default=datetime.date.today())

#     start_date = request.args.get(
#         "start_date", default=end_date - relativedelta(days=7)
#     )
#     info = report.getInfo(site_id)
#     timeline = report.getTimeline(site_id, start_date, end_date).to_json()
#     weekly_delta = report.getDelta(site_id, end_date, freq="w")
#     monthly_delta = report.getDelta(site_id, end_date, freq="m")
#     screenshot = report.getLatestScreenshot()
#     process_img = report.process_image(screenshot)
#     data = {
#         "info": info,
#         "screenshot": screenshot,
#         "detections": process_img,
#         "timeline": timeline,
#         "delta": {"week": weekly_delta, "month": monthly_delta},
#     }
#     return jsonify(data)
