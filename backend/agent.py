import json
import os
from dotenv import load_dotenv
from mistralai.client import Mistral
from google_auth import get_credentials
from tools import search_gmail, get_todays_events, query_excel

load_dotenv()

client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
creds = get_credentials()

tools = [
    {
        "type": "function",
        "function": {
            "name": "search_gmail",
            "description": "Search Gmail for emails matching a query (sender, subject, keywords). Use Gmail search syntax like from:name@example.com.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_todays_events",
            "description": "Get all of today's calendar events.",
            "parameters": {"type": "object", "properties": {}},
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_excel",
            "description": "Get the full contents of the loaded Excel sheet to answer a question about it.",
            "parameters": {"type": "object", "properties": {}},
        }
    },
]

def run_tool(name, tool_input):
    if name == "search_gmail":
        return json.dumps(search_gmail(creds, tool_input.get("query", "")))
    if name == "get_todays_events":
        return json.dumps(get_todays_events(creds))
    if name == "query_excel":
        return query_excel()
    return "Unknown tool"

def ask_agent(user_message: str, history: list = None):
    messages = history.copy() if history else []
    messages.append({"role": "user", "content": user_message})
    
    while True:
        response = client.chat.complete(
            model="mistral-small-latest",
            tools=tools,
            messages=messages,
            temperature=0.3,
        )
        
        response_message = response.choices[0].message
        
        if not response_message.tool_calls:
            return response_message.content

        # Append assistant's tool call message
        messages.append(response_message)
        
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            
            # Mistral returns arguments as a string or a dict depending on SDK version
            args = tool_call.function.arguments
            if isinstance(args, str):
                function_args = json.loads(args)
            else:
                function_args = args
                
            result = run_tool(function_name, function_args)
            
            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": result,
            })
