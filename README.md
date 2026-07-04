# Pokemon Ascended Heroes Stock Monitor

Checks Costco, Best Buy, Target, and Walmart for stock and sends you an
**email and/or free text message** the moment a configured product comes
back in stock. It does **not** buy anything automatically — alert-only, by design.

## 1. Get the code onto your Ubuntu machine

```bash
git clone <your-repo-url> pokemon-stock-monitor
cd pokemon-stock-monitor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 2. Fill in `config.yaml`

Open `config.yaml` and replace the placeholder SKUs/TCINs/URLs with the real
products you're tracking:

- **Best Buy**: find the SKU in the product URL — `bestbuy.com/site/.../6614130.p` → `6614130`
- **Target**: find the TCIN in the product URL — `target.com/p/.../-/A-89729512` → `89729512`
- **Walmart / Costco**: just paste the full product page URL

## 3. Set up credentials (`.env`)

```bash
cp .env.example .env
nano .env
```

- **Email**: if you use Gmail, create an **App Password** (not your real
  password) at https://myaccount.google.com/apppasswords, and put that in
  `SMTP_PASSWORD`.
- **Free text messages**: set `ALERT_SMS_GATEWAY` to
  `your10digitnumber@carriergateway.com` — e.g. `5551234567@vtext.com` for
  Verizon, `5551234567@txt.att.net` for AT&T, `5551234567@tmomail.net` for
  T-Mobile. This uses your carrier's free email-to-text bridge, so there's
  no signup or per-message cost. If your carrier's gateway is unreliable or
  discontinued, leave it blank and rely on email — or swap in Twilio later.
- **Best Buy API key** (recommended, free): sign up at
  https://developer.bestbuy.com/ and put the key in `BESTBUY_API_KEY`. Best
  Buy is the only retailer here with an official API, so it's also the most
  reliable checker of the four.

**Important:** add `.env` and `state.json` to `.gitignore` before pushing to
GitHub — never commit real credentials.

```bash
echo -e ".env\nstate.json\nvenv/\n__pycache__/" >> .gitignore
```

## 4. Test it once, manually

```bash
python3 monitor.py
```

You should see log lines for each retailer/product. It'll only email/text you
the first time a product flips from "out of stock" to "in stock" — running it
again immediately won't re-send while it's still in stock, so it's safe to
test repeatedly.

## 5. Run it automatically on your Ubuntu server

Two options — pick one.

### Option A: systemd timer (recommended for a server)

```bash
sudo cp deploy/pokemon-monitor.service /etc/systemd/system/
sudo cp deploy/pokemon-monitor.timer /etc/systemd/system/
sudo nano /etc/systemd/system/pokemon-monitor.service   # fix the paths/username
sudo systemctl daemon-reload
sudo systemctl enable --now pokemon-monitor.timer

# Check it's running:
systemctl list-timers | grep pokemon
journalctl -u pokemon-monitor.service -f
```

This runs one check pass every 10 minutes (edit `OnUnitActiveSec` in the
`.timer` file to change frequency) and logs to the system journal.

### Option B: simple cron job

```bash
crontab -e
```

Add:
```
*/10 * * * * cd /home/YOUR_USERNAME/pokemon-stock-monitor && venv/bin/python3 monitor.py >> monitor.log 2>&1
```

## Notes on reliability per retailer

| Retailer | Method                        | Reliability |
|----------|-------------------------------|--------------|
| Best Buy | Official public API           | High (needs free API key) |
| Target   | Undocumented public data API  | Medium — Target can change the endpoint shape without notice |
| Walmart  | HTML scraping                 | Lower — Walmart runs bot-detection and may serve a CAPTCHA page instead of the real one; the script detects this and reports it as "unknown" rather than a false negative |
| Costco   | HTML scraping                 | Lowest — no public API, and stock is often tied to your local warehouse/zip |

If Walmart/Target/Costco checks start silently failing, the site's markup or
API most likely changed — re-inspect the product page (`view-source:` in
your browser, or your browser's dev tools Network tab) to update the
selectors/fields in `retailers/*.py`.

## Being a good citizen about polling frequency

Checking every 10 minutes across 4 retailers is generally fine. Don't drop
the interval to seconds — that's how IPs get rate-limited or blocked, and
it won't meaningfully improve your odds during a real launch-day rush
anyway (those get decided by queue/inventory systems, not polling speed).

## What this does NOT do

On purpose, this script only detects and alerts — it doesn't add to cart,
check out, or store any payment info. If you decide later you want it to
go further, be aware most of these retailers' Terms of Service prohibit
automated purchasing, and enforcement varies (from order cancellation to
account bans).
