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
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import requests as r
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
    return round(random.uniform(0.2, 2.5), 2)


class ZugfinderWebdriver:
    def __init__(self):
        # Configure driver
        self.options = Options()
        self.profile = webdriver.FirefoxProfile()
        self.profile.set_preference("browser.download.folderList", 2)
        self.profile.set_preference("browser.download.manager.showWhenStarting", False)
        self.profile.set_preference("browser.download.dir", data_path + "/temp")
        self.profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/octet-stream")
        self.options.profile = self.profile

        # login
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
    stations= stations.loc[:, ~stations.columns.str.contains('^Unnamed')]
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


def find_suitable_trains(d):
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
                    num_of_rows = 0
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
                    counter += 1
                    continue
            finally:
                try:
                    os.remove(data_path + "/temp/zugfinder_export.csv")
                except OSError:
                    pass
                break

        print(f"Processed station {name}")
            
    check_trains = copy.deepcopy(trains)

    # Check if both start and end-station are in germany
    for train in check_trains:
        counter = 0
        while counter <= 3:
            try:
                flags = []
                d.driver.get(f"https://www.zugfinder.net/en/train-{train.replace(' ', '_')}")
                flag_container = d.driver.find_element(
                    By.XPATH, "/ html / body / div[1] / div[1] / div[2] / div[3] / div[2] / h2 / span[1]")
                flag_elements = flag_container.find_elements(By.CSS_SELECTOR, "*")
                for element in flag_elements:
                    flags.append(element.get_attribute("src"))
                if len(flags) > 1 and len(flags) == 0:
                    trains.remove(train)
                break
            except TimeoutException:
                counter += 1
                pass
            except NoSuchElementException:
                trains.remove(train)
                break

        random_wait()

    print(f"Found {len(trains)} suitable trains")

    with open(data_path + "/trains/trains.csv", "a") as output:
        writer = csv.writer(output)
        writer.writerow(trains)


def scrape_delay_data(d):
    print("**Looking for delay data**")
    trains = []
    with open(data_path + "/trains/trains.csv", "r") as possible_trains:
        reader = csv.reader(possible_trains)
        for row in reader:
            for col in row:
                trains.append(col)

    for train in trains[:2]:
        header_written = False

        formatted_train = train.replace(' ', '_')
        d.driver.get(f"https://www.zugfinder.net/en/train-{formatted_train}-720")

        current_date = root_date
        end_date = current_date - datetime.timedelta(days=2)

        punctuality_table = d.driver.find_element(By.XPATH, '/ html / body / div / div[1] / div[2] / div[11] / div[1] / table[1] / tbody')

        while current_date >= end_date:
            try:
                str_date = current_date.strftime('%Y-%m-%d')
                table_el = punctuality_table.find_element(By.XPATH, f'//*[@id="{str_date}"]')
                d.driver.execute_script("arguments[0].click();", table_el)

                punctuality_form = WebDriverWait(d.driver, 1000).until(EC.presence_of_element_located((By.XPATH, f'//*[@id="form_{str_date}"]')))
                punctuality_table = punctuality_form.find_element(By.CSS_SELECTOR, "table")

                rows = punctuality_table.find_elements(By.CSS_SELECTOR, "tr")

                # Build the dataframe
                delay = [str_date]

                # Get data
                for row in rows:
                    cols = row.find_elements(By.CSS_SELECTOR, "td")
                    if not header_written:
                        # Create Headers
                        header = ["date"]
                        header.append(cols[1].text.replace(' ', '_') + ".in")
                        header.append(cols[1].text.replace(' ', '_') + ".out")

                        # Build empty dataframe
                        delay_df = pd.DataFrame(columns=header)
                        delay_df = delay_df[1:]
                        delay_df.set_index("date", inplace=True)

                    for c in cols[2:3]:
                        m = re.search("^.*?\([^\d]*(\d+)[^\d]*\).*$", c.text)
                        if m is not None:
                            if c == cols[2]:
                                delay_df.at[str_date, f"{cols[1].text.replace(' ', '_')}.in"] = float(m.group(1))
                            else:
                                delay_df.at[str_date, f"{cols[1].text.replace(' ', '_')}.out"] = float(m.group(1))

                header_written = True
                current_date -= datetime.timedelta(days=1)

                time.sleep(random_wait())

            except NoSuchElementException:
                print("Element not found")
                pass

        # Fill empty elements
        delay_df.fillna(0.0, inplace=True)
        delay_df.to_csv(data_path + f"/delay/raw/{formatted_train}.csv")
        print(f"Processed {formatted_train}")


w = ZugfinderWebdriver()
scrape_delay_data(w)
