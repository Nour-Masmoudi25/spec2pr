import subprocess

MAX_OUTPUT_CHARS = 4000

def run_in_container(command: str, workdir: str) -> dict:
    """
    Runs `command` inside the sandbox container, with `workdir` (an absolute
    path on your PC) mounted as /workspace. Returns exit code and output.
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

    result = subprocess.run(
        docker_cmd,
        capture_output=True,
        text=True,
        timeout=60,
    )

    output = result.stdout + result.stderr
    truncated = len(output) > MAX_OUTPUT_CHARS
    if truncated:
        output = output[:MAX_OUTPUT_CHARS] + "\n...[output truncated]"

    return {
        "exit_code": result.returncode,
        "output": output,
        "truncated": truncated,
    }


if __name__ == "__main__":
    # quick manual test
    import os
    scratch = os.path.abspath("scratch")
    result = run_in_container("echo hello && ls", scratch)
    print(result)