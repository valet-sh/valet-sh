#!/usr/bin/env bash
#
# Bootstrap valet.sh for testing purpose and run all bats tests given in tests folder
#
# Copyright: (C) 2018 TechDivision GmbH - All Rights Reserved
# Author: Johann Zelger <j.zelger@techdivision.com>
##

# disable autostart valet.sh
export APPLICATION_AUTOSTART=0
# disable spinner by default
export SPINNER_ENABLED=0

# include all valet.sh functions
# shellcheck disable=SC1091
source ./valet.sh

# define helper functions
debug() {
  echo "status: ${1}"
  echo "output: ${2}"
  echo "lines: ${3}"
}