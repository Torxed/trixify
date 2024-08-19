# syntax = docker/dockerfile:1.4

FROM archlinux:latest

RUN pacman-key --init && pacman-key --populate
RUN pacman -Syu --noconfirm git python nvchecker python-pip python-pydantic python-toml
RUN pip install matrix-nio[e2e] --break-system-packages

RUN groupadd -g 1000 api
RUN useradd -u 1000 -g 1000 -m -s /bin/bash api
RUN mkdir /app
RUN chown -R api:api /app

WORKDIR /app
USER api

RUN git clone https://github.com/Torxed/trixify.git

WORKDIR /app/trixify
ENTRYPOINT /usr/bin/python -m trixify --config /app/trixify.toml