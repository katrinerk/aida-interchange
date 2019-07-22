#!/bin/sh

rsync -avhe ssh --exclude '__pycache__' --exclude '*.pyc' aif $1
rsync -avhe ssh --exclude '__pycache__' --exclude '*.pyc' evaluation $1
rsync -avhe ssh --exclude '__pycache__' --exclude '*.pyc' pipeline $1
rsync -avhe ssh --exclude '__pycache__' --exclude '*.pyc' seeds $1
rsync -avhe ssh --exclude '__pycache__' --exclude '*.pyc' test $1
