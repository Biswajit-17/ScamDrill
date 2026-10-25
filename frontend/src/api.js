/* API client. Calls the FastAPI backend on the same origin (proxied in dev
via Vite, served static in prod). */

const BASE = ""

async function request(path, opts = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...opts.headers },
    ...opts,
  })
  if (!res.ok) {
    const detail = (await res.json().catch(() => ({}))).detail || res.statusText
    throw new Error(detail || `Request failed: ${res.status}`)
  }
  return res.json()
}

export const api = {
  listScenarios: () => request("/api/scenarios"),
  health: () => request("/api/healthz"),
  callStart: (body) => request("/api/call/start", { method: "POST", body: JSON.stringify(body) }),
  callTurn: (body) => request("/api/call/turn", { method: "POST", body: JSON.stringify(body) }),
  callDecision: (body) => request("/api/call/decision", { method: "POST", body: JSON.stringify(body) }),
  callDebrief: (body) => request("/api/debrief", { method: "POST", body: JSON.stringify(body) }),
}