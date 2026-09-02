#!/usr/bin/env python3
import os
import time
import shutil
import subprocess
from pathlib import Path

appdata = os.environ.get("APPDATA", "")
ngrok_dir = Path(appdata) / "npm" / "node_modules" / "ngrok" / "bin"
ngrok_exe = ngrok_dir / "ngrok.exe"
ngtunnel_exe = ngrok_dir / "ngtunnel.exe"

print("Starting UnaniMed AI ngrok Persistent Tunnel Supervisor...")

while True:
    try:
        if not ngtunnel_exe.exists() and ngrok_exe.exists():
            shutil.copyfile(ngrok_exe, ngtunnel_exe)

        target_bin = ngtunnel_exe if ngtunnel_exe.exists() else ngrok_exe

        if not target_bin.exists():
            print("Ngrok binary missing. Re-extracting...")
            subprocess.run(["node", "./postinstall.js"], cwd=str(ngrok_dir.parent), capture_output=True)
            if ngrok_exe.exists():
                shutil.copyfile(ngrok_exe, ngtunnel_exe)

        print(f"Launching ngrok tunnel with domain: kabob-folic-prevent.ngrok-free.dev -> port 8010")
        cmd = [
            str(ngtunnel_exe if ngtunnel_exe.exists() else ngrok_exe),
            "http",
            "--url=kabob-folic-prevent.ngrok-free.dev",
            "8010",
            "--log", "stdout",
            "--log-format", "logfmt"
        ]

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in proc.stdout:
            print(line, end="", flush=True)

        proc.wait()
        print(f"Ngrok process exited with code {proc.returncode}. Restarting in 3 seconds...")
    except Exception as e:
        print(f"Supervisor error: {e}. Retrying in 5 seconds...")
        time.sleep(5)
    time.sleep(3)
