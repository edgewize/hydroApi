import hydrofunctions as hf
import pandas as pd


def getTimeline(site_id, start_date, end_date):
    data = hf.NWIS(site_id, "dv", start_date=start_date, end_date=end_date).df()
    data = data[[data.columns[0]]]
    data["date"] = [str(i.date()) for i in data.index]
    data = data.set_index("date")
    return data


def getDelta(site_id, end_date, freq="d"):
    # freq: d (day), w (week), y (year)
    date_range = [
        str(i.date()) for i in pd.date_range(end_date, periods=3, freq=f"-3{freq}")
    ]
    print(date_range)
    current_period = getTimeline(site_id, date_range[1], date_range[0])
    previous_period = getTimeline(site_id, date_range[2], date_range[1])
    current_avg = current_period.mean()
    previous_avg = previous_period.mean()
    data = {"current": current_avg.values[0], "previous": previous_avg.values[0]}
    return data


if __name__ == "__main__":
    import datetime

    delta = getDelta("13206000", datetime.datetime.today(), freq="y")
    print(delta)
