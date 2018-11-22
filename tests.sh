#!/usr/bin/env bash
#
# tests.sh
#
# Bootstrap valet.sh for testing purpose and run all bats tests given in tests folder
#
# Copyright: (C) 2018 TechDivision GmbH - All Rights Reserved
# Author: Johann Zelger <j.zelger@techdivision.com>
##

set -a

export APPLICATION_AUTOSTART=0

# shellcheck disable=SC1091
source ./valet.sh

# execute tests via bats
bats --pretty tests
