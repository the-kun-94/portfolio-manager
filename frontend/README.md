# Frontend — the Terminal

Next.js + React + TypeScript dashboard. Dark "Bloomberg Terminal" theme,
hand-written CSS (no framework dependency — just `next`, `react`,
`react-dom`, kept intentionally minimal since this project's build couldn't
be verified against the npm registry from the sandbox it was written in;
Vercel's build step is the first real compile check it gets).

```
frontend/
├── package.json
├── tsconfig.json
├── next.config.js
├── .env.local.example          # copy to .env.local for local dev
└── src/
    ├── pages/
    │   ├── _app.tsx
    │   └── index.tsx            # assembles all five dashboard modules
    ├── components/
    │   ├── CommandHeader.tsx    # total liquidity / active equity / cash split
    │   ├── ActionFeed.tsx       # prioritized BUY/HARVEST/EXIT alerts only
    │   ├── DualGateLedger.tsx   # full holdings table, every signal state
    │   ├── TradeForm.tsx        # Buy/Sell -> POST /api/trades
    │   └── TransactionHistory.tsx
    ├── lib/
    │   ├── types.ts             # mirrors backend/app/schemas.py
    │   ├── api.ts               # typed fetch wrappers
    │   └── useDashboardData.ts  # polls the backend every 30s
    └── styles/
        └── globals.css
```

## Local dev

```bash
cd frontend
cp .env.local.example .env.local   # points at http://localhost:8000 by default
npm install
npm run dev
```

Requires the backend running (`uvicorn app.main:app --reload --port 8000`
from `backend/`) for data to show up.

## Deploying

See `DEPLOYMENT.md` at the repo root — this deploys to Vercel with
`NEXT_PUBLIC_API_BASE_URL` pointed at your live backend.
