import os

import pandas as pd
from dotenv import load_dotenv

load_dotenv()
data_path = os.environ.get("DATA_PATH")


'''The station and delay data has different formats for the station names, this translates the station names'''
def delay_format_to_station(station):
    # Strip away the .in and .out behind station names
    ret = station.replace("_", " ").split(".")[0]

    # These a various inconsistencies I noticed
    ret = (ret.replace("Hauptbahnhof", "Hbf").replace("(", " (").replace(")Hbf", ") Hbf").replace(" (Rheinl) ", " ")
            .replace(" Gl", "").replace("(M)", "am Main").replace("Fernbf", "Fernbahnhof")
            .replace("Frankfurt (Main)West", "Frankfurt (Main) West")
            .replace("Hannover Messe/Laatzen", "Hannover-Messe / Laatzen")
            .replace("Wittenberg Hbf", "Wittenberg Hauptbahnhof").replace("Niebüll neg", "Niebüll"))

    return ret


'''Some formating of the stations make it hard to match them to the corresponding delay entries'''
def format_station_names(df):
    for station in df["name"].values:
        if " Pbf" in station:
            index = df.loc[(df['name'] == station)].index[0]
            new_name = station.replace(" Pbf", "")
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
    result = pd.DataFrame(columns=["source", "target", "sumDelay", "maxDelay", "minDelay", "stdDev", "n", "connections"])
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
                #exists = result.loc[(result["source"] == outgoing_f) & (result["target"] == incoming_f)].any().all()

                temp = delay_df[incoming] - delay_df[outgoing]
                sum_delay = temp.sum()
                count_delay = temp.count()
                min_delay = temp.min()
                max_delay = temp.max()
                std_dev_delay = round(temp.var(), 5)

                # Skip possible self loops
                if outgoing_f == incoming_f:
                    continue

                if index is None:
                    print(f"{outgoing_f} -> {incoming_f} added")
                    result.loc[len(result.index)] = \
                        [outgoing_f, incoming_f, sum_delay, max_delay, min_delay, std_dev_delay, count_delay, 1.0]
                else:
                    #index = result.index[(result["source"] == outgoing_f) & (result["target"] == incoming_f)].to_list()
                    # Sum of delays (for avg)
                    result.loc[index, "sumDelay"] += sum_delay

                    # Maximum delay
                    tmp = result.loc[index, "maxDelay"]
                    result.loc[index, "maxDelay"] = max(max_delay, tmp)

                    # Minimum delay
                    tmp = result.loc[index, "minDelay"]
                    result.loc[index, "minDelay"] = min(min_delay, tmp)

                    # Standard Deviation
                    result.loc[index, "stdDev"] += std_dev_delay

                    # Num of delay values (for avg)
                    result.loc[index, "n"] += count_delay

                    # Num of trains that use this connection
                    result.loc[index, "connections"] += 1.0

                    print(f"{outgoing_f} -> {incoming_f} updated")
            else:
                raise AttributeError

    result["avgDelay"] = round(result["sumDelay"] / result["n"], 5)
    result["stdDev"] = round(result["stdDev"]**(1/2), 5)
    result.drop(["sumDelay", "n"], axis=1, inplace=True)
    result.to_csv(data_path + "/edges/connection_list.csv", index=False)
    print(f"Constructed {len(result.index)} edges")


'''Small helper function to check for possible duplicates'''
def check_duplicates():
    df = pd.read_csv(data_path + "/edges/connection_list.csv", index_col=False)
    df2 = df[df.duplicated(["source", "target"], keep=False)]
    df2.to_csv(data_path + "/duplicates.csv")


def add_station_delay():
    print("**Calculating station delay**")
    station_df = pd.read_csv(data_path + "/stations/processed/stations.csv", index_col=False)
    station_df["delayDiff"] = 0
    station_df["delayNum"] = 0
    station_names = station_df['name'].values.tolist()

    all_files = os.listdir(data_path + "/delay/processed")
    csv_files = list(filter(lambda f: f.endswith(".csv"), all_files))

    for file in csv_files:
        delay_df = pd.read_csv(data_path + "/delay/processed/" + file, index_col=False)

        columns = delay_df.columns.to_list()[1:]

        for incoming, outgoing in zip(columns[0::2], columns[1::2]):
            station_delay = delay_df[outgoing].sum() - delay_df[incoming].sum()
            station_entries = delay_df[outgoing].count()

            formated_station = delay_format_to_station(incoming)
            index = station_df.index[(station_df["name"] == formated_station)].to_list()[0]

            station_df.loc[index, "delayDiff"] += station_delay
            station_df.loc[index, "delayNum"] += station_entries

    station_df["delay"] = station_df["delayDiff"] / station_df["delayNum"]
    station_df.drop(["delayDiff", "delayNum"], axis=1, inplace=True)
    station_df.to_csv(data_path + "/stations/processed/stations.csv", index=False)


if __name__ == "__main__":
    '''This only keeps the stations we need for the network and some possibly interesting attributes'''
    process_stations()

    '''Builds an edge list with some attributes for the network'''
    process_delay()

    '''Calculates the average delay the station causes'''
    add_station_delay()