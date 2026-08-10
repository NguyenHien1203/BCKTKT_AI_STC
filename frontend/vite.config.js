import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api/auth-identity": {
        target: "http://localhost:8001",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/auth-identity/, ""),
      },
      // UC-029 (Phân tích dữ liệu có cấu trúc) -> data-quality-service.
      "/api/data-quality": {
        target: "http://localhost:8003",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/data-quality/, ""),
      },
      // UC-047 (Xem Bảng điều khiển điều hành) -> reporting-service.
      "/api/reporting": {
        target: "http://localhost:8004",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/reporting/, ""),
      },
    },
  },
});