from googleapiclient.discovery import build
from datetime import datetime
import pandas as pd

EXCEL_FILE = "pod4jsr.xlsx"  # change to your actual excel filename

def search_gmail(creds, query: str, max_results: int = 10):
    service = build("gmail", "v1", credentials=creds)
    results = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    messages = results.get("messages", [])
    output = []
    for msg in messages:
        m = service.users().messages().get(
            userId="me", id=msg["id"], format="metadata",
            metadataHeaders=["From", "Subject", "Date"]
        ).execute()
        headers = {h["name"]: h["value"] for h in m["payload"]["headers"]}
        output.append({
            "from": headers.get("From"),
            "subject": headers.get("Subject"),
            "date": headers.get("Date"),
            "snippet": m.get("snippet"),
        })
    return output

def get_todays_events(creds):
    service = build("calendar", "v3", credentials=creds)
    now = datetime.utcnow()
    start = now.replace(hour=0, minute=0, second=0).isoformat() + "Z"
    end = now.replace(hour=23, minute=59, second=59).isoformat() + "Z"
    events_result = service.events().list(
        calendarId="primary", timeMin=start, timeMax=end,
        singleEvents=True, orderBy="startTime"
    ).execute()
    events = events_result.get("items", [])
    return [{
        "summary": e.get("summary"),
        "start": e["start"].get("dateTime", e["start"].get("date")),
        "attendees": [a.get("email") for a in e.get("attendees", [])],
    } for e in events]

def query_excel():
    df = pd.read_excel(EXCEL_FILE)
    return df.to_csv(index=False)