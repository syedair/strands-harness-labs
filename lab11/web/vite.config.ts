import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: { "/api": `http://127.0.0.1:${process.env.LAB11_API_PORT ?? 8000}` } }, // start.sh sets the port
});
