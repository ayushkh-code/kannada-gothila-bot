# Kannada Gothila auto poster

Posts one funny Bangalore card to Instagram (@kannada.gothila) every day at 7 PM IST.

## How it works
* Claude writes a fresh Bangalore joke, avoiding repeats (history.json)
* post.py renders it as a 1080x1350 card
* GitHub Actions publishes it through the Instagram Graph API (Facebook login route)

## Secrets (Settings > Secrets and variables > Actions)
* `ANTHROPIC_API_KEY`
* `IG_USER_ID` (17841427779137860)
* `IG_ACCESS_TOKEN` (long lived; expires about every 60 days, refresh via the Meta Access Token Debugger)

## Tweaking
* Joke topics: edit `THEMES` in `post.py`
* Colours, header text: edit `PALETTES` and `render()` in `post.py`
* Post time: edit the cron line in `.github/workflows/daily.yml` (UTC; IST minus 5:30)
* Manual run: Actions tab > Daily Kannada Gothila post > Run workflow
