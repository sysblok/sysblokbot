# SysBlokBot
Бот для автоматизации работы редакции

Deployment:
- Create `config_override.json` and put sensitive tokens there (you can copypaste from `config.json` first). Do not push `config_override.json` to the repo, let's keep it empty!
- `pip install -r requirements.txt`
- `python3 app.py`

Adding a regular job:
- implement a method in jobs.py
- add schedule to `config.json`, using your method name as a key (you may use `config_override.json` to test your changes without committing)
- add your method to scheduler.py#init_jobs

How to Docker
- [Install](https://docs.docker.com/get-docker/) docker
- Run `docker_build.sh` to build the docker image
- Run `docker images` to look at the images
- Run `docker_run.sh` to run the app
- Run `docker ps`, look up the container's id and use `docker stop <ID>` to stop it
- Run `docker logs -f <ID>` to look at its logs

How to deploy it to DigitalOcean droplet
- Run `docker save --output sysblokbot.tar sysblokbot` to serialize the docker image (about 300MB)
- `scp` it to the droplet along with `config_gs.json` and `config_override.json`
- Possibly change config roots in `docker_run.sh`
- Run it!
