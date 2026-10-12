# POLTRACKER Privacy Policy

Last updated: 2026-10-12

This policy describes what POLTRACKER itself does with data. It covers the POLTRACKER macOS app and the code in this repository. It does not describe, and does not replace, the privacy practices of the third-party services POLTRACKER can talk to (see "Third parties").

## The short version

- POLTRACKER keeps its data on your Mac. There is no POLTRACKER account, server or cloud service.
- POLTRACKER has no analytics, telemetry or crash reporting.
- API keys for AI providers are stored in the macOS Keychain, nowhere else.
- Nothing is sent to an AI provider unless you ask for an explanation.

## What is stored on your Mac

- **Database** at `~/Library/Application Support/POLTRACKER/poltracker.db` (plus `-wal` and `-shm` files). It holds public congressional trade disclosures, market prices, calculated context signals, your saved views and preferences (including your chosen AI provider and model), and any AI explanations you generated.
- **Pre-upgrade backups** next to the database, named `poltracker.db.backup-...`. They are copies of the database and contain the same data.
- **Window storage** in `~/Library/Application Support/POLTRACKER/webview/`, where the app window keeps things like your light/dark choice.
- **A log** at `~/Library/Logs/POLTRACKER/poltracker.log`. It records start-up and refresh events and errors. When you use an AI provider it also records the time, provider address and result code of each request (for example `POST https://api.openai.com/v1/responses "200 OK"`), not the content of the request or any key.

The trade, price and politician data is public information from the sources below. POLTRACKER does not collect information about you, and the database holds no personal data about the person using the app beyond your preferences, saved view names and generated explanations.

## API keys

If you add an OpenAI or Anthropic (Claude) key in Settings:

- It is stored in your macOS Keychain under the service `com.roamingwizards.poltracker.ai` (one item per provider).
- It is not written to the database, preferences, configuration files, the log, or Git. The app's own screens show only a masked tail such as `sk-••••••••1234`, and automated tests check that a key is not returned by the app's API or written to the database or log.
- You type the key into the app window once. It travels from the window to the app's own server on your Mac (`127.0.0.1`) and is saved to the Keychain.
- The key is read from the Keychain only to make a request to the provider you selected, and is sent only to that provider.
- POLTRACKER does not operate any credential-storage service.

## AI requests

- An AI request is made only when you click **Generate explanation**, **Regenerate**, the advanced manual-explanation action, or confirm **Generate explanations for flagged trades**. **Test connection** also contacts the provider (it checks your key, without sending trade data). Opening a trade or a page never calls a provider.
- For an explanation, POLTRACKER sends the selected provider the facts about that one trade that POLTRACKER has already calculated: ticker, company name, industry code, transaction type, disclosed amount range and dates, the member's name, chamber, state and district, the matched committee evidence and its source links, the calculated signal values, whether the trade is flagged, and fixed written instructions. It does not send your API key (other than to authenticate), other trades, your saved views, or anything about you.
- The provider processes the request under its own terms and privacy policy. POLTRACKER asks OpenAI not to store the request (`store: false`); what any provider keeps is up to that provider.
- AI only explains. The deterministic flags and signals are calculated on your Mac without AI, and no AI answer changes them.
- Accepted explanations are saved in the local database so they can be read offline.

## Data sources

The app's automatic refresh contacts two services:

- **CongressInvests**, for congressional trade disclosures (the app's default address is `congressinfor-production.up.railway.app`).
- **Yahoo Finance**, through the `yfinance` library, for market prices. It is sent the ticker symbols being updated.

Command-line tools in this repository, which the app does not run, can also fetch public records from Congress.gov, the U.S. House Clerk, GovInfo and SEC EDGAR to build committee, member and company-profile information.

Like any internet request, these services can see your IP address and basic request details.

## When the internet is needed

- **Needed:** the first download of data on a new install, refreshes (at launch when the data is stale, about every 6 hours while the app is open, and when you press refresh), and AI actions.
- **Not needed:** browsing trades, politicians, securities and the Flagged page, filters, saved views, and reading cached AI explanations. If a refresh or an AI request fails because you are offline, the app shows an error and keeps your stored data unchanged.
- The app window loads only from your own Mac. Fonts and scripts are bundled, not loaded from the web. Links to outside sources (for example a filing) open only when you click them.

## Telemetry and analytics

POLTRACKER does not collect telemetry, analytics, usage statistics or crash reports, and has no code to do so. It does not check for updates. This was verified in the code when this policy was written. The only record of activity is the local log described above.

## Removing your data

Quit POLTRACKER first for the file steps.

- **API key:** in Settings, choose **Remove key** (this deletes it from the Keychain). Or open Keychain Access and delete the items for `com.roamingwizards.poltracker.ai`. Or run `security delete-generic-password -s com.roamingwizards.poltracker.ai -a openai` (use `-a anthropic` for Claude).
- **Saved views:** use the delete button in the saved views control.
- **AI explanations:** there is no delete button yet. With the app quit, run `sqlite3 ~/Library/Application\ Support/POLTRACKER/poltracker.db "DELETE FROM trade_context_analysis;"`. Backups (`poltracker.db.backup-...`) keep their own copies until you delete them.
- **Preferences (provider/model choice, last screen):** run the same command with `DELETE FROM app_preferences;`.
- **Everything:** delete the folders `~/Library/Application Support/POLTRACKER` and `~/Library/Logs/POLTRACKER`, and remove the Keychain items as above. Moving the app to the Trash does not remove them. A deleted database is rebuilt, and public data re-downloaded, the next time the app runs and is online.

## Third parties

OpenAI, Anthropic, CongressInvests, Yahoo Finance and the government sources above run their own services. When you use them through POLTRACKER, their terms and privacy policies apply to what they receive. Check them before you enter a key or request an explanation.

## Contact

POLTRACKER is maintained by RoamingWizards. For questions or corrections, open an issue at <https://github.com/RoamingWizards/POLTRACKER/issues>. No other contact address is published in the repository.

## Changes

If POLTRACKER's behavior changes in a way that affects this policy, this file will be updated and the date above changed. The history is in Git.
