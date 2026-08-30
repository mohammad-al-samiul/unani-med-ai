#!/usr/bin/env python3
"""
UnaniMed AI — Auto Public HTTPS Tunnel & Webhook URL Generator
─────────────────────────────────────────────────────────────
Generates a 100% free, instant HTTPS URL using Cloudflare Tunnel or Pinggy.
No registration, no credit card, and zero setup required.
"""

import os
import sys
import time
import subprocess
import urllib.request
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
CLOUDFLARED_EXE = SCRIPTS_DIR / "cloudflared.exe"

CLOUDFLARED_DOWNLOAD_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"


def ensure_cloudflared():
    """Ensure cloudflared.exe exists or download it automatically."""
    if CLOUDFLARED_EXE.exists():
        return str(CLOUDFLARED_EXE)

    # Check if installed globally in PATH
    try:
        res = subprocess.run(["cloudflared", "--version"], capture_output=True, text=True)
        if res.returncode == 0:
            return "cloudflared"
    except Exception:
        pass

    # Download standalone binary directly
    print("[*] Downloading free standalone Cloudflare Tunnel binary (one-time setup)...")
    try:
        urllib.request.urlretrieve(CLOUDFLARED_DOWNLOAD_URL, str(CLOUDFLARED_EXE))
        print("[✓] Cloudflare Tunnel downloaded successfully!")
        return str(CLOUDFLARED_EXE)
    except Exception as e:
        print(f"[!] Could not download cloudflared: {e}")
        return None


def run_tunnel(port: int = 5678):
    """Run tunnel and parse the live public URL."""
    print("=" * 65)
    print(f"🚀 UnaniMed AI — Live Public HTTPS Tunnel for Port {port}")
    print("=" * 65)

    cf_binary = ensure_cloudflared()

    if cf_binary:
        cmd = [cf_binary, "tunnel", "--url", f"http://localhost:{port}"]
        print(f"[*] Starting Cloudflare tunnel on http://localhost:{port}...")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        tunnel_url = None
        for line in process.stdout:
            # Match https://xxxx.trycloudflare.com
            match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
            if match:
                tunnel_url = match.group(0)
                break

        if tunnel_url:
            print("\n" + "═" * 65)
            print("🎉 YOUR LIVE PUBLIC URL IS READY!")
            print("═" * 65)
            print(f"\n🌐 Base Public URL:\n   {tunnel_url}\n")
            print(f"📋 Facebook Messenger Webhook Callback URL (Paste this in Facebook):\n   👉 {tunnel_url}/webhook/webhook\n")
            print(f"🔑 Verify Token (Paste in Facebook):\n   👉 unani_verify_token_2026\n")
            print("═" * 65)
            print("⚠️ Keep this terminal window open while using the webhook.")
            print("═" * 65 + "\n")

            # Keep reading output so process doesn't block
            try:
                for line in process.stdout:
                    pass
            except KeyboardInterrupt:
                process.terminate()
            return

    # Fallback to SSH Pinggy tunnel if cloudflared unavailable
    print("[*] Starting free SSH Pinggy HTTPS tunnel...")
    ssh_cmd = f"ssh -o StrictHostKeyChecking=no -R 80:localhost:{port} a.pinggy.io"
    os.system(ssh_cmd)


if __name__ == "__main__":
    port_to_tunnel = 5678
    if len(sys.argv) > 1:
        try:
            port_to_tunnel = int(sys.argv[1])
        except ValueError:
            pass
    run_tunnel(port_to_tunnel)
