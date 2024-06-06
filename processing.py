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
    # Open station as dataframe
    station_df = pd.read_csv(data_path + "/stations/raw/stations.csv")

    # Once again kick out the duplicates
    station_df.drop_duplicates(keep='first', inplace=True)

    # Get all delay files
    all_files = os.listdir(data_path + "/delay/raw")
    csv_files = list(filter(lambda f: f.endswith(".csv"), all_files))

    needed_stations = []

    for file in csv_files:
        print("Processing " + file)

        delay_df = pd.read_csv(data_path + "/delay/raw/" + file)
        header = delay_df.columns.to_list()

        # Get stations from header
        for col in header[1::2]:
            # Strip away the .in and .out behind station names
            formatted_col = col.replace("_", " ").split(".")[0]
            german_stop = True if formatted_col in station_df['name'].to_list() else False

            if col not in needed_stations and german_stop:
                needed_stations.append(formatted_col)

            # Some non german stations are inside the data,
            # simply because the train has been used as a replacement train
            if not german_stop:
                delay_df.drop(col, axis=1)
                delay_df.drop((col.rstrip("in") + "out"), axis=1)

    # Remove every station that is not in the list
    station_df = station_df[station_df["name"].isin(needed_stations)]

    # Remove unneeded columns
    station_df = station_df[["name", "federalState", "location.latitude", "location.longitude",
                            "productLine.type", "productLine.segment", "platforms", "stationManagement.name",
                            "szentrale.name", "operator.id", "operator.name", "regionalbereich.name"]]

    # Rename columns
    new_column_names = {
        "location.latitude": "latitude",
        "location.longitude": "longitude",
        "productLine.type": "type",
        "productLine.segment": "segment",
        "stationManagement.name": "stationManagement",
        "szentrale.name": "controlCenter",
        "operator.id": "operator",
        "operator.name": "operatorShort",
        "regionalbereich.name": "regionalSector"
    }
    station_df.rename(columns=new_column_names, inplace=True)

    print(station_df)

    print(f"Kept {len(needed_stations)} stations")
    station_df.to_csv(data_path + "/stations/processed/stations.csv")


if __name__ == "__main__":
    '''This only keeps the stations we need for the network and some possibly interesting attributes'''
    preprocess_stations()
