# Putting HomeHaat online (free)

This guide puts HomeHaat on the internet using only free plans. You don't need to write any code. Allow about an hour
the first time.

| Part | Service (free plan) | What it does |
|---|---|---|
| Database | **Neon** | stores users, shops, products, orders |
| Photos | **Cloudinary** | stores product photos, shop covers and (privately) custom request photos |
| API (Django) | **Render**, free web service | the server: checkout, payments, seller tools |
| Website (Next.js) | **Vercel**, Hobby | the pages people see |
| Scheduled jobs | **GitHub Actions** | every hour: gives back stock from abandoned checkouts and retries refunds |

> **Money rule:** every step below is free. If any website asks for a card or a paid plan, **stop and tell
> Claude** before clicking anything. Payments stay in Razorpay **test mode** (keys starting `rzp_test_`).

> **Secrets rule:** you'll copy secret values (passwords, keys) from one dashboard into another. Paste them only into
> those dashboards. Never into chat, GitHub files, or a document.

Dashboards change their buttons now and then. If a label is a little different, look for the closest match.

---

## Step 0. Make three random secrets

You need three long random values. Each one is a "shared password" between two services. Make them now and keep
them in a safe place (a password manager, or a private note) until you've finished.

Open **PowerShell** (Start menu → type PowerShell) and run this line **three times**. Each run prints a new value:

```powershell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 48 | ForEach-Object { [char]$_ })
```

Label them:

1. **PROXY_SECRET**: shared by Render and Vercel
2. **JOBS_SECRET**: shared by Render and GitHub
3. **RAZORPAY_WEBHOOK_SECRET**: shared by Render and Razorpay

Also choose an **admin email and password** for the Django admin (at least 12 characters, not a password you use
anywhere else).

---

## Step 1. Neon (the database)

1. Go to <https://neon.tech> and **Sign up** (you can use "Continue with GitHub").
2. Create a project:
   - **Project name:** `homehaat`
   - **Postgres version:** the newest one offered
   - **Region:** **AWS Asia Pacific (Singapore)** (closest to India, and the same region as the API in step 3)
3. When the project is ready, click **Connect** (top right of the project page).
4. Turn **Connection pooling** off (either works; "off" is simpler), then **copy the connection string**. It
   looks like `postgresql://neondb_owner:••••@ep-something.ap-southeast-1.aws.neon.tech/neondb?sslmode=require`.
   This is your **DATABASE_URL**. It contains the database password: treat it as a secret.

Free plan note: Neon's database goes to sleep after 5 quiet minutes and wakes up in under a second. You won't notice.

---

## Step 2. Cloudinary (photos)

1. Go to <https://cloudinary.com> and **Sign up for free**.
2. If it asks what you'll use it for, any answer is fine (e.g. "Developer").
3. Open the **Dashboard** (or **Settings → API Keys**). Find **API environment variable**. It looks like
   `CLOUDINARY_URL=cloudinary://123456789012345:abcdefghijk@your-cloud-name`.
4. Copy only the part **starting at `cloudinary://`**. This is your **CLOUDINARY_URL** (a secret).

What HomeHaat does with it:

- product photos and shop covers are public and load fast from Cloudinary's servers;
- custom request photos are uploaded as **authenticated** (private) images. Cloudinary refuses every normal link to
  them. Only HomeHaat's server can read them, and only shows them to that buyer and that maker.

---

## Step 3. Render (the API)

1. Go to <https://render.com> and **Sign up with GitHub**.
2. When Render asks which repositories it may see, allow **GollapalliRasmitha/homehaat** (it's private, so Render
   needs permission).
3. In the Render dashboard click **New +** → **Blueprint**.
4. Pick the **homehaat** repository → **Connect**. Render reads the file `render.yaml` and shows one service:
   **homehaat-api**, plan **Free**.
5. Render now asks for the values it can't know. Fill them in:

   | Name | What to paste |
   |---|---|
   | `DATABASE_URL` | the Neon connection string (step 1) |
   | `FRONTEND_ORIGIN` | `https://homehaat.vercel.app` for now (you'll correct it in step 4 if Vercel gives a different address). No slash at the end. |
   | `PROXY_SECRET` | secret 1 from step 0 |
   | `JOBS_SECRET` | secret 2 from step 0 |
   | `CLOUDINARY_URL` | from step 2 |
   | `RAZORPAY_KEY_ID` | your Razorpay **test** Key Id (starts `rzp_test_`, see `docs/razorpay-setup.md`) |
   | `RAZORPAY_KEY_SECRET` | your Razorpay test Key Secret |
   | `RAZORPAY_WEBHOOK_SECRET` | secret 3 from step 0 |
   | `GEMINI_API_KEY` | your HomeHaat Gemini key, or leave empty (see `docs/ai-setup.md`) |
   | `DJANGO_ADMIN_EMAIL` | the admin email you chose |
   | `DJANGO_ADMIN_PASSWORD` | the admin password you chose |

   You don't need to fill in the others: `DJANGO_SECRET_KEY` is made by Render, and `DJANGO_DEBUG=false`,
   `AI_ENABLED=true`, `PYTHON_VERSION` are already set by `render.yaml`.
6. Click **Apply** (or **Deploy Blueprint**). Render builds the API. This takes a few minutes. Click the service and
   open **Logs** (or **Events**) to watch. Near the end you should see lines like:
   - `Applying …  OK` (the database tables being created)
   - `8 categories ready.`
   - `Admin account … created.`
7. When the service says **Live**, find its address at the top of the page, for example
   `https://homehaat-api.onrender.com`. This is your **API address**. Open
   `https://<your API address>/api/health/` in your browser. You should see `{"ok": true}`.

If the build fails, the last red lines in the log say why. The most common one is
`DJANGO_ADMIN_PASSWORD is too weak`: choose a longer password in **Environment**, then **Manual Deploy → Deploy
latest commit**.

Free plan note: Render's free server **sleeps after 15 minutes with no visitors**. The next visitor waits up to
about a minute while it wakes up. HomeHaat handles this: pages try again by themselves, and the Pay button first
says **"Waking up the server…"** and only creates the order once the server answers.

---

## Step 4. Vercel (the website)

1. Go to <https://vercel.com> and **Sign up** → **Continue with GitHub**. Choose the **Hobby** (free) plan.
2. **Add New… → Project**. Find **homehaat** and click **Import** (if it isn't listed, click **Adjust GitHub App
   Permissions** and allow the repository).
3. On the "Configure Project" page:
   - **Root Directory:** click **Edit** and choose **`frontend`**.
   - **Framework Preset:** Next.js (it's detected by itself).
   - Open **Environment Variables** and add:

     | Name | Value |
     |---|---|
     | `API_INTERNAL_URL` | your API address from step 3, e.g. `https://homehaat-api.onrender.com` (no slash at the end) |
     | `PROXY_SECRET` | secret 1 from step 0 (the same value as on Render) |
4. Click **Deploy**. After a couple of minutes you get a page with your website's address, for example
   `https://homehaat.vercel.app` (Vercel adds something to the name if it's taken).
5. **If the address isn't exactly `https://homehaat.vercel.app`:** go back to Render → **homehaat-api** →
   **Environment** → edit **`FRONTEND_ORIGIN`** to your real Vercel address (no slash at the end) → **Save**.
   Render redeploys by itself. Until this matches, signing in shows a "CSRF" error.

Note: `API_INTERNAL_URL` is read when the website is built. If you ever change it, go to **Deployments** → the
newest one → **⋯** → **Redeploy**.

Vercel's Hobby plan is for personal, non-commercial projects. That fits HomeHaat while it's a portfolio project in
test mode. If it ever takes real money, Vercel's terms need the paid plan (ask first, as always).

---

## Step 5. Sign in to the admin, then remove the password from Render

1. Open `https://<your API address>/admin/` and sign in with the admin email and password.
2. It works? Then in Render → **homehaat-api** → **Environment**, **delete `DJANGO_ADMIN_PASSWORD`** and save. The
   admin account stays; the password just isn't kept in the dashboard any more. (Keep `DJANGO_ADMIN_EMAIL`. Without
   the password, the deploy step simply skips the admin.)

The admin is where you can see everything and retry a delayed refund (**Refunds → select → Retry**).

---

## Step 6. GitHub (the hourly jobs)

1. Open <https://github.com/GollapalliRasmitha/homehaat> → **Settings** → **Secrets and variables** → **Actions**.
2. **Variables** tab → **New repository variable**:
   - Name `HOMEHAAT_API_URL`, value: your API address (e.g. `https://homehaat-api.onrender.com`).
3. **Secrets** tab → **New repository secret**:
   - Name `HOMEHAAT_JOBS_SECRET`, value: secret 2 from step 0 (the same as `JOBS_SECRET` on Render).
4. Check it: **Actions** tab → **Scheduled jobs** (left) → **Run workflow** → **Run workflow**. After about a minute
   it shows a green tick. Click it to see `{"ok": true, "expire": {"released": 0}, "refunds": {...}}`.

From now on it runs every hour by itself.

**Why every hour, and why that's enough:** the jobs give back stock from checkouts nobody paid for (after 15
minutes), and resend refunds Razorpay couldn't take the first time. Render's own scheduler costs money, so GitHub
runs them for free. Your repository is private, and private repositories get 2,000 free GitHub minutes a month;
every run counts as at least a minute, so "every 5 minutes" (8,640 runs) would run out, but "every hour" (about
720–1,440 minutes) fits. And the stock doesn't actually wait an hour: **every time someone uses the site** (at most
once a minute), and **at the start of every checkout**, HomeHaat also gives back any expired holds. So a buyer is
never blocked by someone else's abandoned checkout. If you ever make the repository public (unlimited minutes), the
schedule in `.github/workflows/scheduled-jobs.yml` can be changed to every 5 minutes.

---

## Step 7. Razorpay webhooks (payments and refunds)

The webhook is how Razorpay tells HomeHaat "this payment was captured" or "this refund was processed", even if the
buyer closes their browser.

1. Open the Razorpay Dashboard and make sure it says **Test Mode** (top of the page).
2. **Account & Settings** → **Webhooks** → **Add New Webhook**.
3. Fill in:
   - **Webhook URL:** `https://<your API address>/api/payments/webhook/` (the **Render** address, with the slash at
     the end)
   - **Secret:** secret 3 from step 0 (the same as `RAZORPAY_WEBHOOK_SECRET` on Render)
   - **Alert email:** your email
   - **Active events:** tick **`payment.captured`**, **`refund.processed`** and **`refund.failed`**
4. **Create Webhook**.

If the server is asleep when Razorpay calls, Razorpay tries again later by itself, and the "Confirming payment…" page
also checks the payment directly, so nothing is lost.

---

## Step 8. Try it

1. Open your Vercel address. The first visit after a quiet spell may take up to a minute (the API waking up).
2. Sign up as a seller, **Open your shop**, add a product with a photo. The photo now comes from
   `res.cloudinary.com`.
3. In a different browser (or a private window), sign up as a buyer, add it to the bag, and pay with a test card
   (`docs/razorpay-setup.md`). You should see **Confirming payment…**, then **Order placed**.
4. In Razorpay → **Webhooks**, the webhook shows a successful `payment.captured` delivery.
5. As the buyer, **Cancel this part** of the order. The page says the refund started. In Razorpay (test mode) →
   **Refunds**, the refund is listed, and a `refund.processed` webhook arrives.
6. Custom request photos: as the buyer, send a custom request with a photo. The seller sees it; signed out, the
   photo's address answers "not found".

---

## Demo shops (optional): fill the live site for visitors

`manage.py seed_showcase` adds 8 demo shops and 20 products with photos (the ones in the README screenshots). It only
**creates** what's missing. It never changes or deletes any user, shop, product, order or refund, and running it
again adds nothing. The demo owners have `@example.test` emails and passwords nobody can use, so nobody can sign in
as them. Each shop's description starts with "Demo shop with sample products." No orders or reviews are made up.

It runs during a deploy only while `SEED_SHOWCASE` is `true`:

1. Render → **homehaat-api** → **Environment** → **Add Environment Variable**: key `SEED_SHOWCASE`, value `true`
   → **Save, rebuild, and deploy** (or **Save changes**, then **Manual Deploy → Deploy latest commit**).
2. In **Logs** (or **Events** → the deploy), look for `Showcase: 8 shop(s) and 20 product(s) created.`
3. Open the website: the home page, **Makers** and **Explore** now show the shops and products with photos.
4. Switch it off: **Environment** → delete `SEED_SHOWCASE` (or set it to `false`) → **Save changes**. Leaving it on
   is harmless (later deploys print `0 shop(s) and 0 product(s) created`), but off is tidier.

To hide a demo shop later, use Django admin (Sellers → the shop → untick "Is active").

## Which value goes where

| Name | Render | Vercel | GitHub | Razorpay | Where it comes from |
|---|---|---|---|---|---|
| `DATABASE_URL` | ✓ | | | | Neon → Connect |
| `CLOUDINARY_URL` | ✓ | | | | Cloudinary → API environment variable |
| `FRONTEND_ORIGIN` | ✓ | | | | your Vercel address |
| `DJANGO_SECRET_KEY` | ✓ (made by Render) | | | | automatic |
| `DJANGO_DEBUG` = `false` | ✓ (already set) | | | | `render.yaml` |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` | ✓ | | | | Razorpay → API Keys (test mode) |
| `RAZORPAY_WEBHOOK_SECRET` | ✓ | | | ✓ (webhook "Secret") | step 0, secret 3 |
| `PROXY_SECRET` | ✓ | ✓ | | | step 0, secret 1 |
| `JOBS_SECRET` | ✓ | | ✓ as `HOMEHAAT_JOBS_SECRET` (secret) | | step 0, secret 2 |
| API address | (Render shows it) | ✓ as `API_INTERNAL_URL` | ✓ as `HOMEHAAT_API_URL` (variable) | ✓ in the webhook URL | Render, top of the service page |
| `AI_ENABLED` (`true` in `render.yaml`), `GEMINI_API_KEY` | ✓ | | | | `docs/ai-setup.md`; the AI button shows only when the key is set too |
| `DJANGO_ADMIN_EMAIL`, `DJANGO_ADMIN_PASSWORD` | ✓ (remove the password after step 5) | | | | you choose |
| `SEED_SHOWCASE` = `true` | ✓ (only while you want the demo shops created; then delete it) | | | | you choose |

All the names are also listed (without values) in `.env.example` (API) and `frontend/.env.example` (website).

---

## Updating the site later

Every push to `main` on GitHub redeploys both Render and Vercel by themselves. New database changes are applied
during Render's build (it only adds; it never deletes data). If a build fails, the old version keeps running.

## Free plan limits (what to expect)

| Service | Free limit | What happens at the limit |
|---|---|---|
| Render | 750 server hours a month (one server running all month is ~744) | it sleeps after 15 quiet minutes anyway, so this is fine for one server; a second free Render server would share the hours |
| Neon | 0.5 GB of data; limited compute hours a month | the database sleeps when quiet, which saves hours |
| Cloudinary | 25 "credits" a month (storage + traffic + resizing) | thousands of photos and views before it matters |
| Vercel Hobby | generous traffic; personal non-commercial use | — |
| GitHub Actions | 2,000 minutes a month for a private repository | the hourly jobs use about 720–1,440 |

## If something goes wrong

| What you see | Likely cause | Fix |
|---|---|---|
| Pages say "HomeHaat's server is just waking up" | Render was asleep | wait a minute and try again |
| Signing in says "CSRF verification failed" | `FRONTEND_ORIGIN` on Render isn't exactly your Vercel address | correct it (https, no slash at the end), save |
| Every page says it can't reach HomeHaat | `API_INTERNAL_URL` missing or wrong on Vercel | correct it, then **Redeploy** |
| Photos disappear after a while | `CLOUDINARY_URL` not set on Render (the build log warns about it) | set it; upload the photos again |
| The GitHub run shows a red ✗ with "Not allowed" | the GitHub secret and Render's `JOBS_SECRET` differ | paste the same value in both |
| Razorpay webhook deliveries fail with 400 | the webhook secret differs from `RAZORPAY_WEBHOOK_SECRET` | paste the same value in both |
| Build log: "HomeHaat only runs Razorpay in test mode" | a live key (`rzp_live_…`) was pasted | use the test keys |
