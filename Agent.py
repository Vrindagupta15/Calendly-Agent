from langgraph.graph import StateGraph
from calendly_agent.states.Basic_state import EmailState
from calendly_agent.Nodes.Load_threads import fetch_threads
from calendly_agent.Nodes.summarize_threads import summarize_threads
from calendly_agent.Nodes.store_summary import store_summaries
from calendly_agent.Nodes.create_google_events import create_google_calendar_event


from pymongo import MongoClient
import os
from dotenv import load_dotenv
import asyncio


# Load environment variables
load_dotenv()
MONGO_URI = os.getenv("MONGODB_URI")

# Initialize MongoDB client
try:
    client = MongoClient(MONGO_URI)
    db = client["qstatedb"]  # Use "qstatedb" as per your company database structure
    users_col = db["users"]
    print("Connected to MongoDB successfully.")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")
    exit()


# Initialize the workflow
workflow = StateGraph(EmailState)

workflow.add_node("fetch", fetch_threads)
workflow.add_node("summarize", summarize_threads)
# workflow.add_node("gen_link", extract_meeting_details)
workflow.add_node("store", store_summaries)
workflow.add_node("create_event", create_google_calendar_event)
workflow.add_edge("store", "create_event")
workflow.set_entry_point("fetch")
workflow.add_edge("fetch", "summarize")
workflow.add_edge("summarize", "store")
workflow.add_edge("store", "create_event")
# workflow.add_edge("summarize", "gen_link")
# workflow.add_edge("gen_link", "store")

graph = workflow.compile()

async def main():
    try:
        # Prompt user for email input (optional)
        user_email = input("Enter your email address: ")

        # Check if user exists in MongoDB
        user_doc = users_col.find_one({"email": user_email})
        if not user_doc:
            print(f"No user found with email {user_email}. Creating a new user.")
            # user_id = users_col.insert_one({"email": user_email}).inserted_id
            # print(f"User created with ID: {user_id}")
        else:
            print(f"User found with ID: {user_doc['_id']}")
            user_id = str(user_doc["_id"])  # Convert ObjectId to string

        # Initialize state with user details
        initial_state = EmailState(
            user_id=user_email,
            client_id=user_doc["_id"],
            other_party_email="nobarakugisaki2033@gmail.com"
        )

        # Execute workflow using asynchronous streaming (astream)
        async for step in graph.astream(initial_state, stream_mode=["values", "updates"]):
            print(step)  # Print each step's output as it streams

    except Exception as e:
        print(f"An error occurred during workflow execution: {e}")

# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())



