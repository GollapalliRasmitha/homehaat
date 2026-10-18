# How the demo videos were made

**`homehaat-demo.mp4`** (the 60 s explainer, same structure and timing as Oppora's): `explainer.html`, rendered with
`PAGE=explainer.html node make.mjs video` (all drawn on a canvas, no recording).

**`homehaat-walkthrough.mp4`** (the 83 s screen walkthrough):

No video editor and no extra tools: only the installed Google Chrome, driven from Node.

1. **Throwaway copy only** (database `homehaat_e2e`, ports 3001/8001; see CLAUDE.md "Safety rule"):
   `manage.py throwaway_check`, then `flush`, `seed_categories`, `seed_showcase`, and `video_setup.py`
   (a fake demo buyer and a session for the demo baker). Nothing touches the real data or the live site.
2. **`capture.mjs`** walks the story in headless Chrome (1600×900 at 1.2× = 1920×1080): shopping from two makers,
   a real Razorpay **test** payment (Netbanking → test bank → Success), cancelling one maker's part (partial refund),
   then the seller side (orders, AI listing helper, out of stock, pausing the shop). It saves a still for every moment
   plus `beats.json` (how long each lasts, where the pointer moves and clicks, the caption). Phone numbers are masked
   on the pages, and the one inside Razorpay's own window is covered in the video.
3. **`make.mjs` + `compose.html`** draw every frame (intro, captions in the Oppora style with HomeHaat's fonts, the
   app in a window, pointer and clicks, the bank page, end card), encode H.264 with Chrome's WebCodecs, compose a
   simple original background tune (WebAudio, no licence needed) as AAC, and write the MP4 with `mp4.js` (run with `PREFIX=homehaat-walkthrough node make.mjs video`).

The scripts were run from a scratch folder; the paths at the top of `cdp.mjs`, `capture.mjs` and `make.mjs` point
there. Change them before running again.
