# Grok Chat Router

One window on your computer. It picks a Grok model before it answers, tracks what you spend, and stops when you hit the budget you set.

This is not a login to grok.com, Grok bot, or Grok code. Those chats cannot see each other, and xAI does not give an app a way to read those credit balances. This app uses one API key from https://console.x.ai and the prepaid API credits on that key.

Anyone can download it and use their own key. Your key stays on your computer.

## Setup

1. Install Python 3.10 or newer.
2. Unzip this folder.
3. In the folder, run: `py app.py`
4. Open http://127.0.0.1:8765
5. Paste an API key from console.x.ai. It is saved only in settings.json on this machine.
6. Set a dollar budget and the three sliders. Accuracy, speed, cost. They work like bass, mid, and treble.

Legal, title, deed, closing, and invoice jobs are forced onto the strong model even if cost is turned up. A cheap answer on a closing is not a saving.

## What it cannot do

- See your Grok chat, Grok bot, or Grok code sessions
- Read the credit balance inside grok.com
- Message another Grok chat
- Share one login across those products

API spend is a different meter from a Grok subscription. Check console.x.ai for the real balance. This app only knows what it has spent itself, plus the budget you type in.
