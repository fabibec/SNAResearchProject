import os
from statistics import variance

import pandas as pd
from dotenv import load_dotenv

load_dotenv()
data_path = os.environ.get("DATA_PATH")


def delay_format_to_station(station):
    # The station and delay data has different formats for the station names, this translates the station names

    # Strip away the .in and .out behind station names
    ret = station.replace("_", " ").split(".")[0]

    # These a various inconsistencies I noticed
    ret = (ret.replace("Hauptbahnhof", "Hbf").replace("(", " (").replace(")Hbf", ") Hbf").replace(" (Rheinl) ", " ")
            .replace(" Gl", "").replace("(M)", "am Main").replace("Fernbf", "Fernbahnhof")
            .replace("Frankfurt (Main)West", "Frankfurt (Main) West")
            .replace("Hannover Messe/Laatzen", "Hannover-Messe / Laatzen")
            .replace("Wittenberg Hbf", "Wittenberg Hauptbahnhof").replace("Niebüll neg", "Niebüll"))

    return ret


def format_station_names(df):
    # Some formating of the stations make it hard to match them to the corresponding delay entries
    for station in df["name"].values:
        if " Pbf" in station:
            index = df.loc[(df['name'] == station)].index[0]
            new_name = station.replace(" Pbf", "")
            print(f"Renamed {station} -> {new_name} in stations")
            df.loc[index, "name"] = new_name
        if " Hauptbahnhof" in station:
            index = df.loc[(df['name'] == station)].index[0]
            new_name = station.replace(" Hauptbahnhof", " Hbf")
            print(f"Renamed {station} -> {new_name} in stations")
            df.loc[index, "name"] = new_name


def process_stations():
    print("**Processing Stations**")
    # Open station as dataframe
    station_df = pd.read_csv(data_path + "/stations/raw/stations.csv")
    format_station_names(station_df)

    # Once again kick out the duplicates
    station_df.drop_duplicates(keep='first', inplace=True)

    known_stations = station_df['name'].to_list()

    # Get all delay files
    all_files = os.listdir(data_path + "/delay/raw")
    csv_files = list(filter(lambda f: f.endswith(".csv"), all_files))

    needed_stations = []
    omission_dict = {}

    for file in csv_files:
        print("Processing " + file)

        delay_df = pd.read_csv(data_path + "/delay/raw/" + file)
        header = delay_df.columns.to_list()[1:]

        # Get stations from header
        for col in header:
            # Strip away the .in and .out behind station names
            formatted_col = delay_format_to_station(col)
            known_stop = True if formatted_col in known_stations else False

            if formatted_col not in needed_stations:
                if known_stop:
                    needed_stations.append(formatted_col)
                else:
                    try:
                        omission_dict[formatted_col] += 1
                    except KeyError:
                        omission_dict[formatted_col] = 1
                    delay_df.drop(col, axis=1, inplace=True)
                    print(f"Omitted {formatted_col} from {file}")

        # Save change to delay dfs
        delay_df.to_csv(data_path + "/delay/processed/" + file, index=False)

    print({k: v for (k, v) in omission_dict.items() if v > 0})

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

    print(f"Kept {len(station_df.index)} stations")
    station_df.to_csv(data_path + "/stations/processed/stations.csv", index=False)


def process_delay():
    print("**Process Delay**")
    # Result dataframe
    result = pd.DataFrame(columns=["source", "target", "sumDelay", "numTrains", "numDelayedTrains"])
    result.set_index(["source", "target"], drop=False, inplace=True, verify_integrity=True)

    # Get all delay files
    all_files = os.listdir(data_path + "/delay/processed")
    csv_files = list(filter(lambda f: f.endswith(".csv"), all_files))

    for file in csv_files:
        delay_df = pd.read_csv(data_path + "/delay/processed/" + file, index_col=False)

        columns = delay_df.columns.to_list()[2:]

        for outgoing, incoming in zip(columns[0::2], columns[1::2]):
            if outgoing is not None and incoming is not None:
                outgoing_f = delay_format_to_station(outgoing)
                incoming_f = delay_format_to_station(incoming)

                try:
                    index = result.index[(result["source"] == outgoing_f) & (result["target"] == incoming_f)].to_list()[0]
                except IndexError:
                    index = None

                temp = delay_df[(delay_df[incoming] > -1) & (delay_df[outgoing] > - 1)]
                num_trains = temp[incoming].count()

                delayed = temp[(temp[incoming] > 0) | (temp[outgoing] > 0)]
                num_delayed_trains = delayed[incoming].count()

                temp = temp.replace(-1, 0)
                sum_delay = temp[incoming].sum() - temp[outgoing].sum()

                # Skip possible self loops
                if outgoing_f == incoming_f:
                    continue

                if index is None:
                    result.loc[len(result.index)] = [outgoing_f, incoming_f, sum_delay, num_trains, num_delayed_trains]
                else:
                    result.loc[index, "sumDelay"] += sum_delay

                    result.loc[index, "numTrains"] += num_trains

                    result.loc[index, "numDelayedTrains"] += num_delayed_trains
            else:
                raise AttributeError

    result.to_csv(data_path + "/edges/connection_list.csv", index=False)
    print(f"Constructed {len(result.index)} edges")


def check_duplicates():
    # Small helper function to check for possible duplicates
    df = pd.read_csv(data_path + "/edges/connection_list.csv", index_col=False)
    df2 = df[df.duplicated(["source", "target"], keep=False)]
    df2.to_csv(data_path + "/duplicates.csv")


def add_station_delay():
    print("**Calculating station delay**")
    station_df = pd.read_csv(data_path + "/stations/processed/stations.csv", index_col=False)
    new_columns = ["sumInDelay", "sumOutDelay", "numTrainsIn", "numTrainsOut",
                   "numDelayedTrainsIn", "numDelayedTrainsOut", "stdDevIn", "stdDevOut"]
    for col in new_columns:
        station_df[col] = 0

    station_names = station_df['name'].values.tolist()

    all_files = os.listdir(data_path + "/delay/processed")
    csv_files = list(filter(lambda f: f.endswith(".csv"), all_files))

    for file in csv_files:
        delay_df = pd.read_csv(data_path + "/delay/processed/" + file, index_col=False)

        columns = delay_df.columns.to_list()[1:]

        for incoming, outgoing in zip(columns[0::2], columns[1::2]):
            # Getting the correct index
            formated_station = delay_format_to_station(incoming)
            if formated_station in station_names:
                index = station_df.index[(station_df["name"] == formated_station)].to_list()[0]
            else:
                print(formated_station)
                continue

            # Handle incoming values
            station_df.loc[index, "sumInDelay"] += delay_df[delay_df[incoming] > -1][incoming].sum()
            station_df.loc[index, "numTrainsIn"] += delay_df[delay_df[incoming] > -1][incoming].count()
            station_df.loc[index, "numDelayedTrainsIn"] += delay_df[delay_df[incoming] > 0][incoming].count()

            # Handle outgoing values
            station_df.loc[index, "sumOutDelay"] += delay_df[delay_df[outgoing] > -1][outgoing].sum()
            station_df.loc[index, "numTrainsOut"] += delay_df[delay_df[outgoing] > -1][outgoing].count()
            station_df.loc[index, "numDelayedTrainsOut"] += delay_df[delay_df[outgoing] > 0][outgoing].count()

            # Calculate standard deviation | adding up variances and sqrt at the end
            std_in = delay_df[delay_df[incoming] > -1][incoming].to_list()
            if len(std_in) < 2:
                std_in = [0, 0]

            std_out = delay_df[delay_df[outgoing] > -1][outgoing].to_list()
            if len(std_out) < 2:
                std_out = [0, 0]

            station_df.loc[index, "stdDevIn"] += float(variance(std_in))
            station_df.loc[index, "stdDevOut"] += float(variance(std_out))

    # Finishing up the stdDev
    station_df["stdDevIn"] = station_df["stdDevIn"].pow(1. / 2)
    station_df["stdDevOut"] = station_df["stdDevOut"].pow(1. / 2)

    station_df.to_csv(data_path + "/stations/processed/stations.csv", index=False)


def calculate_regression_data():
    nodes = pd.read_csv(data_path + "/nodes.csv", index_col=False)
    nodes.set_index("name")
    nodes["avgDelayIn"] = round(nodes["sumInDelay"] / nodes["numTrainsIn"], 4)
    nodes["avgDelayOut"] = round(nodes["sumInDelay"] / nodes["numTrainsIn"], 4)
    nodes["pureDelayIn"] = round(nodes["sumInDelay"] / nodes["numDelayedTrainsIn"], 4)
    nodes["pureDelayOut"] = round(nodes["sumInDelay"] / nodes["numDelayedTrainsOut"], 4)

    nodes["punctuality"] = round((nodes["numDelayedTrainsIn"] + nodes["numDelayedTrainsOut"]) /
                                 (nodes["numTrainsIn"] + nodes["numTrainsOut"]), 4)
    nodes.to_csv(data_path + "/nodes.csv", index=False)

    edges = pd.read_csv(data_path + "/edges.csv", index_col=False)
    edges["avgDelay"] = round(edges["sumDelay"] / edges["numTrains"], 4)
    edges["punctuality"] = round(edges["numDelayedTrains"] / edges["numTrains"], 4)
    edges.to_csv(data_path + "/edges.csv", index=False)


if __name__ == "__main__":
    '''This only keeps the stations we need for the network and some possibly interesting attributes'''
    process_stations()

    '''Builds an edge list with some attributes for the network'''
    process_delay()

    '''Calculates the average delay the station causes'''
    add_station_delay()

    '''Calculate the final delay metrics for the linear regression'''
    calculate_regression_data()
