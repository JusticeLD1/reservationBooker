import os
from playwright.sync_api import sync_playwright
import time
import json
from typing import Optional, Dict, Any
import logging
from datetime import datetime
from book_resy import book_resy

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

        # 4. Set date using calendar widget
        try:
            # Parse the target date from date_str (e.g., "June,5,2025" -> June 5, 2025)
            date_parts = date_str.split(',')
            if len(date_parts) == 3:
                target_month_name = date_parts[0].strip()  # e.g., "June"
                target_day = int(date_parts[1].strip())  # e.g., 5
                target_year = int(date_parts[2].strip())  # e.g., 2025
            else:
                logger.error(f"Invalid date format: {date_str}. Expected format: 'Month,Day,Year'")
                return
            
            logger.info(f"Setting date to {target_month_name} {target_day}, {target_year}")
            
            # Find and click the date input to open calendar widget
            date_input_selectors = [
                '#search-autocomplete-day-picker-label',
                'button[data-test="date-selector"]',
                'input[placeholder*="Date"]',
                'button[aria-label*="Date"]',
                '[data-testid="date-picker-trigger"]',
                'button[class*="date"]',
                'button[data-test="date-picker-trigger"]',
                'button[aria-label*="Select date"]',
                'button[class*="date-picker"]',
                'div[class*="date-picker"] button',
                'button:has-text("Select Date")',
                'button:has-text("Choose Date")',
                'button:has-text("Pick Date")'
            ]
            
            date_input_clicked = False
            for selector in date_input_selectors:
                try:
                    # Wait for the element to be visible
                    date_input = self.page.wait_for_selector(selector, state="visible", timeout=5000)
                    if date_input:
                        # Try to click the element
                        date_input.click()
                        logger.info(f"Clicked date input using selector: {selector}")
                        time.sleep(1)  # Wait for calendar to open
                        
                        # Verify calendar opened by checking for calendar elements
                        calendar_indicators = [
                            'div[aria-live="polite"][role="presentation"]',
                            '[data-test="calendar-header"]',
                            '.calendar-header',
                            'div[class*="month"][class*="year"]'
                        ]
                        
                        for indicator in calendar_indicators:
                            try:
                                if self.page.wait_for_selector(indicator, state="visible", timeout=2000):
                                    date_input_clicked = True
                                    logger.info("Calendar successfully opened")
                                    break
                            except:
                                continue
                        
                        if date_input_clicked:
                            break
                except Exception as e:
                    logger.warning(f"Failed to click date input with {selector}: {e}")
                    continue
            
            if not date_input_clicked:
                # Try one last approach - look for any clickable element that might be the date picker
                try:
                    # Look for elements that might contain date-related text
                    date_elements = self.page.query_selector_all('button, input, div[role="button"]')
                    for element in date_elements:
                        try:
                            text = element.text_content().strip().lower()
                            if any(date_term in text for date_term in ['date', 'calendar', 'pick date', 'select date']):
                                element.click()
                                logger.info("Clicked potential date input element")
                                time.sleep(1)
                                
                                # Verify calendar opened
                                if self.page.query_selector('div[aria-live="polite"][role="presentation"]'):
                                    date_input_clicked = True
                                    logger.info("Calendar successfully opened")
                                    break
                        except:
                            continue
                except Exception as e:
                    logger.warning(f"Failed in final date input attempt: {e}")
            
            if not date_input_clicked:
                logger.error("Could not find or click date input to open calendar")
                return
            
            # Navigate to target month/year
            max_navigation_attempts = 24  # Prevent infinite loops (max 2 years ahead)
            navigation_attempts = 0
            
            while navigation_attempts < max_navigation_attempts:
                try:
                    # Find current month/year display using the most reliable selector first
                    current_month_year = None
                    month_year_element = self.page.query_selector('div[aria-live="polite"][role="presentation"]')
                    if month_year_element:
                        current_month_year = month_year_element.text_content().strip()
                    
                    if not current_month_year:
                        # Fallback to other selectors if the primary one fails
                        for selector in ['[data-test="calendar-header"]', '.calendar-header', 'div[class*="month"][class*="year"]']:
                            element = self.page.query_selector(selector)
                            if element:
                                current_month_year = element.text_content().strip()
                                break
                    
                    if not current_month_year:
                        logger.warning("Could not find current month/year display")
                        break
                    
                    logger.info(f"Current calendar shows: {current_month_year}")
                    
                    # Check if we're at the target month/year
                    if target_month_name in current_month_year and str(target_year) in current_month_year:
                        logger.info(f"Reached target month/year: {target_month_name} {target_year}")
                        break
                    
                    # Click next month button - try the most specific selector first
                    next_button = self.page.query_selector('button[aria-label*="Next month"]')
                    if not next_button:
                        # Fallback to other selectors
                        for selector in ['button[class*="next"]', 'button.xlJIcF4HEgA-.hXVSeTEeYx', 'button[data-test="next-month"]', 'button:has-text(">")']:
                            next_button = self.page.query_selector(selector)
                            if next_button:
                                break
                    
                    if next_button:
                        next_button.click()
                        logger.info("Clicked next month button")
                        time.sleep(0.5)  # Wait for calendar to update
                    else:
                        logger.warning("Could not find next month button")
                        break
                    
                    navigation_attempts += 1
                    
                except Exception as e:
                    logger.error(f"Error during calendar navigation: {e}")
                    break
            
            # Select the target day
            try:
                # First try to find the day using the most specific selector
                day_button = self.page.query_selector(f'button[name="day"][aria-label*="{target_month_name} {target_day}"]')
                
                if not day_button:
                    # Try other selectors if the specific one fails
                    for selector in [
                        f'button[name="day"]:has-text("{target_day}")',
                        f'td button:has-text("{target_day}")',
                        f'button[aria-label*="{target_day}"]'
                    ]:
                        day_buttons = self.page.query_selector_all(selector)
                        for button in day_buttons:
                            button_text = button.text_content().strip()
                            aria_label = button.get_attribute('aria-label') or ''
                            
                            # Verify this is the correct day
                            if button_text == str(target_day) or str(target_day) in aria_label:
                                day_button = button
                                break
                        if day_button:
                            break
                
                if day_button:
                    day_button.click()
                    logger.info(f"Successfully clicked day {target_day}")
                    time.sleep(1)  # Wait for selection to register
                    logger.info(f"Date successfully set to {target_month_name} {target_day}, {target_year}")
                else:
                    logger.warning(f"Could not find or click day {target_day}")
                    
            except Exception as e:
                logger.error(f"Error selecting target day: {e}")
                
        except Exception as e:
            logger.error(f"Error in date setting process: {e}")
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

         # 2. Type "restaurant + location" in the search bar and submit
        search_term = restaurant_name if not location else f"{restaurant_name} {location}"
        search_input = self.page.query_selector('input[placeholder*="Location, Restaurant, or Cuisine"]')
        if not search_input:
            logger.error("Could not find the search input on OpenTable homepage.")
            return None
        search_input.fill(search_term)
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
        
    def input_verification_code(self, code: str) -> bool:
        """
        Input the verification code into the reservation form
        """
        try:
            # Try multiple selectors for the verification code input field
            verification_selectors = [
                'input[placeholder*="verification code" i]',
                'input[id*="verificationCode" i]',
                'input[name*="verification" i]',
                'input[type="text"][aria-label*="verification" i]',
                '#verification-code-input',
                'input[class*="verification" i]'
            ]
            
            code_input = None
            for selector in verification_selectors:
                try:
                    code_input = self.page.wait_for_selector(selector, state='visible', timeout=5000)
                    if code_input:
                        logger.info(f"Found verification input using selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} not found: {str(e)}")
                    continue
            
            if not code_input:
                logger.error("Could not find verification code input field")
                return False
            
            # Clear any existing input and fill in the verification code
            code_input.fill("")  # Clear existing input
            code_input.fill(code)
            logger.info("Successfully input verification code")
            
            # Try to find and click the continue button
            continue_selectors = [
                'button:has-text("Continue")',
                'button[type="submit"]',
                'button[class*="continue" i]',
                'button[class*="submit" i]',
                'button[aria-label*="continue" i]'
            ]
            
            continue_button = None
            for selector in continue_selectors:
                try:
                    continue_button = self.page.wait_for_selector(selector, state='visible', timeout=5000)
                    if continue_button:
                        logger.info(f"Found continue button using selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Continue button selector {selector} not found: {str(e)}")
                    continue
            
            if continue_button:
                continue_button.click()
                logger.info("Clicked continue button")
            else:
                # If no continue button found, try pressing Enter
                code_input.press("Enter")
                logger.info("Pressed Enter key on verification input")
            
            # Wait for the page to load after submission
            self.page.wait_for_load_state('networkidle')
            time.sleep(2)  # Small delay to ensure submission is processed
            
            return True

        except Exception as e:
            logger.error(f"Error in verification code process: {str(e)}")
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
                    verification = booker.input_verification_code(data["verification_code"])
                    if verification:
                        return {
                            "success": True,
                            "message": "Reservation booked successfully"
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Failed to input verification code"
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
        "date": "June,16,2025",
        "time": "20:00",
        "party_size": 5,
        "phone": "1234567890",
        "email": "test@test.com",
        "verification_code": "123456"
    }
    print(book_reservation(test_data))
    #book_reservation_testing(test_data)
