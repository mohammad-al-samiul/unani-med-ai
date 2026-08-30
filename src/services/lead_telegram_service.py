#!/usr/bin/env python3
"""
Customer Lead & Telegram Notification Service
─────────────────────────────────────────────
Extracts customer contact information (Name, Phone, Address, Order/Inquiry)
from messages, stores them in a local SQLite database, and dispatches
instant formatted notifications to Telegram via the Telegram Bot API.
"""

import os
import re
import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

# ── Setup Logging ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("lead-telegram-service")

# ── Configuration ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "databases" / "customer_leads.db"
DB_PATH = Path(os.getenv("LEADS_DB_PATH", str(DEFAULT_DB_PATH)))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

# Ensure database directory exists
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


# ── Database Layer ────────────────────────────────────────────────────────────
def init_db():
    """Initialize customer_leads SQLite database table."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customer_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id TEXT,
            name TEXT,
            phone TEXT,
            address TEXT,
            inquiry_summary TEXT,
            order_items TEXT,
            status TEXT DEFAULT 'new',
            channel TEXT DEFAULT 'web',
            raw_message TEXT,
            telegram_notified BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_phone ON customer_leads(phone)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON customer_leads(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON customer_leads(created_at)")
    conn.commit()
    conn.close()
    logger.info("Customer leads database initialized at %s", DB_PATH)


init_db()


# ── Lead Extraction Engine ────────────────────────────────────────────────────
class LeadExtractor:
    """
    Hybrid extraction combining robust regex patterns for BD & international
    phone numbers, address keywords, and optional local LLM parsing.
    """

    # Bangladeshi phone numbers (013, 014, 015, 016, 017, 018, 019) with optional +88 / 88 or spaces/dashes
    PHONE_REGEX = re.compile(
        r'(?:\+?880\s*|0)?1[3-9]\d{2}[-\s]?\d{6}\b|'
        r'(?:\+?[1-9]\d{1,14}\b)'  # generic international phone
    )

    # Address keywords in Bengali & English
    ADDRESS_KEYWORDS = [
        "ঠিকানা", "বাসা", "রোড", "রাস্তা", "থানা", "জেলা", "গ্রাম", "সেক্টর",
        "ঢাকা", "চট্টগ্রাম", "সিলেট", "খুলনা", "রাজশাহী", "রংপুর", "বরিশাল",
        "ময়মনসিংহ", "কুমিল্লা", "গাজীপুর", "উত্তরা", "মিরপুর", "ধানমন্ডি", "গুলশান",
        "address", "house", "road", "street", "thana", "district", "village",
        "sector", "block", "dhaka", "chattogram", "sylhet", "khulna", "rajshahi",
        "uttara", "mirpur", "dhanmondi", "gulshan", "banani", "narayanganj"
    ]

    # Name indicator patterns
    NAME_PATTERNS = [
        r'(?:আমার\s+নাম|নাম\s*[:ঃ=]|নামটি|নাম)\s*[:ঃ=]?\s*([A-Za-z\u0980-\u09FF\s]{2,40})',
        r'(?:my\s+name\s+is|name\s*[:=])\s*([A-Za-z\s]{2,40})',
        r'(?:আমি\s+)([A-Za-z\u0980-\u09FF]{2,25})\b'
    ]

    @classmethod
    def extract_phone(cls, text: str) -> Optional[str]:
        """Find and normalize phone number from text."""
        # Normalize Bengali numerals to English first
        bn_to_en = str.maketrans('০১২৩৪৫৬৭৮৯', '0123456789')
        text_en = text.translate(bn_to_en)
        
        matches = cls.PHONE_REGEX.findall(text_en)
        if matches:
            for match in matches:
                # clean up spaces and hyphens
                cleaned = re.sub(r'[\s\-]', '', match)
                if len(cleaned) >= 10:
                    # If standard BD number without +88, format as standard 01XXXXXXXXX
                    if cleaned.startswith("880") and len(cleaned) == 13:
                        cleaned = "0" + cleaned[3:]
                    elif cleaned.startswith("+880") and len(cleaned) == 14:
                        cleaned = "0" + cleaned[4:]
                    return cleaned
        return None

    @classmethod
    def extract_name(cls, text: str) -> Optional[str]:
        """Extract customer name using heuristics and patterns."""
        for pattern in cls.NAME_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Stop if hitting common boundary words like 'মোবাইল', 'ঠিকানা', 'phone', 'address'
                name = re.split(r'[,।\n\r]|মোবাইল|ফোন|ঠিকানা|phone|mobile|address', name, flags=re.IGNORECASE)[0].strip()
                if len(name) >= 2:
                    return name
        return None

    @classmethod
    def extract_address(cls, text: str) -> Optional[str]:
        """Extract address based on keyword proximity and patterns."""
        # Check for explicit Address pattern
        addr_match = re.search(
            r'(?:ঠিকানা|এড্রেস|বাসা|address|location)\s*[:ঃ=]?\s*([^\n\r।]{4,100})',
            text, re.IGNORECASE
        )
        if addr_match:
            addr = addr_match.group(1).strip()
            # clean trailing phone numbers if captured accidentally
            addr = re.sub(r'(?:মোবাইল|ফোন|phone|mobile|\d{10,13}).*', '', addr, flags=re.IGNORECASE).strip()
            if len(addr) >= 3:
                return addr

        # Otherwise check if text contains address keywords
        text_lower = text.lower()
        found_keywords = [kw for kw in cls.ADDRESS_KEYWORDS if kw in text_lower]
        if len(found_keywords) >= 1:
            # Extract sentence or line containing address keyword
            lines = text.splitlines()
            for line in lines:
                if any(kw in line.lower() for kw in found_keywords):
                    cleaned = re.sub(r'(?:আমার\s+নাম|নাম|ফোন|মোবাইল|phone|mobile).*?[:ঃ=]?[^\s,]+', '', line, flags=re.IGNORECASE).strip()
                    if len(cleaned) >= 5:
                        return cleaned
        return None

    @classmethod
    def extract_lead(cls, text: str, sender_id: str = "anonymous", channel: str = "web") -> Dict[str, Any]:
        """
        Analyze text and return extracted lead information.
        Returns is_lead: True if at least a phone number or clear address/name combination is found.
        """
        phone = cls.extract_phone(text)
        name = cls.extract_name(text)
        address = cls.extract_address(text)
        
        # Determine if this message is a customer lead / order
        is_lead = bool(phone or (name and address))

        return {
            "is_lead": is_lead,
            "sender_id": sender_id,
            "name": name or "",
            "phone": phone or "",
            "address": address or "",
            "inquiry_summary": text[:250].strip(),
            "order_items": "",
            "channel": channel,
            "raw_message": text
        }


# ── Telegram Notification Dispatcher ─────────────────────────────────────────
class TelegramNotifier:
    """Sends real-time lead alerts to Telegram Bot / Channel."""

    @staticmethod
    async def send_lead_alert(lead: Dict[str, Any], bot_token: str = None, chat_id: str = None) -> bool:
        token = bot_token or TELEGRAM_BOT_TOKEN
        target_chat = chat_id or TELEGRAM_CHAT_ID

        if not token or not target_chat:
            logger.info("Telegram Bot Token or Chat ID not configured. Dry-run alert: %s", lead)
            return False

        # Format message in clean Markdown
        now_str = datetime.now().strftime("%Y-%m-%d %I:%M %p")
        name_display = lead.get("name") or "অনির্ধারিত / Not specified"
        phone_display = lead.get("phone") or "অনির্ধারিত / Not specified"
        address_display = lead.get("address") or "অনির্ধারিত / Not specified"
        inquiry_display = lead.get("inquiry_summary") or lead.get("raw_message", "")
        channel_display = lead.get("channel", "web").upper()

        text_message = (
            "🌿 *নতুন ইউনানী চিকিৎসা পরামর্শ / অর্ডার লিড!* 🌿\n\n"
            f"👤 *গ্রাহকের নাম:* `{name_display}`\n"
            f"📞 *মোবাইল নম্বর:* `{phone_display}`\n"
            f"📍 *ঠিকানা:* `{address_display}`\n"
            f"📝 *রোগের বিবরণ / অর্ডার:* {inquiry_display}\n"
            f"🌐 *উৎস (Channel):* {channel_display}\n"
            f"⏰ *সময়:* {now_str}\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "⚡ *UnaniMed AI Automated Notification*"
        )

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": target_chat,
            "text": text_message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    logger.info("Telegram alert sent successfully for lead %s", lead.get("phone"))
                    return True
                else:
                    logger.error("Telegram API returned error %s: %s", response.status_code, response.text)
                    return False
        except Exception as e:
            logger.error("Failed to send Telegram notification: %s", str(e))
            return False


# ── Customer Leads Repository ─────────────────────────────────────────────────
class LeadRepository:
    """Manages SQLite CRUD operations for customer leads."""

    @staticmethod
    def save_lead(lead_data: Dict[str, Any]) -> int:
        """Insert lead into SQLite database and return generated ID."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO customer_leads (
                sender_id, name, phone, address, inquiry_summary, 
                order_items, status, channel, raw_message, telegram_notified
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            lead_data.get("sender_id", "web-user"),
            lead_data.get("name", ""),
            lead_data.get("phone", ""),
            lead_data.get("address", ""),
            lead_data.get("inquiry_summary", ""),
            lead_data.get("order_items", ""),
            lead_data.get("status", "new"),
            lead_data.get("channel", "web"),
            lead_data.get("raw_message", ""),
            1 if lead_data.get("telegram_notified") else 0
        ))
        
        lead_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return lead_id

    @staticmethod
    def get_leads(limit: int = 50, offset: int = 0, status: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve paginated leads with optional status and search filtering."""
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM customer_leads WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)

        if search:
            query += " AND (name LIKE ? OR phone LIKE ? OR address LIKE ? OR inquiry_summary LIKE ?)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param, search_param])

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        leads = [dict(row) for row in rows]
        conn.close()
        return leads

    @staticmethod
    def get_lead_by_id(lead_id: int) -> Optional[Dict[str, Any]]:
        """Fetch single lead by ID."""
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customer_leads WHERE id = ?", (lead_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def update_lead_status(lead_id: int, status: str) -> bool:
        """Update status of a customer lead."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE customer_leads 
            SET status = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (status, lead_id))
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        return rows_affected > 0

    @staticmethod
    def mark_telegram_notified(lead_id: int) -> bool:
        """Mark that a Telegram notification was sent."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE customer_leads 
            SET telegram_notified = 1, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (lead_id,))
        conn.commit()
        conn.close()
        return True


# ── FastAPI App & Pydantic Models ─────────────────────────────────────────────
app = FastAPI(title="Customer Leads & Telegram Service", version="1.0.0")

class ExtractLeadRequest(BaseModel):
    text: str
    sender_id: Optional[str] = "web-user"
    channel: Optional[str] = "web"
    auto_notify_telegram: Optional[bool] = True

class ManualLeadCreateRequest(BaseModel):
    name: str
    phone: str
    address: Optional[str] = ""
    inquiry_summary: Optional[str] = ""
    order_items: Optional[str] = ""
    channel: Optional[str] = "web"
    sender_id: Optional[str] = "manual"

class StatusUpdateRequest(BaseModel):
    status: str = Field(..., description="Status: new, contacted, confirmed, delivered, cancelled")

class TelegramTestRequest(BaseModel):
    bot_token: Optional[str] = None
    chat_id: Optional[str] = None
    custom_message: Optional[str] = None


@app.post("/extract-and-save")
async def extract_and_save_lead(request: ExtractLeadRequest):
    """
    Extract customer details from message, store in SQLite if valid lead,
    and dispatch Telegram alert.
    """
    extracted = LeadExtractor.extract_lead(
        text=request.text,
        sender_id=request.sender_id,
        channel=request.channel
    )

    if extracted["is_lead"]:
        telegram_sent = False
        if request.auto_notify_telegram:
            telegram_sent = await TelegramNotifier.send_lead_alert(extracted)
            extracted["telegram_notified"] = telegram_sent

        lead_id = LeadRepository.save_lead(extracted)
        extracted["id"] = lead_id
        return {
            "success": True,
            "is_lead": True,
            "lead_id": lead_id,
            "lead": extracted,
            "telegram_sent": telegram_sent,
            "message": "Customer lead detected, saved to database, and processed."
        }

    return {
        "success": True,
        "is_lead": False,
        "lead": extracted,
        "message": "No customer contact details detected in message."
    }


@app.post("/leads")
async def create_manual_lead(request: ManualLeadCreateRequest):
    """Directly insert a lead and notify Telegram."""
    lead_data = {
        "sender_id": request.sender_id,
        "name": request.name,
        "phone": request.phone,
        "address": request.address,
        "inquiry_summary": request.inquiry_summary,
        "order_items": request.order_items,
        "channel": request.channel,
        "raw_message": f"Manual Entry: {request.name}, {request.phone}, {request.address}",
        "status": "new"
    }
    telegram_sent = await TelegramNotifier.send_lead_alert(lead_data)
    lead_data["telegram_notified"] = telegram_sent

    lead_id = LeadRepository.save_lead(lead_data)
    lead_data["id"] = lead_id

    return {
        "success": True,
        "lead_id": lead_id,
        "lead": lead_data,
        "telegram_sent": telegram_sent
    }


@app.get("/leads")
async def list_leads(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    search: Optional[str] = None
):
    """List customer leads from database."""
    leads = LeadRepository.get_leads(limit=limit, offset=offset, status=status, search=search)
    return {
        "success": True,
        "count": len(leads),
        "leads": leads
    }


@app.get("/leads/{lead_id}")
async def get_lead(lead_id: int):
    """Get single customer lead."""
    lead = LeadRepository.get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"success": True, "lead": lead}


@app.patch("/leads/{lead_id}/status")
async def update_status(lead_id: int, request: StatusUpdateRequest):
    """Update lead status (new, contacted, confirmed, delivered, cancelled)."""
    valid_statuses = ["new", "contacted", "confirmed", "delivered", "cancelled"]
    if request.status.lower() not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of {valid_statuses}")
    
    updated = LeadRepository.update_lead_status(lead_id, request.status.lower())
    if not updated:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"success": True, "lead_id": lead_id, "status": request.status.lower()}


@app.post("/test-telegram")
async def test_telegram_connection(request: TelegramTestRequest):
    """Test Telegram Bot notification dispatch."""
    sample_lead = {
        "name": "টেস্ট ব্যবহারকারী (Test User)",
        "phone": "01700000000",
        "address": "মিরপুর ১০, ঢাকা (Mirpur 10, Dhaka)",
        "inquiry_summary": request.custom_message or "ইউনানী স্বাস্থ্য পরামর্শ ও ঔষধ ডেলিভারি টেস্ট মেসেজ।",
        "channel": "API TEST"
    }
    sent = await TelegramNotifier.send_lead_alert(
        lead=sample_lead,
        bot_token=request.bot_token,
        chat_id=request.chat_id
    )
    return {
        "success": sent,
        "configured": bool(request.bot_token or TELEGRAM_BOT_TOKEN),
        "message": "Telegram message sent successfully" if sent else "Failed to send Telegram message. Check BOT_TOKEN and CHAT_ID."
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "customer-lead-telegram-service",
        "database_path": str(DB_PATH),
        "telegram_configured": bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8011)
