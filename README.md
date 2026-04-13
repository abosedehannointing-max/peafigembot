# Telegram Member Adder

A tool to scrape members from a Telegram group and add them to another group.

## ⚠️ Warning
This tool violates Telegram's Terms of Service. Use at your own risk with a secondary account.

## Local Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Get API credentials from [my.telegram.org](https://my.telegram.org)
4. Set environment variables or create a `.env` file
5. Run scraper: `python scrape_members.py`
6. Deploy to Render for continuous adding

## Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

1. Fork this repository
2. Create a new Background Worker on Render
3. Connect your GitHub repository
4. Add environment variables:
   - `API_ID`: Your Telegram API ID
   - `API_HASH`: Your Telegram API Hash
   - `PHONE_NUMBER`: Your phone number with country code
5. Deploy!

## Important Notes
- Background Workers on Render are **paid** (Starter plan ~$7/month)
- Free Web Services will NOT work due to idle shutdowns
- Session file is stored ephemerally and may be lost on redeploy
