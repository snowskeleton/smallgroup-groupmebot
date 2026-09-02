This robot monitors a Google Sheets spreadsheet and sends messages about it to a GroupMe group.

**Setting up a new bot?** See [SETUP.md](SETUP.md) for start-to-finish instructions,
including registering the bot, the OAuth application, service-account access, and
cloning the spreadsheet for another group.

Setup like so:

### Prerequisites
* docker
* git

### Build and run
* `git clone https://github.com/snowskeleton/smallgroup-groupmebot.git`
* `cp example.bot_secrets.py`
* `vi bot_secrets.py`
* * `BOT_ID`: *Sensitive* The **Bot ID** value as reported in dev.groupme.com/bots
* * `BOT_NAME`: The **Bot Name** value as reported in dev.groupme.com/bots
* * `CLIENT_ID`: *Sensitive* The string at the end of the URL of your GroupMe Application as reported in the Settings of your application in dev.groupme.com/applications
* * `CLIENT_SECRET`: *Sensitive* Your user's **Access Token** as reported in dev.groupme.com by clicking on **Access Token**
* * `REDIRECT_URI`: *Sensitive* Your **Callback URL** of your GroupMe Application as reported in the Settings of your application at dev.groupme.com/applications
* Obtain Google Sheets API credentials: *Sensitive*
  * Go to https://console.cloud.google.com/
  * Create or select a project
  * Enable the Google Sheets API
  * Navigate to "APIs & Services" → "Credentials"
  * Create a Service Account and generate a JSON key file
  * Download the JSON key file and save it as `credentials.json` in the project root directory
* `docker compose up -d`

### Post-build configuration
* Ensure your API endpoing is set correctly lol
To make sure it has basic connectivity, from GroupMe run
* `/ping`
To see a full list of commands, run
* `/help`
To authorize it to send some commands, run
* `/authenticate`
* * Have an admin or owner follow the link provided
* `/schedule link <Google Sheets sheet link>`

### The spreadsheet
The bot reads five tabs. The sheet's own `README` tab documents them for whoever
is editing it; the short version:

* `Schedule` — one row per meeting. The bot **only appends** rows below the last
  one, never edits or deletes. Human changes are always final.
* `People` — one row per person. `Household` groups spouses so a couple gets one
  turn, not two. Checkbox columns are per-rotation opt-ins.
* `Rotations` — `Rotation | Column | Pool | Opt-in`. `Pool` is `People`,
  `Households`, or the name of another tab holding a plain ordered list, which
  is how group-level rotations work without a code change.
* `Config` — `Meeting Day`, `Default Time`, `Weeks Ahead`, `Assign Ahead`.
* `README` — ignored by the bot.

**Commands.** `/schedule generate` tops the sheet up to the configured
horizons, and is what the weekly job runs. `/populate <weeks>` fills a given
stretch completely — dates and assignments both — for testing or for planning a
busy month early. `/help` lists everything.

**Two horizons.** `Weeks Ahead` (16) is how far out bare dated rows are laid
down, so there is always somewhere to note a church event or an absence.
`Assign Ahead` (4) is how far out rotations are actually filled in. Assigning
late keeps commitments short and lets a newly added person start leading within
about a month rather than waiting out a queue of pre-filled turns.

**The bot only ever writes into a blank cell.** It never changes or deletes
anything a human typed. A blank cell therefore means "unassigned" — use a dash
to hold a week deliberately empty, and clear a cell to request a re-assignment.

**Whoever has gone longest without a turn goes next.** There is no stored
cursor — the bot reads the schedule above each row, notes when each pool member
last came up, and picks the one who has waited longest. Anyone who has never
come up sorts first; ties break on order in `People`, so a rotation with no
history runs straight down that tab.

Left alone this is just a lap of the list. It differs when a human edits the
schedule: if someone covers for the person whose turn it was, that person still
hasn't had a turn, so they go next rather than dropping to the back of the
queue. It's also why a newly added person starts soon instead of waiting out the
existing cycle.

A `Location` the bot can't resolve to a household (`Panera`) is printed as-is,
updates nobody's last-served position, and so costs nobody their turn — but a
near-miss is logged as a likely typo.

The service account needs **Editor** access on the sheet, since it appends rows.
