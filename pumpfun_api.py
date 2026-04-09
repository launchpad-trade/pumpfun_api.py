"""
Pump Fun API — Complete Developer Guide
========================================
Create tokens and trade on PumpFun using the Launchpad.Trade API.
No official PumpFun API needed. Just REST endpoints.

What this script does:
1. Health check (GET /health)
2. Create wallets (POST /wallets/create)
3. Fund wallets (POST /funding/distribute)
4. Initialize wallets (POST /wallets/init)
5. Upload image to IPFS (POST pump.fun/api/ipfs)
6. Create token on PumpFun (POST /pumpfun/create)
7. Buy with multiple wallets (POST /trading/instant/buy)
8. Check balances (POST /wallets/balance)
9. Sell 100% (POST /trading/instant/sell)
10. Close accounts + withdraw (POST /utilities/close-accounts + /funding/withdraw)

Requirements:
    pip install requests base58 python-dotenv

Setup:
    1. Get your API key at https://launchpad.trade
    2. Copy .env.example to .env and fill in your keys
    3. Put a token image as image.png in this folder
    4. Run: python pumpfun_api.py

Documentation: https://docs.launchpad.trade
Discord: https://discord.com/invite/launchpad-trade
"""

import requests
import json
import os
import sys
import time
import logging
import base58
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

# =============================================================================
# CONFIG — loaded from .env file
# =============================================================================

API_KEY = os.getenv("LAUNCHPAD_API_KEY", "")
BASE_URL = "https://api.launchpad.trade"
MAIN_PRIVATE_KEY = os.getenv("MAIN_PRIVATE_KEY", "")

# Token settings
TOKEN_NAME = "PumpFunAPI"
TOKEN_SYMBOL = "PFAPI"
TOKEN_DESCRIPTION = "Pump Fun API demo — created via Launchpad.Trade"
TOKEN_IMAGE = "image.png"

# Settings
NUM_WALLETS = 3
FUND_AMOUNT = 0.02
BUY_AMOUNT = 0.005
DEV_BUY_AMOUNT = 0.01

# Constants
API_TIMEOUT = 30
SELL_DELAY = 3
SELL_RETRIES = 3
API_BATCH_LIMIT = 50
IPFS_UPLOAD_TIMEOUT = 30
PUBKEY_SIZE = 32
STATE_FILE = "state.json"
WALLETS_FILE = "wallets.json"

HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def derive_public_key(private_key_b58):
    key_bytes = base58.b58decode(private_key_b58)
    return base58.b58encode(key_bytes[PUBKEY_SIZE:PUBKEY_SIZE * 2]).decode("utf-8")


def is_success(data):
    return data.get("success") or data.get("status") == "success"


def api(method, path, body=None):
    url = f"{BASE_URL}{path}"
    try:
        if method == "GET":
            r = requests.get(url, headers=HEADERS, timeout=API_TIMEOUT)
        else:
            r = requests.post(url, headers=HEADERS, json=body, timeout=API_TIMEOUT)
        data = r.json()
    except requests.exceptions.Timeout:
        log.error(f"  [ERROR] Request timed out: {path}")
        return {"success": False}
    except requests.exceptions.ConnectionError:
        log.error(f"  [ERROR] Connection failed: {path}")
        return {"success": False}
    except requests.exceptions.JSONDecodeError:
        log.error(f"  [ERROR] Invalid response from {path}")
        return {"success": False}

    if not is_success(data):
        err = data.get("error", {})
        log.error(f"  [ERROR] {err.get('code', 'UNKNOWN')} -- {err.get('message', data)}")
    return data


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def load_wallets():
    if os.path.exists(WALLETS_FILE):
        with open(WALLETS_FILE, "r") as f:
            return json.load(f)
    return None


def save_wallets(data):
    with open(WALLETS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def validate_config():
    missing = []
    if not API_KEY:
        missing.append("LAUNCHPAD_API_KEY")
    if not MAIN_PRIVATE_KEY:
        missing.append("MAIN_PRIVATE_KEY")
    if missing:
        log.error(f"  [ERROR] Missing env vars: {', '.join(missing)}")
        log.error(f"  Copy .env.example to .env and fill in your keys.")
        sys.exit(1)


# ---------------------------------------------------------------------------
# STEP 1 — GET /health
# ---------------------------------------------------------------------------

def step_health():
    print("=" * 60)
    print("  STEP 1 — API Health Check")
    print("  GET /health")
    print("=" * 60)
    data = api("GET", "/health")
    if is_success(data):
        info = data["data"]
        print(f"  [OK] API is live")
        print(f"     Status  : {info['status']}")
        print(f"     Version : {info['version']}")
        print(f"     Region  : {info['region']}")
    else:
        print("  [FAIL] API not responding.")
        sys.exit(1)


# ---------------------------------------------------------------------------
# STEP 2 — POST /wallets/create
# ---------------------------------------------------------------------------

def step_create_wallets(main_public_key):
    print("=" * 60)
    print(f"  STEP 2 — Create {NUM_WALLETS} Wallets")
    print(f"  POST /wallets/create")
    print("=" * 60)

    existing = load_wallets()
    if existing and existing.get("buyers"):
        buyers = existing["buyers"]
        print(f"  [LOADED] {len(buyers)} wallets from {WALLETS_FILE}")
        return buyers

    data = api("POST", "/wallets/create", {"count": NUM_WALLETS})
    if not is_success(data):
        sys.exit(1)

    buyers = data["data"]["wallets"]
    save_wallets({
        "mainWallet": {"publicKey": main_public_key, "privateKey": MAIN_PRIVATE_KEY},
        "buyers": buyers
    })

    print(f"  [OK] {len(buyers)} wallets created")
    for i, w in enumerate(buyers):
        print(f"     #{i+1}: {w['publicKey']}")
    print(f"  Saved to {WALLETS_FILE}")
    return buyers


# ---------------------------------------------------------------------------
# STEP 3 — POST /funding/distribute
# ---------------------------------------------------------------------------

def step_fund(buyers):
    print("=" * 60)
    print(f"  STEP 3 — Fund Wallets")
    print(f"  POST /funding/distribute")
    print("=" * 60)

    pub_keys = [w["publicKey"] for w in buyers]
    bal_data = api("POST", "/wallets/balance", {"publicKeys": pub_keys})

    to_fund = []
    if is_success(bal_data):
        for b in bal_data["data"]["balances"]:
            if b.get("sol", 0) < FUND_AMOUNT:
                to_fund.append(b["wallet"])

    if not to_fund:
        print(f"  [OK] All wallets funded, skipping")
        return

    for i in range(0, len(to_fund), API_BATCH_LIMIT):
        batch = to_fund[i:i+API_BATCH_LIMIT]
        data = api("POST", "/funding/distribute", {
            "sourcePrivateKey": MAIN_PRIVATE_KEY,
            "destinationPublicKeys": batch,
            "amount": {"mode": "FIXED", "value": FUND_AMOUNT},
            "method": "DIRECT"
        })

        if is_success(data):
            summary = data["data"].get("summary", {})
            print(f"  [OK] {summary.get('successCount', '?')}/{summary.get('totalWallets', '?')} funded")
            print(f"     Total SOL sent: {summary.get('totalSolSent', '?')}")


# ---------------------------------------------------------------------------
# STEP 4 — POST /wallets/init
# ---------------------------------------------------------------------------

def step_init(buyers):
    print("=" * 60)
    print(f"  STEP 4 — Initialize Wallets")
    print(f"  POST /wallets/init")
    print("=" * 60)

    all_keys = [MAIN_PRIVATE_KEY] + [w["privateKey"] for w in buyers]

    for i in range(0, len(all_keys), API_BATCH_LIMIT):
        batch = all_keys[i:i+API_BATCH_LIMIT]
        data = api("POST", "/wallets/init", {"privateKeys": batch})

        if is_success(data):
            ok = sum(1 for w in data["data"].get("initialized", [])
                     if w["status"] in ("initialized", "already_initialized"))
            print(f"  [OK] {ok}/{len(batch)} initialized")


# ---------------------------------------------------------------------------
# STEP 5 — Upload image to IPFS
# ---------------------------------------------------------------------------

def step_upload_image(state):
    print("=" * 60)
    print(f"  STEP 5 — Upload Image to IPFS")
    print(f"  POST https://pump.fun/api/ipfs")
    print("=" * 60)

    if state.get("imageUrl"):
        print(f"  [LOADED] {state['imageUrl']}")
        return state["imageUrl"]

    if not os.path.exists(TOKEN_IMAGE):
        print(f"  [ERROR] Image file '{TOKEN_IMAGE}' not found!")
        sys.exit(1)

    try:
        with open(TOKEN_IMAGE, "rb") as f:
            r = requests.post(
                "https://pump.fun/api/ipfs",
                files={"file": f},
                timeout=IPFS_UPLOAD_TIMEOUT
            )
        result = r.json()
    except requests.exceptions.Timeout:
        log.error(f"  [ERROR] Upload timed out")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        log.error(f"  [ERROR] Could not connect to pump.fun")
        sys.exit(1)
    except requests.exceptions.JSONDecodeError:
        log.error(f"  [ERROR] Invalid response from IPFS")
        sys.exit(1)

    image_url = result.get("metadata", {}).get("image", "")

    if not image_url:
        print(f"  [ERROR] No image URL returned: {result}")
        sys.exit(1)

    print(f"  [OK] {image_url}")
    state["imageUrl"] = image_url
    save_state(state)
    return image_url


# ---------------------------------------------------------------------------
# STEP 6 — POST /pumpfun/create
# ---------------------------------------------------------------------------

def step_create_token(state, image_url):
    print("=" * 60)
    print(f"  STEP 6 — Create Token on PumpFun")
    print(f"  POST /pumpfun/create")
    print("=" * 60)

    if state.get("tokenAddress"):
        print(f"  [LOADED] {state['tokenAddress']}")
        return state["tokenAddress"]

    print(f"  Request:")
    print(f"     name        : {TOKEN_NAME}")
    print(f"     symbol      : {TOKEN_SYMBOL}")
    print(f"     devBuy      : {DEV_BUY_AMOUNT} SOL")

    data = api("POST", "/pumpfun/create", {
        "devPrivateKey": MAIN_PRIVATE_KEY,
        "name": TOKEN_NAME,
        "symbol": TOKEN_SYMBOL,
        "description": TOKEN_DESCRIPTION,
        "image": image_url,
        "devBuy": DEV_BUY_AMOUNT,
        "priorityFee": {"mode": "FAST"}
    })

    if not is_success(data):
        sys.exit(1)

    token_address = data["data"]["tokenAddress"]
    dev_buy = data["data"].get("devBuy", {})

    print(f"  [OK] Token created!")
    print(f"     tokenAddress   : {token_address}")
    print(f"     confirmLatency : {data['data'].get('confirmLatency', '?')}ms")
    if dev_buy:
        print(f"     devBuy.sol     : {dev_buy.get('amountSol', '?')} SOL")
        print(f"     devBuy.tokens  : {dev_buy.get('tokensReceived', '?')}")
    print(f"  PumpFun : https://pump.fun/coin/{token_address}")
    print(f"  Axiom   : https://axiom.trade/t/{token_address}")

    state["tokenAddress"] = token_address
    save_state(state)
    return token_address


# ---------------------------------------------------------------------------
# STEP 7 — POST /trading/instant/buy
# ---------------------------------------------------------------------------

def step_buy(buyers, token_address):
    print("=" * 60)
    print(f"  STEP 7 — Instant Buy ({len(buyers)} wallets)")
    print(f"  POST /trading/instant/buy")
    print("=" * 60)

    private_keys = [w["privateKey"] for w in buyers]

    start = time.time()
    data = api("POST", "/trading/instant/buy", {
        "tokenAddress": token_address,
        "privateKeys": private_keys,
        "amount": {"mode": "FIXED", "value": BUY_AMOUNT},
        "priorityFee": {"mode": "FAST"}
    })
    elapsed = time.time() - start

    if is_success(data):
        transactions = data["data"].get("transactions", [])
        confirmed = sum(1 for tx in transactions if tx.get("status") == "confirmed")

        for tx in transactions:
            status = "[OK]" if tx.get("status") == "confirmed" else "[FAIL]"
            tokens = tx.get('tokensReceived', tx.get('error', '?'))
            print(f"     {status} {tx['wallet'][:20]}... → {tokens}")

        summary = data["data"].get("summary", {})
        print(f"\n  {confirmed}/{len(transactions)} confirmed in {elapsed:.2f}s")
        print(f"  Total SOL spent: {summary.get('totalSolSpent', '?')}")
    return data


# ---------------------------------------------------------------------------
# STEP 8 — POST /wallets/balance
# ---------------------------------------------------------------------------

def step_check(buyers, token_address):
    print("=" * 60)
    print(f"  STEP 8 — Check Balances")
    print(f"  POST /wallets/balance")
    print("=" * 60)

    main_pub = derive_public_key(MAIN_PRIVATE_KEY)
    all_pubs = [main_pub] + [w["publicKey"] for w in buyers]

    data = api("POST", "/wallets/balance", {
        "publicKeys": all_pubs,
        "tokenAddress": token_address
    })

    if is_success(data):
        holders = sum(1 for b in data["data"]["balances"] if b.get("token", 0) > 0)
        print(f"  holders    : {holders}")
        print(f"  totalToken : {data['data'].get('totalToken', '?')}")
        print(f"  totalSol   : {data['data'].get('totalSol', '?')}")


# ---------------------------------------------------------------------------
# STEP 9 — POST /trading/instant/sell
# ---------------------------------------------------------------------------

def step_sell(buyers, token_address):
    print("=" * 60)
    print(f"  STEP 9 — Instant Sell (100%)")
    print(f"  POST /trading/instant/sell")
    print("=" * 60)

    print(f"  -> Waiting {SELL_DELAY}s...")
    time.sleep(SELL_DELAY)

    all_keys = [MAIN_PRIVATE_KEY] + [w["privateKey"] for w in buyers]

    for attempt in range(SELL_RETRIES):
        data = api("POST", "/trading/instant/sell", {
            "tokenAddress": token_address,
            "privateKeys": all_keys,
            "amount": {"type": "PERCENT", "mode": "FIXED", "value": 100},
            "priorityFee": {"mode": "FAST"}
        })

        if is_success(data):
            transactions = data["data"].get("transactions", [])
            if not transactions:
                log.warning(f"  [WARN] No transactions returned")
                if attempt < SELL_RETRIES - 1:
                    time.sleep(SELL_DELAY)
                continue

            confirmed = sum(1 for tx in transactions if tx.get("status") == "confirmed")
            all_confirmed = confirmed > 0 and confirmed == len(transactions)
            summary = data["data"].get("summary", {})

            print(f"  [OK] {confirmed}/{len(transactions)} sold")
            print(f"     SOL recovered: {summary.get('totalSolReceived', '?')}")

            if all_confirmed:
                return data

        if attempt < SELL_RETRIES - 1:
            time.sleep(SELL_DELAY)

    return data


# ---------------------------------------------------------------------------
# STEP 10 — Close Accounts + Withdraw
# ---------------------------------------------------------------------------

def step_cleanup(buyers, main_public_key):
    print("=" * 60)
    print(f"  STEP 10 — Close Accounts + Withdraw")
    print(f"  POST /utilities/close-accounts")
    print(f"  POST /funding/withdraw")
    print("=" * 60)

    all_keys = [MAIN_PRIVATE_KEY] + [w["privateKey"] for w in buyers]

    data = api("POST", "/utilities/close-accounts", {
        "privateKeys": all_keys,
        "simulate": False
    })
    if is_success(data):
        summary = data["data"].get("summary", {})
        print(f"  Closed: {summary.get('totalAccountsClosed', 0)} accounts")
        print(f"  Rent recovered: {summary.get('totalRentRecovered', '?')} SOL")

    buyer_keys = [w["privateKey"] for w in buyers]
    data = api("POST", "/funding/withdraw", {
        "sourcePrivateKeys": buyer_keys,
        "destinationPublicKey": main_public_key,
        "amount": {"mode": "ALL"},
        "method": "DIRECT"
    })

    if is_success(data):
        summary = data["data"].get("summary", {})
        print(f"  [OK] Withdrawn: {summary.get('totalSolReceived', '?')} SOL")

    bal = api("POST", "/wallets/balance", {"publicKeys": [main_public_key]})
    if is_success(bal):
        sol = bal["data"]["balances"][0].get("sol", 0)
        print(f"\n  Main wallet: {sol} SOL")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    validate_config()
    main_public_key = derive_public_key(MAIN_PRIVATE_KEY)

    print()
    print("=" * 60)
    print("  PUMP FUN API — Complete Developer Guide")
    print("  Powered by Launchpad.Trade")
    print("=" * 60)
    print()
    print(f"  Base URL     : {BASE_URL}")
    print(f"  Main wallet  : {main_public_key}")
    print(f"  Token        : {TOKEN_NAME} ({TOKEN_SYMBOL})")
    print()
    print("  Endpoints covered:")
    print("    1. GET  /health")
    print("    2. POST /wallets/create")
    print("    3. POST /funding/distribute")
    print("    4. POST /wallets/init")
    print("    5. POST /pumpfun/create")
    print("    6. POST /trading/instant/buy")
    print("    7. POST /wallets/balance")
    print("    8. POST /trading/instant/sell")
    print("    9. POST /utilities/close-accounts")
    print("   10. POST /funding/withdraw")
    print()

    state = load_state()

    step_health()
    buyers = step_create_wallets(main_public_key)
    step_fund(buyers)
    step_init(buyers)
    image_url = step_upload_image(state)
    token_address = step_create_token(state, image_url)
    step_buy(buyers, token_address)
    step_check(buyers, token_address)
    step_sell(buyers, token_address)
    step_cleanup(buyers, main_public_key)

    print()
    print("=" * 60)
    print("  DEMO COMPLETE!")
    print("=" * 60)
    print(f"  Token   : {TOKEN_NAME} ({TOKEN_SYMBOL})")
    print(f"  Address : {token_address}")
    print(f"  PumpFun : https://pump.fun/coin/{token_address}")
    print()
    print("  10 endpoints. One API. No PumpFun SDK needed.")
    print("  Docs: https://docs.launchpad.trade")
    print()


if __name__ == "__main__":
    main()
