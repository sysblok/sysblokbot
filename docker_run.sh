#!/bin/bash

docker run --name sysblokbot -d \
    -v $(pwd)/config_override.json:/app/config_override.json \
    -v $(pwd)/config_gs.json:/app/config_gs.json sysblokbot
