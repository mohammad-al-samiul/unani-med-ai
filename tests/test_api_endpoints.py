#!/usr/bin/env python3
"""
Test FastAPI API Endpoints for Unified AI Orchestrator
"""

import sys
from pathlib import Path
import unittest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from fastapi.testclient import TestClient
from src.services.unified_ai_service import app

class TestAPIEndpoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_index_page(self):
        """Test that HTML index page serves properly."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("UnaniMed", response.text)
        self.assertIn("পরামর্শ চ্যাট", response.text)

    def test_02_system_status(self):
        """Test system status endpoint."""
        response = self.client.get("/api/system/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "online")
        self.assertIn("ollama", data)
        self.assertIn("database", data)

    def test_03_herbs_endpoint(self):
        """Test herbal catalog endpoint."""
        response = self.client.get("/api/herbs")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertGreater(len(data["herbs"]), 0)

    def test_04_lead_capture_via_chat(self):
        """Test lead capture & DB write when contact details are provided."""
        payload = {
            "text": "আমার নাম মোঃ তানভীর, মোবাইল 01799887766, ঠিকানা ধানমন্ডি ঢাকা। আমলকী তেল লাগবে।",
            "modality_preference": "text_only",
            "language": "bn"
        }
        response = self.client.post("/api/chat", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["lead_detected"])
        self.assertIsNotNone(data.get("lead_id"))
        self.assertIn("তানভীর", data["text_response"])

    def test_05_manual_order_submission(self):
        """Test direct order submission."""
        order_payload = {
            "name": "মাহমুদ হাসান",
            "phone": "01611223344",
            "address": "গুলশান ২, ঢাকা",
            "order_items": "খাঁটি মধু ৫০০ গ্রাম এবং কালোজিরা তেল"
        }
        response = self.client.post("/api/leads/order", json=order_payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIsNotNone(data.get("lead_id"))

    def test_06_herb_image_request_enrichment(self):
        """Test that query asking for medicine pictures returns product cards."""
        payload = {
            "text": "জিএল টন সিরাপের ছবি দেখতে চাই",
            "modality_preference": "text_only",
            "language": "bn"
        }
        response = self.client.post("/api/chat", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertGreater(len(data["herb_cards"]), 0)
        self.assertEqual(data["herb_cards"][0]["id"], "gl-ton")


if __name__ == "__main__":
    unittest.main()
