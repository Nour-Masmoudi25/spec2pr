import json
import os
import uuid

from dotenv import load_dotenv
from groq import Groq, BadRequestError

from agent.sandbox import run_in_container

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])

STEP_LIMIT = 20
MODEL = "openai/gpt-oss-120b"
COST_PER_1M_INPUT = 0.15
COST_PER_1M_OUTPUT = 0.60

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

    messages = [{"role": "user", "content": spec_text}]

    for step in range(1, STEP_LIMIT + 1):
        response = None
        last_error = None
        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                )
                break
            except BadRequestError as e:
                last_error = e

        if response is None:
            log_step(trace_path, step, None, None, str(last_error), None,
                      "stopped: model produced malformed tool call JSON after 3 attempts")
            return {"run_id": run_id, "status": "model_tool_call_malformed", "steps": step}

        msg = response.choices[0].message
        usage = response.usage

        if not msg.tool_calls:
            log_step(trace_path, step, None, None, None, usage,
                      "stopped: model gave a final answer")
            messages.append({"role": "assistant", "content": msg.content})
            return {"run_id": run_id, "status": "stopped_by_model", "steps": step}

        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": msg.tool_calls,
        })

        for tool_call in msg.tool_calls:
            try:
                args = json.loads(tool_call.function.arguments)
                command = args["command"]
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                result = {"exit_code": -1, "output": f"[invalid tool arguments: {e}]", "truncated": False}
                command = None
            else:
                result = run_in_container(command, workdir)

            log_step(trace_path, step, command, result["exit_code"], result["output"], usage, None)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result["output"],
            })

    return {"run_id": run_id, "status": "step_limit_reached", "steps": STEP_LIMIT}


def log_step(trace_path, step, command, exit_code, output, usage, note):
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
        "output": output,
        "tokens_in": usage.prompt_tokens if usage else None,
        "tokens_out": usage.completion_tokens if usage else None,
        "cost_usd": round(cost, 6) if cost is not None else None,
        "note": note,
    }
    with open(trace_path, "a") as f:
        f.write(json.dumps(line) + "\n")


if __name__ == "__main__":
    import glob

    task_dir = os.path.abspath("runs/task-1-workspace")

    with open("bench/tasks/T01/spec.md") as f:
        spec = f.read()

    # Read every file under src/tasklib/ and show it to the model directly,
    # instead of making it explore the sandbox step by step.
    context = "\n\nCurrent contents of src/tasklib/:\n"
    for path in sorted(glob.glob(os.path.join(task_dir, "src", "tasklib", "*.py"))):
        rel_path = os.path.relpath(path, task_dir).replace("\\", "/")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        context += f"\n--- {rel_path} ---\n{content}\n"

    spec += context
    spec += (
        "\n\nYou have been given the full current contents of every file "
        "above. Do not re-read them with sed or cat."
        "\nOnly modify files under src/tasklib/. Do not modify tests."
        "\nDo NOT rewrite the whole file. APPEND only the new method to the "
        "end of src/tasklib/store.py, indented with 4 spaces to match the "
        "other methods in TaskStore, using this exact short pattern:"
        "\npython3 - <<'PYEOF'\n"
        "with open('src/tasklib/store.py', 'a') as f:\n"
        "    f.write('''\\n"
        "    def filter_by_priority(self, priority):\\n"
        "        ...YOUR METHOD BODY HERE...\\n"
        "''')\n"
        "PYEOF"
        "\nKeep this tool call short — only the new method text, nothing else."
        "\nNEVER use 'apply_patch' or diff/patch syntax."
        "\nAfter writing, run: python -m pytest tests/ -q"
    )
    result = run_agent(spec, task_dir)
    print(result)
