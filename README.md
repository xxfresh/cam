# Force Join Code Bot

This Telegram bot gives users a code **after verifying** they've joined required channels.

## Features
- Admin can:
  - Set force-join channels by forwarding a message from the channel.
  - Set instruction message with inline buttons.
  - Add any number of buttons manually.
  - View stats and broadcast messages.
- User only receives the code after pressing **Verify** and joining the required channels.
- Messages auto-delete after 30 minutes.

## Deployment

### Docker (recommended)

```bash
docker build -t force-bot .
docker run -d --name mybot --restart unless-stopped \
  -e API_ID=your_api_id \
  -e API_HASH=your_api_hash \
  -e BOT_TOKEN=your_bot_token \
  force-bot
```

Replace `your_api_id`, `your_api_hash`, and `your_bot_token` with your actual credentials.
