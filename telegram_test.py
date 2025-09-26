import os, requests
t = os.getenv('TELEGRAM_BOT_TOKEN')
c = os.getenv('TELEGRAM_CHAT_ID')
if not t or not c:
    raise SystemExit('Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID')
r = requests.post(f'https://api.telegram.org/bot{t}/sendMessage',
                  data={'chat_id': c, 'text': '✅ Telegram direct test'})
print('HTTP', r.status_code)
print(r.text)
