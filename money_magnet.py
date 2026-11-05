"""money_magnet — finance tracker + money magnet library."""

from __future__ import annotations

import json
import logging
import urllib.request
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home

logger = logging.getLogger(__name__)

STATE_DIR = get_hermes_home() / "money-magnet"


def _state_file(name: str) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / name


def _load_json(name: str, default: Any) -> Any:
    p = _state_file(name)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return default


def _save_json(name: str, data: Any) -> None:
    _state_file(name).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def finance_add(tx_type: str, amount: float, category: str, note: str = "") -> dict:
    txs = _load_json("transactions.json", [])
    entry = {
        "id": len(txs) + 1,
        "ts": datetime.now(UTC).isoformat(),
        "type": tx_type,
        "amount": amount,
        "category": category,
        "note": note,
    }
    txs.append(entry)
    _save_json("transactions.json", txs)
    return {"success": True, "entry": entry, "total_tx": len(txs)}


def finance_list(limit: int = 20, tx_type: str = "all", category: str = "") -> dict:
    txs = _load_json("transactions.json", [])
    if tx_type and tx_type != "all":
        txs = [t for t in txs if t["type"] == tx_type]
    if category:
        txs = [t for t in txs if t["category"].lower() == category.lower()]
    txs = txs[-limit:]
    income = sum(t["amount"] for t in txs if t["type"] == "income")
    expense = sum(t["amount"] for t in txs if t["type"] == "expense")
    return {"count": len(txs), "income": income, "expense": expense, "net": income - expense, "transactions": txs}


def finance_budget(monthly_limit: float = 0) -> dict:
    budgets = _load_json("budget.json", {"monthly_limit": 0})
    if monthly_limit and monthly_limit > 0:
        budgets["monthly_limit"] = monthly_limit
        _save_json("budget.json", budgets)
    limit = budgets.get("monthly_limit", 0)
    txs = _load_json("transactions.json", [])
    now = datetime.now(UTC)
    month_txs = [t for t in txs if t["type"] == "expense" and t["ts"].startswith(now.strftime("%Y-%m"))]
    spent = sum(t["amount"] for t in month_txs)
    remaining = limit - spent if limit else 0
    pct = (spent / limit * 100) if limit else 0
    return {"monthly_limit": limit, "spent": spent, "remaining": remaining, "percent_used": round(pct, 1), "transactions_this_month": len(month_txs)}


def finance_portfolio(holdings: list) -> dict:
    symbols = ",".join(h["symbol"].upper() for h in holdings)
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={_map_symbols(symbols)}&vs_currencies=usd"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            prices = json.loads(r.read())
    except Exception as e:
        return {"error": f"price fetch failed: {e}"}
    results = []
    total_value = 0.0
    total_cost = 0.0
    for h in holdings:
        sym = h["symbol"].upper()
        cg_id = _symbol_to_coingecko(sym)
        price = prices.get(cg_id, {}).get("usd", 0)
        value = price * h["amount"]
        cost = h["buy_price"] * h["amount"]
        pnl = value - cost
        pnl_pct = (pnl / cost * 100) if cost else 0
        results.append({"symbol": sym, "amount": h["amount"], "buy_price": h["buy_price"], "current_price": price, "value": round(value, 2), "cost": round(cost, 2), "pnl": round(pnl, 2), "pnl_pct": round(pnl_pct, 2)})
        total_value += value
        total_cost += cost
    return {"holdings": results, "total_value": round(total_value, 2), "total_cost": round(total_cost, 2), "total_pnl": round(total_value - total_cost, 2), "total_pnl_pct": round((total_value - total_cost) / total_cost * 100, 2) if total_cost else 0}


_SYMBOL_MAP = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "BNB": "binancecoin",
    "XRP": "ripple", "ADA": "cardano", "DOGE": "dogecoin", "AVAX": "avalanche-2",
    "DOT": "polkadot", "MATIC": "matic-network", "LINK": "chainlink", "UNI": "uniswap",
    "LTC": "litecoin", "ATOM": "cosmos", "NEAR": "near", "APT": "aptos",
}


def _symbol_to_coingecko(sym: str) -> str:
    return _SYMBOL_MAP.get(sym.upper(), sym.lower())


def _map_symbols(symbols: str) -> str:
    ids = []
    for s in symbols.split(","):
        ids.append(_symbol_to_coingecko(s.strip()))
    return ",".join(ids)


def finance_arbitrage() -> dict:
    # Compare prices across exchanges via CoinGecko (single source) + Binance ticker
    try:
        with urllib.request.urlopen("https://api.binance.com/api/v3/ticker/price", timeout=10) as r:
            binance = {t["symbol"]: float(t["price"]) for t in json.loads(r.read())}
    except Exception as e:
        return {"error": f"binance fetch failed: {e}"}
    # CoinGecko top coins
    try:
        with urllib.request.urlopen("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=20&page=1", timeout=10) as r:
            cg = json.loads(r.read())
    except Exception as e:
        return {"error": f"coingecko fetch failed: {e}"}
    opps = []
    for c in cg:
        sym = c["symbol"].upper() + "USDT"
        cg_price = c["current_price"]
        bn_price = binance.get(sym)
        if bn_price and cg_price:
            diff_pct = (bn_price - cg_price) / cg_price * 100
            if abs(diff_pct) > 0.5:
                opps.append({"symbol": c["symbol"].upper(), "coingecko": cg_price, "binance": bn_price, "diff_pct": round(diff_pct, 2)})
    opps.sort(key=lambda x: abs(x["diff_pct"]), reverse=True)
    return {"opportunities": opps[:10], "note": "diff > 0.5% flagged; account for fees before trading"}


def handle_money_command(raw_args: str) -> str:
    argv = raw_args.strip().split()
    if not argv or argv[0] in {"help", "-h", "--help"}:
        return ("Money Magnet commands:\n"
                "  /money status          - income/expense summary\n"
                "  /money add <type> <amount> <category> [note]\n"
                "  /money budget [limit]  - set/check monthly budget\n"
                "  /money portfolio       - (use finance_portfolio tool)\n"
                "  /money arbitrage       - (use finance_arbitrage tool)")
    cmd = argv[0]
    if cmd == "status":
        r = finance_list(limit=100)
        return f"Income: {r['income']}\nExpense: {r['expense']}\nNet: {r['net']}\nTx count: {r['count']}"
    if cmd == "add" and len(argv) >= 4:
        tx_type, amount, category = argv[1], float(argv[2]), argv[3]
        note = " ".join(argv[4:])
        r = finance_add(tx_type, amount, category, note)
        return f"Added #{r['entry']['id']}: {tx_type} {amount} {category}"
    if cmd == "budget":
        limit = float(argv[1]) if len(argv) > 1 else 0
        r = finance_budget(limit)
        return f"Limit: {r['monthly_limit']}\nSpent: {r['spent']}\nRemaining: {r['remaining']}\nUsed: {r['percent_used']}%"
    return f"Unknown command: {cmd}. Try /money help."
