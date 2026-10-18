// Small Chrome DevTools helper for the HomeHaat video capture (throwaway copy on :3001 only).
import { spawn } from "node:child_process";

export const SCRATCH = "C:/Users/rasmi/AppData/Local/Temp/claude/C--Users-rasmi-homehaat/36531e30-b328-44a7-9d80-4ec86169daa7/scratchpad";
export const SITE = "http://localhost:3001";
export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
export const SCALE = 1.2; // 1600x900 CSS px -> 1920x1080 video px

export async function launch(port = 9340) {
  const chrome = spawn("C:/Program Files/Google/Chrome/Application/chrome.exe", [
    "--headless=new", `--remote-debugging-port=${port}`, `--user-data-dir=${SCRATCH}/chrome-video-${Date.now()}`,
    "--hide-scrollbars", "--no-first-run", "--no-default-browser-check", "--window-size=1600,900", "about:blank",
  ]);
  let version;
  for (let i = 0; i < 60 && !version; i++) { try { version = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json(); } catch { await sleep(250); } }
  const ws = new WebSocket(version.webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener("open", r));
  let id = 0;
  const pending = new Map();
  const listeners = new Set();
  ws.addEventListener("message", (e) => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } else listeners.forEach((f) => f(m));
  });
  const send = (method, params = {}, sessionId) => new Promise((res, rej) => {
    const n = ++id;
    const t = setTimeout(() => rej(new Error(`${method}: no answer in 60 s`)), 60_000);
    pending.set(n, (m) => { clearTimeout(t); m.error ? rej(new Error(`${method}: ${m.error.message}`)) : res(m.result); });
    ws.send(JSON.stringify({ id: n, method, params, ...(sessionId ? { sessionId } : {}) }));
  });
  const on = (f) => { listeners.add(f); return () => listeners.delete(f); };
  const close = () => { try { ws.close(); } catch {} chrome.kill(); };
  return { send, on, close };
}

/** A page session (a tab), with helpers. */
export async function openPage(b) {
  const { targetId } = await b.send("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await b.send("Target.attachToTarget", { targetId, flatten: true });
  const s = (method, params) => b.send(method, params, sessionId);
  await s("Page.enable");
  await s("Runtime.enable");
  await s("Network.enable");
  await s("Emulation.setDeviceMetricsOverride", { width: 1600, height: 900, deviceScaleFactor: SCALE, mobile: false });
  const page = {
    targetId, sessionId, s,
    async eval(expression) {
      const r = await s("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (r.exceptionDetails) throw new Error("eval: " + (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
      return r.result.value;
    },
    async go(path, settle = 3000) {
      const loaded = new Promise((r) => { const off = b.on((m) => { if (m.sessionId === sessionId && m.method === "Page.loadEventFired") { off(); r(); } }); });
      await s("Page.navigate", { url: path.startsWith("http") ? path : SITE + path });
      await Promise.race([loaded, sleep(30_000)]);
      await sleep(settle);
      await page.tidy();
    },
    /** Wait until fn (a JS expression) is truthy in the page. */
    async waitFor(expr, ms = 30_000, label = expr) {
      const end = Date.now() + ms;
      while (Date.now() < end) { try { if (await page.eval(expr)) return; } catch {} await sleep(250); }
      throw new Error("timed out waiting for " + label);
    },
    /** Centre of the first element matching a CSS selector whose text matches (in video px). */
    async find(selector, text) {
      const r = await page.eval(`(() => { const re = ${text ? `new RegExp(${JSON.stringify(text)}, 'i')` : "null"};
        const el = [...document.querySelectorAll(${JSON.stringify(selector)})].find(e => (!re || re.test(e.innerText || e.value || e.getAttribute('aria-label') || '')) && e.getClientRects().length);
        if (!el) return null; let b = el.getBoundingClientRect(); if (b.top < 70 || b.bottom > innerHeight - 20) { el.scrollIntoView({ block: 'center' }); b = el.getBoundingClientRect(); }
        return { x: b.x + b.width / 2, y: b.y + b.height / 2 }; })()`);
      if (!r) throw new Error(`not found: ${selector} ${text || ""}`);
      await sleep(400);
      return page.eval(`(() => { const re = ${text ? `new RegExp(${JSON.stringify(text)}, 'i')` : "null"};
        const el = [...document.querySelectorAll(${JSON.stringify(selector)})].find(e => (!re || re.test(e.innerText || e.value || e.getAttribute('aria-label') || '')) && e.getClientRects().length);
        const b = el.getBoundingClientRect(); return { x: (b.x + b.width / 2) * ${SCALE}, y: (b.y + b.height / 2) * ${SCALE} }; })()`);
    },
    /** A real mouse click at video-px coordinates (works inside iframes too). */
    async clickAt(p) {
      const x = p.x / SCALE, y = p.y / SCALE;
      await s("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
      await s("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
      await s("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
    },
    async type(text) { await s("Input.insertText", { text }); },
    async tidy() { try { await page.eval(TIDY); } catch {} },
    async shot() {
      await page.tidy();
      const { data } = await s("Page.captureScreenshot", { format: "jpeg", quality: 92 });
      return data;
    },
  };
  return page;
}

// Hide the Next.js dev badge; mask anything that looks like an Indian mobile number (the demo data is fake anyway).
export const TIDY = `(() => {
  document.querySelectorAll('nextjs-portal').forEach(n => n.remove());
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n; (n = w.nextNode());) n.nodeValue = n.nodeValue.replace(/(\\+91[ -]?)?\\b[6-9]\\d{4}[ -]?\\d{5}\\b/g, '98XXX XXXXX');
  document.querySelectorAll('input').forEach(i => { if (/^(\\+91)?[6-9]\\d{9}$/.test(i.value.replace(/\\s/g, ''))) i.value = '98XXX XXXXX'; });
  return true;
})()`;

export async function signIn(email, password) {
  const csrfRes = await fetch(`${SITE}/api/auth/csrf/`);
  const csrf = /homehaat_csrftoken=([^;]+)/.exec(csrfRes.headers.getSetCookie().join(";"))[1];
  const r = await fetch(`${SITE}/api/auth/signin/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrf, Cookie: `homehaat_csrftoken=${csrf}` },
    body: JSON.stringify({ email, password }),
  });
  if (!r.ok) throw new Error("sign in failed " + r.status);
  return { session: /homehaat_session=([^;]+)/.exec(r.headers.getSetCookie().join(";"))[1], csrf };
}

export async function setSession(page, session, csrf) {
  await page.s("Network.clearBrowserCookies");
  await page.s("Network.setCookie", { name: "homehaat_session", value: session, domain: "localhost", path: "/" });
  if (csrf) await page.s("Network.setCookie", { name: "homehaat_csrftoken", value: csrf, domain: "localhost", path: "/" });
}
