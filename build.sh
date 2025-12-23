#!/bin/sh
#
NGINX_USER='www-data'
NGINX_GRP='www-data'
docker build --build-arg UID=$(id -u $NGINX_USER) --build-arg GID=$(id -g $NGINX_GRP) -t pdf_converter .
