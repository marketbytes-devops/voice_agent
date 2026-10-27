# Exotel SIP Trunk to LiveKit Setup Guide

This guide details the procedure for connecting an **Exotel Indian Virtual Phone Number** via SIP Trunking to the **LiveKit Inbound SIP Service**.

---

## Architecture Overview
```
Caller (Mobile / Landline)
       │
       ▼
Exotel Telephony (India PSTN)
       │ (SIP Trunk over TLS / UDP)
       ▼
LiveKit SIP Inbound Trunk
       │ (Dispatches WebRTC Room)
       ▼
ClinicVoice Agent Worker (Python)
```

---

## Step 1: LiveKit Inbound SIP Trunk Configuration

1. **Create an Inbound SIP Trunk in LiveKit:**
   Using the `lk` CLI or LiveKit Cloud Dashboard:
   ```bash
   lk sip inbound create trunk.json
   ```
   **`trunk.json` example:**
   ```json
   {
     "name": "Exotel Kerala Trunk",
     "numbers": ["+919876500001"],
     "allowed_addresses": ["182.76.x.x/24", "125.21.x.x/24"]
   }
   ```
   *(Replace with Exotel's signaling IP ranges).*

2. **Create a SIP Dispatch Rule:**
   Maps the inbound trunk directly to a LiveKit room prefix:
   ```bash
   lk sip dispatch create dispatch.json
   ```
   **`dispatch.json` example:**
   ```json
   {
     "name": "ClinicVoice Dispatch",
     "trunk_ids": ["<TRUNK_ID>"],
     "rule": {
       "dispatch_rule_individual": {
         "room_prefix": "call-"
       }
     }
   }
   ```

---

## Step 2: Exotel Dashboard Configuration

1. **Purchase or Configure Virtual Number:**
   - Log into the Exotel Dashboard (`my.exotel.com`).
   - Navigate to **Phone Numbers** -> Select your virtual number (e.g. `080-XXXXXXXX` or `0477-XXXXXXX` for Alappuzha).

2. **Set up Exotel Applet / Flow:**
   - Go to **App Bazaar** -> Create an Applet flow.
   - Add a **Connect to SIP** applet.
   - Configure the SIP URI:
     `sip:<EXOTEL_PHONE_NUMBER>@<LIVEKIT_SIP_DOMAIN>:5060`
     *(For LiveKit Cloud: `sip:+919876500001@sip.livekit.cloud`).*
   - Set fallback forwarding number (e.g. Sreerudra Ayurveda Hospital front desk mobile number) for emergency or failover calls.

---

## Step 3: DLT Registration for Outbound SMS (India Regulatory)
Before sending post-call appointment confirmation SMS messages in India:
1. Register **Sreerudra Ayurveda Hospital** entity on an Indian Telecom DLT portal (e.g., Jio, Airtel, or Vodafone).
2. Register the Sender Header (e.g., `SRDRUD` or `CLINIC`).
3. Submit the bilingual confirmation template:
   > *"നമസ്കാരം {#var#}, ശ്രീരുദ്ര ആയുർവേദ ഹോസ്പിറ്റലിൽ ഡോക്ടർ {#var#} യുമായുള്ള താങ്കളുടെ അപ്പോയിന്റ്മെന്റ് {#var#} ന് ബുക്ക് ചെയ്തിരിക്കുന്നു. ഹെൽപ്പ്‌ലൈൻ: {#var#}"*
