# RazorFlow AI

### Safe Agentic Commerce — AI recommends. Humans approve. Code enforces.

RazorFlow AI is a policy-gated AI shopping assistant that lets an AI
discover products and build carts, while preventing the AI from
directly authorizing payments.

Every purchase passes through:

**AI → Cart → Policy Engine → Human Approval → Razorpay → Verification → Audit**

[![Demo Video](https://img.shields.io/badge/Demo-Video-red)](https://youtu.be/wim7gSKLrIA)
[![Tests: 181 passing](https://img.shields.io/badge/tests-181%20passing-brightgreen)](backend/tests)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🎥 Demo

<!-- DEMO VIDEO SPACE: to embed a local recording instead of (or next to)
     the YouTube link above, drop the file at docs/demo.gif (or docs/demo.mp4)
     and replace this comment with: ![RazorFlow AI demo](docs/demo.gif) -->

🎬 **Watch:** https://youtu.be/wim7gSKLrIA

### What you're seeing

1. AI recommends products with per-card reasoning
2. Cart is evaluated against deterministic policies on every change
3. AI cannot approve the purchase — it can only request an approval
4. Human explicitly approves (single-use token, itemized summary)
5. Razorpay processes the payment in test mode
6. Payment is independently verified (signature + webhook + status poll)
7. The transaction appears in the hash-chained audit trail and merchant dashboard

## What is RazorFlow AI?

An AI buyer ("SprintGear AI") for running gear, built on a simple boundary:
**the LLM is a recommender and explainer — money moves only through
deterministic code.** A policy engine bounds every cart, a human gate
stands between AI intent and payment, and every step is written to a
tamper-evident audit trail. A merchant console then proves what the AI
earned: revenue, upsell lift, funnel, and orders.

## Why Agentic Commerce Needs Guardrails

General-purpose AI agents are persuasive but untrustworthy with money:
they hallucinate prices, invent availability, and nothing constrains what
an agent may spend or proves what it did. For agentic commerce to be
shippable, three questions need mechanical answers, not promises —
*what stops the AI from spending more? how do failures recover? how is
every number proven?* RazorFlow AI is that proof.

| Traditional AI Shopping Agent | RazorFlow AI            |
| ----------------------------- | ----------------------- |
| AI decides what to buy        | AI recommends           |
| AI-driven purchase flow       | Deterministic checkout  |
| Trust the model               | Enforce policies        |
| Approval can be ambiguous     | Explicit human approval |
| Logs can be altered           | Hash-chained audit      |
| Payment state can be inferred | Gateway verification    |

> **The AI doesn't need to be trusted, because the architecture doesn't give it the authority to spend.**

## How It Works

```text
                    MERCHANT
                       │
                       ▼
                Product Catalog
                       │
                       ▼
             AI-Readable Catalog
                       │
                       ▼
CUSTOMER ───────►  AI BUYER
                       │
                       ▼
                Understand Intent
                       │
                       ▼
                Search Catalog
                       │
                       ▼
                Compare Products
                       │
                       ▼
              Recommend Product
                       │
                       ▼
                Add to Cart
                       │
                       ▼
              Upsell / Cross-sell
                       │
                       ▼
                 Final Cart
                       │
                       ▼
                Calculate Total
                       │
                       ▼
                POLICY ENGINE
                 /          \
               PASS          FAIL
                │              │
                ▼              ▼
          Approval Gate      BLOCK
                │
                ▼
        User Explicitly Approves
                │
                ▼
          Razorpay Test Mode
                │
          ┌─────┴─────┐
          │           │
       SUCCESS      FAILURE
          │           │
          ▼           ▼
   Verify Payment   Explain Failure
          │           │
          ▼           ▼
     Order Confirm  Retry/Return
          │
          └─────┬─────┘
                ▼
           AUDIT TRAIL
                │
                ▼
        MERCHANT DASHBOARD
                │
                ▼
       Revenue / Upsell
```

## The Core Safety Model

**AI ≠ payment authority.** The LLM reaches money through exactly one
tool (`initiate_checkout`), and everything downstream is deterministic:
totals, policy verdicts, approvals, orders, signature checks.
System-originated chat messages are answered from fixed text with zero
LLM calls, so the agent can never hallucinate a paid order.

## Threat → Defense

| Threat                       | Defense                                 |
| ---------------------------- | --------------------------------------- |
| AI overspends                | Deterministic policy engine             |
| AI approves its own purchase | Human approval gate                     |
| Approval replay              | Single-use token                        |
| Cart amount changes          | Amount equality check + policy re-check |
| Duplicate payment            | Idempotent order creation               |
| Payment status spoofing      | Server-side verification                |
| Webhook replay               | Signature + replay protection           |
| Silent browser-side decline  | Failure reporting endpoint              |
| Audit tampering              | SHA-256 hash chain, verifiable live     |
| LLM outage                   | Provider rotation + retry + fallback    |
| Demo data misleading judges  | Explicit HIST/DEMO labeling             |

## Key Features

- 💬 Conversational discovery with per-card reasoning, zero-LLM cart ops, automatic upsells with pairing reasons
- 🛡️ Policy engine (max/min transaction, session limit, quantity + upsell caps), live limit bar, in-buyer settings with the approval gate hard-locked on
- ✅ Itemized approval screen (limits, remaining budget), single-use tokens, stale-amount expiry, renders via polling — never waits on LLM latency
- 💳 Razorpay test mode end to end: server-created orders, checkout.js, signature verify, signed webhooks, 30s status polling, same-approval retry with no double charge
- 📊 Merchant console: revenue / live revenue / conversion over tracked sessions / live-only upsell, With-vs-Without-AI diff, orders, full audit
- 🔍 Audit trail (What / Why / Amount / Actor / Hash), chain-intact badge, protocol Trace strip, frozen policy snapshots, IST timestamps
- 🧪 Demo tooling: Reset demo (history-preserving), Simulate decline (in-browser failure card + retry), policy-block trigger

## 🧪 Safety Isn't a Prompt — It's Tested

```text
181 automated tests

✓ Approval replay protection
✓ Overspending / policy violations
✓ Stale cart amounts
✓ Payment failure handling
✓ Retry without double charge
✓ Webhook reconciliation
✓ Audit-chain verification
✓ Demo/live revenue separation
✓ Reset-state preservation
✓ LLM fallback behavior
```

```bash
cd backend
$env:PYTHONPATH = "C:\projects\RazorFLow AI"   # Windows PowerShell
.\venv\Scripts\python.exe -m pytest tests/ -q
```

Frontend gates: `npm run lint` (0 errors, 0 warnings) and `npm run build` (offline-safe).

## 💳 Payment Flow

Razorpay **test mode** (no real money): approve → server creates the
order → checkout.js modal → success card `4100 2800 0000 1007` /
decline card `4100 2800 0006 0003` → signature verified against our own
order records → webhook or browser report reconciles → paid clears the
cart, failed consumes zero budget, retry reuses the same approval.

## 📊 Merchant Console

Revenue the merchant can prove: total + live-only revenue, conversion
over tracked sessions (never "approx"), upsell share of live revenue,
With-vs-Without-AI diff derived from the same real orders (labeled, no
control group claimed), and the full audit ledger with a live
chain-verification badge.

> **Demo data never masquerades as live revenue.**
> - `RF-*` → live buyer purchases (real test-mode payments)
> - `HIST-*` → seeded demo history · `DEMO-*` → scripted triggers
> - Live metrics are calculated only from actual paid orders

## 🛠 Tech Stack

FastAPI + Pydantic · SQLAlchemy + SQLite (FK-enforced) · Groq
`qwen/qwen3.6-27b` (5-key rotation, Ollama fallback) · Razorpay test
mode · Next.js 16 + React 19 + Tailwind + shadcn · Integer paise
everywhere.

## 🚀 Quick Start

```bash
git clone https://github.com/tisha-varma/RazorFlow-AI.git
cd RazorFlow-AI

# Backend
cd backend && python -m venv venv && venv/Scripts/activate && pip install -r requirements.txt
cp .env.example .env   # add keys (never commit .env)
python init_db.py && cd .. && backend/venv/Scripts/python.exe -m uvicorn backend.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend && npm install && npm run dev
```

```text
Buyer:    http://localhost:3000/buyer
Merchant: http://localhost:3000/merchant
Setup:    http://localhost:3000/setup
API Docs: http://localhost:8000/docs
```

> Run exactly **one** backend worker (the default) — state gating is per-process.

Then: chat *"I need shoes under ₹5000"* → accept the upsell → approve →
pay. Full 2-minute script in [Demo Scenarios](#demo-scenarios).

## ⚙️ Environment Variables

```env
LLM_PROVIDER=groq
LLM_API_KEYS=key1,key2,key3
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=
NEXT_PUBLIC_API_URL=http://localhost:8000/api
DEMO_MODE=True
```

```text
⚠️ Never commit .env
```

| Variable | Purpose | Default |
|----------|---------|---------|
| `LLM_PROVIDER` | `groq` / `ollama` / `gemini` / `auto` | `groq` |
| `LLM_MODEL` | Chat model | `qwen/qwen3.6-27b` |
| `DATABASE_URL` | SQLAlchemy URL (absolute path recommended) | `sqlite:///./razorflow.db` |

Webhooks locally need a tunnel: `cloudflared tunnel --url http://localhost:8000`,
registered as `https://<id>.trycloudflare.com/api/payment/webhook`
(events `payment.captured`, `payment.failed`).

## 📁 Project Structure

```
razorflow-ai/
├── backend/               # FastAPI + SQLAlchemy (63 source files)
│   ├── models/            # 13 models: cart, order, policy, approval, audit…
│   ├── schemas/           # Pydantic contracts
│   ├── routers/           # 10 routers: catalog, cart, agent, checkout,
│   │                      #   payment, policy, audit, dashboard, demo, well-known
│   ├── services/          # Business logic, AI agent, policy engine, state machine
│   ├── tests/             # 10 files, 181 pytest tests
│   ├── init_db.py         # DB + 15-product catalog seed
│   └── seed_demo_history.py  # Idempotent HIST-* seeder
└── frontend/              # Next.js 16 + React 19 + Tailwind + shadcn
    ├── public/products/   # 15 product photos
    └── src/
        ├── app/           # landing, buyer, merchant, setup
        ├── components/    # chat, commerce, audit, merchant
        └── lib/           # API client, types, IST time helpers
```

## 🔌 API

| Area | Key endpoints | Typical flow |
|------|---------------|--------------|
| Catalog | `GET /api/catalog/products`, `GET …/products/{id}/related` | Discover → recommend → upsell |
| Cart | `POST /api/cart`, `POST /api/cart/{id}/items`, `PUT/DELETE …/items/{item}` | Build cart, totals + policy attached |
| Agent | `POST /api/agent/chat`, `POST /api/agent/session` | Every chat turn |
| Checkout | `GET /api/checkout/summary/{cart}`, `POST …/request-approval`, `POST …/approve/{id}` | Mint gate → human decides |
| Payment | `POST /api/payment/create-order/{approval}`, `POST …/verify`, `POST …/webhook`, `GET …/status/{id}` | Order → pay → confirm → reconcile |
| Policy | `GET /api/policy`, `GET /api/policy/session-usage`, `PUT /api/policy/{id}` | Limits in, verdicts out |
| Audit | `GET /api/audit?session_id=…`, `GET /api/audit/verify` | Inspect → verify chain |
| Dashboard | `GET /api/dashboard/summary` | Merchant proof |
| Demo (`DEMO_MODE`) | `POST /api/demo/reset`, `…/seed-history`, `…/run-payment-failure`, `…/run-policy-block` | One-click stories |
| Agent protocol | `GET /.well-known/ai-commerce.json` | Machine-readable storefront |

## Demo Scenarios

1. Happy path: search → upsell → approve → success card → merchant moves
2. Policy blocked: 2× shoes vs ₹5,000 ceiling — refused before any approval exists
3. Payment failed: decline card (or **Simulate decline**) → failed card → **Retry**, same approval
4. Merchant proof: revenue split, With-vs-Without diff, audit chain badge — all live

## Limitations & What's Next

> RazorFlow AI is a demo implementation with a production-shaped safety architecture.

- Auth, multi-merchant, Postgres/Redis, live keys + refunds, shipment tracking → planned (see issues)
- Metrics are honest at small scale: derived baselines, tracked-session conversion, labeled synthetic rows

Found a bug? Open an issue — reproduce + expected vs actual is enough. PRs: cover backend changes with pytest, keep `npm run lint`/`build` clean, never commit `.env`, `*.db`, or keys.

## Engineering Notes

<details><summary>How this was built (condensed)</summary>

- Phased delivery (0–5) then review-driven hardening rounds; test suite grew 40 → 181.
- Load-bearing fixes along the way: FK enforcement + orphan purge (phantom carts), audit-verify repair, gate polling decoupled from LLM latency, provider-failure retries, browser failure reporting, history-preserving resets, IST timestamps, offline-safe build.
- Conventions: integer paise, `SessionState` enum + transition graph, service-per-concern modules, review-ID comments at challenged lines.

</details>

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Razorpay](https://razorpay.com) test mode + Python SDK
- [Groq](https://groq.com) free-tier inference
- [FastAPI](https://fastapi.tiangolo.com), [Next.js](https://nextjs.org), [shadcn/ui](https://ui.shadcn.com), [Tailwind CSS](https://tailwindcss.com), [Lucide](https://lucide.dev)
