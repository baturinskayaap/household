@echo off
echo 🚀 Deploying Household Bot...

set SERVER=botuser@193.222.62.253
set BOT_DIR=/home/botuser/household-bot

echo 📦 Copying files to server...
scp bot.py %SERVER%:%BOT_DIR%/
scp database.py %SERVER%:%BOT_DIR%/
scp models.py %SERVER%:%BOT_DIR%/
scp utils.py %SERVER%:%BOT_DIR%/
scp keyboards.py %SERVER%:%BOT_DIR%/
scp reminder_system.py %SERVER%:%BOT_DIR%/
scp cron_reminder.py %SERVER%:%BOT_DIR%/

echo 🔄 Restarting bot service...
ssh %SERVER% "cd %BOT_DIR% && sudo systemctl restart household-bot.service"

echo ✅ Deployment completed!
pause