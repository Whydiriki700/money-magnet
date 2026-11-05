# money-magnet

Finance tracker + money magnet for Hermes Agent.

## Tools

- `finance_add` - add income/expense transaction
- `finance_list` - list transactions with filters
- `finance_budget` - set/check monthly budget
- `finance_portfolio` - crypto portfolio PnL (CoinGecko prices)
- `finance_arbitrage` - scan crypto arbitrage opportunities (CoinGecko vs Binance)

## Command

`/money status|add|budget`

## Install

```
hermes plugins install money-magnet --enable
```

## Data and disclosure

Transactions and budget are stored in `$HERMES_HOME/money-magnet/` (transactions.json, budget.json), on your own machine only.

Network calls happen only when you use the market tools: `finance_portfolio` and `finance_arbitrage` query the public CoinGecko and Binance price APIs (no account, no API key, no transaction data is sent, only coin symbols). The tracker tools (`finance_add`, `finance_list`, `finance_budget`) work fully offline.
