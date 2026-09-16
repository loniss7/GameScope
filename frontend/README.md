# GameScope frontend

React + TypeScript + Vite prototype built with Mantine.

## Run locally

1. Start the backend from `backend/` with `python -m uvicorn app.main:app --reload`.
2. This project uses pnpm. Install it once with `npm install --global pnpm`, then run `pnpm install` in this directory. `npm install` can fail here with `EUNSUPPORTEDPROTOCOL workspace:*` while resolving Mantine package metadata.
3. Copy `.env.example` to `.env.local` if the API is not at `http://127.0.0.1:8000`.
4. Run `pnpm dev` and open `http://127.0.0.1:5173`.

The app uses only the public GameScope API. Provider keys must remain on the backend.
