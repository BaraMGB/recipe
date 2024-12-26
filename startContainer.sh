#!/bin/bash
#

sudo docker-compose down && sudo docker-compose up -d && sudo docker logs -f rezepte_app
