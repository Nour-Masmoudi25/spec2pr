"""Single bash-tool baseline; one JSONL record per model request."""
import json
import time
from pathlib import Path
import uuid

from agent.sandbox import run_in_container

STEP_LIMIT = 20
MODEL = "openai/gpt-oss-120b"
# Configured estimates inherited from the prototype, not provider invoices.
COST_PER_1M_INPUT = 0.15
COST_PER_1M_OUTPUT = 0.60
TOOLS = [{"type": "function", "function": {
    "name": "bash",
    "description": "Run a shell command inside the sandbox and return its output.",
    # gpt-oss keeps adding a "timeout" argument (and breaks the JSON when it
    # has no slot for it), so we declare it. It is accepted and ignored: the
    # sandbox always applies its own fixed time limit.
    "parameters": {"type": "object", "properties": {
        "command": {"type": "string", "description": "Shell command to run, as one JSON string (may contain newlines, e.g. a heredoc)."},
        "timeout": {"type": "integer", "description": "Optional; ignored. The sandbox has a fixed limit."}},
        "required": ["command"]},
}}]


def call_model(client, messages, max_waits=6):
    """Call the model; on a rate limit, wait and try again (not a new step).

    Returns (response, seconds_waited). Gives up after max_waits waits
    (about 6 minutes at most), e.g. when the daily quota is used up.
    """
    waited = 0
    for attempt in range(max_waits + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL, messages=messages, tools=TOOLS, tool_choice="auto")
            return response, waited
        except Exception as error:
            if type(error).__name__ != "RateLimitError" or attempt == max_waits:
                raise
            try:
                delay = float(error.response.headers.get("retry-after", 20))
            except Exception:
                delay = 20
            delay = min(max(delay, 1), 60)
            print(f"  rate limited, waiting {delay:.0f}s...", flush=True)
            time.sleep(delay)
            waited += delay


def run_agent(spec_text, workdir, *, run_dir=None, model_client=None,
              command_runner=None, step_limit=STEP_LIMIT):
    """Run against a fresh checkout prepared by bench/run.py.

    Optional dependencies are loaded only for real model runs. Injection lets
    the scorer select its Docker limits and tests exercise logging offline.
    Every API attempt, including a rejected request, consumes one step.
    """
    if step_limit < 1:
        raise ValueError("step_limit must be positive")
    if model_client is None:
        from dotenv import load_dotenv
        from groq import Groq
        load_dotenv()
        model_client = Groq(timeout=60, max_retries=0)
    command_runner = command_runner or run_in_container
    directory = Path(run_dir) if run_dir else Path("runs") / uuid.uuid4().hex[:8]
    directory.mkdir(parents=True, exist_ok=True)
    trace = directory / "trace.jsonl"
    trace.touch(exist_ok=False)
    messages = [{"role": "user", "content": spec_text}]
    malformed = 0
    status = "step_limit_reached"
    for step in range(1, step_limit + 1):
        row = {"step": step, "model": MODEL, "tokens_in": None, "tokens_out": None,
               "cost_usd": None, "tools": [], "note": None,
               "rates_per_million": {"input": COST_PER_1M_INPUT, "output": COST_PER_1M_OUTPUT}}
        try:
            response, waited = call_model(model_client, messages)
            if waited:
                row["rate_limit_wait_s"] = waited
        except Exception as error:
            # Keep the start of the message: it shows what the model tried to send.
            row["note"] = "API error: " + type(error).__name__ + ": " + str(error)[:400]
            with trace.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            if type(error).__name__ == "BadRequestError":
                malformed += 1
                if malformed < 3:
                    continue
            status = "api_error"
            break
        malformed = 0  # only 3 broken calls IN A ROW end the run
        usage = response.usage
        if usage is not None:
            row["tokens_in"] = usage.prompt_tokens
            row["tokens_out"] = usage.completion_tokens
            row["cost_usd"] = (usage.prompt_tokens * COST_PER_1M_INPUT
                               + usage.completion_tokens * COST_PER_1M_OUTPUT) / 1_000_000
        try:
            msg = response.choices[0].message
            row["assistant"] = msg.content
            calls = msg.tool_calls or []
            messages.append({"role": "assistant", "content": msg.content,
                             **({"tool_calls": [call.model_dump() for call in calls]} if calls else {})})
            if not calls:
                status = "stopped_by_model"
                row["note"] = "Model returned a final answer"
            for call in calls:
                command = None
                try:
                    args = json.loads(call.function.arguments)
                    command = args["command"]
                    if call.function.name != "bash" or not isinstance(command, str):
                        raise ValueError("Expected bash with a string command")
                    result = command_runner(command, str(Path(workdir).resolve()))
                except (ValueError, KeyError, TypeError) as error:
                    result = {"exit_code": -1, "output": "Invalid tool arguments: " + str(error)}
                row["tools"].append({"id": call.id, "input": call.function.arguments,
                                     "command": command, **result})
                messages.append({"role": "tool", "tool_call_id": call.id,
                                 "content": json.dumps(result, ensure_ascii=False)})
        except Exception as error:
            row["note"] = "Agent error: " + type(error).__name__
            status = "agent_error"
        finally:
            with trace.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        if status != "step_limit_reached":
            break
    return {"run_id": directory.name, "status": status, "steps": step}


if __name__ == "__main__":
    # Start fresh instead of appending to the historical task-1-workspace.
    from bench.run import main
    raise SystemExit(main(["--agent", "single", "--tasks", "bench/tasks/T01", "--n", "1"]))