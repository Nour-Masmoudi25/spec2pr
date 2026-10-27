"""Shared checkout and Docker boundaries for trusted validation and scoring."""
import io
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile
import uuid

PROJECT = Path(__file__).resolve().parents[1]


def export_baseline(repo, commit, destination):
    """Export the recorded Git tree, with no history, secrets or benchmark files."""
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("base_commit must be a full Git commit hash")
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=repo,
                          capture_output=True, text=True, check=True).stdout.strip()
    relative = repo.resolve().relative_to(Path(root).resolve()).as_posix()
    archive = subprocess.run(["git", "archive", f"{commit}:{relative}"], cwd=root,
                             capture_output=True, check=True).stdout
    destination.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        for member in stream.getmembers():
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts or "\\" in member.name:
                raise ValueError("Unsafe baseline archive path")
            target = destination.joinpath(*path.parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(stream.extractfile(member).read())
            else:
                raise ValueError("Baseline archive must contain only regular files")


def docker_command(checkout, command, timeout=60, image="sandbox:py312"):
    """Run without network; kill the named container even on a host timeout.

    Only this checkout is mounted. The Docker socket and host credentials are
    never mounted; model API calls happen separately in the host process.
    """
    name = "spec2pr-" + uuid.uuid4().hex
    args = ["docker", "run", "--rm", "--name", name, "--network", "none",
            "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--pids-limit", "128", "--memory", "512m", "--cpus", "1",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m", "--user", "1000:1000",
            "-v", f"{Path(checkout).resolve()}:/workspace", "-w", "/workspace",
            "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1",
            "-e", "PYTHONPATH=/workspace/src:/workspace", image, *command]
    try:
        return subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout)
    finally:
        # --rm handles normal completion; rm -f handles timeouts/interruption.
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=15)


def preflight(image="sandbox:py312"):
    subprocess.run(["docker", "info"], capture_output=True, check=True, timeout=20)
    subprocess.run(["docker", "image", "inspect", image], capture_output=True,
                   check=True, timeout=20)


def source_changes(baseline, candidate):
    """Reject edits outside src/tasklib and return only changed source bytes.

    Caches created by normal pytest runs are ignored. All symlinks are rejected
    before reading files from the untrusted checkout.
    """
    ignored = {"__pycache__", ".pytest_cache"}

    def files(root):
        found = {}
        for path in root.rglob("*"):
            if path.is_symlink() or path.is_junction():
                raise ValueError("Candidate contains a link")
            rel = path.relative_to(root)
            if any(part in ignored for part in rel.parts):
                continue
            if path.is_file():
                if path.stat().st_size > 2_000_000:
                    raise ValueError("Candidate file exceeds 2 MB")
                found[rel.as_posix()] = path.read_bytes().replace(b"\r\n", b"\n")
        return found

    original, edited = files(baseline), files(candidate)
    changes = {}
    for name in original.keys() | edited.keys():
        if original.get(name) == edited.get(name):
            continue
        if not name.startswith("src/tasklib/"):
            raise ValueError(f"Candidate changed forbidden path: {name}")
        changes[name] = edited.get(name)
    return changes


def install_changes(checkout, changes):
    for name, content in changes.items():
        path = checkout / name
        if content is None:
            path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
