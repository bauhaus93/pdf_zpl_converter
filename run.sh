#!/bin/sh

mkdir -p /tmp/converter
sudo chown www-data:www-data -R /tmp/converter
docker run -d  -v /tmp/converter:/tmp --name converter pdf_converter
