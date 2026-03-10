import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // IMPORTANT: More specific paths must come FIRST
      // Proxy FRED API requests to avoid CORS issues
      "/api/fred": {
        target: "https://api.stlouisfed.org",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/fred/, ""),
        secure: false,
      },
      // Proxy Backend API requests (generic /api - must come AFTER more specific paths)
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
        // WebSocket support for real-time updates
        ws: true,
      },
      // Proxy WebSocket connections
      "/ws": {
        target: "ws://localhost:8000",
        changeOrigin: true,
        ws: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Core vendor libraries
          "vendor-react": ["react", "react-dom", "react-router-dom"],
          // UI libraries
          "vendor-radix": [
            "@radix-ui/react-accordion",
            "@radix-ui/react-alert-dialog",
            "@radix-ui/react-checkbox",
            "@radix-ui/react-dialog",
            "@radix-ui/react-dropdown-menu",
            "@radix-ui/react-label",
            "@radix-ui/react-select",
            "@radix-ui/react-separator",
            "@radix-ui/react-slot",
            "@radix-ui/react-tabs",
            "@radix-ui/react-tooltip",
          ],
          // Icons — extracted from main chunk to reduce app shell size
          "vendor-icons": ["lucide-react"],
          // Chart libraries — kept as a manual chunk so recharts doesn't
          // get duplicated across multiple lazy route chunks. Only loaded
          // when a chart-using route is first visited.
          "vendor-charts": ["recharts"],
          // Map libraries
          "vendor-maps": ["leaflet", "react-leaflet", "leaflet.markercluster"],
          // Drag-and-drop (used by Deals kanban)
          "vendor-dnd": [
            "@dnd-kit/core",
            "@dnd-kit/sortable",
            "@dnd-kit/utilities",
          ],
          // Data/utility libraries
          "vendor-data": [
            "@tanstack/react-query",
            "@tanstack/react-table",
            "zustand",
            "fuse.js",
          ],
          // HTTP + command palette
          "vendor-misc": ["axios", "cmdk", "date-fns"],
          // NOTE: jspdf and exceljs are dynamically imported
          // in src/features/underwriting/utils/exporters.ts
          // Vite creates separate lazy chunks for these automatically.
          // They are only loaded when user clicks export buttons.
          // Date/form libraries
          "vendor-forms": [
            "dayjs",
            "react-hook-form",
            "@hookform/resolvers",
            "zod",
          ],
        },
      },
    },
    // Only lazy-loaded chunks (exceljs ~937KB, jspdf ~386KB, html2canvas ~201KB)
    // exceed this limit — all are loaded on demand, not at page load.
    chunkSizeWarningLimit: 500,
  },
  // Optimize deps for faster dev startup
  optimizeDeps: {
    include: [
      "react",
      "react-dom",
      "react-router-dom",
      "zustand",
      "lucide-react",
    ],
  },
});
