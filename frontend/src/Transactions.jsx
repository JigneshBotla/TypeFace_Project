// src/Transactions.jsx
import React, { useEffect, useState } from "react";
import UploadTransactionsPDF from "./UploadTransactionsPDF";
/*
Transactions view:
- create a transaction (income/expense)
- list transactions (with date range)
- show two simple SVG charts:
    1) expenses by category (bar)
    2) expense totals by date (bar)
Requires: token, API_BASE (e.g. http://127.0.0.1:8000/api/v1)
*/

const API_BASE = "http://127.0.0.1:8000/api/v1";


import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";


/* ---------- helpers ---------- */
function readRawToken() {
  return localStorage.getItem("auth_token") || localStorage.getItem("token") || "";
}
function saveRawToken(t) {
  if (!t) return;
  const normalized = t.startsWith("Bearer ") ? t : `Bearer ${t}`;
  localStorage.setItem("auth_token", normalized);
  return normalized;
}
function authHeaders() {
  const t = readRawToken();
  if (!t) return {};
  return { Authorization: t.startsWith("Bearer ") ? t : `Bearer ${t}` };
}
function currencyFormat(n, c = "INR") {
  if (n == null) return "-";
  try {
    return `${Number(n).toFixed(2)} ${c}`;
  } catch {
    return `${n} ${c}`;
  }
}
function safeJson(res) {
  // try to parse JSON, but don't throw if invalid
  return res
    .text()
    .then((t) => {
      try {
        return t ? JSON.parse(t) : null;
      } catch {
        return t; // return raw if not JSON
      }
    })
    .catch(() => null);
}

/* ---------- small aggregators (fallback) ---------- */
function aggregateByCategory(items) {
  const map = {};
  (items || []).forEach((it) => {
    if (!it) return;
    if (it.type !== "expense") return;
    const cat = (it.category && it.category.name) || (it.category_id ? `#${it.category_id}` : "Uncategorized");
    const amt = Number(it.amount || 0) || 0;
    map[cat] = (map[cat] || 0) + amt;
  });
  return Object.entries(map).map(([key, value]) => ({ key, value }));
}
function aggregateByDate(items) {
  const map = {};
  (items || []).forEach((it) => {
    if (!it) return;
    if (it.type !== "expense") return;
    const d = it.date || it.created_at || "";
    if (!d) return;
    map[d] = (map[d] || 0) + (Number(it.amount || 0) || 0);
  });
  return Object.entries(map)
    .map(([date, total]) => ({ date, total }))
    .sort((a, b) => a.date.localeCompare(b.date));
}

/* ---------- InlineLogin component ---------- */
function InlineLogin({ onLoginSuccess, setError }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e && e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const body = await safeJson(res);
        const msg = (body && (body.detail || body.message)) || `Login failed: ${res.status} ${res.statusText}`;
        throw new Error(msg);
      }
      const data = await res.json();
      if (!data || !data.access_token) throw new Error("Login succeeded but no access_token returned");
      saveRawToken(data.access_token);
      onLoginSuccess && onLoginSuccess();
    } catch (err) {
      console.error("Login error:", err);
      setError(err.message || String(err));
      alert("Login failed: " + (err.message || String(err)));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-white p-4 rounded shadow-sm">
      <h3 className="text-lg font-medium mb-3">Login to your account</h3>
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label className="block text-sm text-gray-600">Email</label>
          <input className="w-full p-2 border rounded" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div>
          <label className="block text-sm text-gray-600">Password</label>
          <input className="w-full p-2 border rounded" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </div>
        <div className="flex justify-end">
          <button type="submit" className="px-4 py-2 bg-indigo-600 text-white rounded" disabled={loading}>
            {loading ? "Logging in..." : "Login"}
          </button>
        </div>
      </form>
    </div>
  );
}

/* ---------- TransactionForm ---------- */
function TransactionForm({ onSaved, categories = [], refreshCategories, isAuthenticated, setError }) {
  const [type, setType] = useState("expense");
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("INR");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [description, setDescription] = useState("");
  const [categoryName, setCategoryName] = useState("");
  const [saving, setSaving] = useState(false);

  async function ensureCategoryId(name) {
    if (!name || !name.trim()) return null;
    const trimmed = name.trim();
    const found = (categories || []).find((c) => c && c.name && c.name.toLowerCase() === trimmed.toLowerCase());
    if (found) return found.id;
    try {
      const res = await fetch(`${API_BASE}/categories`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ name: trimmed }),
      });
      if (!res.ok) {
        console.warn("Failed creating category", res.status, res.statusText);
        return null;
      }
      return await res.json().then((d) => d && d.id ? d.id : null);
    } catch (err) {
      console.warn("ensureCategoryId error", err);
      return null;
    }
  }

  async function submit(e) {
    e && e.preventDefault();
    setError(null);
    if (!isAuthenticated) {
      setError("Not authenticated - login first.");
      return;
    }
    setSaving(true);
    try {
      const payload = {
        type,
        amount: Number(amount),
        currency,
        date,
        description: description || undefined,
        category_id: null,
      };
      if (categoryName && categoryName.trim()) {
        payload.category_id = await ensureCategoryId(categoryName);
      }
      const res = await fetch(`${API_BASE}/transactions`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        // read body safely
        const body = await safeJson(res);
        const msg = (body && (body.detail || body.message)) || `Create failed: ${res.status} ${res.statusText}`;
        if (res.status === 401 || res.status === 403) {
          // clear token and bubble up so parent triggers re-auth flow
          localStorage.removeItem("auth_token");
        }
        throw new Error(msg);
      }
      await res.json().catch(() => null);
      // reset and callback
      setAmount("");
      setDescription("");
      setCategoryName("");
      setType("expense");
      setDate(new Date().toISOString().slice(0, 10));
      onSaved && onSaved();
    } catch (err) {
      console.error("Transaction create error:", err);
      setError(err.message || String(err));
      alert("Create transaction failed: " + (err.message || String(err)));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="bg-white p-4 rounded shadow-sm space-y-3">
      <div className="flex gap-2">
        <label className="flex items-center gap-2">
          <input type="radio" value="expense" checked={type === "expense"} onChange={() => setType("expense")} />
          Expense
        </label>
        <label className="flex items-center gap-2">
          <input type="radio" value="income" checked={type === "income"} onChange={() => setType("income")} />
          Income
        </label>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <input required className="p-2 border rounded" placeholder="Amount" value={amount} onChange={(e) => setAmount(e.target.value)} type="number" step="0.01" disabled={!isAuthenticated || saving} />
        <input className="p-2 border rounded" value={currency} onChange={(e) => setCurrency(e.target.value)} disabled={!isAuthenticated || saving} />
        <input className="p-2 border rounded" type="date" value={date} onChange={(e) => setDate(e.target.value)} disabled={!isAuthenticated || saving} />
      </div>

      <div className="grid grid-cols-2 gap-2">
        <input className="p-2 border rounded" placeholder="Category (optional)" value={categoryName} onChange={(e) => setCategoryName(e.target.value)} disabled={!isAuthenticated || saving} />
        <input className="p-2 border rounded" placeholder="Description" value={description} onChange={(e) => setDescription(e.target.value)} disabled={!isAuthenticated || saving} />
      </div>

      <div className="flex justify-end">
        <button className="px-4 py-2 bg-indigo-600 text-white rounded" type="submit" disabled={!isAuthenticated || saving}>
          {saving ? "Saving..." : "Save"}
        </button>
      </div>
    </form>
  );
}

/* ---------- Main TransactionsView (defensive) ---------- */
export default function TransactionsView() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [errorBanner, setErrorBanner] = useState(null);

  const [list, setList] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(25);
  const [loading, setLoading] = useState(false);

  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [typeFilter, setTypeFilter] = useState("");

  const [byCategoryData, setByCategoryData] = useState([]);
  const [byDateData, setByDateData] = useState([]);
  const [categories, setCategories] = useState([]);

  const palette = ["#8884d8", "#82ca9d", "#ffc658", "#ff7f7f", "#a28fd0", "#8dd1e1", "#f6c85f", "#e76f51"];

  // validate token on mount (cheap)
  useEffect(() => {
    let cancelled = false;
    async function validate() {
      setCheckingAuth(true);
      setErrorBanner(null);
      try {
        const raw = readRawToken();
        if (!raw) {
          if (!cancelled) setIsAuthenticated(false);
          return;
        }
        const res = await fetch(`${API_BASE}/categories`, { headers: { ...authHeaders() } });
        if (!cancelled) setIsAuthenticated(res.ok);
      } catch (err) {
        console.warn("Auth validation error", err);
        if (!cancelled) setIsAuthenticated(false);
      } finally {
        if (!cancelled) setCheckingAuth(false);
      }
    }
    validate();
    return () => {
      cancelled = true;
    };
  }, []);

  // whenever auth/filters change, refresh relevant data
  useEffect(() => {
    if (isAuthenticated) {
      loadTransactions(1);
      fetchAnalytics();
      fetchCategories();
    } else {
      setList([]);
      setTotal(0);
      setByCategoryData([]);
      setByDateData([]);
    }
    // eslint-disable-next-line
  }, [isAuthenticated, from, to, typeFilter, perPage]);

  async function fetchCategories() {
    try {
      const res = await fetch(`${API_BASE}/categories`, { headers: { ...authHeaders() } });
      if (!res.ok) {
        setCategories([]);
        return;
      }
      const arr = await res.json();
      setCategories(Array.isArray(arr) ? arr : []);
    } catch (err) {
      console.warn("fetchCategories error", err);
      setCategories([]);
    }
  }

  async function loadTransactions(p = 1) {
    setErrorBanner(null);
    if (!isAuthenticated) {
      setList([]);
      setTotal(0);
      return;
    }
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("page", String(p));
      params.set("per_page", String(perPage));
      if (from) params.set("start_date", from);
      if (to) params.set("end_date", to);
      if (typeFilter) params.set("type", typeFilter);

      const url = `${API_BASE}/transactions${params.toString() ? `?${params.toString()}` : ""}`;
      const res = await fetch(url, { headers: { ...authHeaders() } });
      if (!res.ok) {
        if (res.status === 401 || res.status === 403) {
          localStorage.removeItem("auth_token");
          setIsAuthenticated(false);
          setErrorBanner("Session expired or unauthorized. Please log in again.");
        } else {
          const body = await safeJson(res);
          setErrorBanner((body && (body.detail || body.message)) || `Failed to load transactions: ${res.status}`);
        }
        setList([]);
        setTotal(0);
        return;
      }
      const data = await res.json().catch(() => null);
      const items = Array.isArray(data && data.items) ? data.items : [];
      setList(items);
      setTotal((data && (typeof data.total === "number" ? data.total : items.length)) || items.length);
      setPage((data && data.page) || p);
      setPerPage((data && data.per_page) || perPage);
    } catch (err) {
      console.error("loadTransactions error", err);
      setErrorBanner("Failed to load transactions. See console for details.");
      setList([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }

  async function fetchAnalytics() {
    setErrorBanner(null);
    if (!isAuthenticated) {
      setByCategoryData([]);
      setByDateData([]);
      return;
    }
    try {
      const params = new URLSearchParams();
      if (from) params.set("start_date", from);
      if (to) params.set("end_date", to);

      const catRes = await fetch(`${API_BASE}/analytics/by_category?${params.toString()}`, { headers: { ...authHeaders() } });
      if (catRes.ok) {
        const rows = await catRes.json();
        setByCategoryData(Array.isArray(rows) ? rows.map((r) => ({ key: r.category, value: Number(r.total || 0) })) : []);
      } else {
        setByCategoryData([]);
      }

      const dateRes = await fetch(`${API_BASE}/analytics/by_date?${params.toString()}`, { headers: { ...authHeaders() } });
      if (dateRes.ok) {
        const rows = await dateRes.json();
        setByDateData(Array.isArray(rows) ? rows.map((r) => ({ date: r.date, total: Number(r.total || 0) })) : []);
      } else {
        setByDateData([]);
      }
    } catch (err) {
      console.warn("fetchAnalytics error", err);
      setByCategoryData([]);
      setByDateData([]);
    }
  }

  async function logout() {
    localStorage.removeItem("auth_token");
    setIsAuthenticated(false);
    setErrorBanner(null);
  }

  function handleApplyFilters(e) {
    e && e.preventDefault();
    loadTransactions(1);
    fetchAnalytics();
  }

  function refreshAll() {
    loadTransactions(page);
    fetchAnalytics();
    fetchCategories();
  }

  const expensesByCategory = (byCategoryData && byCategoryData.length) ? byCategoryData : aggregateByCategory(list);
  const expensesByDate = (byDateData && byDateData.length) ? byDateData : aggregateByDate(list);

  // render
  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Finance App — Transactions</h1>
        <div>
          {isAuthenticated ? <button onClick={logout} className="px-3 py-1 bg-red-500 text-white rounded">Logout</button> : null}
        </div>
      </div>

      {errorBanner ? (
        <div className="bg-red-50 border-l-4 border-red-400 p-3 rounded">
          <strong className="text-red-700">Error:</strong> <span className="text-red-700"> {errorBanner}</span>
        </div>
      ) : null}

      <div className="grid md:grid-cols-2 gap-6">
        <div>
          {!isAuthenticated ? (
            <InlineLogin onLoginSuccess={() => { setIsAuthenticated(true); setErrorBanner(null); }} setError={setErrorBanner} />
          ) : (
            <>
              <h2 className="text-xl font-semibold mb-3">Add transaction</h2>
              <TransactionForm onSaved={() => refreshAll()} categories={categories} refreshCategories={fetchCategories} isAuthenticated={isAuthenticated} setError={setErrorBanner} />
            <div className="mt-6">
                <UploadTransactionsPDF onImported={() => refreshAll()} />
            </div>

            </>
            
          )}
        </div>

        <div>
          <h2 className="text-xl font-semibold mb-3">Filters & quick actions</h2>
          <form className="bg-white p-4 rounded shadow-sm space-y-3" onSubmit={handleApplyFilters}>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-sm text-gray-600">From</label>
                <input className="p-2 border rounded w-full" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
              </div>
              <div>
                <label className="block text-sm text-gray-600">To</label>
                <input className="p-2 border rounded w-full" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
              </div>
            </div>

            <div>
              <label className="block text-sm text-gray-600">Type</label>
              <select className="p-2 border rounded w-full" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
                <option value="">All</option>
                <option value="income">Income</option>
                <option value="expense">Expense</option>
              </select>
            </div>

            <div className="flex gap-2 justify-between">
              <div>
                <label className="block text-sm text-gray-600">Per page</label>
                <input className="p-2 border rounded w-24" type="number" min="1" max="200" value={perPage} onChange={(e) => setPerPage(Number(e.target.value))} />
              </div>
              <div className="flex items-end gap-2">
                <button type="submit" className="px-4 py-2 bg-green-600 text-white rounded">Apply</button>
                <button type="button" onClick={() => { setFrom(""); setTo(""); setTypeFilter(""); setPerPage(25); refreshAll(); }} className="px-4 py-2 bg-gray-200 rounded">Reset</button>
              </div>
            </div>
          </form>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white p-4 rounded shadow-sm">
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-lg font-medium">Transactions</h3>
            <div className="text-sm text-gray-600">Total: {total}</div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y">
              <thead>
                <tr>
                  <th className="px-3 py-2 text-left">Date</th>
                  <th className="px-3 py-2 text-left">Type</th>
                  <th className="px-3 py-2 text-right">Amount</th>
                  <th className="px-3 py-2 text-left">Category</th>
                  <th className="px-3 py-2 text-left">Description</th>
                </tr>
              </thead>
              <tbody>
                {checkingAuth ? (
                  <tr><td colSpan={5} className="p-4 text-center text-gray-500">Checking authentication...</td></tr>
                ) : loading ? (
                  <tr><td colSpan={5} className="p-4 text-center text-gray-500">Loading...</td></tr>
                ) : !list || list.length === 0 ? (
                  <tr><td colSpan={5} className="p-4 text-center text-gray-500">No transactions</td></tr>
                ) : (
                  list.map((tx) => (
                    <tr key={tx && tx.id ? tx.id : Math.random()} className="border-t">
                      <td className="px-3 py-2">{(tx && (tx.date || (tx.created_at ? tx.created_at.slice(0, 10) : ""))) || ""}</td>
                      <td className="px-3 py-2">{tx && tx.type}</td>
                      <td className="px-3 py-2 text-right">{currencyFormat(tx && tx.amount, tx && tx.currency)}</td>
                      <td className="px-3 py-2">{tx && (tx.category ? tx.category.name : tx.category_id ? `#${tx.category_id}` : "-")}</td>
                      <td className="px-3 py-2">{tx && tx.description ? tx.description : "-"}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="mt-3 flex items-center justify-between">
            <div className="text-sm text-gray-600">Showing {list ? list.length : 0} items</div>
            <div className="flex gap-2">
              <button className="px-3 py-1 bg-gray-200 rounded" onClick={() => { const np = Math.max(1, page - 1); setPage(np); loadTransactions(np); }}>Prev</button>
              <div className="px-3 py-1 bg-white rounded">Page {page}</div>
              <button className="px-3 py-1 bg-gray-200 rounded" onClick={() => { const np = page + 1; setPage(np); loadTransactions(np); }}>Next</button>
            </div>
          </div>
        </div>

        <div className="bg-white p-4 rounded shadow-sm space-y-6">
          <div>
            <h4 className="font-medium mb-2">Expenses by category</h4>
            {(!expensesByCategory || expensesByCategory.length === 0) ? (
              <div className="text-gray-500">No expense data</div>
            ) : (
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie data={expensesByCategory} dataKey="value" nameKey="key" outerRadius={80} fill="#8884d8" label>
                    {expensesByCategory.map((entry, idx) => <Cell key={`c-${idx}`} fill={palette[idx % palette.length]} />)}
                  </Pie>
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>

          <div>
            <h4 className="font-medium mb-2">Expenses over time</h4>
            {(!expensesByDate || expensesByDate.length === 0) ? (
              <div className="text-gray-500">No expense data</div>
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={expensesByDate}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="total" stroke="#8884d8" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}