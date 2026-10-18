// Records the HomeHaat demo story on the THROWAWAY copy (localhost:3001, database homehaat_e2e) as stills + a timeline.
// The video maker (compose.html) animates the pointer, clicks, captions and transitions between these stills.
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { launch, openPage, signIn, setSession, sleep, SCRATCH, SITE } from "./cdp.mjs";

const DIR = `${SCRATCH}/video/frames`;
mkdirSync(DIR, { recursive: true });
const logins = JSON.parse(readFileSync(`${SCRATCH}/video_logins.json`, "utf8"));
const products = await (await fetch(`${SITE}/api/products/?limit=60`)).json();
const pid = (name) => products.find((p) => p.name.startsWith(name)).id;

const b = await launch(9342);
const page = await openPage(b);
const popups = [];
b.on((m) => { if (m.method === "Target.targetCreated" && m.params.targetInfo.type === "page" && m.params.targetInfo.openerId) popups.push(m.params.targetInfo); });
await b.send("Target.setDiscoverTargets", { discover: true });

const beats = [];
let n = 0;
async function frame(p = page) {
  const name = `${String(++n).padStart(2, "0")}.jpg`;
  writeFileSync(`${DIR}/${name}`, Buffer.from(await p.shot(), "base64"));
  return name;
}
/** One beat of the video: a still, how long, and optionally where the pointer moves (and clicks). */
const beat = (img, dur, extra = {}) => { beats.push({ img, dur, ...extra }); console.log("beat", beats.length, img, extra.caption?.title || ""); };
const cap = (eyebrow, title, accent) => ({ eyebrow, title, accent });
const RZP_MASK = [{ x: 380, y: 405, w: 326, h: 49, r: 10, fill: "#ffffff", text: "Using as +91 98XXX XXXXX", tx: 432, color: "#1d1d1d" }];

// ---------- Buyer ----------
const buyer = await signIn(logins.buyer.email, logins.buyer.password);
await setSession(page, buyer.session, buyer.csrf);
// Start from an empty bag (the demo buyer's own "Remove", through the app's API).
{
  const hdr = { Cookie: `homehaat_session=${buyer.session}; homehaat_csrftoken=${buyer.csrf}`, "X-CSRFToken": buyer.csrf };
  const cart = await (await fetch(`${SITE}/api/cart/`, { headers: hdr })).json();
  for (const g of cart.groups || []) for (const it of g.items || []) await fetch(`${SITE}/api/cart/items/${it.id}/`, { method: "DELETE", headers: hdr });
  console.log("bag emptied:", (cart.groups || []).flatMap((g) => g.items || []).length, "line(s)");
}

await page.go("/", 4000);
beat(await frame(), 4.2, { caption: cap("Handmade marketplace", "Made at home.", "Made for you."), zoom: [1, 1.04] });

await page.eval("window.scrollTo({ top: document.querySelector('h2') ? [...document.querySelectorAll('h2')].find(h => /fresh|newest/i.test(h.innerText)).getBoundingClientRect().top + scrollY - 150 : 1600 })");
await sleep(1800);
beat(await frame(), 3.6, { caption: cap("Real shops, real photos", "From home makers", "near you"), transition: "slide" });

await page.go("/explore?q=cake", 3500);
const card = await page.find("a", "chocolate truffle cake");
beat(await frame(), 3.2, { caption: cap("Search", "Find it in", "seconds"), cursor: card, click: true });

await page.go(`/product/${pid("Chocolate truffle cake")}`, 3500);
const add1 = await page.find("button", "^add to bag$");
beat(await frame(), 2.4, { caption: cap("Shop 1 · Lakshmi's Kitchen", "Add to", "your bag"), cursor: add1, click: true });
await page.clickAt(add1);
await sleep(1200);
beat(await frame(), 1.4, { cursor: add1 });

await page.go(`/product/${pid("Mango pickle")}`, 3500);
const add2 = await page.find("button", "^add to bag$");
beat(await frame(), 2.4, { caption: cap("Shop 2 · Amma's Pickles", "And from", "another maker"), cursor: add2, click: true });
await page.clickAt(add2);
await sleep(1200);
beat(await frame(), 1.3, { cursor: add2 });

await page.go("/cart", 3500);
const checkoutBtn = await page.find("a,button", "^checkout$");
beat(await frame(), 3.6, { caption: cap("One bag", "Two makers,", "one bag"), cursor: checkoutBtn, click: true });

await page.go("/checkout", 4000);
await page.clickAt(await page.find("button", "continue"));
await sleep(1500);
await page.eval("window.scrollTo(0, 0)");
const pay = await page.find("button", "^pay");
beat(await frame(), 3.8, { caption: cap("Checkout", "One payment,", "split per maker"), cursor: pay, click: true });
await page.clickAt(pay);
await page.waitFor("(() => { const f = document.querySelector('iframe.razorpay-checkout-frame, iframe[src*=razorpay]'); return f && f.getBoundingClientRect().width > 500; })()", 60_000, "Razorpay window");
await sleep(7000); // its payment options animate in
const nb = { x: 790, y: 379 };
beat(await frame(), 2.6, { caption: cap("Razorpay test mode", "Pay with", "Netbanking"), cursor: nb, click: true, masks: RZP_MASK });
await page.clickAt(nb);
await sleep(3500);
const bank = { x: 1287, y: 510 };
beat(await frame(), 1.8, { cursor: bank, click: true, masks: RZP_MASK });
await page.clickAt(bank);
for (let i = 0; i < 80 && !popups.length; i++) { await sleep(250); if (i === 40) await page.clickAt(bank); }
const pop = popups[0];
const { sessionId: popSession } = await b.send("Target.attachToTarget", { targetId: pop.targetId, flatten: true });
const ps = (m, p) => b.send(m, p, popSession);
await ps("Page.enable"); await ps("Runtime.enable");
await ps("Emulation.setDeviceMetricsOverride", { width: 960, height: 600, deviceScaleFactor: 1, mobile: false });
await sleep(3500);
const popName = `${String(++n).padStart(2, "0")}-bank.jpg`;
writeFileSync(`${DIR}/${popName}`, Buffer.from((await ps("Page.captureScreenshot", { format: "jpeg", quality: 92 })).data, "base64"));
const succ = (await ps("Runtime.evaluate", { returnByValue: true, expression: "(() => { const e = [...document.querySelectorAll('button,input[type=submit]')].find(x => /success/i.test(x.innerText || x.value)); const r = e.getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; })()" })).result.value;
// The bank page is shown as a window in the middle of the video (960x600 at offset 480,240).
beat(await frame(), 3.0, { caption: cap("Test bank page", "Netbanking →", "Success"), inset: { img: popName, x: 480, y: 240, w: 960, h: 600 }, cursor: { x: 480 + succ.x, y: 240 + succ.y }, click: true, masks: RZP_MASK });
await ps("Input.dispatchMouseEvent", { type: "mousePressed", x: succ.x, y: succ.y, button: "left", clickCount: 1 });
await ps("Input.dispatchMouseEvent", { type: "mouseReleased", x: succ.x, y: succ.y, button: "left", clickCount: 1 });
await page.waitFor("location.pathname.startsWith('/checkout/confirming')", 30_000, "confirming page");
await sleep(600);
beat(await frame(), 1.4, { caption: cap("Verified on the server", "Confirming", "payment…") });
await page.waitFor("location.pathname.startsWith('/orders/')", 90_000, "order page");
await sleep(3000);
await page.tidy();
const orderUrl = await page.eval("location.pathname");
beat(await frame(), 3.8, { caption: cap("Paid once", "Order placed:", "2 maker orders") });

// Cancel the pickle maker's part (it's still New).
const cancelBtn = await page.eval(`(() => { const blocks = [...document.querySelectorAll('section, article, div')].filter(d => /Amma's Pickles/.test(d.innerText) && /Cancel this part/.test(d.innerText));
  const blk = blocks.sort((a, z) => a.innerText.length - z.innerText.length)[0]; const btn = [...blk.querySelectorAll('button')].find(x => /cancel this part/i.test(x.innerText));
  btn.scrollIntoView({ block: 'center' }); return true; })()`);
await sleep(700);
const cancelAt = await page.eval(`(() => { const blk = [...document.querySelectorAll('section, article, div')].filter(d => /Amma's Pickles/.test(d.innerText) && /Cancel this part/.test(d.innerText)).sort((a, z) => a.innerText.length - z.innerText.length)[0];
  const r = [...blk.querySelectorAll('button')].find(x => /cancel this part/i.test(x.innerText)).getBoundingClientRect(); return { x: (r.x + r.width / 2) * 1.2, y: (r.y + r.height / 2) * 1.2 }; })()`);
beat(await frame(), 2.6, { caption: cap("Changed your mind?", "Cancel", "one maker's part"), cursor: cancelAt, click: true });
await page.clickAt(cancelAt);
await sleep(1200);
const yes = await page.find("button", "yes, cancel");
beat(await frame(), 2.6, { cursor: yes, click: true });
await page.clickAt(yes);
await sleep(5000);
await page.tidy();
beat(await frame(), 4.2, { caption: cap("Partial refund", "Refund started for", "just that part") });

// ---------- Seller (the demo baker; signed in with a session made on the throwaway copy) ----------
await setSession(page, logins.baker_session);
await page.go("/seller", 4500);
beat(await frame(), 3.8, { caption: cap("Seller side", "Every maker sees", "their own orders"), transition: "slide" });

await page.go("/seller/orders", 3500);
const prep = await page.find("button", "start preparing");
beat(await frame(), 2.6, { caption: cap("Shop orders", "One tap to the", "next step"), cursor: prep, click: true });
await page.clickAt(prep);
await sleep(2000);
await page.tidy();
beat(await frame(), 1.8, { cursor: prep });

await page.go("/seller/products/new", 3500);
const fileInput = await page.s("DOM.getDocument", { depth: -1 }).then(async ({ root }) => (await page.s("DOM.querySelector", { nodeId: root.nodeId, selector: "input[type=file]" })).nodeId);
await page.s("DOM.setFileInputFiles", { nodeId: fileInput, files: ["C:/Users/rasmi/homehaat/backend/catalog/showcase/red-velvet-cupcakes.jpg"] });
await sleep(2500);
await page.eval("(() => { const l = [...document.querySelectorAll('label')].find(x => /product name/i.test(x.innerText)); const i = l && (document.getElementById(l.htmlFor) || l.parentElement.querySelector('input')); i && i.focus(); return !!i; })()");
await page.type("Cupcakes");
await sleep(500);
const aiBtn = await page.find("button", "write listing with ai");
beat(await frame(), 2.6, { caption: cap("Add a product", "Upload a photo,", "let AI help"), cursor: aiBtn, click: true });
await page.clickAt(aiBtn);
let aiOk = false;
for (let attempt = 0; attempt < 4 && !aiOk; attempt++) {
  try { await page.waitFor("/use this/i.test(document.body.innerText)", 55_000, "AI suggestion"); aiOk = true; }
  catch { console.log("AI busy, retrying in 20 s"); await sleep(20_000); await page.clickAt(await page.find("button", "write listing with ai|try again")); }
}
await sleep(800);
const useThis = await page.find("button", "use this");
beat(await frame(), 4.6, { caption: cap("✨ AI listing helper", "Writes it from the photo,", "no invented facts"), cursor: useThis });

await page.go("/seller/products", 3500);
const oos = await page.eval(`(() => { const row = [...document.querySelectorAll('li, div')].filter(d => /Butter cookies/.test(d.innerText) && /Mark out of stock/.test(d.innerText)).sort((a, z) => a.innerText.length - z.innerText.length)[0];
  const r = [...row.querySelectorAll('button')].find(x => /mark out of stock/i.test(x.innerText)).getBoundingClientRect(); return { x: (r.x + r.width / 2) * 1.2, y: (r.y + r.height / 2) * 1.2 }; })()`);
beat(await frame(), 2.4, { caption: cap("Products", "Out of stock in", "one tap"), cursor: oos, click: true });
await page.clickAt(oos);
await sleep(2000);
beat(await frame(), 1.8, { cursor: oos });

await page.go("/seller", 3500);
await page.eval("window.scrollTo(0, 0)");
const sw = await page.find("[role=switch]");
beat(await frame(), 2.2, { caption: cap("Taking orders", "Holiday?", "Pause your shop"), cursor: sw, click: true });
await page.clickAt(sw);
await sleep(2000);
beat(await frame(), 2.4, { cursor: sw });
await page.clickAt(sw); // back on (throwaway copy), so the demo shop is open again
await sleep(1500);

writeFileSync(`${SCRATCH}/video/beats.json`, JSON.stringify({ beats, orderUrl }, null, 1));
console.log("done", beats.length, "beats,", beats.reduce((s, x) => s + x.dur, 0).toFixed(1), "s");
b.close();
process.exit(0);
