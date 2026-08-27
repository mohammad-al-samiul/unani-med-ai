# UptimeRobot Monitoring Setup Guide

## Overview
এই গাইডে UptimeRobot সেটআপ ব্যাখ্যা করা হয়েছে যা আপনার n8n webhook URL monitor করবে এবং downtime হলে Telegram দিয়ে notification পাঠাবে।

## Prerequisites

### ১. UptimeRobot Account:
- ফ্রি account create করুন: https://uptimerobot.com/
- Free plan-এ 50 monitors পর্যন্ত পাবেন

### ২. Telegram Bot:
- Telegram-এ BotFather দিয়ে bot create করুন
- Bot token save করুন
- আপনার Telegram chat ID পান

## Step-by-Step Setup

### Step 1: Telegram Bot Setup

#### ১. BotFather দিয়ে Bot Create করুন:
```
1. Telegram-এ @BotFather খুঁজুন
2. /newbot কমান্ড দিন
3. Bot name দিন (যেমন: "UnaniMed AI Monitor")
4. Bot username দিন (যেমন: "unanimed_monitor_bot")
5. Bot token পাবেন (এটি save করুন)
```

#### ২. Chat ID পান:
```
1. আপনার নতুন bot-এ যান
2. "/start" কমান্ড দিন
3. নিচের URL-এ যান (আপনার bot token দিয়ে):
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
4. JSON response-এ "chat": {"id": 123456789} থেকে chat ID কপি করুন
```

### Step 2: UptimeRobot Monitor Setup

#### ১. UptimeRobot Dashboard-এ যান:
```
https://uptimerobot.com/dashboard
```

#### ২. New Monitor Add করুন:
```
1. "Add New Monitor" বাটনে ক্লিক করুন
2. Monitor Type: "HTTP(s)" সিলেক্ট করুন
3. Friendly Name: "UnaniMed AI Webhook"
4. URL: আপনার n8n webhook URL
   (যেমন: https://your-domain.com/webhook)
5. Monitoring Interval: 5 minutes (free plan-এ সর্বোচ্চ)
6. Alert Contacts: নতুন Telegram contact add করুন
```

#### ৩. Telegram Alert Contact Setup:
```
1. "Alert Contacts" সেকশনে যান
2. "Add Alert Contact" ক্লিক করুন
3. Alert Type: "Telegram" সিলেক্ট করুন
4. Bot Token: আপনার Telegram bot token paste করুন
5. Chat ID: আপনার Telegram chat ID paste করুন
6. "Save" ক্লিক করুন
```

#### ৪. Monitor Configuration:
```
Monitor Settings:
- Type: HTTP(s)
- URL: https://your-cloudflare-tunnel-url.com/webhook
- Check interval: 5 minutes
- Response time threshold: 2000ms
- Monitor locations: সব locations সিলেক্ট করুন

Alert Settings:
- Down alerts: Enable
- Up alerts: Enable
- SSL certificate alerts: Enable
- HTTP error alerts: Enable
```

### Step 3: Cloudflare Tunnel Configuration

যদি আপনি Cloudflare Tunnel ব্যবহার করেন:

#### ১. Tunnel URL Verify করুন:
```powershell
# আপনার Cloudflare tunnel URL test করুন
curl https://your-tunnel-url.com/webhook

# Expected: "Webhook verification failed" (বা আপনার verify response)
```

#### ২. UptimeRobot-এ Cloudflare URL Configure করুন:
```
UptimeRobot Monitor URL:
https://your-tunnel-name.your-username.workers.dev/webhook
```

## Alternative: n8n Webhook Health Check

### Health Check Endpoint Create করুন:

#### ১. Simple Health Check Node যোগ করুন:
```json
{
  "name": "Health Check Endpoint",
  "nodes": [
    {
      "parameters": {
        "path": "health",
        "responseMode": "responseNode",
        "options": {}
      },
      "name": "Health Check Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 1,
      "position": [250, 300]
    },
    {
      "parameters": {
        "respondWith": "json",
        "responseBody": "={{ { \"status\": \"healthy\", \"timestamp\": $now.toISO() } }}",
        "options": {}
      },
      "name": "Health Response",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1,
      "position": [450, 300]
    }
  ]
}
```

#### ২. UptimeRobot Monitor URL:
```
https://your-tunnel-url.com/health
```

## Advanced Configuration

### ১. Custom Alert Messages:

UptimeRobot-এ custom alert messages সেট করুন:

```
Down Alert:
"🚨 UnaniMed AI Webhook is DOWN! 
Monitor: {{MonitorName}}
URL: {{MonitorURL}}
Error: {{ErrorMessage}}
Time: {{AlertTime}}"

Up Alert:
"✅ UnaniMed AI Webhook is UP again!
Monitor: {{MonitorName}}
Time: {{AlertTime}}"
```

### ২. Multiple Alert Contacts:

একাধিক Telegram contacts add করুন:
- Primary admin: আপনার personal Telegram
- Backup admin: আপনার team member
- On-call rotation: ভিন্ন chat IDs

### ৩. Status Page:

UptimeRobot Status Page create করুন:
```
1. Dashboard-এ "Status Pages" সেকশনে যান
2. "Create Status Page" ক্লিক করুন
3. Monitors select করুন
4. Custom domain সেট করুন (optional)
5. Public URL share করুন
```

## Testing Setup

### ১. Manual Downtime Test:
```powershell
# n8n বন্ধ করুন
# UptimeRobot alert আসতে 5-10 মিনিট সময় লাগবে

# n8n চালু করুন
# UptimeRobot up alert আসবে
```

### ২. Telegram Notification Test:
```
1. আপনার Telegram bot-এ ম্যানুয়ালি মেসেজ পাঠান
2. Bot response check করুন
3. UptimeRobot alert পেলেন কিনা verify করুন
```

## Troubleshooting

### ১. Telegram Bot Not Responding:
```
Solutions:
- Bot token সঠিক কিনা check করুন
- Chat ID সঠিক কিনা verify করুন
- Bot আপনার দ্বারা start করা হয়েছে কিনা check করুন
- API endpoint test করুন: https://api.telegram.org/bot<token>/getMe
```

### ২. UptimeRobot False Alerts:
```
Solutions:
- Check interval বাড়ান (5 minutes → 10 minutes)
- Response time threshold বাড়ান
- Monitor locations সমন্বয় করুন
- Cloudflare tunnel stability verify করুন
```

### ৃ. Webhook URL Not Accessible:
```
Solutions:
- Cloudflare tunnel running আছে কিনা check করুন
- n8n webhook URL correct কিনা verify করুন
- Firewall settings check করুন
- DNS propagation অপেক্ষা করুন
```

## Integration with Existing Services

### ১. n8n Error Workflow + UptimeRobot:
```
n8n error workflow থেকে সরাসরি Telegram notification:
- Error log করার সময় Telegram bot কল করুন
- Error details send করুন
- UptimeRobot দিয়ে service-level monitoring
```

### ২. Backup Script + UptimeRobot:
```
Backup status monitoring:
- Backup script completion webhook endpoint create করুন
- UptimeRobot monitor করুন backup status endpoint
- Failed backup হলে alert পান
```

## Security Considerations

### ১. Bot Token Security:
```
- Bot token কখনো public repository-এ commit করবেন না
- Environment variables ব্যবহার করুন
- Regular token rotation করুন
```

### ২. Chat ID Privacy:
```
- Chat ID সংবেদনশীল information
- Secure storage ব্যবহার করুন
- Access control implement করুন
```

### ৩. Webhook URL Protection:
```
- Rate limiting implement করুন
- IP whitelisting বিবেচনা করুন
- Authentication add করুন
```

## Cost Analysis

### Free Plan Limitations:
```
UptimeRobot Free:
- 50 monitors
- 5-minute check interval
- 1 alert contact per monitor
- Basic alert types
- No custom SSL certificates

Pro Plan ($7/month):
- 50 monitors
- 1-minute check interval
- Unlimited alert contacts
- Advanced alerting
- Custom SSL certificates
- API access
```

## Maintenance

### ১. Regular Monitoring:
```
- Weekly status check
- Alert threshold সমন্বয়
- False positive analysis
- Performance monitoring
```

### ২. Configuration Updates:
```
- URLs change হলে update করুন
- Team members add/remove করলে alert contacts update করুন
- New services add করলে monitors add করুন
```

### ৩. Backup and Recovery:
```
- UptimeRobot configuration export করুন
- Alert contacts backup রাখুন
- Recovery procedure document করুন
```

## Alternative Solutions

### ১. Free Alternatives:
```
- Pingdom (free tier)
- StatusCake (free tier)
- Better Uptime (free tier)
- Self-hosted: Uptime Kuma
```

### ২. Advanced Solutions:
```
- Datadog (paid)
- New Relic (paid)
- Prometheus + Grafana (self-hosted)
- AWS CloudWatch (paid)
```

এই সেটআপের মাধ্যমে আপনার UnaniMed AI service 24/7 monitor হবে এবং কোনো downtime হলে instant Telegram notification পাবেন।