# bot.py
import requests
import telebot
import time
import re
import threading
import os
import random
from datetime import datetime
from telebot import types
from credit_system import *

# ==================== GATE IMPORTS ====================
# Dynamic import based on gate
import importlib

def get_gate_module(gate_file):
    """Dynamically import gate module"""
    try:
        module = importlib.import_module(gate_file.replace('.py', ''))
        return module
    except Exception as e:
        print(f"Error loading {gate_file}: {e}")
        return None

# Pre-load gate modules
gate_modules = {}
for g in ['gatet1', 'gatet2', 'gatet3', 'gatet4', 'gatet5', 'gatetHB']:
    mod = get_gate_module(g)
    if mod:
        gate_modules[g] = mod

# ==================== CONFIGURATION ====================
token = '8785536380:AAGkXq_OiZk4NXPqGDL7pRlR5VSQ_A3WlCo'
bot = telebot.TeleBot(token, parse_mode="HTML", num_threads=50)
subscriber = '5831292144'

COST_PER_CHECK = 1

RATE_LIMIT = {
    'single': {'max': 10, 'window': 60},
    'mass': {'max': 100, 'window': 60},
}
user_requests = {}

mass_state = {}
active_mass_checks = {}

# ==================== SINGLE CHECK CONFIG ====================
# /h1 -> gatet1, amount 0.5-0.6
# /h2 -> gatet2, amount 0.7-1.0
# /h3 -> gatet3, amount 0.9-1.4
# /h4 -> gatet4, amount 1.0-3.0
# /h5 -> gatet5, amount 1.6-4.0
# /hb -> gatetHB, amount 10-13

SINGLE_GATES = {
    "h1": {"gate_file": "gatet1", "amount_min": 0.5, "amount_max": 0.6, "name": "Gate 1"},
    "h2": {"gate_file": "gatet2", "amount_min": 0.7, "amount_max": 1.0, "name": "Gate 2"},
    "h3": {"gate_file": "gatet3", "amount_min": 0.9, "amount_max": 1.4, "name": "Gate 3"},
    "h4": {"gate_file": "gatet4", "amount_min": 1.0, "amount_max": 3.0, "name": "Gate 4"},
    "h5": {"gate_file": "gatet5", "amount_min": 1.6, "amount_max": 4.0, "name": "Gate 5"},
    "hb": {"gate_file": "gatetHB", "amount_min": 10.0, "amount_max": 13.0, "name": "High Balance Gate"},
}

# ==================== MASS CHECK CONFIG ====================
# /v1 -> gatet1, amount 0.5-1.0
# /v2 -> gatet2, amount 0.7-1.4
# /v3 -> gatet3, amount 0.9-2.0
# /v4 -> gatet4, amount 1.0-2.0
# /v5 -> gatet5, amount 5.0-5.5
# /zv -> gatetHB, amount 20-25

MASS_GATES = {
    "v1": {"gate_file": "gatet1", "amount_min": 0.5, "amount_max": 1.0, "name": "Gate 1"},
    "v2": {"gate_file": "gatet2", "amount_min": 0.7, "amount_max": 1.4, "name": "Gate 2"},
    "v3": {"gate_file": "gatet3", "amount_min": 0.9, "amount_max": 2.0, "name": "Gate 3"},
    "v4": {"gate_file": "gatet4", "amount_min": 1.0, "amount_max": 2.0, "name": "Gate 4"},
    "v5": {"gate_file": "gatet5", "amount_min": 5.0, "amount_max": 5.5, "name": "Gate 5"},
    "zv": {"gate_file": "gatetHB", "amount_min": 20.0, "amount_max": 25.0, "name": "High Balance Gate"},
}

# ==================== RATE LIMITING ====================
def check_rate_limit(user_id, check_type='single'):
    now = time.time()
    if user_id not in user_requests:
        user_requests[user_id] = {'single': [], 'mass': []}
    
    user_reqs = user_requests[user_id][check_type]
    user_reqs = [t for t in user_reqs if now - t < RATE_LIMIT[check_type]['window']]
    user_requests[user_id][check_type] = user_reqs
    
    if len(user_reqs) >= RATE_LIMIT[check_type]['max']:
        return False
    user_reqs.append(now)
    return True

# ==================== CARD EXTRACTION ====================
def extract_card_from_text(text):
    if not text:
        return None
    text = text.strip()
    
    parts = text.split('|')
    if len(parts) >= 4:
        if re.match(r'^\d{13,19}$', parts[0].strip()):
            mm = ''
            yy = ''
            cvc = ''
            
            mm_yy_str = parts[1].strip() if len(parts) > 1 else ''
            mm_yy_match = re.search(r'(\d{1,2})[/|\-]?(\d{2,4})', mm_yy_str)
            if mm_yy_match:
                mm = mm_yy_match.group(1).zfill(2)
                yy_raw = mm_yy_match.group(2)
                yy = yy_raw[-2:] if len(yy_raw) > 2 else yy_raw
            else:
                mm = parts[1].strip()[:2] if len(parts[1].strip()) >= 2 else ''
                yy = parts[2].strip()[:2] if len(parts) > 2 else ''
            
            cvc = parts[2].strip() if len(parts) > 2 else ''
            if not re.match(r'^\d{3,4}$', cvc):
                cvv_match = re.search(r'\b(\d{3,4})\b', parts[3] if len(parts) > 3 else '')
                if cvv_match:
                    cvc = cvv_match.group(1)
            
            if mm and yy and cvc and len(cvc) >= 3:
                return f"{parts[0].strip()}|{mm}|{yy}|{cvc}"
    
    card_patterns = [
        r'(\d{13,19})\s*[|\-]\s*(\d{1,2})[/|\-]?(\d{2,4})\s*[|\-]\s*(\d{3,4})',
        r'(\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4})\s*[|\-]\s*(\d{1,2})[/]?(\d{2,4})\s*[|\-]\s*(\d{3,4})',
        r'(\d{13,19})\s*(\d{1,2})[/](\d{2,4})\s*(\d{3,4})',
    ]
    
    for pattern in card_patterns:
        match = re.search(pattern, text)
        if match:
            card_num = re.sub(r'[-\s]', '', match.group(1))
            mm = match.group(2).zfill(2)
            yy_raw = match.group(3)
            yy = yy_raw[-2:] if len(yy_raw) > 2 else yy_raw
            cvc = match.group(4)
            if len(card_num) >= 13 and len(cvc) >= 3:
                return f"{card_num}|{mm}|{yy}|{cvc}"
    
    return None

# ==================== CHECK PERMISSION ====================
def can_check(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    if str(user_id) == subscriber:
        return True, "ADMIN"
    
    if chat_id != user_id:
        try:
            admins = bot.get_chat_administrators(chat_id)
            for admin in admins:
                if admin.user.id == user_id:
                    return True, "GROUP_ADMIN"
        except:
            pass
        return False, "❌ Only group admins can use this bot in groups."
    
    credits = get_user_credits(user_id)
    if credits >= COST_PER_CHECK:
        return True, f"PRIVATE_{credits}"
    return False, f"❌ Insufficient credits! You have {credits} credits."

# ==================== RESPONSE CLASSIFICATION ====================
def classify_gate_response(response_text):
    last_lower = response_text.lower()
    
    if "expired" in last_lower or "card has expired" in last_lower:
        return "EXPIRED", "EXPIRED", "📅", False
    if any(kw in last_lower for kw in ['network_error', 'timeout', 'stripe_error', 'wp_error']):
        return "ERROR", "ERROR", "⚠️", False
    if any(kw in last_lower for kw in ['thank', 'success', 'succeeded', 'charged', 'hit', 'payment success', 'approved']):
        return "HIT", "APPROVED", "🔥", True
    if any(kw in last_lower for kw in ['security code is incorrect', 'incorrect_cvv', 'incorrect_cvc']):
        return "CCN", "CCN LIVE", "✅", True
    if any(kw in last_lower for kw in ['transaction_not_allowed', 'do_not_honor']):
        return "CVV", "CVV LIVE", "✅", True
    if any(kw in last_lower for kw in ['verifying', 'action_required', 'requires_action', '3ds', 'otp']):
        return "3DS", "3DS REQUIRED", "🔐", True
    if any(kw in last_lower for kw in ['insufficient funds', 'insufficient_funds']):
        return "INSUFFICIENT", "INSUFFICIENT FUNDS", "💰", True
    
    return "DEAD", "DEAD", "❌", False

# ==================== BIN INFO ====================
bin_cache = {}

def get_bin_info(bin_num):
    if bin_num in bin_cache:
        return bin_cache[bin_num].copy()
    try:
        response = requests.get(f'https://lookup.binlist.net/{bin_num}', timeout=10)
        if response.status_code == 200:
            data = response.json()
            info = {
                'bank': data.get('bank', {}).get('name', 'Unknown').upper(),
                'emoji': data.get('country', {}).get('emoji', '🏳️'),
                'country': data.get('country', {}).get('name', 'Unknown').upper(),
                'scheme': data.get('scheme', 'UNKNOWN').upper(),
                'type': data.get('type', 'UNKNOWN').upper(),
                'level': data.get('brand', 'STANDARD').upper(),
            }
            bin_cache[bin_num] = info.copy()
            return info
    except: pass
    
    first_digit = bin_num[0] if bin_num else '4'
    scheme_map = {'4': 'VISA', '5': 'MASTERCARD', '3': 'AMEX', '6': 'DISCOVER'}
    
    info = {
        'bank': 'UNKNOWN BANK', 'emoji': '🏳️', 'country': 'UNKNOWN',
        'scheme': scheme_map.get(first_digit, 'UNKNOWN'), 'type': 'CREDIT', 'level': 'STANDARD',
    }
    bin_cache[bin_num] = info.copy()
    return info

# ==================== CHECK SINGLE CARD ====================
def check_single_card(cc, gate_module, amount, user_id, cl):
    """Check card using specified gate module"""
    for attempt in range(2):
        try:
            time.sleep(random.uniform(0.5, 1.0))
            
            bin_info = get_bin_info(cc[:6])
            result = gate_module.Tele(cc, amount)
            if isinstance(result, tuple) and len(result) >= 2:
                response_text = result[0]
            else:
                response_text = str(result)
            
            if not response_text or len(response_text.strip()) < 5:
                if attempt == 0:
                    time.sleep(2)
                    continue
                response_text = "No response from gateway"
            
            sc, sd, icon, _ = classify_gate_response(response_text)
            
            if sc in ["EXPIRED", "ERROR"] and cc in cl:
                try: add_credits(user_id, COST_PER_CHECK, None, f"Refund: {sc}")
                except: pass
            
            p = cc.split("|")
            return {
                'cc': cc,
                'card_display': f"{p[0]}|{p[1]}|{p[2]}|{p[3]}",
                'status': sd, 'icon': icon, 'status_code': sc,
                'response': response_text[:100], 'bin_info': bin_info
            }
        except Exception as e:
            if attempt == 0:
                time.sleep(2)
                continue
            p = cc.split("|")
            if cc in cl:
                try: add_credits(user_id, COST_PER_CHECK, None, "Refund: exception")
                except: pass
            return {
                'cc': cc,
                'card_display': f"{p[0]}|{p[1]}|{p[2]}|{p[3]}",
                'status': 'ERROR', 'icon': '⚠️', 'status_code': 'ERROR',
                'response': str(e)[:100],
                'bin_info': {'scheme': 'UNKNOWN', 'type': 'UNKNOWN', 'level': 'UNKNOWN', 'country': 'UNKNOWN', 'emoji': '🏳️', 'bank': 'UNKNOWN'}
            }
    
    p = cc.split("|")
    return {
        'cc': cc, 'card_display': f"{p[0]}|{p[1]}|{p[2]}|{p[3]}",
        'status': 'UNKNOWN', 'icon': '❓', 'status_code': 'UNKNOWN',
        'response': 'Check failed after retries',
        'bin_info': {'scheme': 'UNKNOWN', 'type': 'UNKNOWN', 'level': 'UNKNOWN', 'country': 'UNKNOWN', 'emoji': '🏳️', 'bank': 'UNKNOWN'}
    }

# ==================== SINGLE CHECK ====================
@bot.message_handler(func=lambda message: message.text and re.match(r'^(/|\.)(h[1-5]|hb)', message.text, re.IGNORECASE))
def single_check(message):
    if not check_rate_limit(message.from_user.id, 'single'):
        return bot.reply_to(message, "⏳ Rate limit exceeded! Please wait 1 minute.")
    
    allowed, msg = can_check(message)
    if not allowed:
        return bot.reply_to(message, msg)
    
    text = message.text.strip()
    
    if text.startswith('/'):
        cmd_part = text.split()[0].replace('/', '').lower()
        card_part = text.replace(f'/{cmd_part}', '', 1).strip()
    else:
        cmd_part = text.split()[0].replace('.', '').lower()
        card_part = text.replace(f'.{cmd_part}', '', 1).strip()
    
    gate_key = cmd_part.lower()
    
    if gate_key not in SINGLE_GATES:
        return bot.reply_to(message, "❌ Invalid gate! Use: /h1 /h2 /h3 /h4 /h5 /hb")
    
    gate_info = SINGLE_GATES[gate_key]
    
    # Check if gate module is loaded
    if gate_info['gate_file'] not in gate_modules:
        return bot.reply_to(message, f"❌ Gate module {gate_info['gate_file']}.py not found!")
    
    gate_module = gate_modules[gate_info['gate_file']]
    
    if not card_part:
        if message.reply_to_message:
            replied_text = message.reply_to_message.text or message.reply_to_message.caption or ''
            card_part = extract_card_from_text(replied_text)
            if not card_part:
                return bot.reply_to(message, f"📌 Usage: /{cmd_part} card|mm|yy|cvv")
        else:
            return bot.reply_to(message, f"📌 Usage: /{cmd_part} card|mm|yy|cvv")
    
    if '|' not in card_part or len(card_part.split('|')) != 4:
        extracted = extract_card_from_text(card_part)
        if extracted:
            card_part = extracted
        else:
            return bot.reply_to(message, "❌ Could not extract valid card.")
    
    cc = card_part.strip()
    if len(cc.split("|")) != 4:
        return bot.reply_to(message, "❌ Invalid format!")
    
    user_id = message.from_user.id
    chat_id = message.chat.id
    is_private_admin = str(user_id) == subscriber
    is_group = chat_id != user_id
    
    credit_deducted = False
    if not is_group and not is_private_admin:
        if not deduct_credit(user_id, COST_PER_CHECK):
            return bot.reply_to(message, f"❌ Insufficient credits! You have {get_user_credits(user_id)} credits.")
        credit_deducted = True
    
    # Random amount in range
    amount = round(random.uniform(gate_info['amount_min'], gate_info['amount_max']), 2)
    username = message.from_user.username or message.from_user.first_name
    
    processing = bot.reply_to(message, f"⏳ <b>Processing...</b>\n<b>Gate:</b> {gate_info['name']}\n<b>Amount:</b> ${amount}", parse_mode="HTML")
    start_time = time.time()
    
    cl = [cc] if credit_deducted else []
    result = check_single_card(cc, gate_module, str(amount), user_id, cl)
    elapsed = time.time() - start_time
    bi = result['bin_info']
    
    r = f"""<b>Transaction Details</b>
<b>CC:</b> <code>{result['card_display']}</code>
<b>Status:</b> {result['status']} {result['icon']}
<b>Gate:</b> {gate_info['name']} ${amount}
<b>Response:</b> {result['response']}

<b>BIN Details</b>
<b>❖ BIN:</b> {cc[:6]} - {bi['country']} {bi['emoji']}
<b>❖ Details:</b> {bi['scheme']}-{bi['type']}-{bi['level']}
<b>❖ Bank:</b> {bi['bank']}

<b>Bot:</b> @{bot.get_me().username}
<b>Checked By:</b> @{username} [VIP]
<b>Time Taken:</b> {elapsed:.2f} seconds"""
    
    try: bot.edit_message_text(r, message.chat.id, processing.message_id, parse_mode="HTML")
    except: pass

# ==================== MASS CHECK ====================
@bot.message_handler(func=lambda message: message.text and re.match(r'^(/|\.)(v[1-5]|zv)', message.text, re.IGNORECASE))
def mass_check_start(message):
    allowed, msg = can_check(message)
    if not allowed:
        return bot.reply_to(message, msg)
    
    text = message.text.strip()
    
    if text.startswith('/'):
        cmd_part = text.split()[0].replace('/', '').lower()
        cards_part = text.replace(f'/{cmd_part}', '', 1).strip()
    else:
        cmd_part = text.split()[0].replace('.', '').lower()
        cards_part = text.replace(f'.{cmd_part}', '', 1).strip()
    
    gate_key = cmd_part.lower()
    
    if gate_key not in MASS_GATES:
        return bot.reply_to(message, "❌ Invalid gate! Use: /v1 /v2 /v3 /v4 /v5 /zv")
    
    gate_info = MASS_GATES[gate_key]
    
    # Check if gate module is loaded
    if gate_info['gate_file'] not in gate_modules:
        return bot.reply_to(message, f"❌ Gate module {gate_info['gate_file']}.py not found!")
    
    gate_module = gate_modules[gate_info['gate_file']]
    
    cards = []
    if cards_part:
        for line in cards_part.split('\n'):
            line = line.strip()
            if line:
                extracted = extract_card_from_text(line)
                if extracted:
                    cards.append(extracted)
    elif message.reply_to_message:
        replied_text = message.reply_to_message.text or message.reply_to_message.caption or ''
        if replied_text:
            for line in replied_text.split('\n'):
                line = line.strip()
                if line:
                    extracted = extract_card_from_text(line)
                    if extracted:
                        cards.append(extracted)
    
    if len(cards) > 20:
        cards = cards[:20]
        bot.reply_to(message, "⚠️ Limit is 20 cards! Checking first 20.")
    
    if cards:
        user_id = message.from_user.id
        chat_id = message.chat.id
        credit_deducted_list = []
        
        if chat_id == user_id and str(user_id) != subscriber:
            total_cost = len(cards) * COST_PER_CHECK
            if get_user_credits(user_id) < total_cost:
                return bot.reply_to(message, f"❌ Need {total_cost} credits for {len(cards)} cards.")
            for card in cards:
                if deduct_credit(user_id, COST_PER_CHECK):
                    credit_deducted_list.append(card)
        
        # Random amount for each card
        amounts = [round(random.uniform(gate_info['amount_min'], gate_info['amount_max']), 2) for _ in range(len(cards))]
        avg_amount = round(sum(amounts) / len(amounts), 2) if amounts else 0
        
        # Build initial progress
        progress_lines = []
        for i, card in enumerate(cards):
            parts = card.split("|")
            card_num = parts[0]
            month = parts[1] if len(parts) > 1 else "XX"
            year = parts[2] if len(parts) > 2 else "XX"
            cvv = parts[3] if len(parts) > 3 else "XXX"
            
            if i == 0:
                status = "Processing 🏃‍♂️"
            else:
                status = "Waiting ⏳"
            
            progress_lines.append(f"<b>CC:</b> <code>{card_num}|{month}|{year}|{cvv}</code>\n<b>Status:</b> {status}")
        
        bot_username = bot.get_me().username
        username = message.from_user.username or message.from_user.first_name
        
        progress_text = f"""<b>Mass Check</b>
<b>────────────────────────</b>
<b>Gateway:</b> {gate_info['name']}
<b>Amount Range:</b> ${gate_info['amount_min']} - ${gate_info['amount_max']}

{chr(10).join(progress_lines)}

<b>Bot:</b> @{bot_username}
<b>Checked By:</b> @{username} [VIP]
<b>Time Taken:</b> 0.0 seconds"""
        
        status_msg = bot.reply_to(message, progress_text, parse_mode="HTML")
        
        thread = threading.Thread(target=run_mass_check, args=(message, cards, gate_info, gate_module, amounts, credit_deducted_list, status_msg.message_id))
        thread.start()
        return
    
    summary_text = f"""<b>📥 Mass Check - Input Required</b>
<b>Gate:</b> {gate_info['name']}
<b>Amount Range:</b> ${gate_info['amount_min']} - ${gate_info['amount_max']}

Send cards
Format: cc|mm|yy|cvv

🛑 /stop to cancel"""

    sent_msg = bot.reply_to(message, summary_text, parse_mode="HTML")
    mass_state[message.chat.id] = {
        "waiting": True,
        "gate_info": gate_info,
        "gate_module": gate_module,
        "prompt_msg_id": sent_msg.message_id
    }

@bot.message_handler(commands=["stop"])
def stop_mass_check(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    flag_file = f"stop_{chat_id}_{user_id}.flag"
    try:
        with open(flag_file, 'w') as f:
            f.write("stop")
    except:
        pass
    
    if chat_id in active_mass_checks:
        active_mass_checks[chat_id]["stop"] = True
    bot.reply_to(message, "🛑 <b>Mass check stopped.</b>", parse_mode="HTML")

def is_stopped(chat_id, user_id):
    flag_file = f"stop_{chat_id}_{user_id}.flag"
    if os.path.exists(flag_file):
        try:
            os.remove(flag_file)
        except:
            pass
        return True
    return False

@bot.message_handler(func=lambda message: message.chat.id in mass_state and mass_state[message.chat.id].get("waiting"))
def process_mass_cards(message):
    if not message.text:
        return
    
    if message.text.startswith("/"):
        return
    
    gate_info = mass_state[message.chat.id].get("gate_info")
    gate_module = mass_state[message.chat.id].get("gate_module")
    if not gate_info or not gate_module:
        return
    
    lines = message.text.strip().split('\n')
    cards = []
    for line in lines:
        line = line.strip()
        if line:
            extracted = extract_card_from_text(line)
            if extracted:
                cards.append(extracted)
    
    if not cards:
        return bot.reply_to(message, "❌ No valid cards found!")
    
    if len(cards) > 20:
        cards = cards[:20]
        bot.reply_to(message, "⚠️ Limit is 20 cards! Checking first 20.")
    
    user_id = message.from_user.id
    chat_id = message.chat.id
    credit_deducted_list = []
    
    if chat_id == user_id and str(user_id) != subscriber:
        total_cost = len(cards) * COST_PER_CHECK
        if get_user_credits(user_id) < total_cost:
            mass_state.pop(message.chat.id, None)
            return bot.reply_to(message, f"❌ Need {total_cost} credits for {len(cards)} cards.")
        for card in cards:
            if deduct_credit(user_id, COST_PER_CHECK):
                credit_deducted_list.append(card)
    
    mass_state.pop(message.chat.id, None)
    
    # Random amounts
    amounts = [round(random.uniform(gate_info['amount_min'], gate_info['amount_max']), 2) for _ in range(len(cards))]
    
    # Build initial progress
    bot_username = bot.get_me().username
    username = message.from_user.username or message.from_user.first_name
    
    progress_lines = []
    for i, card in enumerate(cards):
        parts = card.split("|")
        card_num = parts[0]
        month = parts[1] if len(parts) > 1 else "XX"
        year = parts[2] if len(parts) > 2 else "XX"
        cvv = parts[3] if len(parts) > 3 else "XXX"
        
        if i == 0:
            status = "Processing 🏃‍♂️"
        else:
            status = "Waiting ⏳"
        
        progress_lines.append(f"<b>CC:</b> <code>{card_num}|{month}|{year}|{cvv}</code>\n<b>Status:</b> {status}")
    
    progress_text = f"""<b>Mass Check</b>
<b>────────────────────────</b>
<b>Gateway:</b> {gate_info['name']}
<b>Amount Range:</b> ${gate_info['amount_min']} - ${gate_info['amount_max']}

{chr(10).join(progress_lines)}

<b>Bot:</b> @{bot_username}
<b>Checked By:</b> @{username} [VIP]
<b>Time Taken:</b> 0.0 seconds"""
    
    status_msg = bot.reply_to(message, progress_text, parse_mode="HTML")
    
    thread = threading.Thread(target=run_mass_check, args=(message, cards, gate_info, gate_module, amounts, credit_deducted_list, status_msg.message_id))
    thread.start()

def run_mass_check(original_message, cards, gate_info, gate_module, amounts, credit_deducted_list, status_msg_id):
    chat_id = original_message.chat.id
    user_id = original_message.from_user.id
    total = len(cards)
    gate_name = gate_info['name']
    start_time = time.time()
    
    if chat_id not in active_mass_checks:
        active_mass_checks[chat_id] = {}
    active_mass_checks[chat_id]["stop"] = False
    active_mass_checks[chat_id]["user_id"] = user_id
    
    if total == 0:
        bot.send_message(chat_id, "❌ No cards to check!")
        return
    
    bot_username = bot.get_me().username
    username = original_message.from_user.username or original_message.from_user.first_name
    
    card_results = []
    checked_count = 0
    
    for idx, cc in enumerate(cards):
        if is_stopped(chat_id, user_id) or active_mass_checks.get(chat_id, {}).get("stop", False):
            for remaining in cards[idx:]:
                parts = remaining.split("|")
                card_num = parts[0]
                month = parts[1] if len(parts) > 1 else "XX"
                year = parts[2] if len(parts) > 2 else "XX"
                cvv = parts[3] if len(parts) > 3 else "XXX"
                card_results.append({
                    'display': f"<b>CC:</b> <code>{card_num}|{month}|{year}|{cvv}</code>\n<b>Status:</b> STOPPED 🛑",
                })
            break
        
        amount = amounts[idx] if idx < len(amounts) else round(random.uniform(gate_info['amount_min'], gate_info['amount_max']), 2)
        
        result = check_single_card(cc, gate_module, str(amount), user_id, credit_deducted_list)
        
        bi = result['bin_info']
        card_results.append({
            'display': f"""<b>CC:</b> <code>{result['card_display']}</code>
<b>Status:</b> {result['status']} {result['icon']}
<b>Response:</b> {result['response']}
<b>BIN:</b> {bi['scheme']} - {bi['type']} - {bi['level']}
{bi['country']} {bi['emoji']} - {bi['bank']}""",
        })
        
        checked_count = idx + 1
        
        # Update progress
        progress_lines = []
        for i, cr in enumerate(card_results):
            if i < checked_count:
                progress_lines.append(cr['display'])
        
        for i in range(checked_count, total):
            remaining = cards[i]
            parts = remaining.split("|")
            card_num = parts[0]
            month = parts[1] if len(parts) > 1 else "XX"
            year = parts[2] if len(parts) > 2 else "XX"
            cvv = parts[3] if len(parts) > 3 else "XXX"
            
            if i == checked_count:
                status = "Processing 🏃‍♂️"
            else:
                status = "Waiting ⏳"
            
            progress_lines.append(f"<b>CC:</b> <code>{card_num}|{month}|{year}|{cvv}</code>\n<b>Status:</b> {status}")
        
        elapsed = time.time() - start_time
        
        progress_text = f"""<b>Mass Check</b>
<b>────────────────────────</b>
<b>Gateway:</b> {gate_name}
<b>Amount Range:</b> ${gate_info['amount_min']} - ${gate_info['amount_max']}

{chr(10).join(progress_lines)}

<b>Bot:</b> @{bot_username}
<b>Checked By:</b> @{username} [VIP]
<b>Time Taken:</b> {elapsed:.1f} seconds"""
        
        try:
            bot.edit_message_text(progress_text, chat_id, status_msg_id, parse_mode="HTML")
        except:
            pass
        
        time.sleep(random.uniform(0.5, 1.0))
    
    elapsed = time.time() - start_time
    final_lines = [cr['display'] for cr in card_results]
    
    final_text = f"""<b>Mass Check</b>
<b>────────────────────────</b>
<b>Gateway:</b> {gate_name}
<b>Amount Range:</b> ${gate_info['amount_min']} - ${gate_info['amount_max']}

{chr(10).join(final_lines)}

<b>Bot:</b> @{bot_username}
<b>Checked By:</b> @{username} [VIP]
<b>Time Taken:</b> {elapsed:.2f} seconds"""
    
    try:
        bot.edit_message_text(final_text, chat_id, status_msg_id, parse_mode="HTML")
    except:
        pass
    
    try:
        active_mass_checks.pop(chat_id, None)
    except: pass

# ==================== CREDIT COMMANDS ====================
@bot.message_handler(commands=["balance"])
def check_balance(message):
    credits = get_user_credits(message.from_user.id)
    bot.reply_to(message, f"💳 <b>Balance:</b> {credits} credits", parse_mode="HTML")

@bot.message_handler(commands=["addcredits"])
def add_credits_cmd(message):
    if str(message.from_user.id) != subscriber:
        bot.reply_to(message, "❌ Admin only!")
        return
    
    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "Usage: /addcredits user_id amount")
        return
    
    try:
        target_id = int(parts[1])
        amount = int(parts[2])
        add_credits(target_id, amount, None, f"Admin added {amount}")
        bot.reply_to(message, f"✅ Added {amount} credits to {target_id}")
    except:
        bot.reply_to(message, "❌ Invalid!")

@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    credits = get_user_credits(user_id)
    
    if credits == 0 and str(user_id) != subscriber:
        add_credits(user_id, 3, username, "Welcome bonus")
        credits = 3
    
    start_text = f"""<b>⚡ VEO3 CHECKER v2.0</b>
<b>Welcome,</b> @{username}
<b>Balance:</b> {credits} credits

<b>Single Check:</b>
/h1 - Gate 1 (0.5-0.6$)
/h2 - Gate 2 (0.7-1.0$)
/h3 - Gate 3 (0.9-1.4$)
/h4 - Gate 4 (1.0-3.0$)
/h5 - Gate 5 (1.6-4.0$)
/hb - High Balance (10-13$)

<b>Mass Check:</b>
/v1 - Gate 1 (0.5-1.0$)
/v2 - Gate 2 (0.7-1.4$)
/v3 - Gate 3 (0.9-2.0$)
/v4 - Gate 4 (1.0-2.0$)
/v5 - Gate 5 (5.0-5.5$)
/zv - High Balance (20-25$)"""

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💰 Pricing", callback_data="view_pricing"),
        types.InlineKeyboardButton("👤 My Info", callback_data="view_my_info")
    )
    markup.add(types.InlineKeyboardButton("🧑‍💻 Contact Admin", url="https://t.me/VEO3_2"))
    bot.reply_to(message, start_text, parse_mode="HTML", reply_markup=markup)

@bot.message_handler(commands=["buy"])
def buy_credits(message):
    bot.reply_to(message, "💳 Contact: @VEO3_2")

# ==================== CALLBACKS ====================
@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    user_id = call.from_user.id
    username = call.from_user.username or call.from_user.first_name
    credits = get_user_credits(user_id)
    
    if call.data == "none":
        bot.answer_callback_query(call.id)
        return

    back_markup = types.InlineKeyboardMarkup()
    back_markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="back_to_start"))
    
    if call.data == "view_pricing":
        text = f"""<b>💰 Pricing</b>
<b>💵 USD:</b> 1300 Credits/$1
<b>🇲🇲 MMK:</b> 1500 Credits/5000 MMK

<i>Contact @VEO3_2 to purchase</i>"""
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=back_markup)
    
    elif call.data == "view_my_info":
        rank = "👑 PREMIUM" if str(user_id) == subscriber else "👤 USER"
        text = f"""<b>👤 My Info</b>
<b>🆔 ID:</b> {user_id}
<b>👤 Username:</b> @{username}
<b>💳 Credits:</b> {credits}
<b>🎖 Rank:</b> {rank}"""
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=back_markup)
    
    elif call.data == "back_to_start":
        start_text = f"""<b>⚡ VEO3 CHECKER v2.0</b>
<b>Welcome,</b> @{username}
<b>Balance:</b> {credits} credits"""
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("💰 Pricing", callback_data="view_pricing"),
            types.InlineKeyboardButton("👤 My Info", callback_data="view_my_info")
        )
        markup.add(types.InlineKeyboardButton("🧑‍💻 Contact Admin", url="https://t.me/VEO3_2"))
        bot.edit_message_text(start_text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)

# ==================== START ====================
if __name__ == "__main__":
    print("=" * 50)
    print("CC CHECKER BOT STARTED")
    print("=" * 50)
    print("Loaded gates:", list(gate_modules.keys()))
    
    while True:
        try:
            bot.polling(non_stop=True, interval=1, timeout=30, long_polling_timeout=60)
        except requests.exceptions.ReadTimeout:
            print("⚠️ Timeout - reconnecting...")
            time.sleep(5)
        except requests.exceptions.ConnectionError:
            print("⚠️ Connection lost - reconnecting...")
            time.sleep(10)
        except Exception as e:
            print(f"⚠️ Error: {e} - restarting in 10s...")
            time.sleep(10)
