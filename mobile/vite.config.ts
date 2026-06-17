import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 1300,
    rollupOptions: {
      output: {
        manualChunks: {
          ionic: ["@ionic/react", "ionicons"]
        }
      }
    }
  },
  server: {
    proxy: {
      "/api": {
        target: "http://192.168.1.54:8000",
        changeOrigin: true
      },
      "/media": {
        target: "http://192.168.1.54:8000",
        changeOrigin: true
      }
    }
  }
});
