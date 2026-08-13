import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Clock, Database, RefreshCw } from "lucide-react";
import { getDataFreshnessSummary, listDataFreshness } from "../api/dataFreshness.js";

function formatDateTime(iso) {
  if (!iso) return "-";
  try {
    return new Date(iso).toLocaleString("vi-VN");
  } catch {
    return iso;
  }
}

function completenessColor(pct) {
  if (pct >= 95) return "#1a7f37";
  if (pct >= 70) return "#9a6700";
  return "#cf222e";
}

/**
 * UC-057 — Hiển thị độ mới dữ liệu (actor: Tất cả người dùng).
 * Bước 1-2: "Xem ô thông tin độ mới dữ liệu trên Bảng điều khiển -> Hệ
 * thống truy vấn view curated.data_freshness" (ô tổng quan).
 * Bước 3-4: "Xem chi tiết last_sync + độ đầy đủ theo nguồn -> Hệ thống
 * hiển thị bảng" (mở rộng khi bấm "Xem chi tiết theo nguồn").
 */
export default function DataFreshnessPanel() {
  const [summary, setSummary] = useState(null);
  const [detail, setDetail] = useState([]);
  const [showDetail, setShowDetail] = useState(false);

  const [loadingSummary, setLoadingSummary] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState(null);

  // ---------- Bước 1-2: ô tổng quan trên Bảng điều khiển ----------
  async function loadSummary() {
    setLoadingSummary(true);
    setError(null);
    try {
      const data = await getDataFreshnessSummary();
      setSummary(data);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoadingSummary(false);
    }
  }

  useEffect(() => {
    loadSummary();
  }, []);

  // ---------- Bước 3-4: xem chi tiết last_sync + độ đầy đủ theo nguồn ----------
  async function loadDetail() {
    setLoadingDetail(true);
    setError(null);
    try {
      const data = await listDataFreshness();
      setDetail(data);
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e.message);
    } finally {
      setLoadingDetail(false);
    }
  }

  function toggleDetail() {
    const next = !showDetail;
    setShowDetail(next);
    if (next && detail.length === 0) {
      loadDetail();
    }
  }

  return (
    <div className="card" style={{ marginBottom: 20 }}>
      <div
        className="card-header"
        style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}
      >
        <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Database size={16} /> Độ mới dữ liệu
        </h3>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() => {
            loadSummary();
            if (showDetail) loadDetail();
          }}
          disabled={loadingSummary}
        >
          <RefreshCw size={14} /> Tải lại
        </button>
      </div>
      <div className="card-body">
        {error && (
          <div className="alert alert-error" style={{ marginBottom: 12 }}>
            {error}
          </div>
        )}

        {/* Bước 1-2 — ô thông tin độ mới dữ liệu */}
        {loadingSummary ? (
          <p style={{ color: "#666" }}>Đang truy vấn curated.data_freshness...</p>
        ) : summary ? (
          <div style={{ display: "flex", gap: 24, flexWrap: "wrap", marginBottom: 14 }}>
            <div>
              <div style={{ fontSize: 11, color: "#666" }}>Số nguồn dữ liệu</div>
              <div style={{ fontSize: 20, fontWeight: 600 }}>{summary.total_sources}</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: "#666" }}>Nguồn chậm trễ (&gt;24h)</div>
              <div
                style={{
                  fontSize: 20,
                  fontWeight: 600,
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  color: summary.stale_sources > 0 ? "#cf222e" : "#1a7f37",
                }}
              >
                {summary.stale_sources > 0 ? (
                  <AlertTriangle size={16} />
                ) : (
                  <CheckCircle2 size={16} />
                )}
                {summary.stale_sources}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: "#666" }}>Độ đầy đủ trung bình</div>
              <div
                style={{
                  fontSize: 20,
                  fontWeight: 600,
                  color: completenessColor(summary.average_completeness_percent),
                }}
              >
                {summary.average_completeness_percent}%
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: "#666" }}>Đồng bộ gần nhất</div>
              <div
                style={{
                  fontSize: 14,
                  fontWeight: 600,
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                <Clock size={14} /> {formatDateTime(summary.latest_last_sync)}
              </div>
            </div>
          </div>
        ) : (
          <div className="empty-state">Chưa có dữ liệu độ mới nào được ghi nhận.</div>
        )}

        <button type="button" className="btn btn-secondary" onClick={toggleDetail}>
          {showDetail ? "Ẩn chi tiết theo nguồn" : "Xem chi tiết theo nguồn"}
        </button>

        {/* Bước 3-4 — bảng chi tiết last_sync + độ đầy đủ theo nguồn */}
        {showDetail && (
          <div style={{ marginTop: 14 }}>
            {loadingDetail ? (
              <p style={{ color: "#666" }}>Đang tải bảng chi tiết...</p>
            ) : detail.length === 0 ? (
              <div className="empty-state">Chưa có nguồn dữ liệu nào được ghi nhận.</div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Nguồn</th>
                      <th>Last sync</th>
                      <th>Độ đầy đủ</th>
                      <th>Số bản ghi (thực/kỳ vọng)</th>
                      <th>Trạng thái</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.map((row) => (
                      <tr key={row.id}>
                        <td>
                          {row.nguon_ten}{" "}
                          <span style={{ color: "#999", fontSize: 11 }}>({row.nguon_code})</span>
                        </td>
                        <td>{formatDateTime(row.last_sync)}</td>
                        <td style={{ color: completenessColor(row.completeness_percent) }}>
                          {row.completeness_percent}%
                        </td>
                        <td>
                          {row.actual_record_count}/{row.expected_record_count}
                        </td>
                        <td>
                          {row.is_stale ? (
                            <span
                              className="badge"
                              style={{ color: "#cf222e", display: "inline-flex", gap: 4 }}
                            >
                              <AlertTriangle size={12} /> Chậm trễ
                            </span>
                          ) : (
                            <span
                              className="badge"
                              style={{ color: "#1a7f37", display: "inline-flex", gap: 4 }}
                            >
                              <CheckCircle2 size={12} /> Đồng bộ
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}