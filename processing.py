import os
import csv

import pandas as pd
from dotenv import load_dotenv

load_dotenv()
data_path = os.environ.get("DATA_PATH")


def preprocess_delay():
    # Result dataframe
    result = pd.DataFrame(columns=["from", "to", "avgDelay", "maxDelay", "minDelay", "stdDev"])


def preprocess_stations():
    # This only keeps the stations we need for the network and some possibly interesting attributes
    with open(data_path + "/stations/raw/stations.csv", "r") as inpt:
        reader = csv.reader(inpt)
        for row in reader:
