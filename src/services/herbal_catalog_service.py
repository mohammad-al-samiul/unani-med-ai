#!/usr/bin/env python3
"""
UnaniMed AI — Official Herbal Medicine & Pharmaceutical Catalog Service
────────────────────────────────────────────────────────────────────────
Provides structured knowledge, Unani formulas (Nuskha), indications,
price ranges, dosage guidelines (Sebonbidhi), pack sizes, and visual cards
for all official Unani Medicines (Galaxy Laboratories Unani lineup).
"""

import re
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

app = FastAPI(title="Unani Medicines & Herbal Catalog Service", version="2.0.0")

# ── Official Unani Medicine Product Catalog ───────────────────────────────────
OFFICIAL_PRODUCTS_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "gl-ton",
        "name_bn": "জিএল টন (GL Ton Syrup)",
        "name_en": "GL Ton Syrup – Natural Heart & Brain Health Booster",
        "formula": "শরবত মুকাব্বী (Sharbat Muqawwi)",
        "type": "Syrup (সিরাপ)",
        "category": "হার্ট, ব্রেন ও স্নায়বিক শক্তিবর্ধক",
        "price_range": "100৳ – 850৳",
        "pack_sizes": "100 ml, 200 ml, 450 ml",
        "benefits_bn": [
            "হার্ট অ্যাটাক, স্ট্রোক ও হার্টের ব্লক প্রতিরোধে অদ্বিতীয়",
            "হৃদযন্ত্রের দুর্বলতা ও হৃদকম্প (Palpitation) দূর করে",
            "মস্তিষ্কের দুর্বলতা, অস্থিরতা ও স্মৃতিশক্তির দুর্বলতা প্রশমনে কার্যকর",
            "স্নায়বিক দুর্বলতা, অনিদ্রা ও মানসিক অবসাদ দূর করতে সাহায্য করে"
        ],
        "usage_bn": "২-৪ চা-চামচ (১০-২০ মিলি) দিনে ১-২ বার অথবা রেজিস্টার্ড চিকিৎসকের পরামর্শ অনুযায়ী সেব্য।",
        "image_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=600&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=300&q=80",
        "keywords": ["gl ton", "জিএল টন", "গ্ল টন", "sharbat muqawwi", "শরবত মুকাব্বী", "heart", "হার্ট", "হৃদরোগ", "স্ট্রোক", "brain", "ব্রেন", "স্মৃতিশক্তি", "অনিদ্রা", "হৃদকম্প"]
    },
    {
        "id": "respirex",
        "name_bn": "রেসপিরেক্স (Respirex Tablet)",
        "name_en": "Respirex Tablet – Natural Relief for Asthma & Cold",
        "formula": "হাব্বে সুআল (Habbe Sual)",
        "type": "Tablet (ট্যাবলেট)",
        "category": "কাশি, ঠান্ডা ও শ্বাসকষ্ট",
        "price_range": "210৳ – 300৳",
        "pack_sizes": "50 Tablets (৩০০৳)",
        "benefits_bn": [
            "শীতলতাজনিত কাশি নিরাময়ে অদ্বিতীয় ও অত্যন্ত কার্যকরী",
            "হাঁপানি ও শ্বাসকষ্টের সমস্যায় দ্রুত আরাম প্রদান করে",
            "শ্বাসনালীর সংকোচন ও কফ দূর করে স্বাভাবিক শ্বাস-প্রশ্বাস নিশ্চিত করে"
        ],
        "usage_bn": "১-২ ট্যাবলেট দিনে ২-৩ বার অথবা রেজিস্টার্ড চিকিৎসকের পরামর্শ অনুযায়ী সেব্য।",
        "image_url": "https://images.unsplash.com/photo-1584017911766-d451b3d0e843?auto=format&fit=crop&w=600&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1584017911766-d451b3d0e843?auto=format&fit=crop&w=300&q=80",
        "keywords": ["respirex", "রেসপিরেক্স", "হাব্বে সুআল", "habbe sual", "কাশি", "শ্বাসকষ্ট", "হাঁপানি", "asthma", "cold", "ঠান্ডা"]
    },
    {
        "id": "diania",
        "name_bn": "ডায়ানিয়া (Diania Capsule)",
        "name_en": "Diania Capsule – Herbal Relief for Cold & Respiratory Care",
        "formula": "রেহমানিয়া (Rehmania)",
        "type": "Capsule (ক্যাপসুল)",
        "category": "শ্বাসতন্ত্রের যত্ন ও অ্যালার্জিক কাশি",
        "price_range": "450৳ – 1,390৳",
        "pack_sizes": "30 Capsules (৪৫০৳)",
        "benefits_bn": [
            "শীতলতাজনিত তীব্র কাশি নিরাময়ে অদ্বিতীয়",
            "শ্বাসকষ্ট ও বুকের ভারী ভাব দূর করতে বিশেষ কার্যকরী",
            "শ্বাসতন্ত্রের প্রতিরোধ ক্ষমতা বৃদ্ধি করে"
        ],
        "usage_bn": "১-২ ক্যাপসুল দিনে ২-৩ বার অথবা রেজিস্টার্ড চিকিৎসকের পরামর্শ অনুযায়ী সেব্য।",
        "image_url": "https://images.unsplash.com/photo-1550572017-edb95dd57ec2?auto=format&fit=crop&w=600&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1550572017-edb95dd57ec2?auto=format&fit=crop&w=300&q=80",
        "keywords": ["diania", "ডায়ানিয়া", "ডায়ানিয়া", "রেহমানিয়া", "rehmania", "কাশি", "শ্বাসকষ্ট", "respiratory", "ঠান্ডা"]
    },
    {
        "id": "rheumarex",
        "name_bn": "রিউমারেক্স (Rheumarex Capsule)",
        "name_en": "Rheumarex Capsule – Natural Relief for Gout & Joint Pain",
        "formula": "কুরুছ আওজা (Quroos Awja)",
        "type": "Capsule (ক্যাপসুল)",
        "category": "বাত-বেদনা ও জয়েন্টের ব্যথা",
        "price_range": "300৳ – 490৳",
        "pack_sizes": "30 Capsules (৩০০৳)",
        "benefits_bn": [
            "বাত-বেদনা ও গেঁটেবাত (Gout) নিরাময়ে অদ্বিতীয়",
            "কটিবাত (কোমর ব্যথা) ও সন্ধি-প্রদাহজনিত রোগে অত্যন্ত কার্যকরী",
            "হাড় ও জয়েন্টের প্রদাহ দ্রুত প্রশমিত করে চলাফেরা সহজ করে"
        ],
        "usage_bn": "২ ক্যাপসুল করে দিনে ১-২ বার অথবা রেজিস্টার্ড চিকিৎসকের পরামর্শ অনুযায়ী সেব্য।",
        "image_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=600&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=300&q=80",
        "keywords": ["rheumarex", "রিউমারেক্স", "কুরুছ আওজা", "quroos awja", "বাত", "ব্যথা", "গেঁটেবাত", "কোমর ব্যথা", "joint pain", "gout", "হাড়ের ব্যথা"]
    },
    {
        "id": "mobic",
        "name_bn": "মোবিক (Mobic Syrup)",
        "name_en": "Mobic Syrup – Natural Remedy for IBS & Chronic Dysentery",
        "formula": "শরবত বেলগিরী (Sharbat Belgeri)",
        "type": "Syrup (সিরাপ)",
        "category": "আইবিএস ও পুরাতন আমাশয়",
        "price_range": "80৳ – 200৳",
        "pack_sizes": "100 ml, 450 ml (২০০৳)",
        "benefits_bn": [
            "দাস্ত ও পুরাতন আমাশয় নিরাময়ে জাদুকরী ভূমিকা রাখে",
            "আইবিএস (IBS / Irritable Bowel Syndrome) সমস্যায় অত্যন্ত ফলপ্রসূ",
            "পেটব্যথা, পেটের মোচড় ও বারবার টয়লেটের বেগ দূর করে"
        ],
        "usage_bn": "২-৪ চা চামচ দৈনিক ২-৪ বার অথবা রেজিস্টার্ড চিকিৎসকের পরামর্শ অনুযায়ী সেব্য।",
        "image_url": "https://images.unsplash.com/photo-1584017911766-d451b3d0e843?auto=format&fit=crop&w=600&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1584017911766-d451b3d0e843?auto=format&fit=crop&w=300&q=80",
        "keywords": ["mobic", "মোবিক", "শরবত বেলগিরী", "sharbat belgeri", "বেলগিরি", "আমাশয়", "dysentery", "ibs", "আইবিএস", "পেটব্যথা", "দাস্ত"]
    },
    {
        "id": "mensoton",
        "name_bn": "মেনসোটন (Mensoton Syrup)",
        "name_en": "Mensoton Syrup – Natural Solution for Women’s Health & Irregular Periods",
        "formula": "নিসওয়ান (Niswan)",
        "type": "Syrup (সিরাপ)",
        "category": "মহিলাদের স্বাস্থ্য ও অনিয়মিত ঋতুস্রাব",
        "price_range": "80৳ – 200৳",
        "pack_sizes": "100 ml, 450 ml (২০০৳)",
        "benefits_bn": [
            "অনিয়মিত ঋতুস্রাব ও শ্বেতপ্রদর (White Discharge) নিরাময়ে কার্যকর",
            "জরায়ু-প্রদাহ ও কষ্টরজঃ (মাসিকের তীব্র পেট ব্যথা) দূর করতে সাহায্য করে",
            "ঋতুবদ্ধতা, জরায়ুর দুর্বলতা ও রক্তস্বল্পতায় বিশেষ কার্যকরী"
        ],
        "usage_bn": "২-৪ চা চামচ দৈনিক ১-২ বার অথবা রেজিস্টার্ড চিকিৎসকের পরামর্শ অনুযায়ী সেব্য।",
        "image_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=600&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=300&q=80",
        "keywords": ["mensoton", "মেনসোটন", "নিসওয়ান", "niswan", "মহিলা", "ঋতুস্রাব", "মাসিক", "শ্বেতপ্রদর", "জরায়ু", "women health", "পিরিয়ড"]
    },
    {
        "id": "janasin",
        "name_bn": "জেনাসিন (Janasin Syrup)",
        "name_en": "Janasin Syrup – Natural Remedy for Vitality & General Weakness",
        "formula": "শরবত জিনসিন (Sharbat Ginseng)",
        "type": "Syrup (সিরাপ)",
        "category": "শারীরিক ও স্নায়বিক শক্তিবর্ধক টনিক",
        "price_range": "120৳ – 450৳",
        "pack_sizes": "100 ml, 200 ml, 450 ml (৪৫০৳)",
        "benefits_bn": [
            "যৌন দুর্বলতা ও অবসাদ দূর করতে বিশেষ কার্যকরী",
            "শরীরের সাধারণ দুর্বলতা, ক্লান্তি ও অনিদ্রা দূর করে",
            "মানসিক প্রশান্তি ও দৈহিক শক্তি বৃদ্ধি করে কর্মক্ষমতা বাড়ায়"
        ],
        "usage_bn": "২-৪ চা চামচ (১০-২০ মিলি) দৈনিক ১-২ বার অথবা রেজিস্টার্ড চিকিৎসকের পরামর্শ অনুযায়ী সেব্য।",
        "image_url": "https://images.unsplash.com/photo-1546868871-7041f2a55e12?auto=format&fit=crop&w=600&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1546868871-7041f2a55e12?auto=format&fit=crop&w=300&q=80",
        "keywords": ["janasin", "জেনাসিন", "sharbat ginseng", "জিনসিন", "শারীরিক দুর্বলতা", "যৌন দুর্বলতা", "vitality", "দুর্বলতা", "ক্লান্তি", "শক্তি"]
    },
    {
        "id": "gfal",
        "name_bn": "জিফাল (Gfal Syrup)",
        "name_en": "Gfal Syrup – Natural Relief for Infants’ Stomach Problems",
        "formula": "শরবত আতফাল (Sharbat Atfal)",
        "type": "Syrup (সিরাপ)",
        "category": "শিশুদের পেটের সমস্যা ও দাঁত ওঠার সময়ের পীড়া",
        "price_range": "100৳",
        "pack_sizes": "100 ml (১০০৳)",
        "benefits_bn": [
            "শিশুদের পেট ফাঁপা ও দাস্ত নিরাময়ে কার্যকর",
            "অজীর্ণ ও বদহজম দূর করতে বিশেষ আরাম প্রদান করে",
            "শিশুদের দন্তোদগমকালীন (দাঁত ওঠার সময়) পেটের পীড়ায় খুবই ফলপ্রসূ"
        ],
        "usage_bn": "৬ মাস বয়স পর্যন্ত: ১/২ চা-চামচ (২.৫ মিলি) দিনে ৩-৪ বার; ৬-১২ মাস: ১ চা-চামচ (৫ মিলি) দিনে ৩-৪ বার; ১-২ বছর: ১-২ চা-চামচ (৫-১০ মিলি) দিনে ৩-৪ বার।",
        "image_url": "https://images.unsplash.com/photo-1584017911766-d451b3d0e843?auto=format&fit=crop&w=600&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1584017911766-d451b3d0e843?auto=format&fit=crop&w=300&q=80",
        "keywords": ["gfal", "জিফাল", "sharbat atfal", "শরবত আতফাল", "শিশু", "বাচ্চা", "দাঁত ওঠা", "পেট ফাঁপা", "শিশুর বদহজম", "infant"]
    },
    {
        "id": "zymoliv",
        "name_bn": "জাইমোলিভ (Zymoliv Syrup)",
        "name_en": "Zymoliv Syrup – Effective Remedy for Jaundice & Liver Health",
        "formula": "শরবত দীনার (Sharbat Deenar)",
        "type": "Syrup (সিরাপ)",
        "category": "লিভারের যত্ন ও জন্ডিস নিরাময়",
        "price_range": "70৳ – 200৳",
        "pack_sizes": "100 ml, 450 ml (২০০৳)",
        "benefits_bn": [
            "যকৃৎ (Liver) প্রদাহ ও প্রতিবন্ধকতাজনিত জন্ডিস নিরাময়ে কার্যকর",
            "শোথ ও ফুসফুসের আবরণ ঝিল্লির প্রদাহ প্রশমন করে",
            "কোষ্ঠকাঠিন্য দূর করে লিভারের বিষাক্ত পদার্থ পরিষ্কার করে"
        ],
        "usage_bn": "প্রাপ্তবয়স্ক: ২-৩ চা চামচ; অপ্রাপ্তবয়স্ক: ১/২-১ চা চামচ দৈনিক ২-৩ বার অথবা রেজিস্টার্ড চিকিৎসকের পরামর্শ অনুযায়ী সেব্য।",
        "image_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=600&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=300&q=80",
        "keywords": ["zymoliv", "জাইমোলিভ", "sharbat deenar", "শরবত দীনার", "লিভার", "যকৃৎ", "জন্ডিস", "liver", "jaundice", "কোষ্ঠকাঠিন্য"]
    },
    {
        "id": "galaxy-pudina",
        "name_bn": "গ্যালাক্সি পুদিনা (Galaxy Pudina Syrup)",
        "name_en": "Galaxy Pudina Syrup – Natural Solution for Digestion & Appetite",
        "formula": "আরক পুদিনা (Arq Pudina)",
        "type": "Syrup (সিরাপ)",
        "category": "পরিপাকতন্ত্র, রুচি ও গ্যাস নিরাময়",
        "price_range": "100৳ – 350৳",
        "pack_sizes": "100 ml (১০০৳), 450 ml",
        "benefits_bn": [
            "রুচি ও ক্ষুধা বর্ধক হিসেবে চমৎকার কাজ করে",
            "পেটফাঁপা ও পাকস্থলীর তীব্র ব্যথা দ্রুত উপশম করে",
            "বমি ভাব, উদরাময় ও পরিপাকের সমস্যায় অত্যন্ত কার্যকরী"
        ],
        "usage_bn": "২-৪ চা চামচ দৈনিক ১-২ বার অথবা রেজিস্টার্ড চিকিৎসকের পরামর্শ অনুযায়ী সেব্য।",
        "image_url": "https://images.unsplash.com/photo-1628556270448-4d4e4148e1b1?auto=format&fit=crop&w=600&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1628556270448-4d4e4148e1b1?auto=format&fit=crop&w=300&q=80",
        "keywords": ["galaxy pudina", "pudina", "পুদিনা", "আরক পুদিনা", "arq pudina", "রুচি", "ক্ষুধা", "বমি", "বদহজম", "পেটফাঁপা"]
    },
    {
        "id": "golap-chandan",
        "name_bn": "গোলাপ চন্দন (Golap Chandan Syrup)",
        "name_en": "Golap Chandan Syrup – Brain & Heart Vitality Tonic",
        "formula": "শরবত গাওজবান (Sharbat Gaozaban)",
        "type": "Syrup (সিরাপ)",
        "category": "মস্তিষ্ক ও হৃদযন্ত্রের শক্তিবর্ধক টনিক",
        "price_range": "100৳ – 350৳",
        "pack_sizes": "100 ml, 450 ml (৩৫০৳)",
        "benefits_bn": [
            "মস্তিষ্কের দুর্বলতা ও হৃদযন্ত্রের দুর্বলতা দূর করে",
            "মানসিক অবসাদ, অতিরিক্ত অস্থিরতা ও হৃদকম্প প্রশমনে কার্যকরী",
            "অরুচি ও শরীরের সাধারণ দুর্বলতা দূর করে দেহ ও মনে সতেজ প্রশান্তি আনে"
        ],
        "usage_bn": "২-৪ চা চামচ দৈনিক ২ বার অথবা রেজিস্টার্ড চিকিৎসকের পরামর্শ অনুযায়ী সেব্য।",
        "image_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=600&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=300&q=80",
        "keywords": ["golap chandan", "গোলাপ চন্দন", "sharbat gaozaban", "শরবত গাওজবান", "মস্তিষ্ক", "হৃদযন্ত্র", "মানসিক অবসাদ", "অস্থিরতা", "brain tonic"]
    },
    {
        "id": "glvit",
        "name_bn": "জিএলভিট (GLvit Syrup)",
        "name_en": "GLvit Syrup – Natural Solution for Deficiency & Vitality",
        "formula": "শরবত মভেষ (Sharbat Maveez)",
        "type": "Syrup (সিরাপ)",
        "category": "পুষ্টির অভাব পূরণ ও জীবনীশক্তি বৃদ্ধি",
        "price_range": "100৳ – 350৳",
        "pack_sizes": "100 ml, 450 ml (৩৫০৳)",
        "benefits_bn": [
            "পুষ্টিহীনতা ও শরীরের দীর্ঘমেয়াদী দুর্বলতা দূর করে",
            "পাকস্থলীর দুর্বলতা ও রক্তস্বল্পতা নিরাময়ে কার্যকর",
            "কোষ্ঠকাঠিন্য দূর করতে সাহায্য করে এবং ভিটামিন এ ও সি এর অভাব পূরণ করে"
        ],
        "usage_bn": "২-৪ চা-চামচ (১০-২০ মিলি) দিনে ২-৩ বার অথবা রেজিস্টার্ড চিকিৎসকের পরামর্শ অনুযায়ী সেব্য।",
        "image_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=600&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=300&q=80",
        "keywords": ["glvit", "জিএলভিট", "sharbat maveez", "শরবত মভেষ", "পুষ্টিহীনতা", "রক্তস্বল্পতা", "ভিটামিন", "দুর্বলতা"]
    },
    {
        "id": "pepto-g",
        "name_bn": "পেপটো-জি (Pepto-G Syrup)",
        "name_en": "Pepto-G Syrup – Effective Remedy for Acidity & Gastric Relief",
        "formula": "আরক নানখা (Arq Nankhwah)",
        "type": "Syrup (সিরাপ)",
        "category": "গ্যাস্ট্রিক, এসিডিটি ও পেটের বায়ু",
        "price_range": "70৳ – 200৳",
        "pack_sizes": "100 ml, 450 ml (২০০৳)",
        "benefits_bn": [
            "পেটফাঁপা ও বায়ুজনিত তীব্র পেটে ব্যথা দ্রুত উপশম করে",
            "হজমের দুর্বলতা দূর করতে অত্যন্ত কার্যকর",
            "অজীর্ণ বা বদহজম নিরাময়ে বিশেষ ভূমিকা রাখে"
        ],
        "usage_bn": "প্রাপ্তবয়স্ক: ২-৩ চা চামচ; অপ্রাপ্তবয়স্ক: ১/২-১ চা চামচ দৈনিক ২-৩ বার অথবা রেজিস্টার্ড চিকিৎসকের পরামর্শ অনুযায়ী সেব্য।",
        "image_url": "https://images.unsplash.com/photo-1584017911766-d451b3d0e843?auto=format&fit=crop&w=600&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1584017911766-d451b3d0e843?auto=format&fit=crop&w=300&q=80",
        "keywords": ["pepto-g", "pepto g", "পেপটো-জি", "পেপটো জি", "আরক নানখা", "arq nankhwah", "গ্যাস্ট্রিক", "এসিডিটি", "gastric", "acidity", "পেট ফাঁপা", "বদহজম"]
    },
    {
        "id": "apple-g",
        "name_bn": "অ্যাপেল জি (Apple-G Syrup)",
        "name_en": "Apple-G Syrup – Herbal Multivitamin for Energy & Liver Health",
        "formula": "শরবত সেব (Sharbat Seb)",
        "type": "Syrup (সিরাপ)",
        "category": "প্রাকৃতিক মাল্টিভিটামিন, রুচি ও লিভার টনিক",
        "price_range": "100৳ – 350৳",
        "pack_sizes": "100 ml, 200 ml, 450 ml",
        "benefits_bn": [
            "সাধারণ দুর্বলতা দূর করতে অত্যন্ত কার্যকর",
            "যকৃতের (Liver) দুর্বলতা দূর করে কার্যক্ষমতা বৃদ্ধি করে",
            "ক্ষুধামান্দ্য দূর করে রুচি বাড়ায় এবং রক্তস্বল্পতা দূর করে",
            "ভিটামিন এ ও সি এর অভাব দূর করতে বিশেষ কার্যকর"
        ],
        "usage_bn": "২-৪ চা চামচ দৈনিক ২ বার অথবা রেজিস্টার্ড চিকিৎসকের পরামর্শ অনুযায়ী সেব্য।",
        "image_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=600&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=300&q=80",
        "keywords": ["apple-g", "apple g", "অ্যাপেল জি", "sharbat seb", "শরবত সেব", "লিভার", "রুচি", "ভিটামিন", "রক্তস্বল্পতা", "দুর্বলতা"]
    },
    {
        "id": "feroxel",
        "name_bn": "ফেরক্সেল (Feroxel Syrup)",
        "name_en": "Feroxel Syrup – Natural Relief for Anemia & Iron Deficiency",
        "formula": "শরবত ফওলাদ (Sharbat Faulad)",
        "type": "Syrup (সিরাপ)",
        "category": "রক্তস্বল্পতা ও আয়রনের অভাব",
        "price_range": "100৳ – 250৳",
        "pack_sizes": "100 ml, 200 ml",
        "benefits_bn": [
            "রক্তস্বল্পতা ও রক্তে লোহিত রক্তকণিকার ঘাটতি দূর করে",
            "শরীরে আয়রনের প্রাকৃতিক অভাব পূরণ করে দ্রুত বল বৃদ্ধি করে",
            "ক্ষুধামন্দা ও যকৃতের দুর্বলতায় বিশেষ কার্যকরী"
        ],
        "usage_bn": "২-৪ চা চামচ দৈনিক ১-২ বার অথবা রেজিস্টার্ড চিকিৎসকের পরামর্শ অনুযায়ী সেব্য।",
        "image_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=600&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=300&q=80",
        "keywords": ["feroxel", "ফেরক্সেল", "শরবত ফওলাদ", "sharbat faulad", "রক্তস্বল্পতা", "রক্তশূন্যতা", "anemia", "iron", "আয়রন", "হিমোগ্লোবিন"]
    },
    {
        "id": "gl-cofton",
        "name_bn": "কফটন (GL-Cofton Syrup)",
        "name_en": "GL-Cofton Syrup – Herbal Remedy for Dry Cough & Cold",
        "formula": "শরবত এজায (Sharbat Aijaz)",
        "type": "Syrup (সিরাপ)",
        "category": "শুকনো কাশি, কফ ও সর্দি",
        "price_range": "85৳ – 200৳",
        "pack_sizes": "100 ml, 450 ml",
        "benefits_bn": [
            "শুকনো কাশি নিরাময়ে বিশেষ কার্যকরী",
            "বুকে জমানো কফ পরিষ্কার ও পাতলা করে সহজে বের করে",
            "নাকের শুকনো সর্দি নিঃসরণে অত্যন্ত কার্যকর"
        ],
        "usage_bn": "২-৪ চা চামচ (১০-২০ মিলি) দৈনিক ২ বার অথবা রেজিস্টার্ড চিকিৎসকের পরামর্শ অনুযায়ী সেব্য।",
        "image_url": "https://images.unsplash.com/photo-1584017911766-d451b3d0e843?auto=format&fit=crop&w=600&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1584017911766-d451b3d0e843?auto=format&fit=crop&w=300&q=80",
        "keywords": ["gl-cofton", "cofton", "কফটন", "জিএল কফটন", "sharbat aijaz", "শরবত এজায", "কাশি", "কফ", "শুকনো কাশি", "সর্দি", "dry cough", "cold"]
    },
    {
        "id": "alkogen",
        "name_bn": "অ্যালকোজেন (Alkogen Syrup)",
        "name_en": "Alkogen Syrup – Natural Unani Remedy for Jaundice & Kidney Care",
        "formula": "শরবত বুযূরী (Sharbat Bazoori)",
        "type": "Syrup (সিরাপ)",
        "category": "কিডনি ও মূত্রনালীর জ্বালাপোড়া, জন্ডিস",
        "price_range": "70৳ – 200৳",
        "pack_sizes": "100 ml, 450 ml",
        "benefits_bn": [
            "মূত্রকৃচ্ছতা (প্রস্রাবের সমস্যা ও জ্বালাপোড়া) দ্রুত দূর করে",
            "যকৃতের প্রতিবন্ধকতা ও জন্ডিস নিরাময়ে কার্যকর",
            "প্রদাহজনিত জ্বর প্রশমন করে এবং কিডনি ও মূত্রথলির বর্জ্য অপসারণ করে"
        ],
        "usage_bn": "২-৪ চা চামচ দৈনিক ২ বার অথবা রেজিস্টার্ড চিকিৎসকের পরামর্শ অনুযায়ী সেব্য।",
        "image_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=600&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=300&q=80",
        "keywords": ["alkogen", "অ্যালকোজেন", "sharbat bazoori", "শরবত বুযূরী", "বুজুরী", "কিডনি", "kidney", "প্রস্রাব", "জন্ডিস", "জ্বর"]
    },
    {
        "id": "galaxy-amloki-plus",
        "name_bn": "আমলকি প্লাস (Galaxy Amloki Plus Syrup)",
        "name_en": "Galaxy Amloki Plus Syrup – Natural Immunity & Vitality Booster",
        "formula": "শরবত আমলা (Sharbat Amla)",
        "type": "Syrup (সিরাপ)",
        "category": "রোগ প্রতিরোধ ক্ষমতা ও ভিটামিন সি টনিক",
        "price_range": "100৳ – 350৳",
        "pack_sizes": "100 ml, 450 ml",
        "benefits_bn": [
            "সাধারণ দুর্বলতা ও স্নায়বিক দুর্বলতা দূর করে",
            "পরিপাকতন্ত্রের দুর্বলতা দূর করে ও অকাল বার্ধক্য রোধ করে",
            "স্মরণশক্তির দুর্বলতা ও ভিটামিন সি এর অভাব দূর করতে অত্যন্ত কার্যকরী"
        ],
        "usage_bn": "২-৪ চা চামচ দৈনিক ১-২ বার অথবা রেজিস্টার্ড চিকিৎসকের পরামর্শ অনুযায়ী সেব্য।",
        "image_url": "https://images.unsplash.com/photo-1599940824399-b87987ceb72a?auto=format&fit=crop&w=600&q=80",
        "thumbnail": "https://images.unsplash.com/photo-1599940824399-b87987ceb72a?auto=format&fit=crop&w=300&q=80",
        "keywords": ["galaxy amloki plus", "amloki plus", "আমলকি প্লাস", "sharbat amla", "শরবত আমলা", "আমলকী", "ভিটামিন সি", "রোগ প্রতিরোধ", "immunity", "বার্ধক্য"]
    }
]


# ── Search & Intent Detection ─────────────────────────────────────────────────
class HerbalCatalogService:
    @staticmethod
    def get_all() -> List[Dict[str, Any]]:
        """Return all official medicine catalog items."""
        return OFFICIAL_PRODUCTS_CATALOG

    @staticmethod
    def find_by_id(item_id: str) -> Optional[Dict[str, Any]]:
        """Find medicine by unique identifier."""
        for item in OFFICIAL_PRODUCTS_CATALOG:
            if item["id"] == item_id:
                return item
        return None

    @staticmethod
    def search(query: str) -> List[Dict[str, Any]]:
        """Search products by name, formula, symptom keywords or category."""
        query_lower = query.lower().strip()
        matched = []
        for item in OFFICIAL_PRODUCTS_CATALOG:
            # Check name matches
            if (query_lower in item["name_bn"].lower() or 
                query_lower in item["name_en"].lower() or 
                query_lower in item["formula"].lower() or
                query_lower in item["category"].lower()):
                matched.append(item)
                continue
            
            # Check keywords and benefits
            for kw in item["keywords"]:
                if kw.lower() in query_lower:
                    matched.append(item)
                    break
        return matched

    @staticmethod
    def detect_image_request(text: str) -> Dict[str, Any]:
        """
        Detect if user is asking for an image/photo of a medicine or product.
        e.g., 'জিএল টনের ছবি দাও', 'show picture of respirex', 'কফটন সিরাপ দেখতে কেমন'
        """
        text_lower = text.lower()
        
        image_triggers = [
            "ছবি", "ফটো", "পিকচার", "পিক", "দেখতে কেমন", "কেমন দেখতে", 
            "photo", "picture", "image", "pic", "look like", "show me", "visual"
        ]
        
        has_image_intent = any(trig in text_lower for trig in image_triggers)
        
        matched_products = []
        if has_image_intent:
            matched_products = HerbalCatalogService.search(text_lower)
        
        return {
            "has_image_intent": has_image_intent,
            "matched_herbs": matched_products,
            "count": len(matched_products)
        }


# ── API Endpoints ─────────────────────────────────────────────────────────────
@app.get("/herbs")
async def list_herbs(search: Optional[str] = None):
    """List or search official Unani medicines catalog."""
    if search:
        results = HerbalCatalogService.search(search)
    else:
        results = HerbalCatalogService.get_all()
    return {"success": True, "count": len(results), "herbs": results}


@app.get("/herbs/{herb_id}")
async def get_herb(herb_id: str):
    """Retrieve specific product details."""
    herb = HerbalCatalogService.find_by_id(herb_id)
    if not herb:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"success": True, "herb": herb}


@app.post("/detect-image-request")
async def detect_image_request_endpoint(payload: Dict[str, str]):
    """Analyze query for product photo request."""
    text = payload.get("text", "")
    result = HerbalCatalogService.detect_image_request(text)
    return {"success": True, **result}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "unani-products-catalog-service",
        "total_products": len(OFFICIAL_PRODUCTS_CATALOG)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8012)
