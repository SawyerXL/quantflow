#!/usr/bin/env python3
"""
QuantFlow Automated Test Suite v2
Runs against live Render backend via multipart/form-data for backtest.
"""

import json
import time
import urllib.request
import urllib.error
from urllib.parse import urlencode

BASE = "https://quantflow-v3q5.onrender.com/api/v1"
PASS = "✅"
FAIL = "❌"
SKIP = "⏭️"

results = []

def test(name, module, actual, expected, notes=""):
    if callable(expected):
        ok = expected(actual)
    else:
        ok = actual == expected
    status = PASS if ok else FAIL
    results.append({"module": module, "name": name, "status": status, "notes": notes})
    print(f"  {status} {name}: {str(actual)[:100]}")
    return ok

def api_post(path, data=None, token=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(f"{BASE}{path}", data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if token: req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())
    except Exception as e:
        return 0, {"error": str(e)}

def api_get(path, token=None):
    req = urllib.request.Request(f"{BASE}{path}")
    if token: req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())
    except Exception as e:
        return 0, {"error": str(e)}

def backtest_post(fields, token):
    """Send multipart/form-data backtest request."""
    boundary = "----QuantFlowTestBoundary"
    body = b""
    for key, val in fields.items():
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode()
        body += f"{val}\r\n".encode()
    body += f"--{boundary}--\r\n".encode()

    req = urllib.request.Request(f"{BASE}/backtest/run-sync", data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    if token: req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())
    except Exception as e:
        return 0, {"error": str(e)}

# =============================================
# Setup: Create test user
# =============================================
print("SETUP: Creating test user...")
ts = int(time.time())
email = f"qa_{ts}@quantflow.io"
status, data = api_post("/auth/register", {"email": email, "password": "qaTest123", "full_name": "QA Bot"})
token = ""
if data.get("success"):
    token = data["data"]["access_token"]
    print(f"  ✅ Registered: {email}")
else:
    # Already exists, login
    status, data = api_post("/auth/login", {"email": email, "password": "qaTest123"})
    if data.get("success"):
        token = data["data"]["access_token"]
        print(f"  ✅ Logged in: {email}")
    else:
        print(f"  ❌ Could not authenticate: {data}")
        exit(1)

# =============================================
# MODULE 1: Auth (7 tests)
# =============================================
print("\n" + "=" * 60)
print("MODULE 1: Authentication")
print("=" * 60)

status, data = api_post("/auth/register", {"email": f"qareg_{ts}@quantflow.io", "password": "testpass123"})
test("1.1 Valid registration → 201", "Auth", status, 201)

status, data = api_post("/auth/register", {"email": "weak@qa.com", "password": "ab1"})
test("1.2 Weak password rejected (422)", "Auth", status, 422)

status, data = api_post("/auth/register", {"email": email, "password": "testpass123"})
test("1.3 Duplicate email rejected", "Auth", status == 409 or (data.get("error", {}).get("code") == "resource.conflict"), True)

status, data = api_post("/auth/login", {"email": email, "password": "qaTest123"})
test("1.4 Valid login → tokens", "Auth", data.get("success"), True)

status, data = api_post("/auth/login", {"email": email, "password": "WRONG"})
test("1.5 Wrong password → 401", "Auth", status, 401)

status, data = api_get("/auth/me", token)
test("1.6 Profile returns user info", "Auth", data.get("success"), True,
     f"Plan: {data.get('data', {}).get('plan')}")

status, data = api_get("/auth/me")
test("1.7 No token → 401", "Auth", status, 401)

# =============================================
# MODULE 3: Data (3 tests)
# =============================================
print("\n" + "=" * 60)
print("MODULE 3: Ticker & Data")
print("=" * 60)

status, data = api_get("/data/search?q=AAPL", token)
test("3.1 Symbol search works", "Data", data.get("success"), True)

status, data = api_get("/data/search?q=AAPL")
test("3.2 Data requires auth", "Data", status, 401)

status, data = api_get("/data/validate-ticker?ticker=AAPL", token)
test("3.3 Ticker validation", "Data", data.get("success"), True,
     f"Result: {str(data.get('data', {}))[:60]}")

# =============================================
# MODULE 5: Backtest Execution (6 tests)
# =============================================
print("\n" + "=" * 60)
print("MODULE 5: Backtest Execution")
print("=" * 60)

t0 = time.time()
status, data = backtest_post({
    "ticker": "AAPL",
    "strategy_type": "ma_cross",
    "strategy_params": '{"fast_period":10,"slow_period":30}',
    "initial_capital": "10000",
    "start_date": "2023-01-01",
    "end_date": "2024-12-31",
    "name": "QA Test MA Cross"
}, token)
t1 = time.time() - t0
ok = data.get("success")
if ok:
    d = data["data"]
    test("5.1 MA Cross (AAPL) runs", "Backtest", d["status"], "completed",
         f"Sharpe={d.get('sharpe_ratio')}, Return={d.get('total_return')}, Time={t1:.1f}s")
    test("5.1a Equity curve present", "Backtest", len(d.get("result_data", {}).get("equity_curve", [])) > 0, True)
    test("5.1b Trades recorded", "Backtest", d.get("total_trades", 0) > 0, True,
         f"Count: {d.get('total_trades')}")
else:
    err = data.get("error", data.get("detail", {}))
    test("5.1 MA Cross (AAPL)", "Backtest", False, True, f"Error: {err}")

# RSI
t0 = time.time()
status, data = backtest_post({
    "ticker": "SPY",
    "strategy_type": "rsi",
    "strategy_params": '{"rsi_period":14,"oversold":30,"overbought":70}',
    "initial_capital": "25000",
    "name": "QA Test RSI"
}, token)
t1 = time.time() - t0
ok = data.get("success")
if ok:
    test("5.2 RSI (SPY) runs", "Backtest", data["data"]["status"], "completed",
         f"Time={t1:.1f}s, Trades={data['data'].get('total_trades')}")
else:
    test("5.2 RSI (SPY)", "Backtest", False, True, f"Error: {data.get('error',{})}")

# Bollinger
t0 = time.time()
status, data = backtest_post({
    "ticker": "QQQ",
    "strategy_type": "bollinger",
    "strategy_params": '{"bb_period":20,"bb_std":2.0}',
    "initial_capital": "15000",
    "name": "QA Test Bollinger"
}, token)
t1 = time.time() - t0
ok = data.get("success")
if ok:
    test("5.3 Bollinger (QQQ) runs", "Backtest", data["data"]["status"], "completed",
         f"Time={t1:.1f}s, WinRate={data['data'].get('win_rate')}")
else:
    test("5.3 Bollinger (QQQ)", "Backtest", False, True, f"Error: {data.get('error',{})}")

# Invalid strategy
status, data = backtest_post({
    "ticker": "AAPL",
    "strategy_type": "momentum",
    "strategy_params": "{}",
    "initial_capital": "10000",
    "name": "Invalid Strategy Test"
}, token)
is_rejected = data.get("success") == False or "error" in data or "detail" in data
test("5.4 Invalid strategy rejected", "Backtest", is_rejected, True,
     f"Code: {str(data.get('error', data.get('detail', {})))[:60]}")

# Auth required
status, _ = backtest_post({"ticker": "AAPL", "strategy_type": "ma_cross", "strategy_params": "{}"}, None)
test("5.5 Backtest requires auth", "Backtest", status, 401)

# =============================================
# MODULE 6: Result Validation (4 tests)
# =============================================
print("\n" + "=" * 60)
print("MODULE 6: Result Consistency")
print("=" * 60)

status, data = backtest_post({
    "ticker": "AAPL",
    "strategy_type": "ma_cross",
    "strategy_params": '{"fast_period":10,"slow_period":30}',
    "initial_capital": "10000",
    "name": "QA Validation"
}, token)
if data.get("success"):
    d = data["data"]
    required = ["total_return", "sharpe_ratio", "max_drawdown", "win_rate", "annual_return", "profit_factor"]
    all_there = all(k in d and d[k] is not None for k in required)
    test("6.1 All 7 metrics present", "Results", all_there, True)

    all_num = all(isinstance(d[k], (int, float)) for k in required if d[k] is not None)
    test("6.2 All metrics are numeric", "Results", all_num, True)

    test("6.3 Max drawdown ≤ 0", "Results", d.get("max_drawdown", 1) <= 0, True,
         f"Value: {d.get('max_drawdown')}")

    trades = d.get("result_data", {}).get("trades", [])
    test("6.4 Trade count ≡ recorded", "Results", len(trades) == d.get("total_trades", -1), True,
         f"Recorded: {d.get('total_trades')}, List: {len(trades)}")
else:
    for t in ["6.1","6.2","6.3","6.4"]:
        test(f"{t} (backtest failed)", "Results", False, True)

# =============================================
# MODULE 7: Limits (2 tests)
# =============================================
print("\n" + "=" * 60)
print("MODULE 7: Plan Limits")
print("=" * 60)

status, data = api_get("/auth/me", token)
plan = data.get("data", {}).get("plan", "free")
count = data.get("data", {}).get("backtest_count_today", 0)
test("7.1 Plan is 'free'", "Limits", plan, "free")
test("7.2 Backtest counter increments", "Limits", count > 0, True,
     f"Count today: {count}")

# =============================================
# MODULE 10: Performance (3 tests)
# =============================================
print("\n" + "=" * 60)
print("MODULE 10: Performance")
print("=" * 60)

t0 = time.time()
try:
    with urllib.request.urlopen("https://quantflow-v3q5.onrender.com/health", timeout=30) as r:
        h = json.loads(r.read())
    ht = time.time() - t0
    test("10.1 Health < 2s", "Performance", ht < 2.0, True,
         f"Time: {ht:.1f}s, DB: {h.get('database')}")
except Exception as e:
    test("10.1 Health check", "Performance", False, True, str(e))

test("10.2 Backtest < 15s", "Performance", t1 < 15, True, f"Last: {t1:.1f}s")

# Backtest auth guard (no token → 401)
st, _ = backtest_post({"ticker": "AAPL", "strategy_type": "ma_cross", "strategy_params": "{}"}, None)
test("10.3 Backtest auth guard → 401", "Performance", st, 401)

# =============================================
# REPORT
# =============================================
print("\n" + "=" * 60)
print("QUANTFLOW AUTOMATED TEST REPORT")
print("=" * 60)

passed = sum(1 for r in results if r["status"] == PASS)
failed = sum(1 for r in results if r["status"] == FAIL)
total = len(results)
rate = passed / total * 100

print(f"\n  Total: {total}  |  {PASS} Passed: {passed}  |  {FAIL} Failed: {failed}")
print(f"  Pass Rate: {rate:.0f}%\n")

modules = {}
for r in results:
    m = r["module"]
    if m not in modules:
        modules[m] = [0, 0]
    if r["status"] == PASS:
        modules[m][0] += 1
    else:
        modules[m][1] += 1

print("  Module          Pass/Total  Bar")
print("  ───────         ──────────  ───")
for mod, (p, f) in modules.items():
    bar = "█" * p + ("░" * f if f else "")
    print(f"  {mod:15s}  {p}/{p+f}       {bar}")

# Failed items
failed_items = [r for r in results if r["status"] == FAIL]
if failed_items:
    print(f"\n  ❌ FAILURES ({len(failed_items)}):")
    for r in failed_items:
        print(f"     {r['name']}: {r['notes']}")
else:
    print(f"\n  ✅ ALL {total} TESTS PASSED")

if rate == 100:
    print(f"\n  🚦 GREEN — Ready for users")
elif rate >= 90:
    print(f"\n  🚦 YELLOW — {failed} minor issue(s)")
else:
    print(f"\n  🚦 RED — {failed} failures need fixing")

# CSV test table
print("\n" + "=" * 60)
print("CSV-READY TEST TABLE")
print("=" * 60)
print("Module,Test,Status,Notes")
for r in results:
    print(f"{r['module']},{r['name']},{r['status']},{r['notes']}")