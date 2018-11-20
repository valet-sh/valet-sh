#!/usr/bin/env bats

@test "Testing function out with type success" {
    test_msg="This should be a successful test"
    run out success "${test_msg}"
    [ "$output" = "$(printf "\033[1;32m✔ %s\033[0m\n" "${test_msg}")" ]
}

@test "Testing function out with type error" {
    test_msg="This should be a error test"
    run out error "${test_msg}"
    [ "$output" = "$(printf "\033[1;31m✘ %s\033[0m\n" "${test_msg}")" ]
}

@test "Testing function out with type task" {
    test_msg="This should be a task test"
    run out task "${test_msg}"

    [ "$output" = "$(printf "▸ %s\n" "${test_msg}")" ]
}

