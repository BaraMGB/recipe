#!/bin/bash
source ~/venv/bin/activate
gunicorn -w 1 -b 0.0.0.0:8000 app:app
deactivate
