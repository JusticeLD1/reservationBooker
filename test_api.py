import requests
import time
import json

# Base URL for your API
BASE_URL = "http://localhost:8000"

def test_parse_endpoint():
    """Test the reservation parsing endpoint"""
    print("🧪 Testing /parse endpoint...")
    
    url = f"{BASE_URL}/parse"
    data = {
        "user_input": "make me a reservation at Nobu in Los Angeles for 4 people on 2025-06-20 at 19:00 phone number is 1234567890 email is test@test.com"
    }
    
    response = requests.post(url, json=data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        parsed_data = response.json()
        print("✅ Parsing successful!")
        print(json.dumps(parsed_data, indent=2))
        return parsed_data
    else:
        print(f"❌ Parsing failed: {response.text}")
        return None

def test_booking_flow(parsed_reservation=None):
    """Test the complete booking flow"""
    print("\n🧪 Testing booking flow...")
    
    if not parsed_reservation:
        # Use default reservation data
        parsed_reservation = {
            "restaurant": "Nobu",
            "date": "2025-06-25",
            "time": "19:00", 
            "party_size": 4,
            "location": "Los Angeles",
            "phone": "1234567890",
            "email": "test@test.com"
        }
    
    # Start booking
    booking_url = f"{BASE_URL}/book"
    booking_data = {
        "reservation_details": parsed_reservation,
        "user_details": {
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
            "phone": "1234567890"
        }
    }
    
    print("Starting booking...")
    response = requests.post(booking_url, json=booking_data)
    
    if response.status_code != 200:
        print(f"❌ Failed to start booking: {response.text}")
        return
    
    booking_response = response.json()
    booking_id = booking_response["booking_id"]
    print(f"✅ Booking started with ID: {booking_id}")
    
    # Poll for status updates
    status_url = f"{BASE_URL}/status/{booking_id}"
    
    for i in range(30):  # Poll for up to 5 minutes
        print(f"\n📊 Checking status (attempt {i+1})...")
        status_response = requests.get(status_url)
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            print(f"Status: {status_data['status']}")
            print(f"Message: {status_data['message']}")
            if status_data.get('progress'):
                print(f"Progress: {status_data['progress']}")
            
            if status_data['status'] in ['completed', 'failed']:
                print(f"\n🎯 Final result: {status_data['status']}")
                if status_data.get('result'):
                    print("Result details:")
                    print(json.dumps(status_data['result'], indent=2))
                break
        else:
            print(f"❌ Failed to get status: {status_response.text}")
            break
        
        time.sleep(10)  # Wait 10 seconds between checks
    else:
        print("⏰ Timeout waiting for booking completion")

def test_health_endpoint():
    """Test the health check endpoint"""
    print("\n🧪 Testing /health endpoint...")
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        health_data = response.json()
        print("✅ Health check successful!")
        print(json.dumps(health_data, indent=2))
    else:
        print(f"❌ Health check failed: {response.text}")

def main():
    """Run all tests"""
    print("🚀 Starting API tests...\n")
    
    # Test health endpoint first
    test_health_endpoint()
    
    # Test parsing
    parsed_data = test_parse_endpoint()
    
    # Test booking flow
    if parsed_data:
        test_booking_flow(parsed_data)
    else:
        print("\n⚠️ Skipping booking test due to parsing failure")
        print("Testing booking with default data...")
        test_booking_flow()

if __name__ == "__main__":
    main()