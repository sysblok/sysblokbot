# SysBlokBot
![Docker](https://github.com/sysblok/SysBlokBot/workflows/Docker/badge.svg)
[![Docker testing](https://github.com/sysblok/sysblokbot/actions/workflows/publish_dev.yml/badge.svg?branch=dev)](https://github.com/sysblok/sysblokbot/actions/workflows/publish_dev.yml)
[![Docker production](https://github.com/sysblok/sysblokbot/actions/workflows/publish_master.yml/badge.svg?branch=master)](https://github.com/sysblok/sysblokbot/actions/workflows/publish_master.yml)

Bot for SysBlok ("Системный Блокъ") editorial processes automatization.

## How to make a first local run
- Create a testing bot through BotFather and obtain the token.
- Create `config_override.json` in the same directory and put sensitive tokens there (you can copypaste from `config.json` first). Do not push `config_override.json` to the repo!
  - Run `export INFRA_HOST=<SYSBLOK_INFRA_HOST>`, putting in the actual URL
  - Run `sh get_keys.sh`. This will download `config_override.json` and `config_gs.json` to your folder.
- `pip install -e .`
- `pip install -r requirements.txt`
- `pre-commit install`
- If access to Telegram servers is restricted by your internet provider: install and run any VPN service
- `python3 app.py`

## How to develop
- Fork the repo.
- Clone your forked repo to your local workspace.
- Create a branch from `dev`. You'll need to do it for every new feature or bugfix.
- Write code in your local repo.
- Run [pre-checks](#how-to-run-pre-checks-locally) locally and write tests (if applicable).
- Create a pull request from your branch to `dev` and ask for relevant approval. It is not strictly necessary to get an approval, but please do that.
- Merge into `dev` branch after approval. This merge triggers tests checks, test docker push and updating of a test bot (not yet).
- When `dev` branch is stable, manually tested and tests are green, commits go from `dev` to `master`. If checks are successful, production bot will update. See Github Actions tab to check CI status.

## How to run pre-checks locally
- `pycodestyle --max-line-length=100 .` checks pep8 compliance.
- `pytest` runs tests.
