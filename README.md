# SysBlokBot
Бот для автоматизации работы редакции

Deployment:
- Manually fill in sensitive api keys in config.json
- pip install -r requirements.txt
- python3 run_bot.py

Adding a regular job:
- implement a method in jobs.py
- add time to config.json, using your method name as a key
- add to scheduler.py#init_jobs