# docker build -t python-rflink .
# sudo docker run -it --device="/dev/ttyACM0:/dev/ttyACM0" python-rflink rflink

FROM python:3.7.3-slim

ARG DEBIAN_FRONTEND=noninteractive
RUN /usr/bin/apt-get update \
 && /usr/local/bin/pip install --no-cache-dir rflink \
 && rm -rf /var/lib/apt/lists/*

