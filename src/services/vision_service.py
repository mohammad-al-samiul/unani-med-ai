#!/usr/bin/env python3
"""
Vision & Image Analysis Service for UnaniMed AI
───────────────────────────────────────────────
Analyzes user-uploaded medical images (prescriptions, skin symptoms,
herbal plants/leaves, Unani medicine packs) using local Ollama vision models
or local OCR + Llama 3.1 fallback. 100% local, zero API cost.
"""

import os
import io
import base64
import logging
from typing import Dict, Any, Optional
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from PIL import Image

# ── Logging Setup ─────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("vision-service")

# ── Config ────────────────────────────────────────────────────────────────────
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "llama3.2-vision:11b")
OLLAMA_TEXT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

app = FastAPI(title="Unani Vision & Image Service", version="1.0.0")


# ── Vision Helper ─────────────────────────────────────────────────────────────
class VisionProcessor:
    @staticmethod
    def encode_image_bytes(image_bytes: bytes) -> str:
        """Convert raw image bytes to base64 string."""
        return base64.b64encode(image_bytes).decode("utf-8")

    @staticmethod
    def try_local_ocr(image_bytes: bytes) -> str:
        """Attempt local OCR using pytesseract if installed, otherwise empty."""
        try:
            import importlib
            pytess = importlib.import_module("pytesseract")
            image_to_string = getattr(pytess, "image_to_string")
            img = Image.open(io.BytesIO(image_bytes))
            text = image_to_string(img, lang="eng+ben")
            return text.strip()
        except Exception as e:
            logger.info("Local OCR not available or failed (%s). Continuing with Ollama vision.", e)
            return ""

    @staticmethod
    async def analyze_with_ollama_vision(
        image_b64: str,
        user_prompt: str = "",
        language: str = "bn"
    ) -> Optional[str]:
        """Attempt image analysis using Ollama's multimodal endpoint."""
        system_instruction = (
            "তুমি একজন দক্ষ ও সতর্ক ইউনানী ভেষজ ও স্বাস্থ্য সহকারী। "
            "ব্যবহারকারী একটি ছবি আপলোড করেছেন (প্রেসক্রিপশন, ভেষজ উদ্ভিদ, চর্মরোগ বা ঔষধি উপাদান)। "
            "ছবিটি বিশদভাবে পর্যবেক্ষণ করে বাংলায়/ইংরেজিতে তথ্য দাও। "
            "প্রেসক্রিপশন হলে তাতে কী লেখা আছে তা সহজে বুঝিয়ে দাও। "
            "ভেষজ উপাদান হলে তার ইউনানী নাম, মিজাজ ও স্বাস্থ্য উপকারিতা বলো। "
            "চর্ম বা বাহ্যিক সমস্যা হলে সাধারণ প্রাকৃতিক যত্ন উল্লেখ করো। "
            "কখনো সুনির্দিষ্ট ডোজ দেবে না এবং সবশেষে হাকিম/ডাক্তারের পরামর্শ নেওয়ার নির্দেশ দাও।"
            if language == "bn" else
            "You are a helpful Unani healthcare and herbal medicine assistant. "
            "Analyze the uploaded image (prescription, herb/plant, skin symptom, or medicine). "
            "Explain what is visible, provide Unani herbal insights, and always advise consulting a qualified Hakim/doctor."
        )

        prompt_text = user_prompt if user_prompt else (
            "এই ছবিটি বিশ্লেষণ করুন এবং ইউনানী স্বাস্থ্য দৃষ্টিভঙ্গিতে বিস্তারিত বলুন।"
            if language == "bn" else
            "Please analyze this image from a traditional Unani and herbal perspective."
        )

        payload = {
            "model": OLLAMA_VISION_MODEL,
            "prompt": f"{system_instruction}\n\nইউজার প্রশ্ন: {prompt_text}",
            "images": [image_b64],
            "stream": False,
            "options": {
                "temperature": 0.5,
                "num_predict": 700
            }
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", "").strip()
                else:
                    logger.warning("Ollama vision returned HTTP %s: %s", response.status_code, response.text)
                    return None
        except Exception as e:
            logger.warning("Ollama vision call failed: %s", e)
            return None

    @staticmethod
    async def analyze_with_text_llm_fallback(
        ocr_text: str,
        user_prompt: str = "",
        language: str = "bn"
    ) -> str:
        """Fallback to Llama 3.1:8b when vision model is not loaded."""
        prompt = (
            f"ব্যবহারকারী একটি চিকিৎসা বা ঔষধের ছবি আপলোড করেছেন।\n"
            f"ছবি থেকে সংগৃহীত টেক্সট/বিবরণ:\n'''{ocr_text if ocr_text else 'ব্যবহারকারী প্রেসক্রিপশন বা ভেষজ ঔষধের ছবি দিয়েছেন'}'''\n\n"
            f"ব্যবহারকারীর প্রশ্ন: {user_prompt or 'এই বিষয়ে ইউনানী পরামর্শ দিন'}\n\n"
            f"দয়া করে ইউনানী স্বাস্থ্য বিজ্ঞান অনুযায়ী বিস্তারিত ও সহায়ক বিশ্লেষণ প্রদান করুন। "
            f"কোনো নির্দিষ্ট প্রেসক্রিপশন ডোজ দেবেন না এবং সরাসরি চিকিৎসকের সাথে সাক্ষাতের পরামর্শ যুক্ত করুন।"
        )

        payload = {
            "model": OLLAMA_TEXT_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.6,
                "num_predict": 500
            }
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
                if response.status_code == 200:
                    return response.json().get("response", "").strip()
        except Exception as e:
            logger.error("LLM fallback failed: %s", e)

        return (
            "ছবিটি গ্রহণ করা হয়েছে। ছবিতে দৃশ্যমান প্রেসক্রিপশন বা ভেষজ উপাদান সম্পর্কিত সঠিক নির্দেশনার জন্য "
            "অনুগ্রহ করে আমাদের বিশেষজ্ঞ ইউনানী হাকিম বা চিকিৎসকের সাথে সরাসরি যোগাযোগ করুন।"
            if language == "bn" else
            "Image received. For accurate diagnosis and herbal advice based on this image, please consult our qualified Hakim or healthcare specialist."
        )


# ── API Models & Endpoints ────────────────────────────────────────────────────
class ImageBase64Request(BaseModel):
    image_base64: str
    prompt: Optional[str] = ""
    language: Optional[str] = "bn"


@app.post("/analyze-image-base64")
async def analyze_image_base64(request: ImageBase64Request):
    """Analyze base64 image data."""
    # Clean potential data URI prefix (e.g. data:image/png;base64,...)
    raw_b64 = request.image_base64
    if "," in raw_b64:
        raw_b64 = raw_b64.split(",", 1)[1]

    # Decode bytes for validation & OCR
    try:
        img_bytes = base64.b64decode(raw_b64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image data")

    # Step 1: Try Ollama Multimodal Vision
    vision_result = await VisionProcessor.analyze_with_ollama_vision(
        image_b64=raw_b64,
        user_prompt=request.prompt,
        language=request.language
    )

    if vision_result:
        return {
            "success": True,
            "method": "ollama_vision",
            "analysis": vision_result,
            "disclaimer": "নোট: এটি কৃত্রিম বুদ্ধিমত্তা চালিত প্রাথমিক তথ্য। চূড়ান্ত সিদ্ধান্তের জন্য চিকিৎসকের শরণাপন্ন হোন।"
        }

    # Step 2: Fallback to OCR + Llama 3.1:8b
    ocr_text = VisionProcessor.try_local_ocr(img_bytes)
    fallback_result = await VisionProcessor.analyze_with_text_llm_fallback(
        ocr_text=ocr_text,
        user_prompt=request.prompt,
        language=request.language
    )

    return {
        "success": True,
        "method": "ocr_text_llm_fallback",
        "ocr_extracted_text": ocr_text,
        "analysis": fallback_result,
        "disclaimer": "নোট: এটি কৃত্রিম বুদ্ধিমত্তা চালিত প্রাথমিক তথ্য। চূড়ান্ত সিদ্ধান্তের জন্য চিকিৎসকের শরণাপন্ন হোন।"
    }


from fastapi import Request

@app.post("/analyze-image-file")
async def analyze_image_file(request: Request):
    """Analyze uploaded image file (raw bytes or form-data)."""
    img_bytes = await request.body()
    if not img_bytes:
        raise HTTPException(status_code=400, detail="Empty image payload")
        
    img_b64 = VisionProcessor.encode_image_bytes(img_bytes)
    req = ImageBase64Request(image_base64=img_b64, prompt="", language="bn")
    return await analyze_image_base64(req)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "unani-vision-service",
        "ollama_vision_model": OLLAMA_VISION_MODEL,
        "ollama_text_model": OLLAMA_TEXT_MODEL
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8013)
