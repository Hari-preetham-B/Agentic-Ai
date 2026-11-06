#!/usr/bin/env python3
import subprocess
import time
import urllib.request

proc = subprocess.Popen(
    ["npm", "run", "dev"],
    cwd=r"C:\Users\harip\Documents\CareerTwin\apps\web",
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1
)

# Wait and read output
for i in range(20):
    time.sleep(2)
    # Check if process is still running
    if proc.poll() is not None:
        print(f"Process exited with code {proc.poll()}")
        stdout = proc.stdout.read()
        stderr = proc.stderr.read()
        print(f"Stdout: {stdout[-300:] if stdout else ''}")
        print(f"Stderr: {stderr[-300:] if stderr else ''}")
        break
    # Check port
    try:
        r = urllib.request.urlopen("http://localhost:3000/", timeout=3)
        print(f"After {i*2}s: Port 3000 OK - status {r.status}")
        content = r.read(200).decode("utf-8", errors="replace")
        print(f"Content preview: {content}")
        break
    except Exception as e:
        print(f"After {i*2}s: Port 3000 not ready yet")

print(f"Final process exit code: {proc.poll()}")