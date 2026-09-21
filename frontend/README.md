# AlgoDesk frontend

Next.js (App Router) + TypeScript + Tailwind CSS + shadcn/ui + TanStack Query + Recharts console for the
algo trading backend. It talks only to the FastAPI backend described in `../docs/API_CONTRACT.md`; it never
calls a broker API and never handles broker credentials.

## Run

```bash
cp .env.example .env.local        # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev -- -p 3001            # http://localhost:3001
```

Checks: `npm run lint`, `npx tsc --noEmit`, `npm run build`.

## Docker

```bash
docker build --build-arg NEXT_PUBLIC_API_URL=http://localhost:8000 -t algodesk-frontend .
docker run -p 3001:3000 algodesk-frontend
```

`NEXT_PUBLIC_API_URL` is inlined at build time, so rebuild the image to point at a different backend.

## Layout

- `app/` routes: `login/` plus the guarded `(app)/` group (dashboard, strategies, orders, positions, trades,
  backtesting, brokers, risk, events, settings)
- `components/` UI by area (`layout`, `dashboard`, `trading`, `tables`, `charts`, `backtesting`, `brokers`,
  `risk`, `ui` = shadcn)
- `hooks/` TanStack Query hooks per resource, `services/` one module per API resource
- `lib/` API client (envelope unwrapping, `ApiError`, JWT), formatters (INR, IST), query client
- `types/` TypeScript mirror of the API contract
