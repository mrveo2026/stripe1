# credit_system.py
import json
import os
from datetime import datetime

# ==================== CONFIGURATION ====================
CREDITS_FILE = "credits.json"
TRANSACTIONS_FILE = "transactions.json"

# ==================== LOAD / SAVE ====================
def load_credits():
    """Load credits from file"""
    try:
        with open(CREDITS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_credits(data):
    """Save credits to file"""
    with open(CREDITS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def load_transactions():
    """Load transaction history"""
    try:
        with open(TRANSACTIONS_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_transaction(user_id, amount, transaction_type, description):
    """Save a transaction record"""
    transactions = load_transactions()
    transactions.append({
        "user_id": str(user_id),
        "amount": amount,
        "type": transaction_type,
        "description": description,
        "timestamp": str(datetime.now())
    })
    # Keep only last 1000 transactions
    if len(transactions) > 1000:
        transactions = transactions[-1000:]
    with open(TRANSACTIONS_FILE, 'w') as f:
        json.dump(transactions, f, indent=2)

# ==================== CREDIT OPERATIONS ====================
def get_user_credits(user_id):
    """Get credits for a user"""
    credits = load_credits()
    return credits.get(str(user_id), 0)

def set_user_credits(user_id, amount):
    """Set credits for a user"""
    credits = load_credits()
    credits[str(user_id)] = amount
    save_credits(credits)

def add_credits(user_id, amount, username=None, description="Added credits"):
    """Add credits to user"""
    credits = load_credits()
    uid = str(user_id)
    
    if uid not in credits:
        credits[uid] = 0
        if username:
            credits[uid + "_username"] = username
    
    credits[uid] += amount
    save_credits(credits)
    save_transaction(user_id, amount, "add", description)
    
    return credits[uid]

def deduct_credit(user_id, amount):
    """Deduct credits from user (return False if insufficient)"""
    credits = load_credits()
    uid = str(user_id)
    
    if uid not in credits:
        return False
    
    if credits[uid] < amount:
        return False
    
    credits[uid] -= amount
    save_credits(credits)
    save_transaction(user_id, -amount, "deduct", f"Check cost: {amount}")
    
    return True

def get_all_users():
    """Get list of all users with credits"""
    credits = load_credits()
    users = []
    
    for uid, value in credits.items():
        if uid.endswith("_username"):
            continue
        
        username = credits.get(uid + "_username", "Unknown")
        users.append((uid, username, value, 0))
    
    # Sort by credits (highest first)
    users.sort(key=lambda x: x[2], reverse=True)
    return users

def get_user_transactions(user_id, limit=20):
    """Get transaction history for a user"""
    transactions = load_transactions()
    user_transactions = [t for t in transactions if str(t["user_id"]) == str(user_id)]
    return user_transactions[-limit:]

def get_total_users():
    """Get total number of users"""
    credits = load_credits()
    count = 0
    for key in credits:
        if not key.endswith("_username"):
            count += 1
    return count

def get_total_credits_in_system():
    """Get total credits in the system"""
    credits = load_credits()
    total = 0
    for key, value in credits.items():
        if not key.endswith("_username"):
            total += value
    return total

def reset_user_credits(user_id):
    """Reset credits for a user to 0"""
    set_user_credits(user_id, 0)
    save_transaction(user_id, 0, "reset", "Credits reset to 0")

def transfer_credits(from_user, to_user, amount):
    """Transfer credits between users"""
    if deduct_credit(from_user, amount):
        add_credits(to_user, amount, None, f"Transfer from {from_user}")
        save_transaction(from_user, -amount, "transfer_out", f"Transfer to {to_user}")
        save_transaction(to_user, amount, "transfer_in", f"Transfer from {from_user}")
        return True
    return False

# ==================== STATISTICS ====================
def get_system_stats():
    """Get system statistics"""
    transactions = load_transactions()
    
    total_checks = len([t for t in transactions if t["type"] == "deduct"])
    total_added = sum(t["amount"] for t in transactions if t["type"] == "add")
    total_spent = abs(sum(t["amount"] for t in transactions if t["type"] == "deduct"))
    
    return {
        "total_users": get_total_users(),
        "total_credits": get_total_credits_in_system(),
        "total_checks": total_checks,
        "total_added": total_added,
        "total_spent": total_spent
    }

# ==================== INIT ====================
def init_system():
    """Initialize credit system files"""
    if not os.path.exists(CREDITS_FILE):
        save_credits({})
    if not os.path.exists(TRANSACTIONS_FILE):
        with open(TRANSACTIONS_FILE, 'w') as f:
            json.dump([], f)

# Auto init on import
init_system()

# ==================== TEST ====================
if __name__ == "__main__":
    print("=" * 50)
    print("Credit System Test")
    print("=" * 50)
    
    # Test user
    test_user = "123456789"
    
    # Add credits
    print(f"\n[+] Adding 100 credits to {test_user}")
    add_credits(test_user, 100, "TestUser", "Initial deposit")
    print(f"    Balance: {get_user_credits(test_user)}")
    
    # Deduct credits
    print(f"\n[+] Deducting 10 credits from {test_user}")
    result = deduct_credit(test_user, 10)
    print(f"    Success: {result}")
    print(f"    Balance: {get_user_credits(test_user)}")
    
    # Check insufficient
    print(f"\n[+] Trying to deduct 1000 credits")
    result = deduct_credit(test_user, 1000)
    print(f"    Success: {result}")
    
    # Get all users
    print(f"\n[+] All Users:")
    for uid, username, credits, used in get_all_users():
        print(f"    {username} ({uid}): {credits} credits")
    
    # Get transactions
    print(f"\n[+] Transactions for {test_user}:")
    for t in get_user_transactions(test_user):
        print(f"    {t['timestamp']}: {t['type']} {t['amount']} - {t['description']}")
    
    # System stats
    print(f"\n[+] System Stats:")
    stats = get_system_stats()
    for key, value in stats.items():
        print(f"    {key}: {value}")
    
    print("\n" + "=" * 50)
