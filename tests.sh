#!/usr/bin/env bash
#
# tests.sh
#
# Bootstrap valet.sh for testing purpose and run all bats tests given in tests folder
#
# Copyright: (C) 2018 TechDivision GmbH - All Rights Reserved
# Author: Johann Zelger <j.zelger@techdivision.com>
##

export APPLICATION_AUTOSTART=0

source ./valet.sh

# export all relevant functions for testing purpose
export -f out
export -f version_validate
export -f version_compare
export -f is_installed

# execute tests via bats
bats --pretty tests