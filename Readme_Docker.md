## How to Docker (not required for a local run)
- [Install](https://docs.docker.com/get-docker/) docker
- Run `docker_build.sh` to build the docker image
- Run `docker images` to look at the images
- Run `docker_run.sh` to run the app
- Run `docker ps`, look up the container's id and use `docker stop <ID>` to stop it
- Run `docker logs -f <ID>` to look at its logs

## How to use Docker Compose (optional for development)
- Install [Docker Compose](https://docs.docker.com/compose/install/) or [Colima](https://github.com/abiosoft/colima) on macOS.
- Run `docker compose -f docker-compose.dev.yml up -d` to build the docker image and run the app.

## How to deploy it to DigitalOcean droplet (test purposes only)
- Run `docker save --output sysblokbot.tar sysblokbot` to serialize the docker image (about 300MB)
- `scp` it to the droplet along with `config_gs.json` and `config_override.json`
- Untar it with `docker load --input sysblokbot.tar`
- Possibly change config roots in `docker_run.sh`
- Run it!
