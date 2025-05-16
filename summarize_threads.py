import dspy
from dspy import Signature, InputField, OutputField
from dotenv import load_dotenv
import os
from calendly_agent.states.Basic_state import EmailState

# Load environment variables for OpenAI API key
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set. Please check your environment variables.")

class SummarizeEmail(Signature):
    """Summarizes an email thread."""
    thread: str = InputField(desc="A full thread of emails (sender + body).")
    summary: str = OutputField(desc="The summary of the email conversation.")

def summarize_threads(state: EmailState):
    """
    Summarizes all email threads using OpenAI's model.
    Only processes conversations with the specified other_party_email.
    """
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    
    # Initialize language model explicitly
    lm = dspy.LM(model="gpt-3.5-turbo", api_key=api_key)
    
    # Create summarizer with explicit LM
    summarizer = dspy.Predict(SummarizeEmail)
    summaries = []
    
    # Debug: Print the structure of conversation_threads
    print(f"Number of conversation threads: {len(state.conversation_threads)}")
    
    filtered_threads = []
    # Filter threads to only include conversations with the specified other_party_email
    for thread in state.conversation_threads:
        has_other_party = False
        for msg in thread.get("messages", []):
            sender = msg.get("from", "")
            recipient = msg.get("to", "")
            if (state.other_party_email in sender) or (state.other_party_email in recipient):
                has_other_party = True
                break
        
        if has_other_party:
            filtered_threads.append(thread)
    
    print(f"Number of filtered threads: {len(filtered_threads)}")
    
    for thread in filtered_threads:
        try:
            # Debug: Print thread structure
            print(f"Processing thread ID: {thread.get('thread_id', 'unknown')}")
            
            # Construct thread text from messages
            messages = thread.get("messages", [])
            if not messages:
                print("No messages found in thread")
                continue
                
            thread_text = ""
            for msg in messages:
                sender = msg.get("from", "Unknown Sender")
                body = msg.get("body", "No Content")
                thread_text += f"{sender}: {body}\n\n"
            
            # Debug: Print thread text length
            print(f"Thread text length: {len(thread_text)}")
            
            # Use context manager to set LM for this operation
            with dspy.context(lm=lm):
                result = summarizer(thread=thread_text)
                summary = result.summary
                print(f"Generated summary: {summary}")
                summaries.append(summary)
            
        except Exception as e:
            print(f"Error summarizing thread: {e}")
            import traceback
            traceback.print_exc()
            summaries.append(f"Error summarizing this thread: {str(e)}")

    # Update state with summaries and generated content
    state.summarized_threads = summaries
    state.generated_content = "\n\n".join(summaries)
    
    return state
