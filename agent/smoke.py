import json
import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])

MODEL = "openai/gpt-oss-20b"  # if this fails, see the note below

tools = [{
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Run a shell command and return its output.",
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
}]

resp = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "List the files in the current directory using the bash tool."}],
    tools=tools,
    tool_choice="auto",
)

msg = resp.choices[0].message
print("Text:", msg.content)
print("Tool calls:", msg.tool_calls)
if msg.tool_calls:
    print("Arguments:", json.loads(msg.tool_calls[0].function.arguments))
print("Tokens used:", resp.usage)