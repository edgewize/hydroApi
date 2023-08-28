import os
import boto3
import hydrofunctions as hf
import pandas as pd
from dotenv import load_dotenv
import datetime
from PIL import Image

def getInfo(site_id):
    data = hf.site_file(site_id).table.to_json()
    return data


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
    current_period = getTimeline(site_id, date_range[1], date_range[0])
    previous_period = getTimeline(site_id, date_range[2], date_range[1])
    current_avg = current_period.mean()
    previous_avg = previous_period.mean()
    data = {"current": current_avg.values[0], "previous": previous_avg.values[0]}
    return data

class WasabiStore():
    def __init__(self):
        load_dotenv()
        s3 = boto3.resource('s3',
            endpoint_url = 'https://s3.us-west-1.wasabisys.com',
            aws_access_key_id =  os.getenv("WASABI_ACCESS"),
            aws_secret_access_key =  os.getenv("WASABI_SECRET")
        )
        self.client = s3
        self.bucket = s3.Bucket('edginton-portfolio')

    def upload_file(self, upload_file_path, destination_path):
        self.bucket.upload_file(upload_file_path, destination_path)
        return f"{upload_file_path} successfully uploaded to {destination_path}"

    def list_files(self, path):
        return [i.key for i in self.bucket.objects.filter(Prefix=path)]
    
def getLatestScreenshot():
    files = WasabiStore().list_files("images/wave/")
    date_files = [i.split("/")[-1].replace(".png", "") for i in files if ":" in i]
    datetimes = [datetime.datetime.strptime(i, "%Y-%m-%d %H:%M:%S.%f") for i in date_files]
    max_date = max(datetimes)
    latest_file = [i for i in files if str(max_date) in i]
    return latest_file[0].replace("images/", "")

if __name__ == "__main__":
    s = WasabiStore()
    files = s.list_files("images/wave")
    image = Image.open(f"https://edgewize.imgix.net/{files[0]}")
    display(image)