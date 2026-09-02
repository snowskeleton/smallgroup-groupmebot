# Setting up a bot

Start-to-finish instructions for wiring up a new instance — a test bot, or a
second bot for another group. Roughly 30–45 minutes the first time.

You will end up with four things: a GroupMe bot, a Google service account, a
spreadsheet, and a server running the code.

---

## 0. What you need first

* A **publicly reachable HTTPS URL** pointing at the machine you'll run this on.
  GroupMe will not deliver messages to plain HTTP or to `localhost`. A reverse
  proxy (Caddy, nginx, Cloudflare Tunnel) or an ngrok tunnel all work. Have this
  URL in hand before you start — several steps need it. These instructions call
  it `https://bot.example.com`.
* A GroupMe account that is a **member of the target group**.
* A Google account.
* Optionally, an SMTP account the bot can send mail from. Without it the bot
  still posts to GroupMe; it just can't send the email digest, and the
  dashboard's magic-link login won't work.
* `docker` and `git`.

---

## 1. GroupMe: register the bot

1. Go to <https://dev.groupme.com/bots> and sign in.
2. **Create Bot**. Pick the target group.
3. Set **Name** to whatever you like. Write it down — this is `BOT_NAME`, and it
   has to match exactly, since the bot uses it to recognize its own messages and
   avoid replying to itself.
4. Set **Callback URL** to:

   ```
   https://bot.example.com/new_event
   ```

   This is the webhook. GroupMe POSTs every group message here.
5. Submit. The bot list now shows a **Bot ID** — that's `BOT_ID`.

The bot learns which group it belongs to from the first message it receives, so
there is no group ID to copy anywhere.

## 2. GroupMe: register the application

Separate from the bot. This is what lets the bot delete its own messages and
create calendar events — the bot token alone can't do either.

1. Go to <https://dev.groupme.com/applications> → **Create Application**.
2. Set **Callback URL** to:

   ```
   https://bot.example.com/oauth/callback
   ```

   This must match `REDIRECT_URI` below **character for character**, trailing
   slash included, or the OAuth handshake fails with an unhelpful error.
3. After saving, open the application's Settings. The long string at the end of
   the URL is `CLIENT_ID`.
4. Back on <https://dev.groupme.com>, click **Access Token** in the top right.
   That value is `CLIENT_SECRET`.

## 3. Google: service account and API access

The bot reads and writes the spreadsheet as a robot user with its own email
address.

1. Go to <https://console.cloud.google.com/> and create or select a project.
2. **APIs & Services → Library**, search for **Google Sheets API**, and click
   **Enable**. Missing this is the single most common failure, and it surfaces
   as a permissions error that looks like a sharing problem.
3. **APIs & Services → Credentials → Create Credentials → Service Account**.
   Name it anything. You can skip the optional role and user-access steps.
4. Open the new service account → **Keys → Add Key → Create new key → JSON**.
5. Save the downloaded file as `credentials.json` in the project root.
6. Open it and find `client_email`. It looks like:

   ```
   yourbot@your-project-123456.iam.gserviceaccount.com
   ```

   **Copy this address.** Step 5 needs it, and it's the thing everyone forgets.

One service account can serve any number of bots and sheets. If you're setting
up a second bot, reuse the existing `credentials.json` rather than making
another.

## 4. Configure

```bash
git clone https://github.com/snowskeleton/smallgroup-groupmebot.git
cd smallgroup-groupmebot
cp .env.example .env
```

Fill in `.env`:

| Variable | Required | Where it comes from |
|---|---|---|
| `BOT_ID` | yes | Step 1 |
| `BOT_NAME` | yes | Step 1 — must match exactly |
| `CLIENT_ID` | yes | Step 2 |
| `CLIENT_SECRET` | yes | Step 2 (your personal access token) |
| `REDIRECT_URI` | yes | `https://bot.example.com/oauth/callback` |
| `SMTP_SERVER` | for email | Your mail provider |
| `SMTP_PORT` | | `587` for STARTTLS (default) |
| `SMTP_USERNAME` | for email | Mail account |
| `SMTP_PASSWORD` | for email | Mail account — use an app password if available |
| `FROM_ADDRESS` | for email | Address the group sees on emails |
| `DASHBOARD_URL` | for dashboard | `https://bot.example.com` — scheme included, no trailing slash, no path |
| `DB_PATH` | | Defaults to `messages.db` |
| `CREDENTIALS_PATH` | | Defaults to `credentials.json` |
| `TIMEZONE` | | Defaults to `America/New_York` |

Only the five GroupMe values gate startup; the app refuses to boot without them
and names the ones you missed. Leaving the SMTP block empty is fine for a test
bot — email attempts fail with a clear message in the logs instead of taking the
whole bot down.

`.env`, `credentials.json`, and the database are all gitignored. Don't commit
them.

> Older deployments kept these in a `bot_secrets.py`. That still works as a
> fallback, but environment variables win where both are set, and the Python
> file is deprecated — one image serving several groups needs env files.

## 5. Create the spreadsheet

### Cloning an existing sheet

**Sharing does not survive a copy.** The new file belongs to whoever made it,
and the service account loses access. This is the step that breaks silently, so
do it deliberately:

1. Open the sheet you're copying → **File → Make a copy**.
2. In the copy, **Share** → paste the service account address from step 3 →
   set it to **Editor** → uncheck "Notify people" → **Share**.

   Editor, not Viewer. The bot appends rows and fills assignments; read-only
   access will fail on the first scheduled run rather than at startup.
3. Delete the inherited data you don't want. The copy carries over every row of
   the original's `Schedule`, and past meetings from someone else's group will
   confuse the rotation. Clear everything below the header row.
4. Update the `People` tab for the new group, and `Config` for its meeting day
   and time.
5. Copy the new sheet's URL — it is **not** the URL of the original.

### Starting from scratch

Create an empty sheet, share it with the service account as **Editor**, and the
tabs can be built from the layout described in `README.md`. The sheet's own
`README` tab documents the format for whoever maintains it.

## 6. Run it

```bash
docker compose up -d
```

Then point your reverse proxy at port **5001**.

Check it's alive:

```bash
curl https://bot.example.com/healthcheck
```

Should return `ok`. If it doesn't, `docker compose logs -f groupmebot` will
usually say why — a missing value from step 4 is the most likely cause, and it
names the offending variable.

> **Don't add gunicorn workers.** The weekly-post scheduler is a background
> thread inside the app, and gunicorn forks a whole process per worker — so
> `-w 4` means four schedulers, and the group gets four copies of every post.
> The Dockerfile runs `-w 1 --threads 8` instead: one scheduler, but eight
> concurrent requests, which is what you actually want for an app that spends
> its time waiting on the Sheets and GroupMe APIs.

### Running more than one group

A single instance serves exactly one group — the GroupMe bot ID it posts to is
fixed at startup, and its settings are a flat table with one sheet link. To
serve another group, run a second container.

`docker-compose.yml` has a commented-out second service showing the shape. Each
instance needs:

* its **own env file** (different `BOT_ID`, `BOT_NAME`, `REDIRECT_URI`)
* its **own database volume** — two containers sharing one `messages.db` will
  overwrite each other's sheet link and schedule
* its **own public callback URL**, so GroupMe can tell them apart

They can share the image, the `credentials.json`, and the Google service
account. Only the spreadsheet differs.

## 7. Wire it up from GroupMe

In the group chat:

1. ```
   /ping
   ```
   Expect `Pong!`. If nothing happens, the webhook from step 1 isn't reaching
   the server — check the callback URL and your proxy.

2. ```
   /schedule link https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit
   ```

3. ```
   /schedule show
   ```
   Expect the next few meetings. `NoSheetLink` means step 2 didn't take; a
   permissions error means the sheet isn't shared with the service account, or
   the Sheets API isn't enabled.

4. ```
   /authenticate
   ```
   Follow the link **as a group admin or owner**. This grants the message-delete
   and calendar-event permissions. Optional — everything else works without it.

5. ```
   /schedule set 0 9 * * 1
   ```
   A cron expression for the weekly post. This example is Mondays at 9am. The
   bot's clock is **America/New_York**, hardcoded in `utils.py`; change it there
   if your group is elsewhere.

6. ```
   /schedule generate
   ```
   Fills the sheet with dates and near-term assignments. Open the sheet and
   confirm it looks right before leaving it to run on its own.

`/help` lists everything.

## 8. Dashboard (optional)

Visit `https://bot.example.com/dashboard`. It shows upcoming events, error logs,
and the sheet link.

> **Claim the first account immediately.** There is no invite step — the first
> email address to sign up becomes a user, and until someone does, anyone who
> finds the URL can claim it. Sign up as yourself before the URL is public.

Login is by emailed magic link, so step 4's SMTP settings have to actually work
for this to be usable.

---

## Troubleshooting

| Symptom | Cause |
|---|---|
| `/ping` silent | Callback URL wrong, or not reachable over HTTPS |
| Container won't start | A missing required variable — the log names it |
| `NoSheetLink` | `/schedule link` hasn't been run on this instance |
| `APIError: 403` on reads | Sheets API not enabled, or sheet not shared with the service account |
| Reads fine, can't write | Service account is Viewer; needs Editor |
| `NoAuthenticationToken` | `/authenticate` not completed |
| OAuth fails after approving | `REDIRECT_URI` doesn't exactly match the app's callback URL |
| Duplicate scheduled posts | More than one gunicorn worker, or two containers running |
| Posts at the wrong time | Set `TIMEZONE` (defaults to `America/New_York`) |
| No email | SMTP block empty, or nobody has an address on the `People` tab |
| Login link won't open, shows `x-webdoc://` | `DASHBOARD_URL` had no `https://`; upgrade and restart |
| Two instances fighting over settings | They're sharing a database volume; give each its own |
| Same household hosts every week | Only one household has `Hosts` checked on the `People` tab |
