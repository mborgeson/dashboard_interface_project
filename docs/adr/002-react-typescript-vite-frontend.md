# ADR-002: React + TypeScript + Vite for frontend

## Status
Accepted

## Context
The dashboard is a complex single-page application with data-heavy views (deal pipeline Kanban, property analytics, charts, maps, underwriting tables). It requires fast dev iteration, strong typing for financial data, and code-splitting to keep initial load times low despite large vendor dependencies (Recharts, Leaflet, ExcelJS, jsPDF).

## Decision
We chose React 19 with TypeScript, Vite as the build tool, and Tailwind CSS + shadcn/ui (Radix primitives) for the component layer. Key libraries: TanStack Query for server state, Zustand for client state, Zod for runtime API response validation, React Router for routing, and React Hook Form for form handling.

Vite config (`vite.config.ts`) defines manual chunk splitting to keep the app shell small:
- `vendor-react`, `vendor-radix`, `vendor-charts`, `vendor-maps`, `vendor-dnd`, `vendor-data`, `vendor-forms`, `vendor-misc`
- Heavy export libraries (ExcelJS, jsPDF) are dynamically imported and never included in the initial bundle.

Zod schemas in `src/lib/api/schemas/` validate and transform API responses from snake_case (backend) to camelCase (frontend), catching contract drift at runtime.

## Consequences
- Vite provides sub-second HMR, significantly faster than Webpack-based alternatives.
- Manual chunk splitting requires maintenance when new large dependencies are added.
- Zod schemas act as a contract layer between backend and frontend, catching type mismatches early but adding a maintenance surface.
- Not using Next.js means no SSR/SSG, which is acceptable since this is an internal tool behind authentication.
