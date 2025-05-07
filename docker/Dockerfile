# syntax = docker/dockerfile:1.4

FROM archlinux:latest

ARG CARGO_TARGET_DIR=target

RUN pacman-key --init && pacman-key --populate
RUN pacman -Syu --noconfirm rust git python nvchecker

RUN groupadd -g 1000 api
RUN useradd -u 1000 -g 1000 -m -s /bin/bash api
RUN mkdir /app
RUN chown -R api:api /app

WORKDIR /app
USER api

RUN git clone https://github.com/Torxed/trixify.git /app/trixify-git
WORKDIR /app/trixify-git
RUN cargo build --release --all-features

WORKDIR /app
RUN mv /app/trixify/target/release/trixify /app/trixify
ENTRYPOINT /app/trixify