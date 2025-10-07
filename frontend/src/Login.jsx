// Login.jsx
import React, { useState } from "react";

const API_BASE = "/api/v1";

function saveTokenRaw(token) {
  if (!token) return;
  // store with explicit Bearer prefix so other code can use it directly
  const normalized = token.startsWith("Bearer ") ? token : `Bearer ${token}`;
  localStorage.setItem("auth_token", normalized);
  return normalized;
}

export default function Login({ onSuccessRedirect = "/" }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || res.statusText || "Login failed");
      }
      const data = await res.json();
      if (!data.access_token) throw new Error("No token in response");
      saveTokenRaw(data.access_token);
      // reload so components read the token from localStorage and fetch their data
      window.location.href = onSuccessRedirect;
    } catch (err) {
      alert("Login failed: " + err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-md mx-auto mt-20 p-6 bg-white rounded shadow">
      <h2 className="text-2xl font-semibold mb-4">Login</h2>
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label className="block text-sm text-gray-600">Email</label>
          <input
            type="email"
            className="w-full p-2 border rounded"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>

        <div>
          <label className="block text-sm text-gray-600">Password</label>
          <input
            type="password"
            className="w-full p-2 border rounded"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
          />
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            className="px-4 py-2 bg-indigo-600 text-white rounded"
            disabled={loading}
          >
            {loading ? "Logging in..." : "Login"}
          </button>
        </div>
      </form>
      <p className="text-sm text-gray-500 mt-3">Use the same credentials you used for register.</p>
    </div>
  );
}
