# store_summary.py
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from calendly_agent.states.Basic_state import EmailState
from datetime import datetime

load_dotenv()

def store_summaries(state: EmailState):
    """
    Store summaries and meeting details with status tracking
    """
    MONGO_URI = os.getenv("MONGODB_URI")
    client = MongoClient(MONGO_URI)
    db = client["qstatedb"]
    summaries_col = db["calendly_summaries"]
    meetings_col = db["meetings"]

    # Store summaries
    summary_doc = {
        "client_email": state.user_id,
        "other_party_email": state.other_party_email,
        "summaries": state.summarized_threads,
        "generated_content": state.generated_content,
        "created_at": datetime.now()
    }
    
    if state.meeting_details:
        summary_doc["calendly_link"] = state.meeting_details.get("calendly_link")
    
    summaries_col.insert_one(summary_doc)

    # Store meeting details
    if state.meeting_details:
        meeting_doc = {
            "client_id": state.client_id,
            "client_email": state.user_id,
            "recipient_email": state.other_party_email,
            "calendly_link": state.meeting_details.get("calendly_link"),
            "is_urgent": state.meeting_details.get("is_urgent", False),
            "proposed_date": state.meeting_details.get("proposed_date"),
            "special_requests": state.meeting_details.get("special_requests", []),
            "status": state.meeting_details.get("status", "scheduled"),
            "status_history": state.meeting_details.get("status_history", []),
            "document_attached": False,
            "created_at": datetime.now()
        }
        
        if "reschedule_of" in state.meeting_details:
            meeting_doc["reschedule_of"] = state.meeting_details["reschedule_of"]
        
        meetings_col.insert_one(meeting_doc)

    print("Stored summary and meeting details to MongoDB")
    return state
