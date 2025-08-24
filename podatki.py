from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv

def time_to_seconds(time_str):
    """Convert MM:SS.sss or +SS.sss to total seconds."""
    if "+" in time_str:  # Relative time (e.g., "+1.474")
        return float(time_str.replace("+", "").strip())
    elif ":" in time_str:  # Full time (e.g., "40:24.740")
        minutes, rest = time_str.split(":")
        seconds = float(rest)
        return int(minutes) * 60 + seconds
    else:
        return float(time_str.strip())  # In case it's just seconds


# Setup Chrome options
options = webdriver.ChromeOptions()
# options.add_argument("--headless")  # Enable this only after debugging
options.add_argument("--disable-blink-features=AutomationControlled")  # Prevent bot detection
options.add_argument("start-maximized")  # Open in full-screen

# Start WebDriver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Leto + države
leta = ["2024", "2023", "2022"]
drzave = [
    "mal","tha","aus","jpn","ina","emi","rsm","ara","aut",
    "gbr","ger","ned","ita","cat","fra","spa","ame","por","qat"
]

# v CSV appenda dirke
with open("motogp_rezultati.csv", mode="a", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    
    for leto in leta:
        for drzava in drzave:
            url = f"https://www.motogp.com/en/gp-results/{leto}/{drzava}/motogp/rac/classification"
            print(f"Scraping: {url}")

            # odpre spletno stran
            driver.get(url)
            time.sleep(5)

            try:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.TAG_NAME, "table"))
                )
                print(f"Page loaded successfully for {drzava} ({leto})!")
            except Exception as e:
                print(f"Error loading page for {drzava} ({leto}): {e}")
                continue  

            try:
                rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

                if rows:
                    print(f"Found {len(rows)} results for {drzava} ({leto})")

                    # doda v CSV header za vsako dirko
                    writer.writerow(["@", "dirka", drzava, leto])

                    base_time = None
                    for row in rows:
                        stolpec = row.find_elements(By.CSS_SELECTOR, "td")

                        time_str = stolpec[5].text.strip()
                        race_time = time_to_seconds(time_str)

                        if base_time is None:  # base time za prvega voznika
                            base_time = race_time

                        if "+" in time_str:
                            race_time = base_time + race_time  # dodamo gap time vozniku ki ni prvi

                        # če niso pridobili nobenih točk nastavimo na 0
                        tocke = stolpec[2].text.strip()
                        if tocke == "":
                            tocke = "0"

                        # pridobimo podatke
                        data = [
                            stolpec[1].text.strip(),  # mesto
                            tocke,  # točke
                            stolpec[3].text.strip().split('\n')[-1],  # voznik
                            stolpec[4].text.strip(),  # ekipa
                            f"{race_time:.3f}",  # čas v sekundah
                        ]

                        # dodamo v CSV
                        writer.writerow(data)
                        print(data)  

                else:
                    print(f"No classification data found for {drzava} ({leto}).")

            except Exception as e:
                print(f"Error extracting results for {drzava} ({leto}): {e}")


driver.quit()
