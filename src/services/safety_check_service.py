#!/usr/bin/env python3
"""
Safety Check Service
Provides pre-check and post-check functionality for medical AI responses.
"""

import json
import re
from typing import Dict, Any, List, Tuple
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Safety Check Service", version="1.0.0")

# Load safety configuration
CONFIG_PATH = Path(__file__).parent.parent / "config" / "safety_config.json"

def load_config() -> Dict[str, Any]:
    """Load safety configuration from JSON file."""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "pre_check_keywords": {},
            "post_check_regex": {},
            "pre_check_message": "এই বিষয়ে অনুগ্রহ করে সরাসরি একজন হাকিম/ডাক্তারের পরামর্শ নিন।",
            "post_check_disclaimer": "নোট: নির্দিষ্ট ডোজ বা পরিমাণ সম্পর্কে তথ্য সরিয়ে দেওয়া হয়েছে। ঔষধ সেবনের আগে অবশ্যই একজন হাকিম/ডাক্তারের পরামর্শ নিন।",
            "threshold_settings": {
                "min_match_count": 1,
                "case_sensitive": False,
                "whole_word_match": False
            }
        }

safety_config = load_config()

class SafetyChecker:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pre_check_keywords = config.get("pre_check_keywords", {})
        self.post_check_regex = config.get("post_check_regex", {})
        self.pre_check_message = config.get("pre_check_message", "")
        self.post_check_disclaimer = config.get("post_check_disclaimer", "")
        self.threshold_settings = config.get("threshold_settings", {})
    
    def pre_check(self, text: str) -> Dict[str, Any]:
        """
        Check if text contains high-risk keywords that should trigger immediate medical referral.
        
        Returns:
            Dictionary with check results and action required
        """
        found_keywords = []
        matched_categories = []
        
        text_lower = text.lower() if not self.threshold_settings.get("case_sensitive", False) else text
        
        for category, keywords in self.pre_check_keywords.items():
            for keyword in keywords:
                keyword_lower = keyword.lower() if not self.threshold_settings.get("case_sensitive", False) else keyword
                
                if self.threshold_settings.get("whole_word_match", False):
                    # Whole word match
                    pattern = r'\b' + re.escape(keyword_lower) + r'\b'
                    if re.search(pattern, text_lower):
                        found_keywords.append(keyword)
                        matched_categories.append(category)
                else:
                    # Partial match
                    if keyword_lower in text_lower:
                        found_keywords.append(keyword)
                        matched_categories.append(category)
        
        min_matches = self.threshold_settings.get("min_match_count", 1)
        should_block = len(found_keywords) >= min_matches
        
        return {
            "should_block": should_block,
            "found_keywords": found_keywords,
            "matched_categories": matched_categories,
            "block_message": self.pre_check_message if should_block else "",
            "reason": f"Found {len(found_keywords)} high-risk keywords in {len(matched_categories)} categories"
        }
    
    def post_check(self, text: str) -> Dict[str, Any]:
        """
        Check if response contains specific dosage information that should be filtered.
        
        Returns:
            Dictionary with check results and modified text if needed
        """
        all_patterns = []
        
        # Add dosage patterns
        if "dosage_patterns" in self.post_check_regex:
            all_patterns.extend(self.post_check_regex["dosage_patterns"])
        
        # Add specific medication patterns
        if "specific_medication" in self.post_check_regex:
            all_patterns.extend(self.post_check_regex["specific_medication"])
        
        # Add frequency patterns
        if "frequency_patterns" in self.post_check_regex:
            all_patterns.extend(self.post_check_regex["frequency_patterns"])
        
        found_patterns = []
        modified_text = text
        modifications_made = 0
        
        for pattern in all_patterns:
            try:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    found_patterns.append({
                        "pattern": pattern,
                        "match": match.group(),
                        "start": match.start(),
                        "end": match.end()
                    })
                    
                    # Remove the matched portion
                    modified_text = modified_text[:match.start()] + "[ডোজ তথ্য সরিয়ে দেওয়া হয়েছে]" + modified_text[match.end():]
                    modifications_made += 1
            except re.error:
                continue
        
        should_modify = len(found_patterns) > 0
        
        if should_modify:
            # Add disclaimer at the end
            modified_text += f"\n\n{self.post_check_disclaimer}"
        
        return {
            "should_modify": should_modify,
            "found_patterns": found_patterns,
            "modifications_made": modifications_made,
            "original_text": text,
            "modified_text": modified_text,
            "disclaimer_added": should_modify
        }

safety_checker = SafetyChecker(safety_config)

class PreCheckRequest(BaseModel):
    text: str

class PostCheckRequest(BaseModel):
    text: str

@app.post("/pre-check")
async def pre_check(request: PreCheckRequest):
    """
    Perform pre-check on user input to detect high-risk medical queries.
    
    Returns check results and blocking action if needed.
    """
    result = safety_checker.pre_check(request.text)
    return result

@app.post("/post-check")
async def post_check(request: PostCheckRequest):
    """
    Perform post-check on AI response to filter dosage information.
    
    Returns modified text with disclaimers if dosage patterns found.
    """
    result = safety_checker.post_check(request.text)
    return result

@app.post("/reload-config")
async def reload_config():
    """Reload safety configuration from file."""
    global safety_config, safety_checker
    safety_config = load_config()
    safety_checker = SafetyChecker(safety_config)
    return {"status": "success", "message": "Configuration reloaded"}

@app.get("/config")
async def get_config():
    """Get current safety configuration."""
    return safety_config

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "safety-check-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)