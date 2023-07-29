from flask import Blueprint, jsonify, request
import datetime
import hydroApp.report as report
from dateutil.relativedelta import relativedelta

# 13206000 - Boise River

bp = Blueprint("main", __name__)


@bp.route("/")
def home():
    # TODO: Document the API and show it here
    return "Hydrofunctions API"

@bp.route("/info/<site_id>")
def info(site_id):
    request = hf.site_file(site_id)
    json = request.table.to_json()
    return jsonify(json)


@bp.route("/report/<site_id>", methods=["GET"])
def get_report(site_id):
    global request
    end_date = request.args.get("end_date", default=datetime.date.today())

    start_date = request.args.get(
        "start_date", default=end_date - relativedelta(days=7)
    )
    timeline = report.getTimeline(site_id, start_date, end_date).to_json()
    weekly_delta = report.getDelta(site_id, end_date, freq="w")
    monthly_delta = report.getDelta(site_id, end_date, freq="m")
    data = {
        "timeline": timeline,
        "delta": {
            "week": weekly_delta,
            "month": monthly_delta
        }
    }
    return jsonify(data)
