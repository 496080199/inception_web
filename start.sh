#!/bin/sh

gunicorn --error-logfile=/tmp/inception.err_log -w 2 -b 0.0.0.0:5000 app:app &
