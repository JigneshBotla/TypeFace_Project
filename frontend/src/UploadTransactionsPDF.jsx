// UploadTransactionsPDF.jsx
import React, { useState } from "react";

const API_BASE = "http://127.0.0.1:8000/api/v1"; // or "/api/v1" if same origin

function readRawToken() {
  return localStorage.getItem("auth_token") || localStorage.getItem("token") || "";
}
function authHeaders() {
  const t = readRawToken();
  if (!t) return {};
  return { Authorization: t.startsWith("Bearer ") ? t : `Bearer ${t}` };
}

export default function UploadTransactionsPDF({ onImported }) {
  const [file, setFile] = useState(null);
  const [rows, setRows] = useState([]);
  const [selected, setSelected] = useState({});
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  async function uploadPdf(e) {
    e && e.preventDefault();
    setMessage(null);
    if (!file) {
      setMessage("Please select a PDF file first");
      return;
    }
    setLoading(true);
    const fd = new FormData();
    fd.append("file", file, file.name);
    try {
      const res = await fetch(`${API_BASE}/transactions/upload_pdf`, {
        method: "POST",
        headers: {
          ...authHeaders(),
          // don't set Content-Type for FormData
        },
        body: fd,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error((body && body.detail) || `Upload failed: ${res.status}`);
      }
      const data = await res.json();
      const parsed = data.rows || [];
      setRows(parsed);
      // select all by default
      const sel = {};
      parsed.forEach((r, i) => (sel[i] = true));
      setSelected(sel);
      setMessage(`${parsed.length} candidate rows parsed`);
    } catch (err) {
      console.error("uploadPdf error", err);
      setMessage("Upload/parse failed: " + (err.message || err));
    } finally {
      setLoading(false);
    }
  }

  function toggleSelect(i) {
    setSelected((s) => ({ ...s, [i]: !s[i] }));
  }

  async function importSelected() {
    setMessage(null);
    const toImport = rows
      .map((r, i) => ({ ...r, type: "expense" })) // default type
      .filter((_, i) => selected[i]);
    if (!toImport.length) {
      setMessage("No rows selected to import");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/transactions/bulk`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ rows: toImport }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error((body && body.detail) || `Import failed: ${res.status}`);
      }
      const data = await res.json();
      setMessage(`Imported ${data.created} transactions`);
      setRows([]);
      setSelected({});
      if (onImported) onImported();
    } catch (err) {
      console.error("importSelected error", err);
      setMessage("Import failed: " + (err.message || err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-white p-4 rounded shadow">
      <h3 className="text-lg font-medium mb-3">Upload transactions from PDF</h3>

      <div className="space-y-2">
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files && e.target.files[0])}
        />
        <div className="flex gap-2">
          <button onClick={uploadPdf} className="px-3 py-1 bg-blue-600 text-white rounded" disabled={loading}>
            {loading ? "Uploading..." : "Upload & Parse"}
          </button>
          <button onClick={() => { setFile(null); setRows([]); setSelected({}); setMessage(null); }} className="px-3 py-1 bg-gray-200 rounded">
            Reset
          </button>
        </div>
      </div>

      {message ? <div className="mt-3 text-sm text-gray-700">{message}</div> : null}

      {rows && rows.length > 0 ? (
        <div className="mt-4">
          <table className="min-w-full border">
            <thead>
              <tr>
                <th className="p-1 border">Sel</th>
                <th className="p-1 border">Date</th>
                <th className="p-1 border">Description</th>
                <th className="p-1 border">Amount</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  <td className="p-1 border text-center">
                    <input type="checkbox" checked={!!selected[i]} onChange={() => toggleSelect(i)} />
                  </td>
                  <td className="p-1 border">{r.date || "-"}</td>
                  <td className="p-1 border">{r.description || "-"}</td>
                  <td className="p-1 border">{r.amount}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="mt-3 flex gap-2">
            <button onClick={importSelected} className="px-3 py-1 bg-green-600 text-white rounded" disabled={loading}>
              {loading ? "Importing..." : "Import selected"}
            </button>
            <button onClick={() => { setSelected(rows.reduce((acc, _, i) => ({ ...acc, [i]: true }), {})); }} className="px-3 py-1 bg-gray-200 rounded">
              Select all
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
