from flask import Blueprint, jsonify, request
import hydrofunctions as hf
import datetime
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


@bp.route("/data/<site_id>", methods=["GET"])
def data(site_id):
    global request
    end_date = request.args.get("end_date", default=datetime.date.today())

    start_date = request.args.get(
        "start_date", default=end_date - relativedelta(days=7)
    )

    data = hf.NWIS(site_id, "dv", start_date=start_date, end_date=end_date).df()
    data = data[[data.columns[0]]]
    data["date"] = [str(i.date()) for i in data.index]
    data = data.set_index("date")
    return jsonify(data.to_json())
