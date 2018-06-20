#!/bin/bash

source run_or_fail.sh

# delete previous id 
rm -f .commit_id

function get_commit_id() {
    local COMMIT
    COMMIT=$(run_or_fail "Could not call 'git log' on repository" git log -n1)
    echo $COMMIT | awk '{ print $2 }'
}

# go to repo and update it to given commit
run_or_fail "Repository folder not found!" pushd $1 1> /dev/null
run_or_fail "Could not reset git" git reset --hard HEAD

# get current commit id
COMMIT_ID=`get_commit_id`

# update the repo
run_or_fail "Could not pull from repository" git pull

# get current commit id after update the repo
NEW_COMMIT_ID=`get_commit_id $COMMIT`

# if the id changed, then write it to a file
if [ $NEW_COMMIT_ID != $COMMIT_ID ]; then
  popd 1> /dev/null
  echo $NEW_COMMIT_ID > .commit_id
fi
