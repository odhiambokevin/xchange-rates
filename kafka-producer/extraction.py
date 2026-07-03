import json
import os
import re
import random
import time

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

#standardize currency labels
def standardize_currency(currency_str):
    if not currency_str:
        return "UNKNOWN"
    clean = str(currency_str).strip().upper()
    
    #mapping rules for common variations
    mapping = {
        "US DOLLAR": "USD",
        "UNITED STATES DOLLAR": "USD",
        "STERLING POUND": "GBP",
        "EURO": "EUR",
    }
    return mapping.get(clean, clean)

#initialize selenium webdriver only when needed
def get_selenium_driver():
    options = webdriver.ChromeOptions()
    
    #configure for brave and other chromium based browsers    
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    service = Service(ChromeDriverManager().install())

    #launching the actual session
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def parse_custom_divs(source, selectors):
    soup = BeautifulSoup(source, 'html.parser')
    results = []
    
    container = soup.find(class_=selectors.get("container_class"))
    if not container:
        return results
        
    rows = container.find_all(class_=selectors.get("row_class"))
    for row in rows:
        # NOTE: You will need to adjust the exact text/tag extractions 
        # below based on the actual inner structure of firm1's divs.
        text_elements = [el.text.strip() for el in row.find_all(string=True) if el.strip()]
        print(f"Found elements for row: {text_elements}")
        if len(text_elements) >= 3:
            results.append({
                "currency": standardize_currency(text_elements[0]),
                "buy": text_elements[1],
                "sell": text_elements[2]
            })
    return results

def parse_dynamic_ticker(source, selectors):
    soup = BeautifulSoup(source, 'html.parser')
    results = []
    
    container = soup.find(id=selectors.get("container_id"))
    if not container:
        return results
        
    items = container.find_all(selectors.get("row_element"))
    
    for item in items:
        # 1. Extract the raw text from the 'li' (e.g., "USD/KES: Buying: 127.2 , Selling: 132.65")
        raw_text = item.get_text(separator=" ").strip()
        
        try:
            #extract the currency - everything before the colon)
            currency_pair = raw_text.split(":")[0].strip() #results in USD/KES
            #normalize to just the base currency if needed e.g."USD/KES" to "USD"
            currency = currency_pair.split("/")[0] 
            
            # 3. Use regular expressions to extract the numeric rates safely
            # Looks for numeric patterns following "Buying" and "Selling"
            buy_match = re.search(r'Buying:\s*([\d\.]+)', raw_text, re.IGNORECASE)
            sell_match = re.search(r'Selling:\s*([\d\.]+)', raw_text, re.IGNORECASE)
            
            if buy_match and sell_match:
                results.append({
                    "currency": standardize_currency(currency),
                    "buy": buy_match.group(1),
                    "sell": sell_match.group(1)
                })
        except Exception as e:
            print(f"Skipping malformed ticker item: '{raw_text}'. Error: {e}")
            continue
    return results


def parse_api_endpoint(url, selectors):
    results = []
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        #incase root key changes dynamically, we iterate through keys or adjust to look for the payload
        fields = selectors.get("fields", {})
        
        #cases where data is nested under a timestamp/dynamic root key
        payload = data
        if selectors.get("root_key") in data:
            payload = data[selectors.get("root_key")]
        elif isinstance(data, dict) and len(data) == 1:
            # If the root key is truly random/dynamic, grab the first value
            payload = list(data.values())[0]

        #expecting payload to be a list of currency objects
        if isinstance(payload, list):
            for item in payload:
                results.append({
                    "currency": standardize_currency(item.get(fields.get("currency_code"))),
                    "buy": item.get(fields.get("buy_rate")),
                    "sell": item.get(fields.get("sell_rate"))
                })
    except Exception as e:
        print(f"Error parsing API endpoint: {e}")
    return results

def main():
    input_json = 'firms.json'
    
    #check if the file exists before reading
    if os.path.exists(input_json):
        with open(input_json, 'r') as file:
            firms = json.load(file)
    else:
        print(f"Error: The file '{input_json}' was not found.")
        return
    
    all_extracted_data = [] 
    driver = None

    for firm in firms:
        print(f"{'_'*50} Processing {firm['firm']} {'_'*50}\n")
        source_code = ""
        rates = []

        #fetch source code selenium or requests
        if firm.get("render_js"):
            if not driver:
                driver = get_selenium_driver()
            try:
                driver.get(firm["url"])
                
                if firm["parser_type"] == "dynamic_ticker":
                    try:
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.ID, "stocks-ticker"))
                        )
                    except Exception:
                        print(f"\nTimed out waiting for ticker on {firm['firm']}")
                        continue    
                else:
                    time.sleep(2)

                source_code = driver.page_source
            except Exception as e:
                print(f"Selenium failed for {firm['firm']}: {e}\n")
                continue
        else:
            if firm["parser_type"] != "api_endpoint":
                try:
                    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
                    res = requests.get(firm["url"], headers=headers, timeout=10)
                   
                    source_code = res.text
                except Exception as e:
                    print(f"Requests failed for {firm['firm']}: {e}")
                    continue

        ptype = firm["parser_type"]
        selectors = firm.get("selectors", {})

        if ptype == "custom_divs":
            rates = parse_custom_divs(source_code, selectors)
        elif ptype == "dynamic_ticker":
            rates = parse_dynamic_ticker(source_code, selectors)
        elif ptype == "api_endpoint":
            rates = parse_api_endpoint(firm["url"], selectors)
        
        #add the firm name to the extracted data
        for rate in rates:
            rate["firm"] = firm["firm"]
            all_extracted_data.append(rate)
        
        delay = random.uniform(3.0, 7.0)
        print(f"\nSleeping for {delay:.2f} seconds to breathe...\n")
        time.sleep(delay)

    #clean up Selenium driver if it was opened
    if driver:
        driver.quit()
    
    return all_extracted_data

from kafka import KafkaProducer
kafka_nodes = "kafka:9092"
topic_name = "fx_rates"

def produce_to_kafka():
    scraped_data = main()

    if not scraped_data:
        print("No data was scraped. Exiting Kafka pipeline.")
        return
    
    prod = KafkaProducer(
    bootstrap_servers=kafka_nodes,
    key_serializer=lambda k: k.encode("utf-8") if k else None,
    value_serializer=lambda x: json.dumps(x).encode("utf-8"),
)
   
    print(f"\nStreaming {len(scraped_data)} records to Kafka topic [{topic_name}]...")

    #process, clean, and send data
    for row in scraped_data:
        # Manual Data Cleaning (Moved from your original CSV block)
        clean_buy = re.sub(r'[^\d\.]', '', str(row.get('buy', '')))
        clean_sell = re.sub(r'[^\d\.]', '', str(row.get('sell', '')))
        try:
            buy_price = float(clean_buy) if clean_buy else 0.0
        except ValueError:
            buy_price = 0.0

        try:
            sell_price = float(clean_sell) if clean_sell else 0.0
        except ValueError:
            sell_price = 0.0

        payload = {
                        'firm': str(row.get('firm', '')).strip(),
                        'currency': str(row.get('currency', '')).strip(),
                        'buy': buy_price,
                        'sell': sell_price
                    }
        prod.send(topic_name,key=payload['currency'], value=payload)
        print(f"Sent: {payload}")
       
    #flush and close the connection safely
    print("\nFlushing remaining messages and closing producer...")
    prod.flush()
    prod.close()
    print("Kafka streaming completed successfully!")

if __name__ == "__main__":
    produce_to_kafka()