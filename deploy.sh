#!/bin/bash
cd ~/YANGI-TAXI-BOT
git pull
screen -X -S taxibot quit
sleep 2
screen -dmS taxibot bash -c "cd ~/YANGI-TAXI-BOT && source venv/bin/activate && export \$(cat .env | xargs) && python -m bot.main"

