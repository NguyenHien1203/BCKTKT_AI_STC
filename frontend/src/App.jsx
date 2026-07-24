import { Route, Routes, Link } from "react-router-dom";
import OrgUnitsPage from "./pages/OrgUnitsPage.jsx";

function HomePage() {
  return (
    <div style={{ padding: 24, fontFamily: "sans-serif" }}>
      <h1>Kho Dữ Liệu Tổng Hợp Ngành Tài Chính — Tỉnh Hưng Yên</h1>
      <p>
        Frontend đang trong giai đoạn phát triển theo từng Use Case (xem{" "}
        <code>PLAN.md</code> ở gốc project). Hiện đã có:
      </p>
      <ul>
        <li>
          <Link to="/org-units">UC-01: Quản lý cơ cấu tổ chức</Link>
        </li>
      </ul>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/org-units" element={<OrgUnitsPage />} />
    </Routes>
  );
}
