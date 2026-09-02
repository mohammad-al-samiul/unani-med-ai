#!/usr/bin/env python3
"""
Patient Profile Service
Manages SQLite database for patient profiles with conversation flow support.
"""

import os
import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env ─────────────────────────────────────────────────────────────────
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "databases" / "patient_profiles.db"
DB_PATH = Path(os.getenv("PATIENT_PROFILE_DB_PATH", str(DEFAULT_DB_PATH)))
PATIENT_PROFILE_PORT = int(os.getenv("PATIENT_PROFILE_PORT", "8003"))

# Ensure directory exists
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class PatientProfileService:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or DB_PATH)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize SQLite database with patient profiles schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                sender_id TEXT PRIMARY KEY,
                age_range TEXT,
                gender TEXT,
                is_pregnant BOOLEAN,
                prior_conditions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_state (
                sender_id TEXT PRIMARY KEY,
                current_step TEXT,
                collected_data TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def check_profile_exists(self, sender_id: str) -> bool:
        """Check if profile exists for given sender_id."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT sender_id FROM patients WHERE sender_id = ?", (sender_id,))
        result = cursor.fetchone()
        
        conn.close()
        return result is not None
    
    def get_profile(self, sender_id: str) -> Optional[Dict[str, Any]]:
        """Get patient profile for given sender_id."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT sender_id, age_range, gender, is_pregnant, prior_conditions, created_at, updated_at
            FROM patients WHERE sender_id = ?
        """, (sender_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "sender_id": result[0],
                "age_range": result[1],
                "gender": result[2],
                "is_pregnant": bool(result[3]) if result[3] is not None else None,
                "prior_conditions": result[4],
                "created_at": result[5],
                "updated_at": result[6]
            }
        return None
    
    def create_profile(self, sender_id: str, profile_data: Dict[str, Any]) -> bool:
        """Create new patient profile."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO patients (sender_id, age_range, gender, is_pregnant, prior_conditions)
                VALUES (?, ?, ?, ?, ?)
            """, (
                sender_id,
                profile_data.get("age_range"),
                profile_data.get("gender"),
                profile_data.get("is_pregnant"),
                profile_data.get("prior_conditions")
            ))
            
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def update_profile(self, sender_id: str, profile_data: Dict[str, Any]) -> bool:
        """Update existing patient profile."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            update_fields = []
            update_values = []
            
            if "age_range" in profile_data:
                update_fields.append("age_range = ?")
                update_values.append(profile_data["age_range"])
            
            if "gender" in profile_data:
                update_fields.append("gender = ?")
                update_values.append(profile_data["gender"])
            
            if "is_pregnant" in profile_data:
                update_fields.append("is_pregnant = ?")
                update_values.append(profile_data["is_pregnant"])
            
            if "prior_conditions" in profile_data:
                update_fields.append("prior_conditions = ?")
                update_values.append(profile_data["prior_conditions"])
            
            if update_fields:
                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                update_values.append(sender_id)
                
                query = f"UPDATE patients SET {', '.join(update_fields)} WHERE sender_id = ?"
                cursor.execute(query, update_values)
                conn.commit()
                return True
            
            return False
        finally:
            conn.close()
    
    def start_conversation_flow(self, sender_id: str) -> str:
        """Start profile collection conversation flow."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO conversation_state (sender_id, current_step, collected_data, started_at, last_activity)
                VALUES (?, 'age_range', '{}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (sender_id,))
            
            conn.commit()
            return "age_range"
        finally:
            conn.close()
    
    def get_conversation_state(self, sender_id: str) -> Optional[Dict[str, Any]]:
        """Get current conversation state for profile collection."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT current_step, collected_data, started_at, last_activity
            FROM conversation_state WHERE sender_id = ?
        """, (sender_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "current_step": result[0],
                "collected_data": json.loads(result[1]) if result[1] else {},
                "started_at": result[2],
                "last_activity": result[3]
            }
        return None
    
    def update_conversation_state(self, sender_id: str, step: str, collected_data: Dict[str, Any]) -> bool:
        """Update conversation state during profile collection."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE conversation_state 
                SET current_step = ?, collected_data = ?, last_activity = CURRENT_TIMESTAMP
                WHERE sender_id = ?
            """, (step, json.dumps(collected_data), sender_id))
            
            conn.commit()
            return True
        finally:
            conn.close()
    
    def end_conversation_flow(self, sender_id: str) -> bool:
        """End conversation flow and clean up state."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM conversation_state WHERE sender_id = ?", (sender_id,))
            conn.commit()
            return True
        finally:
            conn.close()
    
    def get_next_question(self, current_step: str, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get next question based on current step and collected data."""
        questions = {
            "age_range": {
                "question": "আপনার বয়স কত? (উদাহরণ: ১৮-২৫, ২৬-৩৫, ৩৬-৪৫, ৪৬-৫৫, ৪৬+)",
                "next_step": "gender",
                "field": "age_range"
            },
            "gender": {
                "question": "আপনার লিঙ্গ কি? (পুরুষ/মহিলা/অন্যান্য)",
                "next_step": "pregnancy_check",
                "field": "gender"
            },
            "pregnancy_check": {
                "question": self._get_pregnancy_question(collected_data),
                "next_step": "prior_conditions",
                "field": "is_pregnant",
                "conditional": True
            },
            "prior_conditions": {
                "question": "আপনার কোনো পূর্ববর্তী রোগ আছে কি? (যদি থাকে লিখুন, না থাকলে 'না' লিখুন)",
                "next_step": "complete",
                "field": "prior_conditions"
            }
        }
        
        return questions.get(current_step, {})
    
    def _get_pregnancy_question(self, collected_data: Dict[str, Any]) -> str:
        """Get pregnancy question based on gender."""
        gender = collected_data.get("gender", "").lower()
        if gender in ["মহিলা", "female", "f"]:
            return "আপনি কি বর্তমানে গর্ভবতী? (হ্যাঁ/না)"
        return "প্রশ্ন স্কিপ করা হচ্ছে..."  # Skip for male
    
    def process_answer(self, sender_id: str, answer: str) -> Dict[str, Any]:
        """Process user answer and return next action."""
        state = self.get_conversation_state(sender_id)
        
        if not state:
            return {"error": "No active conversation flow"}
        
        current_step = state["current_step"]
        collected_data = state["collected_data"]
        
        question_info = self.get_next_question(current_step, collected_data)
        
        if not question_info:
            return {"error": "Invalid conversation step"}
        
        # Handle conditional steps
        if question_info.get("conditional"):
            field = question_info["field"]
            gender = collected_data.get("gender", "").lower()
            
            if field == "is_pregnant" and gender not in ["মহিলা", "female", "f"]:
                # Skip pregnancy question for male
                collected_data[field] = False
                next_step = question_info["next_step"]
                self.update_conversation_state(sender_id, next_step, collected_data)
                return self._get_next_step_response(sender_id, next_step, collected_data)
        
        # Store the answer
        field = question_info["field"]
        processed_answer = self._process_answer(field, answer)
        collected_data[field] = processed_answer
        
        # Move to next step
        next_step = question_info["next_step"]
        
        if next_step == "complete":
            # Save profile and end conversation
            self.create_profile(sender_id, collected_data)
            self.end_conversation_flow(sender_id)
            return {
                "status": "complete",
                "message": "আপনার প্রোফাইল সফলভাবে সেভ হয়েছে। এখন আপনি আপনার স্বাস্থ্য সমস্যা সম্পর্কে জিজ্ঞেস করতে পারেন।"
            }
        else:
            self.update_conversation_state(sender_id, next_step, collected_data)
            return self._get_next_step_response(sender_id, next_step, collected_data)
    
    def _process_answer(self, field: str, answer: str) -> Any:
        """Process and validate user answer."""
        answer = answer.strip()
        
        if field == "is_pregnant":
            if answer.lower() in ["হ্যাঁ", "yes", "y", "true"]:
                return True
            return False
        
        if field == "age_range":
            # Validate age range format
            valid_ranges = ["১৮-২৫", "২৬-৩৫", "৩৬-৪৫", "৪৬-৫৫", "৪৬+", "18-25", "26-35", "36-45", "46-55", "46+"]
            if answer in valid_ranges:
                return answer
            return answer  # Accept custom input
        
        return answer
    
    def _get_next_step_response(self, sender_id: str, next_step: str, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get response for next step in conversation."""
        if next_step == "complete":
            return {
                "status": "complete",
                "message": "প্রোফাইল সম্পন্ন হয়েছে।"
            }
        
        question_info = self.get_next_question(next_step, collected_data)
        return {
            "status": "continue",
            "question": question_info.get("question", ""),
            "current_step": next_step
        }
    
    def format_patient_context(self, sender_id: str) -> str:
        """Format patient profile data for context in RAG prompt."""
        profile = self.get_profile(sender_id)
        
        if not profile:
            return "পেশেন্ট প্রোফাইল উপলব্ধ নেই।"
        
        context_parts = []
        
        if profile.get("age_range"):
            context_parts.append(f"বয়স: {profile['age_range']}")
        
        if profile.get("gender"):
            context_parts.append(f"লিঙ্গ: {profile['gender']}")
        
        if profile.get("is_pregnant") is not None:
            pregnancy_status = "গর্ভবতী" if profile["is_pregnant"] else "গর্ভবতী নন"
            context_parts.append(f"গর্ভাবস্থা: {pregnancy_status}")
        
        if profile.get("prior_conditions"):
            context_parts.append(f"পূর্ববর্তী রোগ: {profile['prior_conditions']}")
        
        if context_parts:
            return " | ".join(context_parts)
        
        return "পেশেন্ট প্রোফাইল উপলব্ধ নেই।"

# FastAPI wrapper for n8n integration
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Patient Profile Service", version="1.0.0")

profile_service = PatientProfileService()

class ProfileCheckRequest(BaseModel):
    sender_id: str

class ProfileCreateRequest(BaseModel):
    sender_id: str
    age_range: str
    gender: str
    is_pregnant: bool = None
    prior_conditions: str = None

class AnswerProcessRequest(BaseModel):
    sender_id: str
    answer: str

@app.post("/check-profile")
async def check_profile(request: ProfileCheckRequest):
    """Check if profile exists for sender_id."""
    exists = profile_service.check_profile_exists(request.sender_id)
    profile = profile_service.get_profile(request.sender_id) if exists else None
    
    return {
        "exists": exists,
        "profile": profile
    }

@app.post("/start-profile-flow")
async def start_profile_flow(request: ProfileCheckRequest):
    """Start profile collection conversation flow."""
    first_step = profile_service.start_conversation_flow(request.sender_id)
    question_info = profile_service.get_next_question(first_step, {})
    
    return {
        "status": "started",
        "current_step": first_step,
        "question": question_info.get("question", "")
    }

@app.post("/process-answer")
async def process_answer(request: AnswerProcessRequest):
    """Process user answer in profile collection flow."""
    result = profile_service.process_answer(request.sender_id, request.answer)
    return result

@app.post("/get-conversation-state")
async def get_conversation_state(request: ProfileCheckRequest):
    """Get current conversation state."""
    state = profile_service.get_conversation_state(request.sender_id)
    return state or {"error": "No active conversation"}

@app.post("/format-patient-context")
async def format_patient_context(request: ProfileCheckRequest):
    """Format patient profile for RAG context."""
    context = profile_service.format_patient_context(request.sender_id)
    return {"context": context}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "patient-profile-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PATIENT_PROFILE_PORT)