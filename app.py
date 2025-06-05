from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import uuid
import asyncio
from datetime import datetime, timedelta
import logging
import json
from sqlalchemy.orm import Session

# Import your existing functions
from parse_reservation import parse_reservation_request
from book_opentable import book_reservation
from database import get_db, User
from auth import (
    UserCreate, UserResponse, Token, create_access_token,
    get_current_active_user, ACCESS_TOKEN_EXPIRE_MINUTES
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Restaurant Reservation API",
    description="AI-powered restaurant reservation booking system",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for booking status (use Redis/DB in production)
booking_sessions: Dict[str, Dict[str, Any]] = {}

# Pydantic models for request/response
class ReservationRequest(BaseModel):
    user_input: str = Field(..., description="Natural language reservation request")
    
class ParsedReservation(BaseModel):
    restaurant: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    party_size: Optional[int] = None
    location: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    restaurant_url: Optional[str] = None

class BookingRequest(BaseModel):
    reservation_details: ParsedReservation
    user_details: Optional[Dict[str, str]] = None

class BookingResponse(BaseModel):
    booking_id: str
    status: str
    message: str

class BookingStatus(BaseModel):
    booking_id: str
    status: str  # "pending", "in_progress", "completed", "failed"
    message: str
    progress: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

@app.get("/")
async def root():
    return {"message": "Restaurant Reservation API is running"}

@app.post("/parse", response_model=ParsedReservation)
async def parse_reservation(request: ReservationRequest):
    """
    Parse natural language reservation request into structured data
    """
    try:
        logger.info(f"Parsing reservation request: {request.user_input}")
        
        # Call your existing parsing function
        parsed_data = parse_reservation_request(request.user_input)
        
        if not parsed_data:
            raise HTTPException(
                status_code=400, 
                detail="Could not parse reservation request. Please provide more details."
            )
        
        # Validate that we have minimum required fields
        if "restaurant" not in parsed_data:
            raise HTTPException(
                status_code=400,
                detail="Could not identify restaurant name. Please specify the restaurant."
            )
        
        return ParsedReservation(**parsed_data)
        
    except Exception as e:
        logger.error(f"Error parsing reservation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Parsing error: {str(e)}")

@app.post("/book", response_model=BookingResponse)
async def start_booking(booking_request: BookingRequest, background_tasks: BackgroundTasks):
    """
    Start the reservation booking process in the background
    """
    try:
        # Generate unique booking ID
        booking_id = str(uuid.uuid4())
        
        # Validate required fields
        reservation = booking_request.reservation_details
        if not reservation.restaurant:
            raise HTTPException(status_code=400, detail="Restaurant name is required")
        if not reservation.location:
            raise HTTPException(status_code=400, detail="Location is required")
        if not reservation.date:
            raise HTTPException(status_code=400, detail="Date is required")
        if not reservation.time:
            raise HTTPException(status_code=400, detail="Time is required")
        if not reservation.party_size:
            raise HTTPException(status_code=400, detail="Party size is required")
        if not reservation.phone:
            raise HTTPException(status_code=400, detail="Phone number is required")
        
        # Initialize booking session
        now = datetime.now()
        booking_sessions[booking_id] = {
            "booking_id": booking_id,
            "status": "pending",
            "message": "Booking request received",
            "progress": "Initializing...",
            "reservation_details": reservation.dict(),
            "user_details": booking_request.user_details,
            "result": None,
            "created_at": now,
            "updated_at": now
        }
        
        # Start booking process in background
        background_tasks.add_task(process_booking, booking_id)
        
        return BookingResponse(
            booking_id=booking_id,
            status="pending",
            message="Booking process started. Use the booking_id to check status."
        )
        
    except Exception as e:
        logger.error(f"Error starting booking: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Booking error: {str(e)}")

@app.get("/status/{booking_id}", response_model=BookingStatus)
async def get_booking_status(booking_id: str):
    """
    Get the current status of a booking request
    """
    if booking_id not in booking_sessions:
        raise HTTPException(status_code=404, detail="Booking ID not found")
    
    session = booking_sessions[booking_id]
    return BookingStatus(**session)

@app.get("/bookings")
async def list_bookings():
    """
    List all booking sessions (for debugging/admin)
    """
    return {
        "total": len(booking_sessions),
        "bookings": list(booking_sessions.keys())
    }

@app.delete("/booking/{booking_id}")
async def cancel_booking(booking_id: str):
    """
    Cancel or remove a booking session
    """
    if booking_id not in booking_sessions:
        raise HTTPException(status_code=404, detail="Booking ID not found")
    
    session = booking_sessions[booking_id]
    if session["status"] == "in_progress":
        # In a real app, you'd want to actually stop the browser automation
        session["status"] = "cancelled"
        session["message"] = "Booking cancelled by user"
        session["updated_at"] = datetime.now()
        return {"message": "Booking cancelled"}
    else:
        del booking_sessions[booking_id]
        return {"message": "Booking session removed"}

async def process_booking(booking_id: str):
    """
    Background task to handle the actual booking process
    """
    session = booking_sessions[booking_id]
    
    try:
        # Update status to in_progress
        session["status"] = "in_progress"
        session["message"] = "Starting browser automation..."
        session["progress"] = "Opening OpenTable..."
        session["updated_at"] = datetime.now()
        
        logger.info(f"Starting booking process for {booking_id}")
        
        # Prepare data for the booking function
        booking_data = session["reservation_details"].copy()
        
        # Add user details if provided
        if session.get("user_details"):
            booking_data["user_details"] = session["user_details"]
        
        # Update progress
        session["progress"] = "Searching for restaurant..."
        session["updated_at"] = datetime.now()
        
        # Call your existing booking function
        # Note: This needs to be run in a thread since it's synchronous
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(book_reservation, booking_data)
            result = future.result()  # This will block until completion
        
        # Update session with results
        if result.get("success"):
            session["status"] = "completed"
            session["message"] = "Reservation booked successfully!"
            session["progress"] = "Completed"
            session["result"] = result
        else:
            session["status"] = "failed"
            session["message"] = f"Booking failed: {result.get('error', 'Unknown error')}"
            session["progress"] = "Failed"
            session["result"] = result
            
    except Exception as e:
        logger.error(f"Error in booking process {booking_id}: {str(e)}")
        session["status"] = "failed"
        session["message"] = f"Booking failed due to error: {str(e)}"
        session["progress"] = "Error occurred"
        session["result"] = {"success": False, "error": str(e)}
    
    finally:
        session["updated_at"] = datetime.now()
        logger.info(f"Booking process completed for {booking_id}: {session['status']}")

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "active_bookings": len([s for s in booking_sessions.values() if s["status"] == "in_progress"])
    }

# User management endpoints
@app.post("/users/", response_model=UserResponse)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    hashed_password = User.get_password_hash(user.password)
    db_user = User(
        email=user.email,
        name=user.name,
        phone_number=user.phone_number,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not user.verify_password(form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me/", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )