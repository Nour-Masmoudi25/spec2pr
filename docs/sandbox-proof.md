# Sandbox proof

Checks run on 2026-11-01 on Windows with Docker Desktop, image `sandbox:py312`
(built from the repository `Dockerfile`: Python 3.12, user `agent` with uid 1000).

In three of the four checks the expected result is an **error**: the sandbox is
holding when the forbidden action fails.

| # | Question | Result |
|---|---|---|
| 1 | Can the container reach the internet? | No: name resolution fails, exit code 1 |
| 2 | Does it run as root? | No: `uid=1000(agent)` |
| 3 | Can it change the system outside `/workspace`? | No: "Read-only file system" |
| 4 | Can it write in `/workspace` only? | Yes in `/workspace`; no in `/usr` |

## 1. No internet

This is the supervisor's own Week 1 check.

```powershell
docker run --rm --network none sandbox:py312 python -c "import urllib.request as u; u.urlopen('https://pypi.org')"
$LASTEXITCODE
```

Output (traceback shortened to its first and last lines):

```text
Traceback (most recent call last):
  ...
socket.gaierror: [Errno -3] Temporary failure in name resolution

During handling of the above exception, another exception occurred:
  ...
urllib.error.URLError: <urlopen error [Errno -3] Temporary failure in name resolution>
1
```

The request to `pypi.org` fails because the container has no network, and the
exit code is non-zero (`1`). The benchmark runner starts every agent command with
the same `--network none` option.

## 2. Not root

```powershell
docker run --rm sandbox:py312 id
```

```text
uid=1000(agent) gid=1000(agent) groups=1000(agent)
```

## 3. Cannot change the system

```powershell
docker run --rm --read-only sandbox:py312 sh -c "touch /etc/test"
```

```text
touch: cannot touch '/etc/test': Read-only file system
```

## 4. Writes work only in the mounted `/workspace`

```powershell
mkdir $env:TEMP\labtest
docker run --rm --read-only -v "$env:TEMP\labtest:/workspace" sandbox:py312 sh -c "touch /workspace/ok && echo workspace-write-ok; touch /usr/test"
```

```text
workspace-write-ok
touch: cannot touch '/usr/test': Read-only file system
```

Creating `/workspace/ok` succeeds, creating `/usr/test` fails.

## Scope of this proof

- These four commands use the minimum options needed for each check. The
  benchmark runner (`bench/runtime.py`) also adds `--cap-drop ALL`,
  `--security-opt no-new-privileges`, a process limit (128), a memory limit
  (512 MB), one CPU and a small `/tmp` that cannot run programs (`noexec`).
  These extra limits are described in `bench/README.md` but not exercised by the
  commands above.
- `/tmp` is writable inside the container (temporary, in memory).
- This is process isolation. It does not claim to stop deliberately malicious
  code from tampering with its own grading process.
