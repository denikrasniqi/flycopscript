from datetime import datetime, timedelta
import json
import random
import time
from playwright.sync_api import sync_playwright, TimeoutError
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from database import save_flights

load_dotenv()

def random_sleep(min_seconds=1, max_seconds=5):
    time.sleep(random.uniform(min_seconds, max_seconds))

def extract_flight_info(page_html, target_date):
    soup = BeautifulSoup(page_html, 'html.parser')
    flights = []


    # Select all rows in the table
    rows = soup.select('table.flug_auswahl tr.flugzeile')
    print(f"Found {len(rows)} rows in the flight table.")

    for row in rows:
        # Extract date from the row
        date_cell = row.select_one('td.ab_datum')
        if date_cell:
            flight_date = date_cell.get_text(strip=True)
            flight_date_part = flight_date.split(' ')[1]  # Assuming the date is the second part
            current_year = datetime.now().year
            flight_date_with_year = f"{flight_date_part}.{current_year}"
            flight_date_formatted = datetime.strptime(flight_date_with_year, '%d.%m.%Y').strftime('%d.%m.%Y')
            # Check if this is the desired date
            print(f"Checking flight date: {flight_date_formatted}")
            print(f"Target date: {target_date}")
            if target_date in flight_date_formatted:
                # Extract flight details
                time_cell = row.select_one('td.ab_an')
                flight_number_cell = row.select_one('td.carrier_flugnr')
                price_cell = row.select_one('td.b_ges_preis')

                flight = {
                    'date': flight_date,
                    'time': time_cell.get_text(strip=True) if time_cell else 'N/A',
                    'flight_number': flight_number_cell.get_text(strip=True) if flight_number_cell else 'N/A',
                    'price': price_cell.get_text(strip=True) if price_cell else 'N/A'
                }
                flights.append(flight)
    
    return flights
def run_arkpy_ticket_script():
    airport_pairs = [
        ('MLH', 'PRN'),
        ('PRN', 'DUS'),
        ('PRN', 'MUC'),
        ('DUS', 'PRN'),
        ('PRN', 'STR'),
        ('STR', 'PRN'),
        ('PRN', 'MLH'),
        ('MUC', 'PRN'),
        ('PRN', 'NUE'),
        ('NUE', 'PRN'),
    ]

    for departure, arrival in airport_pairs:
        for day in range(0, 8):
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)  # Set to True to run headlessly
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    extra_http_headers={
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Connection': 'keep-alive',
                        'DNT': '1',
                    }
                )
                page = context.new_page()

                url = 'https://www.airtiketa.com'
                page.goto(url)
                random_sleep(2, 3)

                # Click the "Njëdrejtimshe" (one-way) radio button
                page.click('input[value="ow"]')

                # Select the "Nisja nga" (Departure from) dropdown
                page.select_option('select[name="VON"]', value=departure)

                # Select the "Kthimi" (Return to) dropdown
                page.select_option('select[name="NACH"]', value=arrival)

                # Set the departure date
                target_date = (datetime.now() + timedelta(days=day)).strftime('%d.%m.%Y')
                print(f"Searching for flights from {day}")
                print(f"Target date in near main: {target_date}")
                page.fill('input[name="DATUM_HIN"]', target_date)

                # Click the search button
                button_selector = 'button#buchen_aktion'

                # Wait for the button to be visible
                page.wait_for_selector(button_selector, state='visible')
                
                # Click the search button
                page.click(button_selector)
                
                try:
                    # Wait for the page to load or content to update
                    page.wait_for_load_state('networkidle', timeout=20000)  # Increase timeout to 60 seconds
                except TimeoutError:
                    print(f"Timeout while waiting for page to load for {departure} to {arrival} on {target_date}.")
                    continue

                random_sleep(2, 3)
                page_html = page.content()
                flights = extract_flight_info(page_html, target_date)
                print(flights)
                save_flights(flights, departure, arrival, day, url)
                print(f"Flight information saved for {departure} to {arrival} on day {day}")

                browser.close()

if __name__ == "__main__":
    run_arkpy_ticket_script()
