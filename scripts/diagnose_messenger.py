#!/usr/bin/env python3
"""
UnaniMed AI — Facebook Messenger Auto-Reply Diagnostics
───────────────────────────────────────────────────────
Checks every Meta-side setting required for the page to auto-reply to
*any* customer (not just page admins / app testers):

  1. Page access token validity, page name & granted scopes
  2. Whether the app is subscribed to the page and to the `messages` /
     `messaging_postbacks` webhook fields
  3. App mode (Development vs Live) and `pages_messaging` access level
  4. Optional live send test to a given PSID

Usage:
    export FB_PAGE_ACCESS_TOKEN=EAAG...        # required
    export FB_APP_ID=123...                    # optional (mode/permission check)
    export FB_APP_SECRET=abc...                # optional (mode/permission check)
    python scripts/diagnose_messenger.py
    python scripts/diagnose_messenger.py --send-test <PSID>
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

GRAPH = "https://graph.facebook.com/v18.0"
REQUIRED_FIELDS = {"messages", "messaging_postbacks"}


def graph_get(path: str, params: dict) -> dict:
    url = f"{GRAPH}/{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode("utf-8"))
    except Exception as e:  # network failure
        return {"error": {"message": str(e)}}


def graph_post(path: str, params: dict, body: dict) -> dict:
    url = f"{GRAPH}/{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode("utf-8"))
    except Exception as e:
        return {"error": {"message": str(e)}}


def fail(message: str) -> None:
    print(f"[FAIL] {message}")


def ok(message: str) -> None:
    print(f"[ OK ] {message}")


def warn(message: str) -> None:
    print(f"[WARN] {message}")


def check_token(token: str) -> str:
    """Return the page id, or exit if the token is unusable."""
    me = graph_get("me", {"fields": "id,name", "access_token": token})
    if "error" in me:
        fail(f"Page access token rejected: {me['error'].get('message')}")
        sys.exit(1)
    ok(f"Token belongs to page '{me.get('name')}' (id {me.get('id')})")
    return me["id"]


def check_subscription(page_id: str, token: str) -> None:
    subs = graph_get(f"{page_id}/subscribed_apps", {"access_token": token})
    if "error" in subs:
        fail(f"Cannot read subscribed apps: {subs['error'].get('message')}")
        return

    apps = subs.get("data", [])
    if not apps:
        fail(
            "No app is subscribed to this page. Run: "
            f"curl -X POST '{GRAPH}/{page_id}/subscribed_apps"
            "?subscribed_fields=messages,messaging_postbacks&access_token=<PAGE_TOKEN>'"
        )
        return

    for app in apps:
        fields = set(app.get("subscribed_fields", []))
        missing = REQUIRED_FIELDS - fields
        label = f"App '{app.get('name', app.get('id'))}'"
        if missing:
            fail(f"{label} is subscribed but missing webhook fields: {sorted(missing)}")
        else:
            ok(f"{label} is subscribed to messages + messaging_postbacks")


def check_app_mode(app_id: str, app_secret: str) -> None:
    app_token = f"{app_id}|{app_secret}"
    info = graph_get(app_id, {"fields": "name,link", "access_token": app_token})
    if "error" in info:
        warn(f"Cannot read app info: {info['error'].get('message')}")
        return
    ok(f"App '{info.get('name')}' reachable ({info.get('link')})")

    perms = graph_get(f"{app_id}/permissions", {"access_token": app_token})
    if "error" in perms:
        warn(
            "Cannot read app permission levels; check manually at "
            "App Dashboard > App Review > Permissions and Features > pages_messaging"
        )
        return

    for perm in perms.get("data", []):
        if perm.get("permission") == "pages_messaging":
            status = perm.get("status", "unknown")
            if status == "live":
                ok("pages_messaging has Advanced Access (works for all users)")
            else:
                fail(
                    f"pages_messaging access level is '{status}'. With Standard Access "
                    "only app admins/developers/testers receive auto-replies. Request "
                    "Advanced Access and switch the app to Live mode."
                )
            return
    warn("pages_messaging not listed for this app — request it in App Review.")


def send_test(psid: str, token: str) -> None:
    result = graph_post(
        "me/messages",
        {"access_token": token},
        {
            "recipient": {"id": psid},
            "messaging_type": "RESPONSE",
            "message": {"text": "UnaniMed AI diagnostics: auto-reply pipeline is reachable."},
        },
    )
    if "error" in result:
        err = result["error"]
        fail(f"Test send failed ({err.get('code')}/{err.get('error_subcode')}): {err.get('message')}")
        if err.get("code") == 10:
            print(
                "       Code 10 usually means the app lacks Advanced Access for "
                "pages_messaging, or the 24-hour messaging window has closed."
            )
    else:
        ok(f"Test message delivered to PSID {psid}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose Messenger auto-reply setup")
    parser.add_argument("--send-test", metavar="PSID", help="send a live test message to this PSID")
    args = parser.parse_args()

    token = os.getenv("FB_PAGE_ACCESS_TOKEN", "").strip()
    if not token:
        fail("FB_PAGE_ACCESS_TOKEN is not set.")
        return 1

    page_id = check_token(token)
    check_subscription(page_id, token)

    app_id = os.getenv("FB_APP_ID", "").strip()
    app_secret = os.getenv("FB_APP_SECRET", "").strip()
    if app_id and app_secret:
        check_app_mode(app_id, app_secret)
    else:
        warn("FB_APP_ID / FB_APP_SECRET not set — skipping app mode & permission check.")

    if args.send_test:
        send_test(args.send_test, token)

    return 0


if __name__ == "__main__":
    sys.exit(main())
