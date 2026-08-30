# RazorFlow AI — Implementation Plan

This is a concrete checklist restating the 12-phase development order with actual file/module names.

## Phase 0 — Planning Docs
- [x] `docs/architecture.md`
- [x] `docs/database-schema.md`
- [x] `docs/api-contract.md`
- [x] `docs/state-machine.md`
- [x] `docs/policy-spec.md`
- [x] `docs/implementation-plan.md` (this file)
- [ ] Commit: `phase(0): planning docs`

## Phase 1 — Foundation
- [ ] `.gitignore`, `README.md`
- [ ] `backend/requirements.txt`
- [ ] `backend/main.py` — FastAPI app with CORS
- [ ] `backend/config.py` — Pydantic Settings
- [ ] `backend/database.py` — SQLAlchemy engine + session
- [ ] `backend/models/` — All 12 models
- [ ] `backend/init_db.py` — Create tables + seed 15 products
- [ ] Frontend: `npx create-next-app` + Tailwind + shadcn/ui
- [ ] `frontend/src/app/page.tsx` — Landing page
- [ ] `frontend/src/lib/api.ts` — API client
- [ ] Verify both servers run
- [ ] Commit: `phase(1): foundation`

## Phase 2 — Catalog & Policy Setup
- [ ] `backend/schemas/catalog.py`
- [ ] `backend/routers/catalog.py` — 8 endpoints
- [ ] `backend/services/catalog_service.py`
- [ ] `backend/schemas/policy.py`
- [ ] `backend/routers/policy.py`
- [ ] `backend/services/policy_engine.py`
- [ ] `backend/services/audit_service.py`
- [ ] `frontend/src/app/setup/page.tsx`
- [ ] Commit: `phase(2): catalog and policy`

## Phase 3 — AI Agent
- [ ] `backend/services/ai/llm_client.py` — Gemini Flash
- [ ] `backend/services/ai/tool_registry.py` — 12 tools
- [ ] `backend/services/ai/agent.py` — Message loop
- [ ] `backend/services/ai/prompts.py` — System prompt
- [ ] `backend/routers/agent.py` — Plain JSON chat
- [ ] `backend/services/state_machine.py`
- [ ] `frontend/src/app/buyer/page.tsx` — Split-screen
- [ ] Chat components
- [ ] Commerce panel components
- [ ] Commit: `phase(3): ai agent`

## Phase 4 — Cart + Upsell + Tests
- [ ] `backend/schemas/cart.py`
- [ ] `backend/routers/cart.py`
- [ ] `backend/services/cart_service.py`
- [ ] `frontend/src/components/commerce/CartSummary.tsx`
- [ ] `frontend/src/components/commerce/UpsellOffer.tsx`
- [ ] `backend/tests/test_policy.py` — 3+ boundary tests
- [ ] `backend/tests/test_catalog.py`
- [ ] `backend/tests/test_cart.py`
- [ ] Commit: `phase(4): cart and upsell`

## Phase 5 — Approval Gate
- [ ] `backend/schemas/approval.py`
- [ ] `backend/routers/checkout.py`
- [ ] `frontend/src/components/commerce/ApprovalScreen.tsx`
- [ ] State machine enforcement (409 on invalid transitions)
- [ ] Commit: `phase(5): approval gate`

## Phase 6 — Razorpay Payment
- [ ] `backend/services/payment_service.py`
- [ ] `backend/routers/payments.py`
- [ ] Frontend Razorpay Checkout integration
- [ ] `backend/tests/test_payment.py`
- [ ] Commit: `phase(6): razorpay payment`

## Phase 7 — Failure + Audit
- [ ] Deliberate failure demo path
- [ ] Recovery UI (Retry / Return to Cart)
- [ ] `backend/routers/audit.py`
- [ ] `frontend/src/components/audit/AuditTimeline.tsx`
- [ ] `frontend/src/app/merchant/audit/page.tsx`
- [ ] Commit: `phase(7): failure and audit`

## Phase 8 — Merchant Dashboard
- [ ] `backend/services/analytics_service.py`
- [ ] `backend/routers/analytics.py`
- [ ] `frontend/src/app/merchant/page.tsx`
- [ ] Revenue cards, orders table
- [ ] Commit: `phase(8): merchant dashboard`

## Phase 9 — Policy Settings + CSV + Webhooks
- [ ] `frontend/src/app/merchant/policy/page.tsx`
- [ ] `backend/services/upload_service.py`
- [ ] `backend/routers/upload.py`
- [ ] `frontend/src/app/merchant/catalog/page.tsx`
- [ ] `backend/routers/webhooks.py`
- [ ] Commit: `phase(9): csv and webhooks`

## Phase 10 — UI Polish
- [ ] Premium fintech aesthetic across all pages
- [ ] Client-side fake activity indicators
- [ ] Micro-animations + transitions
- [ ] Test-mode badge
- [ ] Mobile responsiveness
- [ ] Commit: `phase(10): ui polish`

## Phase 11 — Analytics + Funnel + Demo
- [ ] Revenue impact simulation
- [ ] `frontend/src/app/merchant/analytics/page.tsx`
- [ ] Funnel chart
- [ ] `backend/routers/demo.py` + `frontend/src/components/demo/DemoControls.tsx`
- [ ] Commit: `phase(11): analytics and demo`

## Phase 12 — Tests + Final
- [ ] `backend/tests/test_agent.py`
- [ ] `backend/tests/test_e2e.py`
- [ ] Rate limiting
- [ ] Security audit
- [ ] Final README
- [ ] Update `/docs/` to match reality
- [ ] Commit: `phase(12): final`
