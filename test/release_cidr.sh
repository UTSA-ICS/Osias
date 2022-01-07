#!/bin/bash

CIDR="$1"

AVAILABLE_CIDRS_FILE="/opt/gitlab-data/available_cidrs"
USED_CIDRS_FILE="/opt/gitlab-data/used_cidrs"

if [ -z "$1" ]
  then
    echo "No argument supplied"
    exit 1
fi

if [[ $CIDR == *[1234567890./]* ]];then
  echo ""
  sed -i "\|$CIDR|d" $USED_CIDRS_FILE
  echo "$CIDR" >> $AVAILABLE_CIDRS_FILE
else
  echo "Input <$CIDR> is not a valid CIDR"
  echo ""
fi

available_cidrs=("$(cat $AVAILABLE_CIDRS_FILE)")
echo "*** Available CIDRS ***"
for cidr in "${available_cidrs[@]}"
do
  echo "$cidr"
done

used_cidrs=("$(cat $USED_CIDRS_FILE)")
echo ""
echo "*** Used CIDRS ***"
for cidr in "${used_cidrs[@]}"
do
  echo "$cidr"
done
