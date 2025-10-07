import React, { useEffect, useState } from "react";
// near other imports
import TransactionsView from "./Transactions.jsx"; // or `./Transactions` depending on your file name

/*
Simple frontend for your Finance API.
- BASE_URL: adjust if backend not on 127.0.0.1:8000
- Provides: Register, Login, Upload receipt, List receipts, Download, View parsed JSON
*/

const BASE_URL = "http://127.0.0.1:8000/api/v1";

function useAuthToken() {
  const [token, setToken] = useState(localStorage.getItem("jwt") || "");
  useEffect(() => {
    if (token) localStorage.setItem("jwt", token);
    else localStorage.removeItem("jwt");
  }, [token]);
  return [token, setToken];
}

function AuthForm({ onLogin }) {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const toggle = () => setIsRegister((s) => !s);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    try {
      const url = `${BASE_URL}/auth/${isRegister ? "register" : "login"}`;
      const payload = isRegister
        ? { email, password, username }
        : { email, password };
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
      onLogin(data.access_token);
    } catch (err) {
      alert("Auth error: " + err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h3>{isRegister ? "Register" : "Login"}</h3>
      <form onSubmit={submit}>
        <div className="form-row">
          <input className="input" placeholder="Email" value={email} onChange={(e)=>setEmail(e.target.value)} />
        </div>
        {isRegister && (
          <div className="form-row">
            <input className="input" placeholder="Username" value={username} onChange={(e)=>setUsername(e.target.value)} />
          </div>
        )}
        <div className="form-row">
          <input className="input" type="password" placeholder="Password" value={password} onChange={(e)=>setPassword(e.target.value)} />
        </div>
        <div className="row">
          <button className="btn" disabled={busy} type="submit">{busy ? "Please wait..." : (isRegister ? "Register" : "Login")}</button>
          <button type="button" className="btn-ghost" onClick={toggle}>{isRegister ? "Have an account? Login" : "Need an account? Register"}</button>
        </div>
      </form>
    </div>
  );
}

function ReceiptUpload({ token, onUploaded }) {
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    if (!file) {
      alert("Pick a file first");
      return;
    }
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(`${BASE_URL}/receipts`, {
        method: "POST",
        headers: {
          Authorization: "Bearer " + token,
        },
        body: fd,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
      onUploaded && onUploaded();
      setFile(null);
      alert("Uploaded OK");
    } catch (err) {
      alert("Upload failed: " + err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h3>Upload Receipt</h3>
      <form onSubmit={submit}>
        <div className="form-row">
          <input type="file" accept="image/*" onChange={(e)=>setFile(e.target.files?.[0] || null)} />
        </div>
        <div className="row">
          <button className="btn" disabled={busy}>{busy ? "Uploading..." : "Upload"}</button>
        </div>
        <div className="small">Uploads will be processed by the server (OCR runs in background).</div>
      </form>
    </div>
  );
}

function ReceiptsList({ token }) {
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const res = await fetch(`${BASE_URL}/receipts`, {
        headers: { Authorization: "Bearer " + token },
      });
      if (!res.ok) {
        const err = await res.json().catch(()=>({detail:res.statusText}));
        throw new Error(err.detail || res.statusText);
      }
      const data = await res.json();
      setList(data);
    } catch (err) {
      alert("Could not load receipts: " + err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(()=> {
    if (token) load();
  }, [token]);

  if (!token) return <div className="card small">Login to see receipts</div>;

  return (
    <div className="card">
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
        <h3>Receipts</h3>
        <button className="btn-ghost" onClick={load}>{loading ? "Refreshing..." : "Refresh"}</button>
      </div>

      {list.length === 0 && <div className="small">No receipts yet.</div>}

      {list.map(r => (
        <div key={r.id} className="receipt">
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
            <div>
              <strong>Receipt #{r.id}</strong>
              <div className="small">Uploaded: {new Date(r.uploaded_at).toLocaleString()}</div>
            </div>
            <div style={{display:"flex",gap:8}}>
              <a className="btn-ghost" href={`${BASE_URL.replace("/api/v1","")}/${r.file_path}`} target="_blank" rel="noreferrer">Open file</a>
              <a className="btn" href={`${BASE_URL.replace("/api/v1","")}/${r.file_path}`} download>Download</a>
            </div>
          </div>

          <div style={{marginTop:8}}>
            <div><strong>Merchant:</strong> {safeGet(r.parsed_json, "merchant") ?? "—"}</div>
            <div><strong>Total:</strong> {safeGet(r.parsed_json, "total") ?? "—"}</div>
            <div className="small" style={{marginTop:6}}><strong>Raw OCR text:</strong></div>
            <div className="json-box">{r.raw_text || "(empty - OCR may still be running)"}</div>

            <div className="small" style={{marginTop:8}}><strong>Parsed JSON:</strong></div>
            <div className="json-box">{prettyJson(r.parsed_json)}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

function prettyJson(maybe) {
  if (!maybe) return "(none)";
  try {
    const obj = typeof maybe === "string" ? JSON.parse(maybe) : maybe;
    return JSON.stringify(obj, null, 2);
  } catch {
    return String(maybe);
  }
}
function safeGet(parsed_json, key) {
  if (!parsed_json) return null;
  try {
    const obj = typeof parsed_json === "string" ? JSON.parse(parsed_json) : parsed_json;
    return obj[key];
  } catch {
    return null;
  }
}

export default function App(){
  const [token, setToken] = useAuthToken();
  const [tab, setTab] = useState("home");

  async function handleLogout(){
    setToken("");
    alert("Logged out");
  }

  function onLogin(newToken){
    setToken(newToken);
    setTab("receipts");
  }

  return (
    <div className="app">
      <div className="header">
        <div className="logo">Finance App</div>
        <div className="nav">
          <button className="btn-ghost" onClick={()=>setTab("receipts")}>Receipts</button>
          <button className="btn-ghost" onClick={()=>setTab("upload")}>Upload</button>
          <button className="btn-ghost" onClick={()=>setTab("auth")}>Auth</button>
          <button className="btn-ghost" onClick={()=>setTab("transactions")}>Transactions</button>

          {token ? <button className="btn" onClick={handleLogout}>Logout</button> : null}
        </div>
      </div>

      <div className="grid">
        {tab === "auth" && <AuthForm onLogin={onLogin} />}
        {tab === "upload" && <ReceiptUpload token={token} onUploaded={()=>setTab("receipts")} />}
        {tab === "receipts" && <ReceiptsList token={token} />}
        {tab === "transactions" && <TransactionsView token={token} />}
        {tab === "home" &&
          <div className="card">
            <h2>Welcome</h2>
            <p className="small">Use the Auth tab to login or register. Then upload receipts and check the Receipts tab for OCR results.</p>
          </div>
        }
      </div>

      <div className="footer">Local dev frontend — talks to <code>{BASE_URL}</code></div>
    </div>
  );
}
