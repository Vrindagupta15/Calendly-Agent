from pymongo import MongoClient
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
import json
import os
import base64
from dotenv import load_dotenv
from calendly_agent.states.Basic_state import EmailState
from datetime import datetime

# Load environment variables
load_dotenv()

def get_or_create_gmail_service(user_email, mongodb_uri, db_name, scopes):
    """
    Fetches or creates Gmail API tokens for a user and initializes the Gmail service.
    """
    print(f"Initializing Gmail service for: {user_email}")
    client = MongoClient(mongodb_uri)
    db = client[db_name]
    users_collection = db["users"]

    # Check if user exists in MongoDB
    user = users_collection.find_one({"email": user_email})
    creds = None

    try:
        if user and "gmail_access_token" in user:
            print("Found existing token in database")
            # Load existing credentials from the database
            token = user["gmail_access_token"]
            creds = Credentials.from_authorized_user_info(token, scopes)

        if not creds or not creds.valid:
            print("Need to refresh or create new token")
            if creds and creds.expired and creds.refresh_token:
                try:
                    print("Attempting to refresh expired token")
                    creds.refresh(Request())
                except Exception as refresh_error:
                    print(f"Token refresh failed: {refresh_error}")
                    creds = None
            
            if not creds:
                print("Creating new token via OAuth flow")
                # Create new credentials using OAuth flow
                flow = InstalledAppFlow.from_client_secrets_file('Credentials.json', scopes)
                creds = flow.run_local_server(port=0)

                # Save new tokens in MongoDB
                token_dict = json.loads(creds.to_json())
                users_collection.update_one(
                    {"email": user_email},
                    {"$set": {"gmail_access_token": token_dict}},
                    upsert=True
                )

        # Initialize Gmail API service
        service = build('gmail', 'v1', credentials=creds)
        print("Gmail service initialized successfully")
        return service

    except Exception as e:
        print(f"Error in Gmail authentication: {e}")
        # Force new token creation if something goes wrong
        print("Forcing new token creation...")
        flow = InstalledAppFlow.from_client_secrets_file('Credentials.json', scopes)
        creds = flow.run_local_server(port=8080)
        
        # Save new tokens in MongoDB
        token_dict = json.loads(creds.to_json())
        users_collection.update_one(
            {"email": user_email},
            {"$set": {"gmail_access_token": token_dict}},
            upsert=True
        )
        
        service = build('gmail', 'v1', credentials=creds)
        print("Gmail service initialized successfully after recovery")
        return service

def fetch_threads(state: EmailState):
    """
    Fetch Gmail conversation threads containing the specified tag and store them in MongoDB.
    """
    MONGODB_URI = os.getenv("MONGODB_URI")
    DB_NAME = "qstatedb"
    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",
    ]

    client = MongoClient(MONGODB_URI)
    db = client[DB_NAME]
    email_threads_col = db["email_threads"]

    try:
        # Get or create Gmail service
        gmail_service = get_or_create_gmail_service(state.user_id, MONGODB_URI, DB_NAME, SCOPES)

        # Load threads with the tag "MeetingBookmark"
        query = 'label:Agreed-to-Meet (from:nobarakugisaki2033@gmail.com OR to:nobarakugisaki2033@gmail.com)'

        threads = gmail_service.users().threads().list(userId="me", q=query).execute().get("threads", [])

        if not threads:
            print("No threads found with tag 'MeetingBookmark'.")
            state.conversation_threads = []
            return state

        threads_data = []
        for thread in threads:
            thread_id = thread["id"]
            thread_data = gmail_service.users().threads().get(userId="me", id=thread_id, format="full").execute()

            messages = []
            for message in thread_data.get("messages", []):
                payload = message.get("payload", {})
                headers = {header["name"]: header["value"] for header in payload.get("headers", [])}

                body_data = payload.get("body", {}).get("data")
                if not body_data and "parts" in payload:
                    for part in payload["parts"]:
                        if part["mimeType"] == "text/plain":
                            body_data = part["body"].get("data")
                            break

                body = base64.urlsafe_b64decode(body_data).decode("utf-8") if body_data else ""

                messages.append({
                    "message_id": message["id"],
                    "thread_id": message["threadId"],
                    "subject": headers.get("Subject", ""),
                    "from": headers.get("From", ""),
                    "to": headers.get("To", ""),
                    "date": headers.get("Date", ""),
                    "body": body,
                })

            threads_data.append({"thread_id": thread_id, "messages": messages})

            # Store thread data in email_threads collection
            email_threads_col.insert_one({
                "client_id": state.client_id,
                "thread_id": thread_id,
                "participants": [state.user_id, state.other_party_email],
                "messages": messages,
                "tagged_status": None,
                "document_required": False,
                "attached_document_path": None,
                "last_updated": datetime.now()
            })

        state.conversation_threads = threads_data

    except Exception as e:
        print(f"An error occurred while fetching threads: {e}")
        state.conversation_threads = []

    return state
