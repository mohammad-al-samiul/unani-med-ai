#!/usr/bin/env python3
"""
UnaniMed AI — Unified Multimodal Orchestration Service
───────────────────────────────────────────────────────
Master backend service orchestrating Voice (STT & TTS), Bilingual Text,
Vision & Image Analysis, Customer Lead Extraction & Database Persistence,
Telegram Bot Alerts, Safety Guardrails, and Ollama Llama 3.1:8b inference.
Serves the modern web frontend at Port 8010.
"""

import os
import io
import re
import json
import base64
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ── Local Service Imports ─────────────────────────────────────────────────────
from src.services.lead_telegram_service import (
    LeadExtractor, TelegramNotifier, LeadRepository, DB_PATH
)
from src.services.herbal_catalog_service import HerbalCatalogService
from src.services.safety_check_service import SafetyChecker, load_config as load_safety_config

# ── Logging Setup ─────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("unani-unified-service")

# ── Paths & Config ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = BASE_DIR / "src" / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "llama3.2-vision:11b")
STT_PORT = int(os.getenv("STT_PORT", "8001"))
TTS_PORT = int(os.getenv("TTS_PORT", "8002"))
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

safety_checker = SafetyChecker(load_safety_config())

# ── FastAPI Initialization ────────────────────────────────────────────────────
app = FastAPI(
    title="UnaniMed AI Unified Service",
    description="Multimodal Unani Healthcare Assistant with Voice, Vision, Lead Capture & Telegram Alerts",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── System Prompts ────────────────────────────────────────────────────────────
UNANI_SYSTEM_PROMPT = """তুমি গ্যালাক্সি ল্যাবরেটরিজ (Galaxy Laboratories Unani)-এর অফিসিয়াল ইউনানী স্বাস্থ্য-পরামর্শক ও প্রোডাক্ট স্পেশালিস্ট এআই।
তোমার দায়িত্ব হলো ব্যবহারকারীদের স্বাস্থ্য সমস্যার ধরন অনুযায়ী আমাদের অফিসিয়াল ইউনানী ঔষধগুলো বিশদভাবে সুপারিশ করা এবং এগুলোর কার্যকারিতা, ইউনানী সূত্র (যেমন: শরবত মুকাব্বী, হাব্বে সুআল, শরবত বেলগিরী ইত্যাদি), সেবনবিধি ও মূল্য (Price) সুস্পষ্টভাবে জানিয়ে দেওয়া।

আমাদের অফিসিয়াল প্রোডাক্ট তালিকা (Official Products Catalog):
১. জিএল টন (GL Ton Syrup) – শরবত মুকাব্বী | হার্ট অ্যাটাক, স্ট্রোক ও হার্ট ব্লকের ঝুঁকি প্রতিরোধ, হৃদকম্প, ব্রেন দুর্বলতা, অনিদ্রা ও স্নায়বিক অবসাদ দূর করে। (মূল্য: 100৳ – 850৳ | সেবনবিধি: ২-৪ চা চামচ দিনে ১-২ বার)
২. রেসপিরেক্স (Respirex Tablet) – হাব্বে সুআল | শীতলতাজনিত কাশি ও শ্বাসকষ্ট নিরাময়ে অদ্বিতীয়। (৫০ ট্যাবলেট মূল্য: ৩০০৳ | সেবনবিধি: ১-২ ট্যাবলেট দিনে ২-৩ বার)
৩. ডায়ানিয়া (Diania Capsule) – রেহমানিয়া | ঠান্ডা ও শ্বাসতন্ত্রের সমস্যায় বিশেষ আরামদায়ক ও কাশি নিরামক। (৩০ ক্যাপসুল মূল্য: ৪৫০৳ | সেবনবিধি: ১-২ ক্যাপসুল দিনে ২-৩ বার)
৪. রিউমারেক্স (Rheumarex Capsule) – কুরুছ আওজা | বাত-বেদনা, গেঁটেবাত, কটিবাত ও সন্ধি-প্রদাহজনিত হাড়ের জয়েন্টের তীব্র ব্যথায় অত্যন্ত কার্যকরী। (৩০ ক্যাপসুল মূল্য: ৩০০৳ | সেবনবিধি: ২ ক্যাপসুল দিনে ১-২ বার)
৫. মোবিক (Mobic Syrup) – শরবত বেলগিরী | দাস্ত, পুরাতন আমাশয়, আইবিএস (IBS) ও পেটের মোচড়/ব্যথা দূর করতে সেরা। (৪৫০ মিলি মূল্য: ২০০৳ | সেবনবিধি: ২-৪ চা চামচ দিনে ২-৪ বার)
৬. মেনসোটন (Mensoton Syrup) – নিসওয়ান | মহিলাদের অনিয়মিত ঋতুস্রাব, শ্বেতপ্রদর, জরায়ুর প্রদাহ ও কষ্টরজঃ নিরাময়ে বিশেষ কার্যকরী। (৪৫০ মিলি মূল্য: ২০০৳ | সেবনবিধি: ২-৪ চা চামচ দিনে ১-২ বার)
৭. জেনাসিন (Janasin Syrup) – শরবত জিনসিন | যৌন দুর্বলতা, ক্লান্তি, অবসাদ দূর করে শারীরিক ও স্নায়বিক শক্তি বৃদ্ধি করে। (৪৫০ মিলি মূল্য: ৪৫০৳ | সেবনবিধি: ২-৪ চা চামচ দিনে ১-২ বার)
৮. জিফাল (Gfal Syrup) – শরবত আতফাল | শিশুদের পেট ফাঁপা, দাস্ত, অজীর্ণ, বদহজম ও দাঁত ওঠার সময়ের পেটের পীড়ায় বিশেষ ফলপ্রসূ। (১০০ মিলি মূল্য: ১০০৳ | সেবনবিধি: ৬ মাস: ১/২ চামচ, ৬-১২ মাস: ১ চামচ দিনে ৩-৪ বার)
৯. জাইমোলিভ (Zymoliv Syrup) – শরবত দীনার | যকৃৎ প্রদাহ, প্রতিবন্ধকতাজনিত জন্ডিস ও কোষ্ঠকাঠিন্য নিরাময়ে অত্যন্ত কার্যকরী। (৪৫০ মিলি মূল্য: ২০০৳ | সেবনবিধি: প্রাপ্তবয়স্ক ২-৩ চামচ দিনে ২-৩ বার)
১০. গ্যালাক্সি পুদিনা (Galaxy Pudina Syrup) – আরক পুদিনা | রুচি ও ক্ষুধা বর্ধক, পেটফাঁপা, পাকস্থলীর ব্যথা ও বমি দূর করে। (১০০ মিলি মূল্য: ১০০৳ | সেবনবিধি: ২-৪ চা চামচ দিনে ১-২ বার)
১১. গোলাপ চন্দন (Golap Chandan Syrup) – শরবত গাওজবান | মস্তিষ্ক ও হৃদযন্ত্রের কর্মক্ষমতা বৃদ্ধি, মানসিক অস্থিরতা ও হৃদকম্প প্রশমনে টনিক। (৪৫০ মিলি মূল্য: ৩৫০৳ | সেবনবিধি: ২-৪ চা চামচ দিনে ২ বার)
১২. জিএলভিট (GLvit Syrup) – শরবত মভেষ | পুষ্টিহীনতা, শারীরিক দুর্বলতা ও রক্তস্বল্পতা দূর করে জীবনীশক্তি বাড়ায়। (৪৫০ মিলি মূল্য: ৩৫০৳ | সেবনবিধি: ২-৪ চা চামচ দিনে ২-৩ বার)
১৩. পেপটো-জি (Pepto-G Syrup) – আরক নানখা | গ্যাস, এসিডিটি, পেটফাঁপা ও বায়ুজনিত পেটে ব্যথা দ্রুত উপশম করে। (৪৫০ মিলি মূল্য: ২০০৳ | সেবনবিধি: প্রাপ্তবয়স্ক ২-৩ চা চামচ দিনে ২-৩ বার)
১৪. অ্যাপেল জি (Apple-G Syrup) – শরবত সেব | প্রাকৃতিক মাল্টিভিটামিন, সাধারণ দুর্বলতা, রুচি বৃদ্ধি ও লিভার টনিক। (মূল্য: 100৳ – 350৳ | সেবনবিধি: ২-৪ চা চামচ দিনে ২ বার)
১৫. ফেরক্সেল (Feroxel Syrup) – শরবত ফওলাদ | রক্তস্বল্পতা, আয়রনের ঘাটতি ও রক্তে লোহিত রক্তকণিকা বৃদ্ধিতে সহায়ক। (মূল্য: 100৳ – 250৳ | সেবনবিধি: ২-৪ চা চামচ দিনে ১-২ বার)
১৬. কফটন (GL-Cofton Syrup) – শরবত এজায | শুকনো কাশি, বুকে জমানো কফ পরিষ্কার ও নাকের সর্দি দূর করে। (মূল্য: 85৳ – 200৳ | সেবনবিধি: ২-৪ চা চামচ দিনে ২ বার)
১৭. অ্যালকোজেন (Alkogen Syrup) – শরবত বুযূরী | মূত্রকৃচ্ছতা (প্রস্রাবে জ্বালাপোড়া/সমস্যা), জন্ডিস ও কিডনি/মূত্রথলির অসার পদার্থ অপসারণে কার্যকর। (মূল্য: 70৳ – 200৳ | সেবনবিধি: ২-৪ চা চামচ দিনে ২ বার)
১৮. আমলকি প্লাস (Galaxy Amloki Plus Syrup) – শরবত আমলা | রোগ প্রতিরোধ ক্ষমতা বৃদ্ধি, স্নায়বিক দুর্বলতা ও ভিটামিন সি ঘাটতি পূরণ করে। (মূল্য: 100৳ – 350৳ | সেবনবিধি: ২-৪ চা চামচ দিনে ১-২ বার)

নির্দেশনাবলী:
১. ব্যবহারকারী যেকোনো রোগ বা সমস্যার কথা বললে (যেমন: কাশি, গ্যাস, লিভার, হার্ট, বাত-ব্যথা ইত্যাদি) আমাদের সম্পর্কিত ঔষধের নাম, কার্যকারিতা, ফর্মুলা ও মূল্য সুন্দরভাবে তুলে ধরো।
২. ভয়েস, টেক্সট বা ছবি যেভাবেই জানতে চাক—সেই মাধ্যম অনুযায়ী সঠিক উত্তর দাও।
৩. ব্যবহারকারীকে অর্ডার করার জন্য উৎসাহিত করো এবং বলো যে তিনি নাম, মোবাইল নম্বর ও ঠিকানা দিলে হোম ডেলিভারি পৌঁছে দেওয়া হবে।
৪. উত্তর সবসময় মার্জিত, সুবিন্যস্ত ও স্পষ্ট বুলেট পয়েন্টে প্রদান করো।"""


# ── Internal Helpers ──────────────────────────────────────────────────────────
async def transcribe_audio_base64(audio_b64: str, language: Optional[str] = None) -> Optional[str]:
    """Call local STT service on Port 8001 or fallback internal whisper."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"http://localhost:{STT_PORT}/transcribe-base64",
                json={"audio_base64": audio_b64, "language": language}
            )
            if resp.status_code == 200:
                return resp.json().get("text", "")
    except Exception as e:
        logger.warning("Local STT HTTP call failed: %s. Attempting fallback...", e)
    
    # Fallback to direct Whisper if importable
    try:
        from src.services.stt_service import get_whisper_model
        model = get_whisper_model()
        if model:
            raw_b64 = audio_b64.split(",", 1)[1] if "," in audio_b64 else audio_b64
            audio_bytes = base64.b64decode(raw_b64)
            
            import tempfile, uuid
            temp_file = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.webm")
            with open(temp_file, "wb") as f:
                f.write(audio_bytes)
            
            segments, info = model.transcribe(temp_file, language=language)
            text = " ".join([s.text for s in segments])
            os.remove(temp_file)
            return text.strip()
    except Exception as e:
        logger.error("Internal STT transcription failed: %s", e)
    
    return None


async def generate_speech_audio(text: str, language: str = "bn") -> Dict[str, Any]:
    """Call TTS service on Port 8002 to generate audio."""
    # Clean text of markdown symbols for speech synthesis
    clean_text = re.sub(r'[*_#`~\[\]\(\)]', '', text)
    # Truncate clean text to first 2-3 sentences for concise speech
    sentences = re.split(r'[।\.\n]', clean_text)
    speech_snippet = "। ".join([s.strip() for s in sentences[:3] if s.strip()]) + "।"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"http://localhost:{TTS_PORT}/text-to-speech-base64",
                json={"text": speech_snippet, "language": language}
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("audio_data"):
                    return {
                        "audio_base64": data["audio_data"],
                        "use_browser_speech": False,
                        "format": data.get("format", "mp3")
                    }
    except Exception as e:
        logger.info("TTS service call failed (%s). Falling back to client-side speech.", e)

    return {
        "audio_base64": None,
        "use_browser_speech": True,
        "speech_text": speech_snippet,
        "format": "speech-api"
    }


async def call_local_ollama(prompt: str, system_prompt: str = UNANI_SYSTEM_PROMPT, history: List[Dict[str, str]] = None) -> str:
    """Send prompt to local Ollama llama3.1:8b."""
    formatted_prompt = f"{system_prompt}\n\n"
    if history:
        for turn in history[-4:]:
            role = "ব্যবহারকারী" if turn.get("role") == "user" else "সহকারী"
            formatted_prompt += f"{role}: {turn.get('content', '')}\n"
    
    formatted_prompt += f"ব্যবহারকারী: {prompt}\nসহকারী:"

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": formatted_prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "num_predict": 750
        }
    }

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
            if resp.status_code == 200:
                return resp.json().get("response", "").strip()
            else:
                logger.error("Ollama returned status %s: %s", resp.status_code, resp.text)
    except Exception as e:
        logger.error("Ollama call failed: %s", e)

    return (
        "দুঃখিত, স্থানীয় Ollama সার্ভারের সাথে সংযোগ করা সম্ভব হয়নি। "
        "অনুগ্রহ করে নিশ্চিত করুন যে Ollama চালু আছে (`ollama run llama3.1:8b`)।"
    )


# ── Request / Response Schemas ────────────────────────────────────────────────
class ChatRequest(BaseModel):
    text: Optional[str] = ""
    audio_base64: Optional[str] = None
    image_base64: Optional[str] = None
    modality_preference: Optional[str] = "auto"  # auto, voice_only, text_only, both
    language: Optional[str] = "auto"             # bn, en, auto
    sender_id: Optional[str] = "web-user"
    channel: Optional[str] = "web"
    history: Optional[List[Dict[str, str]]] = []


# ── Core Unified Chat Endpoint ────────────────────────────────────────────────
@app.post("/api/chat")
async def unified_chat_endpoint(payload: ChatRequest):
    """
    Main Multimodal Gateway:
    Handles text, voice audio, image uploads, lead capturing & Telegram alerts,
    Ollama inference, and speech generation.
    """
    user_query = payload.text.strip() if payload.text else ""
    transcription = None
    vision_analysis = None
    is_voice_input = bool(payload.audio_base64)
    is_image_input = bool(payload.image_base64)

    # ── Step 1: Voice Input Processing (STT) ──────────────────────────────────
    if is_voice_input:
        transcription = await transcribe_audio_base64(
            payload.audio_base64,
            language="bn" if payload.language == "bn" else None
        )
        if transcription:
            user_query = f"{user_query} {transcription}".strip() if user_query else transcription
        else:
            if not user_query:
                user_query = "ভয়েস বার্তা পাওয়া গেছে কিন্তু বুঝতে কিছুটা সমস্যা হয়েছে।"

    # ── Step 2: Image Input Processing (Vision) ───────────────────────────────
    if is_image_input:
        try:
            from src.services.vision_service import VisionProcessor
            raw_b64 = payload.image_base64.split(",", 1)[1] if "," in payload.image_base64 else payload.image_base64
            
            # Try Ollama Vision
            vision_analysis = await VisionProcessor.analyze_with_ollama_vision(
                image_b64=raw_b64,
                user_prompt=user_query,
                language="bn" if payload.language != "en" else "en"
            )
            
            if not vision_analysis:
                img_bytes = base64.b64decode(raw_b64)
                ocr_text = VisionProcessor.try_local_ocr(img_bytes)
                vision_analysis = await VisionProcessor.analyze_with_text_llm_fallback(
                    ocr_text=ocr_text,
                    user_prompt=user_query,
                    language="bn" if payload.language != "en" else "en"
                )
        except Exception as e:
            logger.error("Vision processing failed: %s", e)
            vision_analysis = "ছবি বিশ্লেষণ করতে সমস্যা হয়েছে। অনুগ্রহ করে পরিষ্কার ছবি দিন।"

    # ── Step 3: Customer Lead Extraction & Telegram Notification ──────────────
    lead_result = LeadExtractor.extract_lead(
        text=user_query,
        sender_id=payload.sender_id,
        channel=payload.channel
    )
    
    lead_id = None
    telegram_sent = False
    if lead_result.get("is_lead"):
        telegram_sent = await TelegramNotifier.send_lead_alert(lead_result)
        lead_result["telegram_notified"] = telegram_sent
        lead_id = LeadRepository.save_lead(lead_result)
        logger.info("Saved customer lead #%s and notified Telegram (sent=%s)", lead_id, telegram_sent)

    # ── Step 4: Herb Visual Catalog Detection ─────────────────────────────────
    herb_intent = HerbalCatalogService.detect_image_request(user_query)
    herb_cards = herb_intent.get("matched_herbs", [])
    
    # If no specific image request, search if any herb is explicitly mentioned to enrich response
    if not herb_cards and user_query:
        matched_herbs = HerbalCatalogService.search(user_query)
        if matched_herbs:
            herb_cards = matched_herbs[:2]  # attach top 2 relevant herb cards

    # ── Step 5: Safety Pre-Check ──────────────────────────────────────────────
    safety_check = safety_checker.pre_check(user_query)
    if safety_check.get("should_block"):
        block_msg = safety_check.get("block_message") or "এই উপসর্গটি গুরুতর। অবিলম্বে নিকটস্থ হাসপাতাল বা চিকিৎসকের শরণাপন্ন হোন।"
        return {
            "success": True,
            "text_response": f"🚨 **জরুরী সতর্কতা / Medical Alert:**\n\n{block_msg}",
            "audio": await generate_speech_audio(block_msg, language=payload.language),
            "safety_triggered": True,
            "lead_detected": lead_result.get("is_lead", False),
            "herb_cards": []
        }

    # ── Step 6: Generate Final Response ───────────────────────────────────────
    final_text = ""
    if vision_analysis and not user_query:
        # User uploaded photo without extra text
        final_text = vision_analysis
    elif vision_analysis and user_query:
        # Photo + query
        final_text = f"📷 **ছবি বিশ্লেষণ ও ইউনানী পর্যালোচনা:**\n\n{vision_analysis}"
    else:
        # Standard chat prompt to Ollama Llama 3.1:8b
        extra_context = ""
        if lead_result.get("is_lead"):
            extra_context += "\n(নোট: ব্যবহারকারী তার যোগাযোগের তথ্য দিয়েছেন। ধন্যবাদ জানান এবং আশ্বস্ত করুন যে আমাদের দল দ্রুত যোগাযোগ করবে।)"
        
        prompt_with_context = f"{user_query}{extra_context}"
        final_text = await call_local_ollama(
            prompt=prompt_with_context,
            history=payload.history or []
        )

    # ── Step 7: Safety Post-Check (Dosage filtering) ───────────────────────────
    post_check = safety_checker.post_check(final_text)
    if post_check.get("has_modifications"):
        final_text = post_check.get("modified_text", final_text)

    # If lead was detected, add friendly confirmation badge if not present
    if lead_result.get("is_lead"):
        confirm_badge = (
            f"\n\n---\n✅ **আপনার তথ্য সংরক্ষিত হয়েছে!**\n"
            f"👤 নাম: `{lead_result.get('name') or 'গ্রাহক'}` | 📞 মোবাইল: `{lead_result.get('phone')}`\n"
            f"📍 ঠিকানা: `{lead_result.get('address') or 'নির্ধারিত নয়'}`\n"
            f"আমাদের প্রতিনিধি শীঘ্রই আপনার সাথে যোগাযোগ করবেন। 🌿"
        )
        if "সংরক্ষিত হয়েছে" not in final_text:
            final_text += confirm_badge

    # ── Step 8: Dynamic Voice Generation (TTS) ────────────────────────────────
    should_generate_voice = (
        payload.modality_preference == "voice_only" or
        payload.modality_preference == "both" or
        (payload.modality_preference == "auto" and is_voice_input)
    )

    audio_payload = None
    if should_generate_voice:
        audio_payload = await generate_speech_audio(final_text, language=payload.language)

    return {
        "success": True,
        "text_response": final_text,
        "input_transcription": transcription,
        "audio": audio_payload,
        "is_voice_response": should_generate_voice,
        "vision_analysis": vision_analysis,
        "herb_cards": herb_cards,
        "lead_detected": lead_result.get("is_lead", False),
        "lead_id": lead_id,
        "telegram_notified": telegram_sent,
        "safety_triggered": False
    }


# ── Leads API (Admin & Web Form) ──────────────────────────────────────────────
@app.get("/api/leads")
async def get_all_leads(limit: int = 50, offset: int = 0, status: Optional[str] = None, search: Optional[str] = None):
    """Retrieve customer leads for the Admin Dashboard."""
    leads = LeadRepository.get_leads(limit=limit, offset=offset, status=status, search=search)
    return {"success": True, "count": len(leads), "leads": leads}


@app.patch("/api/leads/{lead_id}/status")
async def update_lead_status_endpoint(lead_id: int, payload: Dict[str, str]):
    """Update lead status (new, contacted, confirmed, delivered, cancelled)."""
    status = payload.get("status", "new").lower()
    updated = LeadRepository.update_lead_status(lead_id, status)
    if not updated:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"success": True, "lead_id": lead_id, "status": status}


@app.post("/api/leads/order")
async def submit_direct_order(payload: Dict[str, Any]):
    """Submit direct lead/order from web UI form."""
    lead_data = {
        "sender_id": payload.get("sender_id", "web-form"),
        "name": payload.get("name", ""),
        "phone": payload.get("phone", ""),
        "address": payload.get("address", ""),
        "inquiry_summary": payload.get("inquiry_summary", ""),
        "order_items": payload.get("order_items", ""),
        "channel": "Web Form",
        "raw_message": f"Web Order: {payload.get('name')}, {payload.get('phone')}, {payload.get('address')}",
        "status": "new"
    }
    telegram_sent = await TelegramNotifier.send_lead_alert(lead_data)
    lead_data["telegram_notified"] = telegram_sent
    lead_id = LeadRepository.save_lead(lead_data)
    return {"success": True, "lead_id": lead_id, "telegram_notified": telegram_sent}


# ── Herbs Catalog Endpoint ────────────────────────────────────────────────────
@app.get("/api/herbs")
async def get_herbs_list(search: Optional[str] = None):
    """Retrieve herbal catalog for web visual remedies explorer."""
    if search:
        herbs = HerbalCatalogService.search(search)
    else:
        herbs = HerbalCatalogService.get_all()
    return {"success": True, "herbs": herbs}


# ── Live System Health Monitor ────────────────────────────────────────────────
@app.get("/api/system/status")
async def system_status():
    """Live health status of all sub-components."""
    # Check Ollama
    ollama_ok = False
    ollama_models = []
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            res = await client.get(f"{OLLAMA_URL}/api/tags")
            if res.status_code == 200:
                ollama_ok = True
                ollama_models = [m.get("name") for m in res.json().get("models", [])]
    except Exception:
        ollama_ok = False

    # Check STT
    stt_ok = False
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"http://localhost:{STT_PORT}/health")
            stt_ok = res.status_code == 200
    except Exception:
        stt_ok = False

    # Check TTS
    tts_ok = False
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"http://localhost:{TTS_PORT}/health")
            tts_ok = res.status_code == 200
    except Exception:
        tts_ok = False

    return {
        "status": "online",
        "service": "UnaniMed AI Unified Master Engine",
        "port": 8010,
        "ollama": {
            "online": ollama_ok,
            "url": OLLAMA_URL,
            "target_model": OLLAMA_MODEL,
            "available_models": ollama_models
        },
        "stt": {"online": stt_ok, "port": STT_PORT},
        "tts": {"online": tts_ok, "port": TTS_PORT},
        "database": {"path": str(DB_PATH), "exists": DB_PATH.exists()},
        "telegram": {
            "configured": bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID),
            "chat_id_set": bool(TELEGRAM_CHAT_ID)
        }
    }


# ── Serve Static Assets and UI ────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve modern web portal frontend."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h2>UnaniMed AI Server Running. Building frontend...</h2>")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
