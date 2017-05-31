#!/bin/sh


ps -ef|grep gunicorn|grep 5000|awk '{print $2}'|xargs kill -15
