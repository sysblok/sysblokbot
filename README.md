# SysBlokBot
Бот для автоматизации работы редакции

Deployment:
- Add sensitive tokens to `config_override.json` (you can copypaste from `config.json` first). Do not push `config_override.json` to the repo, let's keep it empty!
- `pip install -r requirements.txt`
- `python3 run_bot.py`

Adding a regular job:
- implement a method in jobs.py
- add schedule to `config.json`, using your method name as a key (you may use `config_override.json` to test your changes without committing)
- add your method to scheduler.py#init_jobs