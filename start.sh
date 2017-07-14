#!/bin/sh

gunicorn -w 1 -b 0.0.0.0:5000 app:app &
