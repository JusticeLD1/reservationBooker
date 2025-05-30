from parse_reservation import parse_reservation_request
from book_opentable import book_reservation

def main():
    user_input = input("Enter your reservation request: ")

    print("\n Parsing your request...\n")
    data = parse_reservation_request(user_input)

    if not data or "restaurant" not in data:
        print(" Could not understand your request. Try again.")
        return

    print(f" Parsed request:\n{data}\n")
    confirm = input("Proceed with this reservation? (y/n): ").strip().lower()
    if confirm != 'y':
        print(" Canceled.")
        return

    print("\n Trying to book your reservation...\n")
    # Add user details to the data dictionary
    data["user_details"] = {
        "first_name": "Your",  # Replace with actual user details
        "last_name": "Name",
        "email": "your.email@example.com",
        "phone": "1234567890"
    }
    result = book_reservation(data)

    if result.get("success"):
        print(f" Success! {result.get('message')}")
    else:
        print(f" Failed: {result.get('error')}")

if __name__ == "__main__":
    main()
