from pydantic import BaseModel
from typing import List, Dict, Optional, Union, Any
from bson import ObjectId  # Import ObjectId for MongoDB compatibility

class EmailState(BaseModel):
    user_id: Optional[str] = None  # MongoDB ObjectId or email of the user
    client_id: Optional[Union[str, ObjectId]] = None  # Accepts both ObjectId and string
    other_party_email: str  # Email of the other end party
    conversation_threads: Optional[List[Dict[str, Any]]] = None  # Changed from List[Dict[str, str]]
    summarized_threads: Optional[List[str]] = None  # List of summaries
    generated_content: Optional[str] = None  # Additional content generated from summaries
    meeting_details: Optional[Dict[str, Any]] = None  # Updated to Any to handle various data types

    class Config:
        arbitrary_types_allowed = True  # Allow arbitrary types like ObjectId
