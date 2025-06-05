import os
import json
from dotenv import load_dotenv
import openai

# Load .env file
load_dotenv()

# Get API key from environment
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found. Make sure your .env file is in the project directory.")

# Set the API key for the OpenAI library
openai.api_key = api_key

def parse_reservation_request(prompt: str) -> dict:
    system_prompt = """
    You are a helpful assistant that extracts reservation information from natural language.
    Return a JSON object with the following keys: restaurant, date (change number format to month,day,year as in "June,5,2025"), time, party_size, and location (if available), phone if available, email if available. use the restaurant_url to find the restaurant on opentable.com using the restaurant name and location. First name and last name if left blank can be auto filled with the user's account info.
    Example:
    {
      "restaurant": "Nobu",
      "date": "June,5,2025",
      "time": "19:00",
      "party_size": 2,
      "location": "Los Angeles",
      "phone": "1234567890",
      "email": "test@test.com",
      "restaurant_url": "https://www.opentable.com/r/restuarantName-location",
      "first_name": "John",
      "last_name": "Doe"
    }
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    content = response.choices[0].message.content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        print("⚠️ Failed to parse response as JSON:", e)
        print("Raw response content:\n", content)
        return {}