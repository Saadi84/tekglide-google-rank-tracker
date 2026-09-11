# TekGlide Google US Rank Tracker

A Python and Selenium-based rank-tracking application that checks the organic Google US position of approved TekGlide landing pages. It includes a Flask dashboard, exact URL matching, location verification, CSV reporting, and a shareable local interface.

## Key Features

* Tracks approved commercial keywords from `targets.csv`
* Searches up to 100 Google organic results
* Uses Google US search parameters
* Matches exact approved landing-page URLs
* Excludes advertisements and unrelated TekGlide pages
* Verifies the active IP location before running a search
* Displays live progress through a Flask dashboard
* Saves ranking history to `rank_results.csv`
* Supports manual CAPTCHA verification when required
* Provides a LocalTunnel script for sharing the dashboard

## Technology Stack

* Python 3
* Flask
* Selenium WebDriver
* HTML5
* CSS3
* JavaScript
* CSV data storage
* LocalTunnel

## Project Structure

```text
tekglide-google-rank-tracker/
├── static/
│   ├── app.js
│   └── style.css
├── templates/
│   └── index.html
├── tests/
│   └── test_nonbrowser.py
├── app.py
├── rank_tracker.py
├── requirements.txt
├── targets.csv
├── run_local_app.bat
├── run_tracker.bat
└── share_live_link.bat
```

## Requirements

Before running the application, make sure you have:

* Windows 10 or later
* Python 3 installed
* Google Chrome installed
* An active internet connection
* A US VPN connection when checking Google US rankings

## Installation

1. Download or clone this repository.
2. Extract the project if downloaded as a ZIP file.
3. Open the project folder.
4. Run:

```bat
run_local_app.bat
```

The script creates a Python virtual environment and installs the required packages automatically during the first run.

## Using the Dashboard

1. Connect your VPN to a US location.
2. Double-click `run_local_app.bat`.
3. Open `http://127.0.0.1:5000/` if it does not open automatically.
4. Select an approved keyword.
5. Confirm the required location checks.
6. Click **Check Rank**.
7. If Google displays a CAPTCHA, solve it manually in the visible Chrome window.
8. Keep Chrome open until the search is complete.
9. Review the result on the dashboard or in `rank_results.csv`.

## Command-Line Usage

Run the complete tracker:

```bat
run_tracker.bat
```

Test URL normalization without opening Chrome:

```bat
.venv\Scripts\python.exe rank_tracker.py --self-test
```

Test a single keyword:

```bat
.venv\Scripts\python.exe rank_tracker.py --test-keyword "SEO Consulting Services" --pause-after-found
```

## Sharing the Local Dashboard

Run:

```bat
share_live_link.bat
```

This creates a temporary public LocalTunnel URL. The application still runs on your computer, so your computer and local Flask server must remain active.

## Output

Completed checks are stored in `rank_results.csv`, including:

* Search date and time
* Keyword
* Organic position
* Google results page
* Result title
* Found URL
* Approved target URL
* Search status

## Important Notes

* Search rankings may vary by location, device, session, time, and personalization.
* Google may display CAPTCHA or temporarily restrict repeated automated searches.
* This application does not bypass CAPTCHA; manual verification may be required.
* Run searches responsibly and avoid sending a high volume of repeated requests.
* Review and update `targets.csv` before performing production checks.

## Privacy

Generated browser profiles, virtual environments, cache files, diagnostics, logs, and ranking results are excluded from the repository through `.gitignore`.

## Disclaimer

This project was developed for educational and internal SEO monitoring purposes. Users are responsible for complying with Google's terms and all applicable policies.

## Author

**Saud Ahmed**

GitHub: [@Saadi84](https://github.com/Saadi84)
