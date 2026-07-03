import anthropic
import json
import os
from dotenv import load_dotenv
from google_auth import get_credentials
from tools import search_gmail, get_todays_events, query_excel

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
creds = get_credentials()

tools = [
    {
        "name": "search_gmail",
        "description": "Search Gmail for emails matching a query (sender, subject, keywords). Use Gmail search syntax like from:name@example.com.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "get_todays_events",
        "description": "Get all of today's calendar events.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "query_excel",
        "description": "Get the full contents of the loaded Excel sheet to answer a question about it.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

def run_tool(name, tool_input):
    if name == "search_gmail":
        return json.dumps(search_gmail(creds, tool_input["query"]))
    if name == "get_todays_events":
        return json.dumps(get_todays_events(creds))
    if name == "query_excel":
        return query_excel()
    return "Unknown tool"

def ask_agent(user_message: str):
    messages = [{"role": "user", "content": user_message}]
    while True:
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=1500,
            tools=tools,
            messages=messages,
        )
        if response.stop_reason != "tool_use":
            return "".join(b.text for b in response.content if b.type == "text")

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = run_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })
        messages.append({"role": "user", "content": tool_results})

if __name__ == "__main__":
    print("Agent ready. Type 'exit' to quit.\n")
    while True:
        q = input("You: ")
        if q.lower() == "exit":
            break
        print("Agent:", ask_agent(q), "\n")
