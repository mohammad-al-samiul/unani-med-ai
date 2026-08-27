#!/usr/bin/env python3
"""
Automated Backup Script  (polished v2)
────────────────────────────────────────
Changes from v1:
  • Telegram notification on success AND failure
  • Compression is now actually called per backup item (zip every backup)
  • Summary report at the end with total size saved
  • Separate backup dirs for config files (Modelfile, safety_config, etc.)
  • Idempotent: if a DB file doesn't exist yet, skips gracefully

Usage:
    python backup_script.py            # manual run
    # or schedule via Windows Task Scheduler to run daily
"""

import json
import logging
import os
import shutil
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import requests

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("backup.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("backup")

# ── Telegram helpers ───────────────────────────────────────────────────────────

def _telegram_notify(message: str, config: dict) -> bool:
    """Send a Telegram message. Returns True on success."""
    bot_token = config.get("telegram_bot_token", "")
    chat_id   = config.get("telegram_chat_id", "")
    if not bot_token or not chat_id:
        logger.info("Telegram credentials not configured — skipping notification.")
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as exc:
        logger.warning("Telegram notification failed: %s", exc)
        return False


# ── Backup helpers ─────────────────────────────────────────────────────────────

def _ensure_dir(path: str) -> bool:
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as exc:
        logger.error("Cannot create directory %s: %s", path, exc)
        return False


def _zip_item(src: str) -> str:
    """Compress a file or folder into <src>.zip. Returns zip path."""
    zip_path = src + ".zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        if os.path.isfile(src):
            zf.write(src, os.path.basename(src))
            os.remove(src)
        elif os.path.isdir(src):
            for root, _dirs, files in os.walk(src):
                for file in files:
                    fp = os.path.join(root, file)
                    zf.write(fp, os.path.relpath(fp, os.path.dirname(src)))
            shutil.rmtree(src)
    return zip_path


def _backup_sqlite(source: str, backup_dir: str, timestamp: str, compress: bool) -> Dict:
    """Backup SQLite DB with integrity check. Returns result dict."""
    result = {"type": "sqlite", "source": source, "status": "skipped", "size_bytes": 0}
    if not os.path.exists(source):
        logger.warning("SQLite DB not found: %s", source)
        return result
    if not _ensure_dir(backup_dir):
        result["status"] = "failed"
        return result

    # Integrity check
    try:
        conn = sqlite3.connect(source)
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        conn.close()
        if ok != "ok":
            raise ValueError(f"Integrity check failed: {ok}")
    except Exception as exc:
        logger.error("SQLite integrity check failed for %s: %s", source, exc)
        result["status"] = "failed"
        return result

    dest = os.path.join(backup_dir, f"{os.path.basename(source)}.{timestamp}")
    try:
        shutil.copy2(source, dest)
        if compress:
            dest = _zip_item(dest)
        result["status"] = "success"
        result["dest"] = dest
        result["size_bytes"] = os.path.getsize(dest)
        logger.info("SQLite backup → %s  (%d bytes)", dest, result["size_bytes"])
    except Exception as exc:
        logger.error("SQLite backup failed: %s", exc)
        result["status"] = "failed"
    return result


def _backup_chromadb(source: str, backup_dir: str, timestamp: str, compress: bool) -> Dict:
    """Backup ChromaDB persistence folder."""
    result = {"type": "chromadb", "source": source, "status": "skipped", "size_bytes": 0}
    if not os.path.exists(source):
        logger.warning("ChromaDB persist folder not found: %s", source)
        return result
    if not _ensure_dir(backup_dir):
        result["status"] = "failed"
        return result

    dest = os.path.join(backup_dir, f"{os.path.basename(source)}.{timestamp}")
    try:
        shutil.copytree(source, dest)
        if compress:
            dest = _zip_item(dest)
        result["status"] = "success"
        result["dest"] = dest
        result["size_bytes"] = os.path.getsize(dest)
        logger.info("ChromaDB backup → %s  (%d bytes)", dest, result["size_bytes"])
    except Exception as exc:
        logger.error("ChromaDB backup failed: %s", exc)
        result["status"] = "failed"
    return result


def _backup_file(source: str, backup_dir: str, timestamp: str, compress: bool) -> Dict:
    """Backup a single config/data file."""
    result = {"type": "file", "source": source, "status": "skipped", "size_bytes": 0}
    if not os.path.exists(source):
        logger.warning("File not found: %s", source)
        return result
    if not _ensure_dir(backup_dir):
        result["status"] = "failed"
        return result

    dest = os.path.join(backup_dir, f"{os.path.basename(source)}.{timestamp}")
    try:
        shutil.copy2(source, dest)
        if compress:
            dest = _zip_item(dest)
        result["status"] = "success"
        result["dest"] = dest
        result["size_bytes"] = os.path.getsize(dest)
        logger.info("File backup → %s  (%d bytes)", dest, result["size_bytes"])
    except Exception as exc:
        logger.error("File backup failed: %s", exc)
        result["status"] = "failed"
    return result


def _cleanup_old(backup_dir: str, retention_days: int) -> int:
    """Delete backup files/folders older than retention_days. Returns removed count."""
    if not os.path.exists(backup_dir):
        return 0
    cutoff = datetime.now().timestamp() - retention_days * 86400
    removed = 0
    for item in os.listdir(backup_dir):
        full = os.path.join(backup_dir, item)
        try:
            mtime = os.path.getmtime(full)
            if mtime < cutoff:
                if os.path.isfile(full):
                    os.remove(full)
                elif os.path.isdir(full):
                    shutil.rmtree(full)
                removed += 1
                logger.info("Removed old backup: %s", full)
        except Exception as exc:
            logger.warning("Could not remove %s: %s", full, exc)
    return removed


# ── Config ─────────────────────────────────────────────────────────────────────

def _load_config(path: str = "backup_config.json") -> dict:
    default = {
        "sqlite_databases": [
            {"source": "./patient_profiles.db",  "backup_dir": "./backups/sqlite"},
            {"source": "./feedback.db",          "backup_dir": "./backups/sqlite"},
            {"source": "./analytics.db",         "backup_dir": "./backups/sqlite"}
        ],
        "chromadb_persistence": [
            {"source": "./chromadb_persist", "backup_dir": "./backups/chromadb"}
        ],
        "additional_files": [
            {"source": "./src/config/safety_config.json",  "backup_dir": "./backups/config"},
            {"source": "./Modelfile",           "backup_dir": "./backups/config"}
        ],
        "retention_days": 30,
        "compression": True,
        "telegram_bot_token": "",
        "telegram_chat_id": ""
    }
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                loaded = json.load(f)
                default.update(loaded)
        except Exception as exc:
            logger.warning("Could not load %s (%s) — using defaults.", path, exc)
    else:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2, ensure_ascii=False)
        logger.info("Created default backup_config.json — fill in telegram credentials.")
    return default


# ── Main ───────────────────────────────────────────────────────────────────────

class BackupManager:
    def __init__(self, config_file: str = "backup_config.json"):
        self.config = _load_config(config_file)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.compress = self.config.get("compression", True)
        self.retention = self.config.get("retention_days", 30)

    def run(self) -> dict:
        results: List[Dict] = []
        errors: List[Dict] = []

        # SQLite databases
        for item in self.config.get("sqlite_databases", []):
            r = _backup_sqlite(item["source"], item["backup_dir"], self.timestamp, self.compress)
            (results if r["status"] == "success" else errors).append(r)
            _cleanup_old(item["backup_dir"], self.retention)

        # ChromaDB
        for item in self.config.get("chromadb_persistence", []):
            r = _backup_chromadb(item["source"], item["backup_dir"], self.timestamp, self.compress)
            (results if r["status"] == "success" else errors).append(r)
            _cleanup_old(item["backup_dir"], self.retention)

        # Config files
        for item in self.config.get("additional_files", []):
            r = _backup_file(item["source"], item["backup_dir"], self.timestamp, self.compress)
            (results if r["status"] == "success" else errors).append(r)
            _cleanup_old(item["backup_dir"], self.retention)

        total_bytes = sum(r.get("size_bytes", 0) for r in results)
        overall_ok = len(errors) == 0

        summary = {
            "timestamp": self.timestamp,
            "success": overall_ok,
            "backed_up": len(results),
            "failed": len(errors),
            "total_size_bytes": total_bytes,
            "total_size_mb": round(total_bytes / 1_048_576, 2),
            "results": results,
            "errors": errors,
        }

        logger.info(
            "Backup complete. Backed up: %d  Failed: %d  Total size: %.2f MB",
            len(results), len(errors), summary["total_size_mb"],
        )

        # Telegram notification
        if overall_ok:
            msg = (
                f"✅ *UnaniMed AI Backup Succeeded*\n\n"
                f"🕐 `{self.timestamp}`\n"
                f"📦 Items backed up: `{len(results)}`\n"
                f"💾 Total size: `{summary['total_size_mb']} MB`\n"
                f"🗑️ Retention: `{self.retention} days`"
            )
        else:
            failed_list = "\n".join(f"  • {e['source']}" for e in errors)
            msg = (
                f"❌ *UnaniMed AI Backup FAILED*\n\n"
                f"🕐 `{self.timestamp}`\n"
                f"✅ Succeeded: `{len(results)}`  ❌ Failed: `{len(errors)}`\n"
                f"Failed items:\n{failed_list}"
            )
        _telegram_notify(msg, self.config)

        return summary


def main() -> int:
    logger.info("=" * 60)
    logger.info("UnaniMed AI Backup starting…")
    manager = BackupManager()
    summary = manager.run()
    logger.info("Summary: %s", json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
