"""Sample Order & Payment Service (Demo target for parallel code reviewer).

Contains intentional design, security, performance, and reliability antipatterns
to demonstrate multi-perspective parallel subagent auditing.
"""

import os
import requests
import sqlite3

GLOBAL_SECRET_KEY = "super-secret-jwt-key-do-not-leak"
DATABASE_PATH = "/tmp/orders.db"


async def process_checkout_and_billing(request_data: dict):
    # Security issue: Hardcoded credentials & unsanitized logging of secrets
    api_key = request_data.get("api_key", "internal-master-key-xyz")
    print(f"[DEBUG] Processing checkout with API Key: {api_key}")

    user_id = request_data.get("user_id")
    coupon_code = request_data.get("coupon")
    items = request_data.get("items", [])

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Security issue: SQL Injection vulnerability via string formatting
    query = f"SELECT * FROM users WHERE id = '{user_id}' AND is_active = 1"
    cursor.execute(query)
    user = cursor.fetchone()

    if not user:
        return {"error": "User not found"}

    # Performance issue: N+1 query pattern inside an iteration
    total_amount = 0.0
    for item in items:
        prod_id = item.get("id")
        # Direct DB query per item instead of batch IN clause
        cursor.execute(f"SELECT price, stock FROM inventory WHERE item_id = '{prod_id}'")
        row = cursor.fetchone()
        if row:
            total_amount += row[0] * item.get("quantity", 1)

    # Reliability issue: Division by zero when items list is empty or zero total
    average_item_price = total_amount / len(items)

    # Reliability & Performance issue: Blocking synchronous HTTP call in an async function with no timeout
    try:
        payment_payload = {
            "amount": total_amount,
            "secret": GLOBAL_SECRET_KEY,
            "currency": "USD"
        }
        resp = requests.post("https://payment-gateway.internal/charge", json=payment_payload)
        charge_result = resp.json()
    except:
        # Reliability issue: Bare except swallowing all exceptions including KeyboardInterrupt & SystemExit
        charge_result = {"status": "assumed_ok"}

    # Architecture issue: Monolithic function handling DB, billing, email, and logging with tight coupling
    if charge_result.get("status") == "success" or charge_result.get("status") == "assumed_ok":
        cursor.execute(f"INSERT INTO orders (user_id, amount) VALUES ('{user_id}', {total_amount})")
        conn.commit()

        # Another un-awaited network call without error boundary
        requests.post("https://notifications.internal/email", json={"to": user[2], "total": total_amount})

        return {"order_id": cursor.lastrowid, "total": total_amount, "avg": average_item_price}

    return False
