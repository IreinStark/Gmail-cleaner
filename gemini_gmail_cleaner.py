import os
import json
from typing import Dict, Any, List

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import google.generativeai as genai

# ----- CONFIG -----
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
QUERY = "category:promotions newer_than:30d"
MAX_RESULTS = 50
DRY_RUN = True  # Set to False when you're ready to actually process emails
SAFE_ARCHIVE = True  # Archives instead of permanently deleting

# Custom labels for organizing processed emails
KEEP_LABEL = "AI_KEEP"
ARCHIVE_LABEL = "AI_ARCHIVED" 
REVIEW_LABEL = "AI_REVIEW"

# Load environment variables
load_dotenv()

# Configure Gemini API
try:
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    genai.configure(api_key=gemini_api_key)
    print("✓ Gemini API configured successfully")
except Exception as e:
    print(f"✗ Error configuring Gemini API: {e}")
    exit(1)

# ----- GMAIL AUTHENTICATION -----
def get_gmail_service():
    """Authenticate and return Gmail service object"""
    creds = None
    
    # Token file stores the user's access and refresh tokens
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    # If there are no valid credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists("credentials.json"):
                print("✗ credentials.json not found!")
                print("Please download OAuth credentials from Google Cloud Console")
                exit(1)
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    
    return build("gmail", "v1", credentials=creds)

def list_messages(service, query: str, max_results: int) -> List[str]:
    """Get list of message IDs matching the query"""
    try:
        result = service.users().messages().list(
            userId="me", 
            q=query, 
            maxResults=max_results
        ).execute()
        messages = result.get("messages", [])
        return [msg["id"] for msg in messages]
    except HttpError as error:
        print(f"An error occurred: {error}")
        return []

def get_header(headers: List[Dict[str, str]], name: str) -> str:
    """Extract specific header value from email headers"""
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""

def fetch_email_preview(service, msg_id: str) -> Dict[str, Any]:
    """Fetch email metadata for classification"""
    try:
        message = service.users().messages().get(
            userId="me",
            id=msg_id,
            format="metadata",
            metadataHeaders=["From", "Subject", "Date", "List-Unsubscribe"]
        ).execute()
        
        headers = message.get("payload", {}).get("headers", [])
        
        return {
            "id": msg_id,
            "from": get_header(headers, "From"),
            "subject": get_header(headers, "Subject"),
            "date": get_header(headers, "Date"),
            "list_unsubscribe": get_header(headers, "List-Unsubscribe"),
            "snippet": message.get("snippet", "")
        }
    except HttpError as error:
        print(f"An error occurred fetching message {msg_id}: {error}")
        return None

def ensure_label_exists(service, label_name: str) -> str:
    """Create label if it doesn't exist, return label ID"""
    try:
        # Get all labels
        labels_result = service.users().labels().list(userId="me").execute()
        labels = labels_result.get("labels", [])
        
        # Check if label already exists
        for label in labels:
            if label["name"] == label_name:
                return label["id"]
        
        # Create new label
        label_body = {
            "name": label_name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show"
        }
        created_label = service.users().labels().create(
            userId="me", 
            body=label_body
        ).execute()
        print(f"✓ Created label: {label_name}")
        return created_label["id"]
        
    except HttpError as error:
        print(f"An error occurred creating label {label_name}: {error}")
        return None

# ----- GEMINI AI CLASSIFIER -----
CLASSIFIER_SYSTEM_PROMPT = """
You are an intelligent email classifier designed to help manage Gmail promotional emails.

Your task is to classify emails into one of three categories:

KEEP - Important emails that should be preserved:
- Receipts and invoices from purchases
- Order confirmations and shipping notifications  
- Account updates, billing statements, and security notices
- Flight/hotel bookings and travel confirmations
- Password reset and security alerts
- Legitimate transactional emails

ARCHIVE - Potentially useful promotional content:
- Newsletters from subscribed services
- Educational content or industry updates
- Promotional emails that might have some value
- Emails from known brands the user likely interacts with

DELETE - Unwanted promotional emails:
- Bulk advertising and spam
- Repeated discount offers and sales promotions
- Emails from unknown senders
- Generic marketing blasts
- Obvious promotional content with no personal relevance

When in doubt, prefer ARCHIVE over DELETE to avoid losing potentially important emails.

You must respond with ONLY valid JSON in this exact format:
{"action": "KEEP|ARCHIVE|DELETE", "confidence": 0.85, "reason": "Brief explanation"}

The confidence should be a float between 0.0 and 1.0.
"""

def classify_email_with_ai(email_data: Dict[str, Any]) -> Dict[str, Any]:
    """Use Gemini AI to classify the email"""
    if not email_data:
        return {"action": "KEEP", "confidence": 0.0, "reason": "No email data"}
    
    # Prepare email content for classification
    email_content = f"""
From: {email_data.get('from', 'Unknown')}
Subject: {email_data.get('subject', 'No Subject')}
Date: {email_data.get('date', 'Unknown')}
Snippet: {email_data.get('snippet', 'No preview available')}
Has Unsubscribe Link: {'Yes' if email_data.get('list_unsubscribe') else 'No'}

Please classify this promotional email according to the rules provided.
"""
    
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content([
            CLASSIFIER_SYSTEM_PROMPT,
            email_content
        ])
        
        # Parse JSON response
        result = json.loads(response.text.strip())
        
        # Validate response format
        if "action" not in result or result["action"] not in ["KEEP", "ARCHIVE", "DELETE"]:
            raise ValueError("Invalid action in response")
        
        # Ensure confidence is a float
        result["confidence"] = float(result.get("confidence", 0.5))
        result["reason"] = result.get("reason", "No reason provided")
        
        return result
        
    except json.JSONDecodeError as e:
        print(f"✗ Failed to parse AI response as JSON: {e}")
        return {"action": "KEEP", "confidence": 0.0, "reason": "JSON parse error"}
    except Exception as e:
        print(f"✗ Error with AI classification: {e}")
        return {"action": "KEEP", "confidence": 0.0, "reason": f"AI error: {str(e)}"}

# ----- EMAIL ACTIONS -----
def archive_email(service, msg_id: str):
    """Remove email from inbox (archive it)"""
    try:
        service.users().messages().modify(
            userId="me",
            id=msg_id,
            body={"removeLabelIds": ["INBOX"]}
        ).execute()
        return True
    except HttpError as error:
        print(f"Error archiving message {msg_id}: {error}")
        return False

def add_label_to_email(service, msg_id: str, label_id: str):
    """Add a custom label to an email"""
    try:
        service.users().messages().modify(
            userId="me",
            id=msg_id,
            body={"addLabelIds": [label_id]}
        ).execute()
        return True
    except HttpError as error:
        print(f"Error adding label to message {msg_id}: {error}")
        return False

def trash_email(service, msg_id: str):
    """Move email to trash"""
    try:
        service.users().messages().trash(userId="me", id=msg_id).execute()
        return True
    except HttpError as error:
        print(f"Error trashing message {msg_id}: {error}")
        return False

# ----- MAIN PROCESSING LOGIC -----
def main():
    print("🤖 Starting Gemini Gmail Cleaner...")
    print(f"📧 Query: {QUERY}")
    print(f"🔄 Max results: {MAX_RESULTS}")
    print(f"🧪 Dry run mode: {DRY_RUN}")
    print(f"🛡️ Safe archive mode: {SAFE_ARCHIVE}")
    print("-" * 60)
    
    try:
        # Initialize Gmail service
        print("🔐 Authenticating with Gmail...")
        service = get_gmail_service()
        print("✓ Gmail authentication successful")
        
        # Ensure custom labels exist
        print("🏷️ Setting up labels...")
        keep_label_id = ensure_label_exists(service, KEEP_LABEL)
        archive_label_id = ensure_label_exists(service, ARCHIVE_LABEL)
        review_label_id = ensure_label_exists(service, REVIEW_LABEL)
        
        if not all([keep_label_id, archive_label_id, review_label_id]):
            print("✗ Failed to create required labels")
            return
        
        # Get promotional emails
        print(f"📨 Fetching promotional emails...")
        message_ids = list_messages(service, QUERY, MAX_RESULTS)
        
        if not message_ids:
            print("✅ No promotional emails found matching criteria")
            return
        
        print(f"📊 Found {len(message_ids)} promotional emails to process")
        print("-" * 60)
        
        # Process each email
        stats = {"keep": 0, "archive": 0, "delete": 0, "errors": 0}
        
        for i, msg_id in enumerate(message_ids, 1):
            print(f"\n[{i:2d}/{len(message_ids)}] Processing email...")
            
            # Fetch email data
            email_data = fetch_email_preview(service, msg_id)
            if not email_data:
                stats["errors"] += 1
                continue
            
            # Classify with AI
            decision = classify_email_with_ai(email_data)
            action = decision.get("action", "KEEP").upper()
            confidence = decision.get("confidence", 0.0)
            reason = decision.get("reason", "No reason provided")
            
            # Apply confidence threshold for safety
            if confidence < 0.6 and action == "DELETE":
                action = "ARCHIVE"
                reason += " (low confidence, archived instead)"
            
            # Display decision
            subject_preview = email_data.get("subject", "No Subject")[:50]
            sender_preview = email_data.get("from", "Unknown")[:30]
            
            print(f"📧 From: {sender_preview}")
            print(f"📝 Subject: {subject_preview}")
            print(f"🤖 Decision: {action} (confidence: {confidence:.2f})")
            print(f"💭 Reason: {reason}")
            
            # Take action (if not in dry run mode)
            if not DRY_RUN:
                success = False
                
                if action == "KEEP":
                    success = add_label_to_email(service, msg_id, keep_label_id)
                    stats["keep"] += 1
                    
                elif action == "ARCHIVE":
                    success = (add_label_to_email(service, msg_id, archive_label_id) and
                             archive_email(service, msg_id))
                    stats["archive"] += 1
                    
                elif action == "DELETE":
                    if SAFE_ARCHIVE:
                        # Archive instead of delete for safety
                        success = (add_label_to_email(service, msg_id, archive_label_id) and
                                 archive_email(service, msg_id))
                        print("🛡️ Archived instead of deleted (safe mode)")
                    else:
                        success = trash_email(service, msg_id)
                    stats["delete"] += 1
                
                if not success:
                    stats["errors"] += 1
                    print("✗ Failed to process email")
                else:
                    print("✓ Email processed successfully")
            else:
                # Just count for dry run stats
                stats[action.lower()] += 1
        
        # Final summary
        print("\n" + "=" * 60)
        print("📊 PROCESSING COMPLETE")
        print("=" * 60)
        print(f"📧 Total emails processed: {len(message_ids)}")
        print(f"✅ Keep: {stats['keep']}")
        print(f"📦 Archive: {stats['archive']}")
        print(f"🗑️ Delete: {stats['delete']}")
        print(f"❌ Errors: {stats['errors']}")
        
        if DRY_RUN:
            print("\n🧪 This was a DRY RUN - no actual changes were made")
            print("💡 Set DRY_RUN = False to apply these actions")
        
        print("\n✅ Gmail cleaning session completed!")
        
    except HttpError as error:
        print(f"✗ Gmail API error: {error}")
    except Exception as error:
        print(f"✗ Unexpected error: {error}")

if __name__ == "__main__":
    main()

