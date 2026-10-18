// Runs compose.html in headless Chrome. `node make.mjs preview 1.5 10 40` saves preview stills; `node make.mjs video` renders the MP4.
import { createServer } from "node:http";
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { extname, join } from "node:path";
import { launch, openPage, sleep, SCRATCH } from "./cdp.mjs";

const ROOT = `${SCRATCH}/video`;
const OUT = "C:/Users/rasmi/homehaat/docs/demo";
const [mode, ...times] = process.argv.slice(2);
const types = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".jpg": "image/jpeg" };
const names = { video: "homehaat-demo.mp4", poster: "homehaat-demo-poster.png", endcard: "homehaat-demo-endcard.png" };
const server = createServer((req, res) => {
  if (req.method === "POST" && req.url.startsWith("/out/")) {
    const parts = [];
    req.on("data", (d) => parts.push(d));
    req.on("end", () => {
      mkdirSync(OUT, { recursive: true });
      const name = names[req.url.slice(5)];
      writeFileSync(join(OUT, name), Buffer.concat(parts));
      console.log("saved", name, Math.round(Buffer.concat(parts).length / 1024), "KB");
      res.end("ok");
    });
    return;
  }
  const file = join(ROOT, decodeURIComponent(req.url.split("?")[0]));
  if (!existsSync(file)) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { "Content-Type": types[extname(file)] || "application/octet-stream" });
  res.end(readFileSync(file));
}).listen(9420);

const b = await launch(9343);
const page = await openPage(b);
await page.s("Emulation.clearDeviceMetricsOverride");
await page.go("http://127.0.0.1:9420/compose.html", 2500);
if (mode === "preview") {
  mkdirSync(`${ROOT}/preview`, { recursive: true });
  for (const t of times) {
    const url = await page.eval(`preview(${t})`);
    writeFileSync(`${ROOT}/preview/t${t}.jpg`, Buffer.from(url.split(",")[1], "base64"));
    console.log("preview", t);
  }
} else {
  const started = Date.now();
  await page.eval("window.__result = null; window.__error = null; makeVideo().then(r => window.__result = r, e => window.__error = String(e && e.stack || e)); true");
  let last = "";
  for (;;) {
    await sleep(5000);
    const st = await page.eval("JSON.stringify({ r: window.__result, e: window.__error, t: document.title })");
    const { r, e, t } = JSON.parse(st);
    if (t !== last) { console.log(t); last = t; }
    if (e) { console.log("ERROR", e); break; }
    if (r) { console.log(JSON.stringify(r), "in", Math.round((Date.now() - started) / 1000), "s"); break; }
  }
}
b.close();
server.close();
process.exit(0);
