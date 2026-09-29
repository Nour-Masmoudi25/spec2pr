import subprocess

MAX_OUTPUT_CHARS = 4000
TIMEOUT_SECONDS = 60

def run_in_container(command: str, workdir: str) -> dict:
    """
    Runs `command` inside the sandbox container, with `workdir` (an absolute
    path on your PC) mounted as /workspace. Returns exit code and output.
    Never raises — timeouts and Docker errors come back as a normal result.
    """
    docker_cmd = [
        "docker", "run", "--rm",
        "--network", "none",
        "--read-only",
        "--tmpfs", "/tmp",
        "-v", f"{workdir}:/workspace",
        "sandbox:py312",
        "sh", "-c", command,
    ]

    try:
        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
        output = result.stdout + result.stderr
        exit_code = result.returncode

    except subprocess.TimeoutExpired:
        output = f"[command timed out after {TIMEOUT_SECONDS}s]"
        exit_code = -1

    except Exception as e:
        output = f"[sandbox error: {e}]"
        exit_code = -1

    truncated = len(output) > MAX_OUTPUT_CHARS
    if truncated:
        output = output[:MAX_OUTPUT_CHARS] + "\n...[output truncated]"

    return {
        "exit_code": exit_code,
        "output": output,
        "truncated": truncated,
    }