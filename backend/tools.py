"""
tools.py
Tool functions for the Jarvis agent: Gmail, Calendar, and Excel/JSR tracker.

EXCEL / JSR NOTES
-----------------
Workbook structure (confirmed from real file):
- Each brand (Ganga, 4S Developers, etc.) has its OWN TAB.
- Every brand tab shares the SAME schema, but the real header row is NOT
  row 1 — there's a title row above it (e.g. "Ganga", merged banner text,
  "VIDEO" label, etc.). The real column headers sit on the row starting
  with "JOB ID". We detect that row automatically instead of hardcoding
  an index, since it can shift slightly between tabs.
- "Projects" is a sub-grouping WITHIN a brand tab (e.g. Ganga's tab has
  Projects like "Ganga919", "Swarnim", "Tathastu", "Anantam 85"). It is
  NOT a separate tab.
- Two tabs are structurally different and must be excluded from the job
  concat: "Clients Meeting Schedule" (a calendar/attendance tracker) and
  any SOW / scope-of-work reference doc (e.g. "Panasonic SOW") which is
  descriptive text, not tabular job data.
"""

from googleapiclient.discovery import build
from datetime import datetime
import pandas as pd

# ---------------------------------------------------------------------
# Config: tabs to exclude from the unified job dataframe
# ---------------------------------------------------------------------
NON_JOB_SHEETS = {
    "Clients Meeting Schedule",
    "Panasonic SOW",
    "SOW",
    "Summary",
    "Dashboard",
}

JOB_ID_MARKER = "JOB ID"  # string that identifies the real header row


# ---------------------------------------------------------------------
# GMAIL
# ---------------------------------------------------------------------
def search_gmail(creds, query: str, max_results: int = 10):
    service = build("gmail", "v1", credentials=creds)
    results = service.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()
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


# ---------------------------------------------------------------------
# CALENDAR
# ---------------------------------------------------------------------
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


# ---------------------------------------------------------------------
# EXCEL / JSR TRACKER
# ---------------------------------------------------------------------
def _find_header_row(raw_df: pd.DataFrame):
    """
    Scan the first ~10 rows of a raw (headerless) read for the row that
    contains 'JOB ID' — that's the real header row for this tab.
    Returns the row index (0-based) to use as header, or None if no
    suitable header row exists (e.g. the sheet is empty, near-empty, or
    a pivot-table artifact with too few rows to have a real header).
    """
    for i in range(min(10, len(raw_df))):
        row_values = raw_df.iloc[i].astype(str).str.strip().str.upper()
        if (row_values == JOB_ID_MARKER).any():
            return i
    # No "JOB ID" row found. Only fall back to row 1 if the sheet
    # actually has at least 2 rows — otherwise there's nothing usable
    # here (e.g. hidden pivot-table tabs with just a title cell).
    if len(raw_df) > 1:
        return 1
    return None


def load_master_job_df(excel_path: str) -> pd.DataFrame:
    """
    Load every brand tab, auto-detect the real header row per tab,
    tag each row with its Brand Name (the tab name), and concat into
    one unified dataframe covering the whole workbook.

    Sheets that are empty, too small to have a real header, or that
    raise any read error (e.g. malformed pivot-table tabs) are skipped
    rather than crashing the whole load.
    """
    xls = pd.ExcelFile(excel_path)
    all_dfs = []

    for sheet_name in xls.sheet_names:
        if sheet_name.strip() in NON_JOB_SHEETS:
            continue

        try:
            # Read raw first to find where the real header row is
            raw = pd.read_excel(xls, sheet_name=sheet_name, header=None)

            header_row = _find_header_row(raw)
            if header_row is None:
                # Nothing usable in this sheet (empty / near-empty /
                # pivot-table artifact) — skip it silently.
                continue

            df = pd.read_excel(xls, sheet_name=sheet_name, header=header_row)

            # Skip tabs that don't actually have a JOB ID column
            # (guards against unexpected/non-job tabs slipping through)
            cols_upper = [str(c).strip().upper() for c in df.columns]
            if JOB_ID_MARKER not in cols_upper:
                continue

            # Drop fully-empty rows (common in these sheets — blank template rows)
            df = df.dropna(how="all")

            # Clean column names: strip whitespace/newlines
            df.columns = [str(c).strip().replace("\n", " ") for c in df.columns]

            df["Brand Name"] = sheet_name.strip()
            all_dfs.append(df)

        except Exception as e:
            # Don't let one malformed/unusual tab (e.g. a pivot table
            # with an unexpected layout) take down the whole load.
            print(f"[load_master_job_df] Skipping sheet '{sheet_name}': {e}")
            continue

    if not all_dfs:
        raise ValueError("No job tabs found — check NON_JOB_SHEETS config or header detection.")

    master_df = pd.concat(all_dfs, ignore_index=True, sort=False)
    return master_df


def load_meeting_schedule(excel_path: str) -> pd.DataFrame:
    """
    Load the 'Clients Meeting Schedule' tab separately — this is a
    calendar/attendance tracker, not job data, so it gets its own loader
    and its own tool for the agent to call.
    """
    xls = pd.ExcelFile(excel_path)
    sheet_name = next(
        (s for s in xls.sheet_names if "meeting" in s.lower()), None
    )
    if sheet_name is None:
        raise ValueError("Could not find a 'Clients Meeting Schedule' tab.")

    # Real headers here start a few rows down too (row with "Month" etc.)
    raw = pd.read_excel(xls, sheet_name=sheet_name, header=None)
    header_row = None
    for i in range(min(10, len(raw))):
        row_values = raw.iloc[i].astype(str).str.strip().str.upper()
        if (row_values == "MONTH").any():
            header_row = i
            break
    if header_row is None:
        header_row = 3  # fallback based on observed layout

    # Guard against a fallback header row that exceeds the sheet's
    # actual row count (would otherwise raise a pandas ValueError).
    if header_row >= len(raw):
        raise ValueError(
            f"Sheet '{sheet_name}' has only {len(raw)} rows — "
            "too few to contain a real meeting-schedule header."
        )

    df = pd.read_excel(xls, sheet_name=sheet_name, header=header_row)
    df.columns = [str(c).strip().replace("\n", " ") for c in df.columns]
    df = df.dropna(how="all")
    return df


def run_pandas_code(df: pd.DataFrame, code: str):
    """
    Execute Claude-generated pandas code against a given dataframe.
    The code MUST assign its final answer to a variable called `result`.
    This is safer/more accurate than passing raw CSV text for Claude to
    eyeball, especially for counts, filters, and aggregations.
    """
    local_vars = {"df": df, "pd": pd}
    try:
        exec(code, {"pd": pd}, local_vars)
        return local_vars.get("result", "No `result` variable was set by the code.")
    except Exception as e:
        return f"Error running pandas code: {e}"
