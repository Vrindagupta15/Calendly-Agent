import datetime
from dateutil import parser as date_parser
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
import os
import pytz
from google.auth.transport.requests import Request
from calendly_agent.states.Basic_state import EmailState
from dotenv import load_dotenv
from pymongo import MongoClient
import json
load_dotenv()

# def get_or_create_gmail_service(user_email, mongodb_uri, db_name, scopes):
#     """
#     Fetches or creates Gmail API tokens for a user and initializes the Gmail service.
#     """
#     print(f"Initializing Gmail service for: {user_email}")
#     client = MongoClient(mongodb_uri)
#     db = client[db_name]
#     users_collection = db["users"]

#     # Check if user exists in MongoDB
#     user = users_collection.find_one({"email": user_email})
#     creds = None

#     try:
#         if user and "gmail_access_token" in user:
#             print("Found existing token in database")
#             # Load existing credentials from the database
#             token = user["gmail_access_token"]
#             creds = Credentials.from_authorized_user_info(token, scopes)

#         if not creds or not creds.valid:
#             print("Need to refresh or create new token")
#             if creds and creds.expired and creds.refresh_token:
#                 try:
#                     print("Attempting to refresh expired token")
#                     creds.refresh(Request())
#                 except Exception as refresh_error:
#                     print(f"Token refresh failed: {refresh_error}")
#                     creds = None
            
#             if not creds:
#                 print("Creating new token via OAuth flow")
#                 # Create new credentials using OAuth flow
#                 flow = InstalledAppFlow.from_client_secrets_file('Credentials.json', scopes)
#                 creds = flow.run_local_server(port=0)

#                 # Save new tokens in MongoDB
#                 token_dict = json.loads(creds.to_json())
#                 users_collection.update_one(
#                     {"email": user_email},
#                     {"$set": {"gmail_access_token": token_dict}},
#                     upsert=True
#                 )

#         # Initialize calender API service
#         service = build('calendar', 'v3', credentials=creds)
#         print("calender service initialized successfully")
#         return service

#     except Exception as e:
#         print(f"Error in Gmail authentication: {e}")
#         # Force new token creation if something goes wrong
#         print("Forcing new token creation...")
#         flow = InstalledAppFlow.from_client_secrets_file('Credentials.json', scopes)
#         creds = flow.run_local_server(port=8080)
        
#         # Save new tokens in MongoDB
#         token_dict = json.loads(creds.to_json())
#         users_collection.update_one(
#             {"email": user_email},
#             {"$set": {"gmail_access_token": token_dict}},
#             upsert=True
#         )
        
#         service = build('calendar', 'v3', credentials=creds)
#         print("calender service initialized successfully after recovery")
#         return service

import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Define the required scope
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def authenticate_google():
    creds = None
    token_path = 'token.json'
    creds_path = 'Credentials.json'

    # Load existing token if it exists
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # If no valid credentials are available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=8080)
        # Save the credentials for the next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    return creds


def infer_meeting_datetime(summary_text: str) -> datetime.datetime:
    """
    Parses summary text to find references like 'next day', 'tomorrow' etc.
    and converts to datetime. (Basic version — you can later plug in NLP)
    """
    if "next day" in summary_text or "tomorrow" in summary_text:
        return datetime.datetime.now() + datetime.timedelta(days=1)

    # Default fallback: next day at 10:00 AM
    return datetime.datetime.now().replace(hour=10, minute=0) + datetime.timedelta(days=1)


def create_google_calendar_event(state: EmailState):
    # service = get_or_create_gmail_service(
    # user_email="yuvraj07102024@gmail.com",
    # mongodb_uri=os.getenv("MONGODB_URI"),
    # db_name="qstatedb",
    # scopes=[
    #     "https://www.googleapis.com/auth/calendar.events"
    # ]
    # )
    creds = authenticate_google()
    service = build('calendar', 'v3', credentials=creds)
    # Extract details from state
    summary_text = state.generated_content or (state.summarized_threads[0] if state.summarized_threads else "")
    start_time = infer_meeting_datetime(summary_text)

    # Define event
    event = {
        'summary': 'Business Discussion: QState x Wick Solutions',
        'location': 'Google Meet',
        'description': summary_text,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'Asia/Kolkata',  # Change if needed
        },
        'end': {
            'dateTime': (start_time + datetime.timedelta(hours=1)).isoformat(),
            'timeZone': 'Asia/Kolkata',
        },
        'attendees': [
            {'email': state.user_id},
            {'email': state.other_party_email}
        ],
        'reminders': {
            'useDefault': True
        },
        'conferenceData': {
            'createRequest': {
                'requestId': 'meet123',
                'conferenceSolutionKey': {
                    'type': 'hangoutsMeet'
                }
            }
        }
    }

    event = service.events().insert(
        calendarId='primary',
        body=event,
        conferenceDataVersion=1
    ).execute()

    print(f"Event created: {event.get('htmlLink')}")
    state.meeting_details = {
        "event_link": event.get('htmlLink'),
        "start_time": start_time.isoformat()
    }
    return state
