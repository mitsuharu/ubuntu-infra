#!/usr/bin/env bash
run sudo apt-get update
run sudo apt-get install -y build-essential git curl ca-certificates gnupg python3 python3-gi \
  zsh unzip zip pkg-config autoconf bison patch rustc \
  libssl-dev libyaml-dev libreadline-dev zlib1g-dev libffi-dev libgmp-dev \
  libncurses-dev libdb-dev uuid-dev liblzma-dev \
  openjdk-17-jdk gh pinentry-gnome3 watchman xdg-user-dirs desktop-file-utils
