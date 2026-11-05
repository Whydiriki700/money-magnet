"""money-magnet plugin — finance tracker + money magnet for Hermes Agent."""

from __future__ import annotations

import json
import logging
from typing import Any

from . import money_magnet as mm

logger = logging.getLogger(__name__)

TOOLSET = "money_magnet"


def _wrap(fn, allowed):
    """Adapt a kwargs-style library function to the Hermes handler contract.

    Hermes dispatches plugin tool handlers as handler(args_dict, **kwargs)
    (tools/registry.py dispatch), while the money_magnet library functions
    take named parameters. The wrapper unpacks only the parameters the
    library function actually declares, so stray keys can never break a call.
    """

    def handler(args: dict | None = None, **_kw: Any):
        data = args or {}
        result = fn(**{k: v for k, v in data.items() if k in allowed})
        # Hermes tool results must be strings (tools/registry.py
        # _normalize_handler_result rejects anything else with
        # "unsupported result type"); the library returns dicts, and the
        # call itself has already executed by the time that error would
        # surface, so serialize here instead of failing after the fact.
        return result if isinstance(result, str) else json.dumps(result)

    return handler


def register(ctx) -> None:
    ctx.register_tool(
        name="finance_add",
        toolset=TOOLSET,
        schema={
            "name": "finance_add",
            "description": "Add a transaction (income or expense).",
            "parameters": {
                "type": "object",
                "properties": {
                    "tx_type": {"type": "string", "enum": ["income", "expense"], "description": "Transaction type."},
                    "amount": {"type": "number", "description": "Amount in base currency."},
                    "category": {"type": "string", "description": "Category (food, transport, salary, etc)."},
                    "note": {"type": "string", "description": "Optional note."},
                },
                "required": ["tx_type", "amount", "category"],
            },
        },
        handler=_wrap(mm.finance_add, {"tx_type", "amount", "category", "note"}),
    )
    ctx.register_tool(
        name="finance_list",
        toolset=TOOLSET,
        schema={
            "name": "finance_list",
            "description": "List recent transactions with optional filters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max rows (default 20)."},
                    "tx_type": {"type": "string", "enum": ["income", "expense", "all"], "description": "Filter by type."},
                    "category": {"type": "string", "description": "Filter by category."},
                },
            },
        },
        handler=_wrap(mm.finance_list, {"limit", "tx_type", "category"}),
    )
    ctx.register_tool(
        name="finance_budget",
        toolset=TOOLSET,
        schema={
            "name": "finance_budget",
            "description": "Set or check monthly budget status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "monthly_limit": {"type": "number", "description": "Set monthly expense limit (optional)."},
                },
            },
        },
        handler=_wrap(mm.finance_budget, {"monthly_limit"}),
    )
    ctx.register_tool(
        name="finance_portfolio",
        toolset=TOOLSET,
        schema={
            "name": "finance_portfolio",
            "description": "Track crypto portfolio PnL. Pass holdings as list of {symbol, amount, buy_price}.",
            "parameters": {
                "type": "object",
                "properties": {
                    "holdings": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "symbol": {"type": "string"},
                                "amount": {"type": "number"},
                                "buy_price": {"type": "number"},
                            },
                            "required": ["symbol", "amount", "buy_price"],
                        },
                        "description": "List of holdings.",
                    },
                },
                "required": ["holdings"],
            },
        },
        handler=_wrap(mm.finance_portfolio, {"holdings"}),
    )
    ctx.register_tool(
        name="finance_arbitrage",
        toolset=TOOLSET,
        schema={
            "name": "finance_arbitrage",
            "description": "Scan crypto arbitrage opportunities across exchanges (price differences).",
            "parameters": {"type": "object", "properties": {}},
        },
        handler=_wrap(mm.finance_arbitrage, set()),
    )
    ctx.register_command(
        "money",
        handler=mm.handle_money_command,
        description="Money magnet commands: /money status|add|budget|portfolio",
    )
