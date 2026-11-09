"""Fail-closed Linux offline verifier; never fall back to an ambient shell."""
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import subprocess
import tempfile
import time


RUNNER = """import json, sys, unittest
sys.path.insert(0, '/workspace')
suite = unittest.defaultTestLoader.discover('/workspace/tests')
result = unittest.TextTestRunner(verbosity=1).run(suite)
passed = result.wasSuccessful() and result.testsRun > 0 and not result.skipped
print('ATTUNE_CHECK=' + json.dumps({'tests_run': result.testsRun, 'passed': passed}), flush=True)
sys.exit(0 if passed else 1)
"""


def verify(project, permitted, timeout: float = 20):
    """Execute real unittest code inside fresh namespaces, without host secrets.

    The callback rechecks live authority while the child runs. This is a Linux
    process/filesystem/network boundary, not a VM or a semantic-quality judge.
    """
    bwrap, prlimit = shutil.which("bwrap"), shutil.which("prlimit")
    if not bwrap or not prlimit or not Path("/usr/bin/python3").is_file():
        raise ValueError("Offline preview requires Linux Bubblewrap, prlimit and /usr/bin/python3; no fallback")
    # RLIMIT_NPROC counts the UID's existing host threads, not just this worker.
    # Keep a finite ceiling without rejecting this host's normal thread load.
    command = [prlimit, "--as=536870912", "--cpu=15", "--fsize=1048576", "--nofile=64", "--nproc=1024", "--",
               bwrap, "--unshare-all", "--die-with-parent", "--new-session", "--cap-drop", "ALL"]
    for mount in ("/usr", "/lib", "/lib64"):
        if Path(mount).exists():
            command += ["--ro-bind", mount, mount]
    command += ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
                "--ro-bind", str(Path(project).resolve()), "/workspace", "--chdir", "/workspace",
                "--clearenv", "--setenv", "PATH", "/usr/bin", "--setenv", "HOME", "/tmp",
                "--setenv", "LANG", "C.UTF-8", "--setenv", "TZ", "UTC", "--",
                "/usr/bin/python3", "-I", "-B", "-c", RUNNER]
    if not permitted():
        raise ValueError("Build authority changed before execution")
    reason = None
    # Separate runner completion from arbitrary test stdout. This is framing,
    # not attestation: project Python can still inspect/alter its own runner.
    marker = "ATTUNE_CHECK_" + secrets.token_hex(16) + "="
    command[-1] = RUNNER.replace("ATTUNE_CHECK=", marker)
    with tempfile.TemporaryFile() as log:
        process = subprocess.Popen(command, stdout=log, stderr=log, cwd="/", env={"PATH": "/usr/bin:/bin"}, start_new_session=True)
        deadline = time.monotonic() + timeout
        try:
            while process.poll() is None:
                if time.monotonic() >= deadline or not permitted():
                    reason = "timeout" if time.monotonic() >= deadline else "authority_revoked"
                    os.killpg(process.pid, signal.SIGKILL)
                    break
                time.sleep(.05)
            process.wait(timeout=5)
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
        log.seek(0, os.SEEK_END)
        log.seek(max(0, log.tell() - 64000))
        output = log.read(64000).decode("utf-8", errors="replace")
    matches = re.findall(r'^' + re.escape(marker) + r'(\{[^\n]+\})$', output, flags=re.M)
    try:
        check = json.loads(matches[0]) if len(matches) == 1 else {}
    except ValueError:
        check = {}
    valid = (isinstance(check, dict) and type(check.get("passed")) is bool
             and type(check.get("tests_run")) is int and 0 <= check["tests_run"] <= 1000000)
    if not valid:
        check = {"tests_run": 0, "passed": False}
        reason = reason or "invalid_test_report"
    passed = not reason and process.returncode == 0 and check["passed"] and check["tests_run"] > 0
    return {"backend": "linux-bubblewrap", "passed": passed, "returncode": process.returncode,
            "tests_run": check.get("tests_run", 0), "reason": reason, "output": output,
            "command": "python3 -I -B <Attune unittest discovery runner>",
            "network": "unshared namespace", "source_mount": "read-only selected files", "ambient_credentials": "not mounted or inherited"}
