import os
from playwright.sync_api import sync_playwright
import time
import json
from typing import Optional, Dict, Any
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("opentable_booking.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("opentable_booking")

class OpenTableBooker:
    BASE_URL = "https://www.opentable.com"
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.page = None
    
    def start(self) -> None:
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.page = self.browser.new_page()
        self.page.set_viewport_size({"width": 1280, "height": 800})
        self.page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        })
        self.page.set_default_timeout(15000)

    def close(self) -> None:
        try:
            if self.page:
                self.page.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            logger.error(f"Error closing browser: {str(e)}")
    
    def time_to_12h(self, time: str) -> str:
        """
        Convert 24-hour time string to 12-hour format (e.g., "20:00" -> "8:00 PM")
        """
        time2 = int(time.split(":")[0])
        if time2 > 12:
            time2 = time2 - 12
            return f"{time2}:{time.split(':')[1]} PM"
        else:
            return f"{time2}:{time.split(':')[1]} AM"
    
    def search_restaurant(self, restaurant_name: str, location: Optional[str] = None, date_str: str = None, time_str: str = None, party_size: int = None) -> Optional[str]:
        """
        1. Go to opentable.com
        2. Search for "restaurant + location" in the search bar
        3. Set date, time, and party size on the search page using robust selectors
        4. Click on the restaurant name link
        """
        logger.info(f"Searching for restaurant: {restaurant_name} in {location or 'any location'}")

        # 1. Go to OpenTable homepage
        self.page.goto(self.BASE_URL)
        self.page.wait_for_load_state("networkidle")
        time.sleep(2)

        # 2. Type "restaurant + location" in the search bar and submit
        search_term = restaurant_name if not location else f"{restaurant_name} {location}"
        search_input = self.page.query_selector('input[placeholder*="Location, Restaurant, or Cuisine"]')
        if not search_input:
            logger.error("Could not find the search input on OpenTable homepage.")
            return None
        search_input.fill(search_term)
        time.sleep(1)

        # 3. Set party size
        party_selectors = [
            '#restaurantProfileDtpPartySizePicker',
            '[data-test="party-size-picker"]',
            '[aria-label="Party size selector"]'
        ]
        party_dropdown = None
        for selector in party_selectors:
            party_dropdown = self.page.query_selector(selector)
            if party_dropdown:
                try:
                    self.page.select_option(selector, str(party_size))
                    logger.info(f"Party size set to {party_size} using selector {selector}.")
                    break
                except Exception as e:
                    logger.warning(f"Failed to set party size with {selector}: {e}")
        if not party_dropdown:
            logger.warning("Could not find party size dropdown with any selector.")

        # 4. Set date
        date_selectors = [
            '#search-autocomplete-day-picker',
            '[data-test="day-picker"]',
            '[data-testid="day-picker-overlay"]',
            '[aria-label="Date selector"]'
        ]
        date_input = None
        for selector in date_selectors:
            date_input = self.page.query_selector(selector)
            if date_input:
                try:
                    date_input.fill(date_str)
                    logger.info(f"Date set to {date_str} using selector {selector}.")
                    break
                except Exception as e:
                    logger.warning(f"Failed to set date with {selector}: {e}")
        if not date_input:
            logger.warning("Could not find date input with any selector.")

        # 5. Set time
        time_selectors = [
            'select[data-test="time-picker"]',
            '[data-test="time-picker"]',
            '[aria-label="Time selector"]'
        ]
        time_dropdown = None
        for selector in time_selectors:
            time_dropdown = self.page.query_selector(selector)
            if time_dropdown:
                try:
                    # Convert "19:00" to "7:00 PM" if needed
                    time_obj = datetime.strptime(time_str, "%H:%M")
                    time_display = time_obj.strftime("%-I:%M %p").replace("AM", "AM").replace("PM", "PM")
                    self.page.select_option(selector, label=time_display)
                    logger.info(f"Time set to {time_display} using selector {selector}.")
                    break
                except Exception as e:
                    logger.warning(f"Failed to set time with {selector}: {e}")
        if not time_dropdown:
            logger.warning("Could not find time dropdown with any selector.")

        time.sleep(1)

        # 6. Click enter on keyboard
        self.page.keyboard.press("Enter")
        time.sleep(1)

        
        return True
    
    def confirm_reservation(self, phone: str, email: str, time: str) -> bool:
        """
        Confirm the reservation with the given phone and email
        """
        logger.info(f"Confirming reservation with phone: {phone} and email: {email}")
        
        # Convert 24-hour time string to 12-hour format (e.g., "20:00" -> "8:00 PM")
        time_12h = self.time_to_12h(time)

        # Wait for the time slot button to be visible and interactive
        time_selector = f'a[title="{time_12h}"]'
        try:
            self.page.wait_for_selector(time_selector, state="visible", timeout=5000)
            self.page.click(time_selector)
            print(f"Clicked time slot button for {time_12h}")
            time_clicked = True
            # Wait for the page to load after clicking the time slot
            self.page.wait_for_load_state("networkidle")
        except Exception as e:
            print(f"Could not select time slot {time_12h}: {e}")
            return False

        if time_clicked:
            # Wait for the phone input to be visible and interactive
            phone_input = self.page.query_selector('input[name="phone"]')
            if phone_input:
                phone_input.fill(phone)
                print(f"Inputted phone: {phone}")
        
            return True
        
    def input_info(self, phone: str, email: str) -> bool:
        """
        Input the phone and email into the reservation form
        """
        try:
            # Wait for and fill in phone number
            phone_input = self.page.wait_for_selector('#phoneNumber', state='visible', timeout=5000)
            if phone_input:
                phone_input.fill(phone)
                logger.info(f"Successfully input phone number: {phone}")
                
                # Click the complete reservation button
                complete_button = self.page.wait_for_selector('#complete-reservation', state='visible', timeout=5000)
                if complete_button:
                    complete_button.click()
                    logger.info("Clicked complete reservation button")
                    
                    # Wait for the page to load after clicking
                    self.page.wait_for_load_state('networkidle')
                    time.sleep(15)  # Additional small delay to ensure page loads completely
                    return True
                else:
                    logger.error("Could not find complete reservation button")
                    return False
            else:
                logger.error("Could not find phone number input field")
                return False
        except Exception as e:
            logger.error(f"Error in reservation process: {str(e)}")
            return False

def book_reservation(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Book a reservation using OpenTable search and navigation.
    Args:
        data: Dictionary containing at least 'restaurant' and 'location'
    Returns:
        Dictionary with results of the booking attempt
    """
    required_fields = ["restaurant", "location"]
    for field in required_fields:
        if field not in data:
            return {
                "success": False,
                "error": f"Missing required field: {field}"
            }
    
    booker = OpenTableBooker(headless=False)
    try:
        booker.start()
        restaurant_url = booker.search_restaurant(
            restaurant_name=data["restaurant"],
            location=data["location"],
            date_str=data["date"],
            time_str=data["time"],
            party_size=data["party_size"]
        )
        if restaurant_url:
            booking_confirmation = booker.confirm_reservation(data["phone"], data["email"], data['time'])
            if booking_confirmation:
                info_inputted = booker.input_info(data["phone"], data["email"])
                if info_inputted:
                    return {
                        "success": True,
                        "message": "Reservation booked successfully"
                    }
                else:
                    return {
                        "success": False,
                        "error": "Failed to input phone and email"
                    }
            else:
                return {
                    "success": False,
                    "error": "Failed to confirm reservation"
                }
        else:
            return {
                "success": False,
                "error": f"Could not find restaurant '{data['restaurant']}' in '{data['location']}'"
            }
    except Exception as e:
        logger.error(f"Error during booking: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        booker.close()



# Example usage
if __name__ == "__main__":
    test_data = {
        "restaurant": "Katana",
        "location": "Los Angeles",
        "date": "2025-06-20",
        "time": "20:00",
        "party_size": 5,
        "phone": "1234567890",
        "email": "test@test.com"
    }
    print(book_reservation(test_data))
    #book_reservation_testing(test_data)
