from datetime import datetime, timedelta
import json
import os
import random
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from database import save_flights

load_dotenv()

def random_sleep(min_seconds=1, max_seconds=2):
    time.sleep(random.uniform(min_seconds, max_seconds))

def extract_flight_info(page_html, flight_date):
    soup = BeautifulSoup(page_html, 'html.parser')
    flights = []

    flight_rows = soup.select('div.available-flight')
    for flight_row in flight_rows:
        price_div = flight_row.select_one('div.price span.value')
        airline_div = flight_row.select_one('div.flight-nr')
        departure_div = flight_row.select_one('span.departure-time')

        if price_div and airline_div and departure_div:
            flights.append({
                'price': price_div.get_text(strip=True),
                'flight_number': airline_div.get_text(strip=True),
                'time': departure_div.get_text(strip=True),
                'date': flight_date
            })

    return flights

def run_airprishtina_ticket_script():
    airport_pairs = [
        ('Pristina', 'Basel-Mulhouse'),
        ('Pristina', 'Stuttgart'),
        ('Pristina', 'Düsseldorf'),
        ('Pristina', 'München'),
        ('Düsseldorf', 'Pristina'),
        ('München', 'Pristina'),
        ('Stuttgart', 'Pristina'),
        ('Basel-Mulhouse', 'Pristina')
        
    ]
    city_to_airport_code = {
        'Pristina': 'PRN',
        'Düsseldorf': 'DUS',
        'München': 'MUC',
        'Stuttgart': 'STR',
        'Basel-Mulhouse':'BSL'
    }

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

                url = 'https://www.airprishtina.com/sq/'
                page.goto(url)
                random_sleep(1)

                # Click on the "One Way" option
                page.click('div.one-way')
                random_sleep(1)
                print(f"Checking departure  : {departure}")
                page.fill('input#txt_Flight1From', departure)
                random_sleep(1)
                page.locator(f'[data-text="{departure}"]').click()
                random_sleep(1)
                # Populate the "To" input field with the arrival location
                page.fill('input#txt_Flight1To', arrival)
                random_sleep(3)
                page.locator(f'[data-text="{arrival}"]').click()
                random_sleep(1)

                # Get the target date in the required format
                target_date = (datetime.now() + timedelta(days=day)).strftime('%Y-%m-%d')

                # Click on the date input field to open the date picker
                page.click('input#txt_FromDateText')
                random_sleep(1)

                # Debug print to check if the date picker is opened

                # Ensure the date picker is visible
                date_element = page.locator(f'td[data-usr-date="{target_date}"]')
                if date_element.is_visible():
                    date_element.click()
                else:
                    # Wait for the date element to be visible
                    page.wait_for_selector(f'td[data-usr-date="{target_date}"]', timeout=5000)
                    date_element.click()

                random_sleep(1)

                # Click the search button
                search_button_selector = 'button.btn.btn-red.ac-popup'
                page.click(search_button_selector)
                random_sleep(5)  # Increase sleep time to allow search results to load

                try:
                    load_more_button = page.locator("//button[contains(text(), 'Load more')]")
                    if load_more_button.is_visible():
                        load_more_button.click()
                        random_sleep(2, 3)
                except Exception as e:
                    print(f"Load More button not found or error occurred: {e}")

                random_sleep(5)  # Additional sleep to ensure the page content is fully loaded
                page_html = page.content()
                flights = extract_flight_info(page_html, target_date)

                # Filter out incomplete flight records
                complete_flights = [flight for flight in flights if all(flight.values())]
                tempdeparture = departure
                temparival = arrival
                departure = city_to_airport_code[departure]
                arrival = city_to_airport_code[arrival]

                # Save the flight information to the database
                save_flights(complete_flights, departure, arrival, day, url)
                departure = tempdeparture
                arrival = temparival
                print(f"Flight information saved for {departure} to {arrival} on day {day}")

                browser.close()

if __name__ == "__main__":
    run_airprishtina_ticket_script()
