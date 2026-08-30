#!/usr/bin/env python3
"""
UnaniMed AI — Multimodal Test Suite
───────────────────────────────────
Tests Lead Extraction, SQLite Persistence, Telegram Notification Formatting,
Herbal Visual Catalog, Safety Guardrails, and Unified Chat Workflow.
"""

import os
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.services.lead_telegram_service import LeadExtractor, LeadRepository, TelegramNotifier
from src.services.herbal_catalog_service import HerbalCatalogService
from src.services.safety_check_service import SafetyChecker, load_config as load_safety_config


class TestUnaniMedMultimodal(unittest.TestCase):

    def test_01_phone_extraction(self):
        """Test extraction of English and Bengali phone numbers."""
        test_cases = [
            ("আমার নাম্বার 01712345678 ঔষধ পাঠাবেন", "01712345678"),
            ("Please deliver to +8801812345678 urgent", "01812345678"),
            ("আমার ফোন নং ০১৭৯৮৭৬৫৪৩২", "01798765432"),
            ("Call me at 01955-123456 for confirmation", "01955123456")
        ]
        for text, expected in test_cases:
            extracted = LeadExtractor.extract_phone(text)
            self.assertEqual(extracted, expected, f"Failed on text: {text}")

    def test_02_lead_extraction(self):
        """Test full lead extraction (Name, Phone, Address)."""
        msg = "আমার নাম মোঃ সাকিব, মোবাইল 01711223344, ঠিকানা উত্তরা সেক্টর ৭ ঢাকা। কাশির জন্য তুলসী ও মধু চাই।"
        lead = LeadExtractor.extract_lead(msg, sender_id="test-user-1")

        self.assertTrue(lead["is_lead"])
        self.assertEqual(lead["phone"], "01711223344")
        self.assertIn("সাকিব", lead["name"])
        self.assertIn("উত্তরা", lead["address"])

    def test_03_sqlite_lead_crud(self):
        """Test saving, retrieving, and updating lead in SQLite DB."""
        lead_data = {
            "sender_id": "test_sender_101",
            "name": "আব্দুল করিম",
            "phone": "01899887766",
            "address": "মিরপুর ১০, ঢাকা",
            "inquiry_summary": "কালোজিরা তেল ও আমলকী চূর্ণ",
            "channel": "unit-test",
            "status": "new"
        }
        lead_id = LeadRepository.save_lead(lead_data)
        self.assertIsInstance(lead_id, int)
        self.assertGreater(lead_id, 0)

        # Retrieve
        saved = LeadRepository.get_lead_by_id(lead_id)
        self.assertIsNotNone(saved)
        self.assertEqual(saved["phone"], "01899887766")
        self.assertEqual(saved["status"], "new")

        # Update Status
        updated = LeadRepository.update_lead_status(lead_id, "confirmed")
        self.assertTrue(updated)

        updated_lead = LeadRepository.get_lead_by_id(lead_id)
        self.assertEqual(updated_lead["status"], "confirmed")

    def test_04_herbal_catalog(self):
        """Test official product search and visual image intent detection."""
        # Search GL Ton
        results = HerbalCatalogService.search("জিএল টন")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["id"], "gl-ton")
        self.assertIn("শরবত মুকাব্বী", results[0]["formula"])

        # Detect Image Request Intent
        intent = HerbalCatalogService.detect_image_request("জিএল টন সিরাপ দেখতে কেমন ছবি দেখাও")
        self.assertTrue(intent["has_image_intent"])
        self.assertGreater(intent["count"], 0)
        self.assertEqual(intent["matched_herbs"][0]["id"], "gl-ton")

    def test_05_safety_checks(self):
        """Test safety emergency pre-check filter."""
        checker = SafetyChecker(load_safety_config())

        # Normal query -> should NOT block
        res_normal = checker.pre_check("আমার সামান্য সর্দি ও গলা ব্যথা হয়েছে")
        self.assertFalse(res_normal["should_block"])

        # High risk emergency query -> should trigger referral
        res_emergency = checker.pre_check("বুকে তীব্র ব্যথা ও শ্বাস বন্ধ হয়ে যাচ্ছে")
        self.assertTrue(res_emergency["should_block"])


if __name__ == "__main__":
    unittest.main()
