# Histology WebScraper

This project is a powerful, specialized web scraper designed to extract high-resolution histology images from the [NUS Pathweb Normal Histology](https://medicine.nus.edu.sg/pathweb/normal-histology/) website.

## Features

- **Consolidated Logic**: A single, robust script (`scraper.py`) handles all scraping tasks.
- **Automated Navigation**: Dynamically discovers organ systems and subsections (e.g., Skin, Gastrointestinal Tract).
- **Manual Overrides**: Includes built-in support for known hard-to-find sections (Appendix, Tongue, Tonsil).
- **Anti-Bot Bypass**: Uses advanced Selenium + JavaScript `fetch` injection to bypass security challenges and download images as blobs.
- **Smart Resumption**: Automatically detecting existing files to skip redundant downloads, allowing for easy resumption of interrupted sessions.

## Prerequisites

- Python 3.x
- Google Chrome (latest version)

## Installation

1. Clone this repository.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Twice the power, half the files. Just run:

```bash
python scraper.py
```

1. **Launch**: The script opens a Chrome window.
2. **Solve Captchas**: *Action Required*. Manually solve any security checks (Incapsula/Captchas) in the browser.
3. **Start**: Press **Enter** in the terminal once the "Normal Histology" page is visible.
4. **Sit Back**: The script analyzes the page, adds manual overrides for missing sections, and downloads everything into `images_scraped/`.

## Project Structure

- `scraper.py`: The all-in-one scraping engine.
- `images_scraped/`: Output directory.
- `requirements.txt`: Python dependencies.

## Disclaimer

For educational purposes only. Respect the target website's rate limits and terms.
