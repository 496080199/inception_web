#!/bin/sh
CURDIR=$(cd `dirname $0`; pwd)
CURUSER=`whoami`
su - $CURUSER -c "cd $CURDIR&&python run.py"
