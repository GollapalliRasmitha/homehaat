# Razorpay test mode: setup (about 10 minutes)

HomeHaat only ever uses **Razorpay Test Mode**. No real money moves, and you don't need KYC or a bank account for test mode.
The server refuses to start if a key doesn't begin with `rzp_test_`.

## 1. Create a free Razorpay account

1. Go to <https://dashboard.razorpay.com/signup> and sign up with your email.
2. You can skip business details / KYC for now. Test mode works without them.

## 2. Switch to Test Mode

At the top of the dashboard there's a **Test Mode / Live Mode** switch. Make sure it says **Test Mode**.

## 3. Generate test API keys

1. In the dashboard open **Account & Settings → API Keys** (on some layouts: **Settings → API Keys**).
2. Click **Generate Test Key**.
3. You'll see a **Key Id** (starts with `rzp_test_`) and a **Key Secret**.
   **The secret is shown only once**, so copy it now. If you lose it, just regenerate.

## 4. Put the keys in `.env` (never in chat, never in git)

Open `homehaat\.env` in a text editor and fill in:

```
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
```

`.env` is in `.gitignore`, so it is never committed. The Key Secret stays on the Django server; the browser only ever sees the Key Id (which is public by design).

Then close the **HomeHaat API :8000** window and run `start-homehaat.ps1` again (or restart Django) so it reads the new keys.

## 5. Make a test payment

1. Sign up as a seller → **Open your shop** → **Add a product** (e.g. a ₹450 cake).
2. Sign out, sign up as a buyer, add the cake to your bag → **Checkout** → add an address → **Pay ₹490**.
3. In the Razorpay window, use a test card from Razorpay's own list:
   <https://razorpay.com/docs/payments/payments/test-card-details/>
   Any future expiry date and any CVV work. On the bank page, click **Success**.
   (UPI also works in test mode with the test UPI id `success@razorpay`.)
4. You'll see **Confirming payment…**, then **Order placed**.
5. Sign in as the seller → **My shop**: the paid order is listed with the buyer's address.

## How the payment gets confirmed locally

Razorpay normally tells our server "this payment was captured" by calling a **webhook**. It can't call `localhost`,
so locally HomeHaat uses the backup path you chose: after you pay, the browser forwards Razorpay's **signed** reply to
`POST /api/payments/verify/`. The server checks the signature with the Key Secret, asks Razorpay how much was really
captured, and only then marks the order paid. See "How it works" in `CLAUDE.md`.

## Later (Stage 8): the webhook

Once the API has a public URL (Render), add a webhook in the dashboard:

1. **Account & Settings → Webhooks → Add New Webhook**
2. URL: `https://<your-api>/api/payments/webhook/`
3. Secret: make up a long random string and also put it in `.env` / Render as `RAZORPAY_WEBHOOK_SECRET`
4. Active event: **payment.captured**

The webhook then becomes the source of truth, and the verify endpoint stays as a fallback.
