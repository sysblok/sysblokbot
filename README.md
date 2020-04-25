# SysBlokBot
![Docker](https://github.com/sysblok/SysBlokBot/workflows/Docker/badge.svg)

Бот для автоматизации работы редакции

## How to develop
- Fork the repo, if not yet.
- Create a branch from `dev`.
- Work in your local repo.
- Perform pre-checks locally and write tests (if applicable).
- Create pull request to `dev` and ask for relevant approval. It is not strictly necessary to get an approval, but please do that.
- Merge into `dev` branch after approval. This merge triggers tests checks, test docker push and updating of a test bot (not yet).
- When `dev` branch is stable, manually tested and tests are green, commits go from `dev` to `master`. If checks are successful, production bot will update. See Github Actions tab to check CI status.

## How to make a first local run
- Create `config_override.json` in the same directory and put sensitive tokens there (you can copypaste from `config.json` first). Do not push `config_override.json` to the repo!
- `pip install -r requirements.txt`
- `python3 app.py`

## How to run pre-checks locally
- `pycodestyle .` checks pep8 compliance.
- `pytest` runs tests.

## How to add a scheduled job
- Implement a method in `jobs.py`
- Add schedule to `config.json`, using your exact method name as a key (you may use `config_override.json` to test your changes without committing)

## How to Docker
- [Install](https://docs.docker.com/get-docker/) docker
- Run `docker_build.sh` to build the docker image
- Run `docker images` to look at the images
- Run `docker_run.sh` to run the app
- Run `docker ps`, look up the container's id and use `docker stop <ID>` to stop it
- Run `docker logs -f <ID>` to look at its logs

## How to deploy it to DigitalOcean droplet (test purposes only)
- Run `docker save --output sysblokbot.tar sysblokbot` to serialize the docker image (about 300MB)
- `scp` it to the droplet along with `config_gs.json` and `config_override.json`
- Untar it with `docker load --input sysblokbot.tar`
- Possibly change config roots in `docker_run.sh`
- Run it!

## How to use Trello API
- Get API Key and Token: https://trello.com/app-key
- Get ID of main board: curl 'https://api.trello.com/1/members/me/boards?key={yourKey}&token={yourToken}'
