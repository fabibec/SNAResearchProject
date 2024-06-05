import copy
import csv
import datetime
import os
import re
import random
import time

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import requests as r
from requests_ratelimiter import LimiterSession
import pandas as pd

from ofunctions.network import set_ip_version
from dotenv import load_dotenv

load_dotenv()
data_path = os.environ.get("DATA_PATH")
driver_path = os.environ.get("DRIVER_PATH")
zugfinder_mail = os.environ.get("ZF_MAIL")
zugfinder_pw = os.environ.get("ZF_PW")
root_date = datetime.date(2024, 5, 30)


def random_wait():
    return round(random.uniform(5.0, 12.5), 2)


class ZugfinderWebdriver:
    def __init__(self):
        # Configure driver
        self.options = Options()
        self.options.add_argument("--headless")
        self.profile = webdriver.FirefoxProfile()
        self.profile.set_preference("browser.download.folderList", 2)
        self.profile.set_preference("browser.download.manager.showWhenStarting", False)
        self.profile.set_preference("browser.download.dir", data_path + "/temp")
        self.profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/octet-stream")
        self.options.profile = self.profile

        # login
        print("**Performing Login**")
        self.driver = webdriver.Firefox(self.options)
        self.driver.get('https://www.zugfinder.net/en/login')
        login_form = self.driver.find_element(By.ID, "bewertung")
        mail_field = login_form.find_element(By.NAME, "email")
        pw_field = login_form.find_element(By.NAME, "pass")
        mail_field.send_keys(zugfinder_mail)
        pw_field.send_keys(zugfinder_pw)
        login_form.submit()
        time.sleep(2.0)

    def __del__(self):
        self.driver.quit()


def get_list_of_german_train_stations():
    set_ip_version(4)
    print("**Listing German Train Stations**")
    response = r.get("https://v6.db.transport.rest/stations")
    raw_data = response.json()
    stations = pd.json_normalize(raw_data.values())

    # Remove unneeded columns
    stations.drop(list(stations.filter(regex='^localServiceStaff.*')), axis=1, inplace=True)
    stations.drop(list(stations.filter(regex='^DBinformation.*')), axis=1, inplace=True)
    stations.drop(list(stations.filter(regex='^address.*')), axis=1, inplace=True)
    stations.drop(list(stations.filter(regex='^timeTableOffice.*')), axis=1, inplace=True)
    stations = stations.loc[:, ~stations.columns.str.contains('^Unnamed')]
    stations.drop('type', axis=1, inplace=True)

    stations.rename(columns={'productLine.productLine': 'productLine.type'}, inplace=True)

    stations = stations[
        stations['productLine.type'].isin(['Knotenbahnhof', 'Zubringerbahnhof', 'Metropolbahnhof'])]

    # drop duplicate stations based on id
    stations.drop_duplicates(subset=['id'], keep='first', inplace=True)

    # set station id as index
    stations.set_index('id', inplace=True)

    print(f"Found {len(stations.index)} stations")

    stations.to_csv(data_path + "/stations/raw/stations.csv")


def append_num_of_platforms():
    # Append number of platform by using DB-API
    try:
        station_df = pd.read_csv(data_path + "/stations/raw/stations.csv")
    except FileNotFoundError:
        print("Base Dataframe not found")
        return

    station_df["platforms"] = pd.Series(dtype=int)

    session = LimiterSession(per_second=9)
    session.headers.update({'DB-Client-ID': os.environ.get("DB_CLIENT_ID")})
    session.headers.update({'DB-Api-Key': os.environ.get("DB_CLIENT_SEC")})
    session.headers.update({'accept': 'application/vnd.de.db.ris+json'})

    for index, row in station_df.iterrows():
        platforms = []
        main_station_id = row['id']
        response = session.get(
            f"https://apis.deutschebahn.com/db-api-marketplace/apis/ris-stations/v1/platforms/{main_station_id}" +
            "?includeSectors=false" +
            "&includeAccessibility=false&includeOperational=false&includeSubPlatforms=false")

        data = response.json()["platforms"]

        for d in data:
            if d["name"] not in platforms:
                platforms.append(d["name"])

            for lp in d["linkedPlatforms"]:
                if lp not in platforms:
                    platforms.append(d["name"])

        station_df.at[index, "platforms"] = len(platforms)
        print("Processed " + row['name'])

    station_df.to_csv(data_path + "/stations/raw/stations.csv")


def scrape_trains(d):
    print("**Looking for suitable Trains**")
    station_names = pd.read_csv(data_path + "/stations/raw/stations.csv")
    station_names = station_names['name'].tolist()
    date = root_date.strftime("%Y%m%d")
    trains = []

    # Collect some train lines
    for name in station_names:
        counter = 0
        while counter <= 3:
            try:
                d.driver.get(f"https://www.zugfinder.net/en/stationboard-{name.replace(' ', '_')}-{date}-dep")
                export_link = d.driver.find_element(By.CSS_SELECTOR, "[title=\"Export table as CSV\"]")
                random_wait()
                export_link.click()
            except NoSuchElementException:
                pass
            else:
                try:
                    with open(data_path + "/temp/zugfinder_export.csv", "r") as file:
                        reader = csv.reader(file)
                        num_of_rows = sum(1 for row in reader)
                        for row in reader:
                            if row[3] in station_names:
                                trains.append(row[0])

                    if num_of_rows > 1:
                        os.rename(data_path + "/temp/zugfinder_export.csv",
                                  data_path + f"/stationTimetables/{name.replace(' ', '_')}.csv")

                    trains = list(dict.fromkeys(trains))
                except FileNotFoundError:
                    random_wait()
                    counter += 1
                    continue
            finally:
                try:
                    os.remove(data_path + "/temp/zugfinder_export.csv")
                except OSError:
                    pass
                break

        print(f"Processed station {name}")


def find_suitable_trains(d):
    print("**Removing trains that are also driving to outside of Germany**")
    all_files = os.listdir(data_path + "/stationTimetables")
    csv_files = list(filter(lambda f: f.endswith(".csv"), all_files))

    all_trains = []

    for file in csv_files:
        with open(data_path + "/stationTimetables/" + file) as station:
            reader = csv.reader(station)
            next(reader, None)
            for row in reader:
                all_trains.append(row[0])

    # Remove duplicates
    all_trains = list(set(all_trains))
    print(f"Checking {len(all_trains)} trains")

    check_trains = copy.deepcopy(all_trains)

    # Check if both start and end-station are in germany
    for train in check_trains:
        try:
            # Trains like ICE11.be or IC9634.nl are not allowed
            train.split(".")[1]
            all_trains.remove(train)
            continue
        except IndexError:
            pass
        counter = 0
        while counter <= 3:
            try:
                flags = []
                d.driver.get(f"https://www.zugfinder.net/en/train-{train.replace(' ', '_')}")
                flag_container = d.driver.find_element(
                    By.XPATH, "/ html / body / div / div[1] / div[2] / div[3] / div[2] / h2 / span[1]")
                flag_elements = flag_container.find_elements(By.CSS_SELECTOR, "img")
                print(f"Train: {train} | {len(flag_elements)} Countries")

                for element in flag_elements:
                    flags.append(element.get_attribute("src"))

                if len(flag_elements) > 1 or len(flag_elements) == 0:
                    all_trains.remove(train)
                    print(f"Removed {train}")
                break
            except TimeoutException:
                counter += 1
                pass
            except NoSuchElementException:
                all_trains.remove(train)
                print(f"Removed {train} | No such element")
                break

        random_wait()

    all_trains = list(set(all_trains))
    print(f"Found {len(all_trains)} suitable trains")

    with open(data_path + "/trains/trains.csv", "w") as output:
        writer = csv.writer(output)
        for train in all_trains:
            writer.writerow([train])


def scrape_delay_data(d, start_index, go_back_days=60):
    print("**Looking for delay data**")
    print(f"Start at index {start_index}.")

    trains = []
    with open(data_path + "/trains/trains.csv", "r") as possible_trains:
        reader = csv.reader(possible_trains)
        for row in reader:
            for col in row:
                trains.append(col)

    for tnum, train in enumerate(trains[start_index:]):
        # Saving station information in order to recreate the journey later
        journey = []

        # Build empty dataframe
        delay_df = pd.DataFrame(columns=["date"])
        delay_df.set_index("date", inplace=True)

        formatted_train = train.replace(' ', '_')
        d.driver.get(f"https://www.zugfinder.net/en/train-{formatted_train}-730")

        current_date = root_date
        end_date = current_date - datetime.timedelta(days=go_back_days)

        punctuality_table = d.driver.find_element(By.XPATH,
            "/ html / body / div / div[1] / div[2] / div[11] / div[1] / table[1] / tbody")

        while current_date > end_date:
            try:
                str_date = current_date.strftime('%Y-%m-%d')

                table_el = punctuality_table.find_element(By.XPATH, f'//*[@id="{str_date}"]')
                d.driver.execute_script("arguments[0].click();", table_el)

                punctuality_form = WebDriverWait(d.driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, f'//*[@id="form_{str_date}"]')))
                punctuality_table = punctuality_form.find_element(By.CSS_SELECTOR, "table")

                rows = punctuality_table.find_elements(By.CSS_SELECTOR, "tr")

                # Get data
                for num, row in enumerate(rows):
                    cols = row.find_elements(By.CSS_SELECTOR, "td")

                    s = cols[1].text.replace(' ', '_')

                    if s == "Zu_viele_Abfragen_in_zu_kurzer_Zeit._Bitte_bestätige,_dass_du_ein_Mensch_bist!":
                        print(f"Bot-Detection. Restart at index {tnum + start_index}.")
                        bypass_bot_detection(d)
                        return tnum + start_index

                    if s not in journey:
                        journey.insert(num, s)

                    for c in cols[2:4]:
                        # Search for delay in minutes
                        m = re.search("^.*?\([^\d]*(\d+)[^\d]*\).*$", c.text)

                        # Build column name
                        if c == cols[2]:
                            column_name = f"{cols[1].text.replace(' ', '_')}.in"
                        else:
                            column_name = f"{cols[1].text.replace(' ', '_')}.out"

                        # Add new column if needed
                        if column_name not in delay_df:
                            delay_df[column_name] = pd.Series(dtype=int)

                        # Add data if present
                        if m is not None:
                            delay_df.loc[str_date, column_name] = int(m.group(1))
                        else:
                            delay_df.loc[str_date, column_name] = 0

                current_date -= datetime.timedelta(days=1)

                time.sleep(2.0)

            except NoSuchElementException:
                current_date -= datetime.timedelta(days=1)
                pass

        # Fill empty elements
        delay_df.fillna(0, inplace=True)

        # Use Journey information to correctly rearrange the station order
        rearranged_columns = []
        for s in journey:
            rearranged_columns.append(s + ".in")
            rearranged_columns.append(s + ".out")

        delay_df.to_csv(data_path + f"/delay/raw/{formatted_train}.csv", columns=rearranged_columns)
        print(f"Processed {formatted_train}")

    return -1


def bypass_bot_detection(d):
    d.driver.get(f"https://www.zugfinder.net/en/train-ICE_1679")
    test_date = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    table_el = d.driver.find_element(By.XPATH, f'//*[@id="{test_date}"]')
    d.driver.execute_script("arguments[0].click();", table_el)
    not_a_bot_link = WebDriverWait(d.driver, 10).until(
        EC.presence_of_element_located((By.XPATH,
            "/html/body/div/div[1]/div[2]/div[11]/div[1]/table[1]/tbody/tr[6]/td/form/table/tr[1]/td[2]/a")))
    d.driver.execute_script("arguments[0].click();", not_a_bot_link)
    # Switching to popup window

    question = WebDriverWait(d.driver, 1000).until(
        EC.presence_of_element_located((By.XPATH,
            "/html/body/div/div[1]/div[3]/div/form/fieldset/input")))

    attempts = 0
    while attempts <= 5:
        try:
            d.driver.execute_script("arguments[0].setAttribute('value', '8');", question)
            break
        except StaleElementReferenceException:
            attempts += 1
    time.sleep(2)
    check = d.driver.find_element(By.XPATH, "/html/body/div/div[1]/div[3]/div/form/input")
    check.click()
    #d.driver.execute_script("arguments[0].click();", check)
    time.sleep(1)
    print("Bot-Detection solved! Will continue.")

if __name__ == "__main__":
    # w = ZugfinderWebdriver()
    get_list_of_german_train_stations()
    # find_suitable_trains(w)

    append_num_of_platforms()
'''
    up_to = 49
    while up_to != -1:
        try:
            up_to = scrape_delay_data(w, up_to)
        except TimeoutError:
            time.sleep(120)
            print("Timeout, wait 2 Minutes")
            continue

    w.driver.quit()'''
