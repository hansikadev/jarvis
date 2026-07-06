"""
agent.py
Mistral tool-use loop for Jarvis: Gmail, Calendar, and the JSR Excel tracker.

FIXES APPLIED (vs. previous version):
1. ask_agent() now accepts (user_message, history) — main.py was calling it
   with 2 args while the old signature only took 1, causing a TypeError on
   every single request (this was the actual cause of the generic
   "Sorry, I encountered an error" message in the frontend).
2. EXCEL_PATH corrected to the real filename "pod4jsr.xlsx" (was pointing
   at a non-existent "jsr_tracker.xlsx", which would crash at import time).
3. Uses MISTRAL_API_KEY from .env via Mistral's chat.complete() function
   calling, matching the mistralai SDK installed in your venv.

KEY DESIGN CHOICE (unchanged)
------------------------------
For Excel, Mistral does NOT see raw rows of data. It only sees the SCHEMA
(column names + a few sample values) so it can write correct pandas code.
That code is then actually executed by run_pandas_code() against the real
dataframe, and only the computed RESULT goes back to Mistral to explain.
"""

import json
import os
import pandas as pd
from dotenv import load_dotenv
from mistralai.client import Mistral

from google_auth import get_credentials
from tools import (
    search_gmail,
    get_todays_events,
    load_master_job_df,
    load_meeting_schedule,
    run_pandas_code,
)

load_dotenv()

client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
creds = get_credentials()

EXCEL_PATH = "pod4jsr.xlsx"  # matches the real file in backend/

# Load once at startup; refresh via reload_data() if the file changes
master_job_df = load_master_job_df(EXCEL_PATH)
meeting_df = load_meeting_schedule(EXCEL_PATH)


def _schema_summary(df: pd.DataFrame, n_samples: int = 3) -> str:
    """Give Mistral column names + a few sample values — not full rows."""
    lines = []
    for col in df.columns:
        samples = df[col].dropna().unique()[:n_samples]
        lines.append(f"- {col} (e.g. {list(samples)})")
    return "\n".join(lines)


tools = [
    {
        "type": "function",
        "function": {
            "name": "search_gmail",
            "description": (
                "Search Gmail for emails matching a query (sender, subject, "
                "keywords). Use Gmail search syntax like "
                "'from:client@company.com' or 'subject:invoice'."
            ),
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_todays_events",
            "description": "Get all of today's calendar events.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_job_tracker",
            "description": (
                "Run pandas code against the unified JSR job tracker "
                "dataframe (all brand tabs combined: Ganga, 4S Developers, "
                "etc., tagged with a 'Brand Name' column). Use this for any "
                "question about jobs, priority (XXL/XL/L), status, "
                "deliverables, deadlines, person assigned, department, "
                "projects, or per-brand counts. Write pandas code using the "
                "variable `df` for the dataframe, and assign your final "
                "answer to a variable called `result`."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Pandas code operating on `df`. Must set `result`.",
                    }
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_meeting_schedule",
            "description": (
                "Run pandas code against the 'Clients Meeting Schedule' "
                "dataframe (daily JSR call tracker: Month, Week, Date, Mode, "
                "Day, Time, attendance checkbox, remarks, and team "
                "assignments per Client Servicing / Design / Content / "
                "Strategy). Use this for questions about meeting days, "
                "who's on a call, or JSR schedule. Write pandas code using "
                "`df`, and assign the answer to `result`."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Pandas code operating on `df`. Must set `result`.",
                    }
                },
                "required": ["code"],
            },
        },
    },
]


def run_tool(name, tool_input):
    if name == "search_gmail":
        return json.dumps(search_gmail(creds, tool_input.get("query", "")))
    if name == "get_todays_events":
        return json.dumps(get_todays_events(creds))
    if name == "query_job_tracker":
        result = run_pandas_code(master_job_df, tool_input["code"])
        return json.dumps(result, default=str)
    if name == "query_meeting_schedule":
        result = run_pandas_code(meeting_df, tool_input["code"])
        return json.dumps(result, default=str)
    return "Unknown tool"


def build_system_prompt() -> str:
    return f"""You are Jarvis, a personal assistant agent with access to Gmail,
Google Calendar, and a JSR job tracker Excel workbook.

For any Excel/job-tracker question, write pandas code against the schema
below rather than guessing. Always assign your final answer to `result`.

JOB TRACKER SCHEMA (query_job_tracker -> df):
{_schema_summary(master_job_df)}

MEETING SCHEDULE SCHEMA (query_meeting_schedule -> df):
{_schema_summary(meeting_df)}
"""


def ask_agent(user_message: str, history: list = None) -> str:
    """
    history: list of {"role": "user"|"assistant", "content": str} from
    previous turns (as sent by the frontend). Optional — safe to omit.
    """
    messages = [{"role": "system", "content": build_system_prompt()}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    while True:
        response = client.chat.complete(
            model="mistral-large-latest",
            tools=tools,
            messages=messages,
            temperature=0.2,
        )

        response_message = response.choices[0].message

        if not response_message.tool_calls:
            return response_message.content

        messages.append(response_message)

        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            args = tool_call.function.arguments
            function_args = json.loads(args) if isinstance(args, str) else args

            result = run_tool(function_name, function_args)

            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": result,
            })


def reload_data():
    """Call this if the Excel file changes and you want fresh data without restarting."""
    global master_job_df, meeting_df
    master_job_df = load_master_job_df(EXCEL_PATH)
    meeting_df = load_meeting_schedule(EXCEL_PATH)


if __name__ == "__main__":
    print("Agent ready. Type 'exit' to quit.\n")
    history = []
    while True:
        q = input("You: ")
        if q.lower() == "exit":
            break
        answer = ask_agent(q, history)
        print("Agent:", answer, "\n")
        history.append({"role": "user", "content": q})
        history.append({"role": "assistant", "content": answer})
