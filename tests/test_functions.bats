#!/usr/bin/env bats

load bootstrap

#################################################################################################
# Testing function: out
#################################################################################################
@test "Testing function out with type success" {
    test_msg="This should be a successful test"
    run out success "${test_msg}"

    debug "${status}" "${output}" "${lines}"
    [ "$output" = "$(printf "\033[1;32m✔ %s\033[0m\n" "${test_msg}")" ]

    unset test_msg
}

@test "Testing function out with type error" {
    test_msg="This should be a error test"
    run out error "${test_msg}"

    debug "${status}" "${output}" "${lines}"
    [ "$output" = "$(printf "\033[1;31m✘ %s\033[0m\n" "${test_msg}")" ]

    unset test_msg
}

@test "Testing function out with type task" {
    test_msg="This should be a task test"
    run out task "${test_msg}"

    debug "${status}" "${output}" "${lines}"
    [ "$output" = "$(printf "▸ %s\n" "${test_msg}")" ]

    unset test_msg
}

#################################################################################################
# Testing function: version_compare
#################################################################################################
@test "Testing function version_compare with version1 < version2 in patch" {
    version1="1.0.0-beta1+4718762"
    version2="1.0.1-beta1+4718762"
    run version_compare ${version1} ${version2}

    debug "${status}" "${output}" "${lines}"
    [ "$output" = "-1" ]
    
    unset version1
    unset version2
}

@test "Testing function version_compare with version1 < version2 in minor" {
    version1="1.0.0-beta1+4718762"
    version2="1.1.0-beta1+4718762"
    run version_compare ${version1} ${version2}

    debug "${status}" "${output}" "${lines}"
    [ "$output" = "-1" ]
    
    unset version1
    unset version2
}

@test "Testing function version_compare with version1 < version2 in major" {
    version1="1.0.0-beta1+4718762"
    version2="2.0.0-beta1+4718762"
    run version_compare ${version1} ${version2}

    debug "${status}" "${output}" "${lines}"
    [ "$output" = "-1" ]
    
    unset version1
    unset version2
}

@test "Testing function version_compare with version1 = version2" {
    version1="1.2.3-beta1+4718762"
    version2="1.2.3-beta1+4718762"
    run version_compare "${version1}" "${version2}"

    debug "${status}" "${output}" "${lines}"
    [ "$output" = "0" ]

    unset version1
    unset version2
}

@test "Testing function version_compare with version1 > version2 in patch" {
    version1="1.0.2-beta1+4718762"
    version2="1.0.1-beta1+4718762"
    run version_compare "${version1}" "${version2}"

    debug "${status}" "${output}" "${lines}"
    [ "$output" = "1" ]

    unset version1
    unset version2
}

@test "Testing function version_compare with version1 > version2 in minor" {
    version1="1.2.1-beta1+4718762"
    version2="1.1.1-beta1+4718762"
    run version_compare "${version1}" "${version2}"

    debug "${status}" "${output}" "${lines}"
    [ "$output" = "1" ]

    unset version1
    unset version2
}

@test "Testing function version_compare with version1 > version2 in major" {
    version1="1.4.2-beta1+4718762"
    version2="1.2.1-beta1+4718762"
    run version_compare "${version1}" "${version2}"

    debug "${status}" "${output}" "${lines}"
    [ "$output" = "1" ]

    unset version1
    unset version2
}


#################################################################################################
# Testing function: error
#################################################################################################
@test "Testing function error with message" {
    test_msg="something went wrong!"
    run error $test_msg

    debug "${status}" "${output}" "${lines}"
    [ "$output" = "$(out error "${test_msg}")" ]
    [ "$status" = "${APPLICATION_RETURN_CODE_ERROR}" ]

    unset test_msg
}

@test "Testing function error without message" {
    run error

    debug "${status}" "${output}" "${lines}"
    [ "$output" = "no error message given" ]
    [ "$status" = "${APPLICATION_RETURN_CODE_ERROR}" ]
}