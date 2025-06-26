This robot monitors a Google Sheets spreadsheet and sends messages about it to a GroupMe group.

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
