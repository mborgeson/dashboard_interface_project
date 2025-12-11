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
          // Chart libraries
          "vendor-charts": ["recharts", "chart.js", "react-chartjs-2"],
          // Map libraries
          "vendor-maps": ["leaflet", "react-leaflet", "leaflet.markercluster"],
          // Data/utility libraries
          "vendor-data": [
            "@tanstack/react-query",
            "@tanstack/react-table",
            "zustand",
            "fuse.js",
          ],
          // Export libraries - split for better lazy loading
          "vendor-pdf": ["jspdf", "html2canvas"],
          "vendor-xlsx": ["xlsx"],
          // Date/form libraries
          "vendor-forms": [
            "date-fns",
            "react-hook-form",
            "@hookform/resolvers",
            "zod",
          ],
        },
      },
    },
    // Increase chunk size warning limit (optional)
    chunkSizeWarningLimit: 600,
  },
  // Optimize deps for faster dev startup
  optimizeDeps: {
    include: [
      "react",
      "react-dom",
      "react-router-dom",
      "recharts",
      "zustand",
      "lucide-react",
    ],
  },
});
