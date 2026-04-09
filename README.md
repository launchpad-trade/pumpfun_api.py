# Pump Fun API — Create & Trade Tokens on PumpFun

Create tokens on PumpFun and trade them with multiple wallets using one API. 10 endpoints covered in one script.

Built with [Launchpad.Trade](https://launchpad.trade) API.

## What it does

1. **Health check** — `GET /health`
2. **Create wallets** — `POST /wallets/create`
3. **Fund wallets** — `POST /funding/distribute`
4. **Initialize wallets** — `POST /wallets/init`
5. **Upload image to IPFS** — `POST pump.fun/api/ipfs`
6. **Create token on PumpFun** — `POST /pumpfun/create` (with dev buy)
7. **Buy with multiple wallets** — `POST /trading/instant/buy`
8. **Check balances** — `POST /wallets/balance`
9. **Sell 100%** — `POST /trading/instant/sell`
10. **Close accounts + withdraw** — `POST /utilities/close-accounts` + `POST /funding/withdraw`

## Requirements

- Python 3.8+
- A [Launchpad.Trade](https://launchpad.trade) API key (free)
- ~0.15 SOL in your main wallet
- A token image (PNG, JPG, GIF or WebP)

## Installation

```bash
pip install requests base58 python-dotenv
```

## Setup

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Fill in your keys in `.env`:
```env
LAUNCHPAD_API_KEY=your_api_key_here
MAIN_PRIVATE_KEY=your_private_key_here
```

3. Put your token image as `image.png` in this folder.

> **Important:** Never commit your `.env` file.

## Run

```bash
python pumpfun_api.py
```

Press Enter at each step. The script creates a token on PumpFun, buys with multiple wallets, sells, and withdraws.

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `TOKEN_NAME` | PumpFunAPI | Token name (max 32 chars) |
| `TOKEN_SYMBOL` | PFAPI | Token symbol (max 10 chars) |
| `NUM_WALLETS` | 3 | Number of buyer wallets (max 50) |
| `FUND_AMOUNT` | 0.02 | SOL per wallet |
| `BUY_AMOUNT` | 0.005 | SOL each wallet spends |
| `DEV_BUY_AMOUNT` | 0.01 | SOL for dev's initial buy |

## Links

- [Launchpad.Trade](https://launchpad.trade) — Solana Trading API
- [Documentation](https://docs.launchpad.trade)
- [Blog Post: Pump Fun API Guide](https://www.launchpad.trade/post/pump-fun-api-documentation-a-developer-guide-2)
- [Discord](https://discord.com/invite/launchpad-trade)
- [YouTube Tutorial](https://youtube.com)

## Disclaimer

This project is for educational purposes only. Trading cryptocurrency involves risk. Always do your own research. This is not financial advice.
