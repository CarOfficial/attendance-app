# Admin panel

React + Vite + Tailwind. Persian RTL UI with Jalali dates. The branch map uses OpenStreetMap (internet access required for tiles).

## Development

```bash
cd admin
npm install
npm run dev          # http://127.0.0.1:5173 (proxies /api to http://127.0.0.1:8000)
```

## Build

```bash
npm run build        # typecheck + production build into dist/
```

Serve `dist/` from the same domain as the API, or set up `/api` as a reverse-proxy path in production so no CORS configuration is needed.

## Pages

- **Dashboard:** today's counts (active, present, absent, still checked in) and today's attendance.
- **Attendance:** filter by date range and employee. Edit check-in/check-out times and branch (for missed check-outs).
- **Employees:** create accounts with an initial password, edit name and branches, reset passwords, activate or deactivate.
- **Branches:** set each branch's coordinates by clicking the map, plus the allowed radius.
