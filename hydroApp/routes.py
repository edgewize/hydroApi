from flask import Blueprint, jsonify, request
import datetime
from dateutil.relativedelta import relativedelta
import hydroApp.report as report
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
