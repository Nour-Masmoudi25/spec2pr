import json
import os
import time
import uuid

from dotenv import load_dotenv
from groq import Groq

from sandbox import run_in_container

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])

MODEL = "openai/gpt-oss-20b"  # same model you tested in smoke.py
STEP_LIMIT = 15

COST_PER_1M_INPUT = 0.075
COST_PER_1M_OUTPUT = 0.30

TOOLS = [{
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Run a shell command inside the sandbox and return its output.",
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
}]


def run_agent(spec_text: str, workdir: str) -> dict:
    run_id = str(uuid.uuid4())[:8]
    os.makedirs(f"runs/{run_id}", exist_ok=True)
    trace_path = f"runs/{run_id}/trace.jsonl"

    messages = [
        {"role": "user", "content": spec_text},
    ]

    for step in range(1, STEP_LIMIT + 1):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        msg = response.choices[0].message
        usage = response.usage


        if not msg.tool_calls:
            # Model is done — it answered in plain text instead of calling a tool.
            log_step(trace_path, step, None, None, usage, "stopped: model gave a final answer")
            messages.append({"role": "assistant", "content": msg.content})
            return {"run_id": run_id, "status": "stopped_by_model", "steps": step}

        # We only handle the first tool call per step, to keep this simple.
        tool_call = msg.tool_calls[0]
        args = json.loads(tool_call.function.arguments)
        command = args["command"]

        result = run_in_container(command, workdir)

        log_step(trace_path, step, command, result["exit_code"], usage, None)

        # Feed the model's own tool call back, then the result, so it has context.
        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [tool_call],
        })
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": result["output"],
        })

    return {"run_id": run_id, "status": "step_limit_reached", "steps": STEP_LIMIT}


def log_step(trace_path, step, command, exit_code, usage, note):
    if usage:
        cost = (
            usage.prompt_tokens / 1_000_000 * COST_PER_1M_INPUT
            + usage.completion_tokens / 1_000_000 * COST_PER_1M_OUTPUT
        )
    else:
        cost = None

    line = {
        "step": step,
        "command": command,
        "exit_code": exit_code,
        "tokens_in": usage.prompt_tokens if usage else None,
        "tokens_out": usage.completion_tokens if usage else None,
        "cost_usd": round(cost, 6) if cost is not None else None,
        "note": note,
    }
    with open(trace_path, "a") as f:
        f.write(json.dumps(line) + "\n")


if __name__ == "__main__":
    scratch = os.path.abspath("scratch")
    spec = "Create a file called hello.txt in the current directory containing the word hi. Then confirm it's there."
    result = run_agent(spec, scratch)
    print(result)