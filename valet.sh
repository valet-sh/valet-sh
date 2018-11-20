#!/usr/bin/env bash
#
# valet.sh
#
# Copyright: (C) 2018 TechDivision GmbH - All Rights Reserved
# Author: Johann Zelger <j.zelger@techdivision.com>
# Author: Florian Schmid <f.schmid@techdivision.com>
##

# Set a global trap for e.g. ctrl+c to run shutdown routine
trap shutdown INT

# define script main function
: "${MAIN_FUNCTION:=main}"

#######################################
# Toggles spinner animation
# Globals:
#   SPINNER_PID
# Arguments:
#   Message
# Returns:
#   None
#######################################
spinner_toggle() {

    # Start spinner background function
    function _spinner_start() {
        local list=( $(echo -e '\xe2\xa0\x8b')
                     $(echo -e '\xe2\xa0\x99')
                     $(echo -e '\xe2\xa0\xb9')
                     $(echo -e '\xe2\xa0\xb8')
                     $(echo -e '\xe2\xa0\xbc')
                     $(echo -e '\xe2\xa0\xb4')
                     $(echo -e '\xe2\xa0\xa6')
                     $(echo -e '\xe2\xa0\xa7')
                     $(echo -e '\xe2\xa0\x87')
                     $(echo -e '\xe2\xa0\x8f') )
        local i=0
        tput sc
        # wait for .inprogress flag file to be created by ansible callback plugin
        while [ ! -f "$APPLICATION_INPROGRESS_FILE_PATH" ]; do sleep 0.5; done
        while true; do
            printf "\e[32m%s\e[39m $1 " "${list[i]}"
            i=$(($i+1))
            i=$(($i%10))
            sleep 0.1
            tput rc
        done
    }

    function _spinner_stop() {
        kill "$SPINNER_PID" > /dev/null 2>&1
        wait $! 2>/dev/null
        SPINNER_PID=0
        rm -rf "$APPLICATION_INPROGRESS_FILE_PATH"
        tput rc
    }

    # check if spinner pid exist
    if [[ "$SPINNER_PID" -lt 1 ]]; then
        tput sc
        _spinner_start "$1" &
        SPINNER_PID=$!
    else
        _spinner_stop
    fi

}

#######################################
# Logs messages in given type
# Globals:
#   None
# Arguments:
#   Message
#   Type
# Returns:
#   None
#######################################
function out() {
    case "${1--h}" in
        error) printf "\033[1;31m✘ %s\033[0m\n" "$2";;
        success) printf "\033[1;32m✔ %s\033[0m\n" "$2";;
        task) printf "▸ %s\n" "$2";;
        *) printf "%s\n" "$*";;
    esac
}

#######################################
# Validates version against semver
# Globals:
#   None
# Arguments:
#   Version
# Returns:
#   None
#######################################
function version_validate() {
    local version=$1
    if [[ "$version" =~ $SEMVER_REGEX ]]; then
        if [ "$#" -eq "2" ]; then
            local major=${BASH_REMATCH[1]}
            local minor=${BASH_REMATCH[2]}
            local patch=${BASH_REMATCH[3]}
            local prere=${BASH_REMATCH[4]}
            local build=${BASH_REMATCH[5]}
            eval "$2=(\"$major\" \"$minor\" \"$patch\" \"$prere\" \"$build\")"
        else
            echo "$version"
        fi
    else
        out error "Version $version does not match the semver scheme 'X.Y.Z(-PRERELEASE)(+BUILD)'. See help for more information." error
    fi
}

#######################################
# Compares versions
# Globals:
#   None
# Arguments:
#   Version1
#   Version2
# Returns:
#  -1   if version1 < version2
#   0   if version1 == version2
#   1   if version1 > version2
#######################################
function version_compare() {
    version_validate "$1" V
    version_validate "$2" V_

    for i in 0 1 2; do
        local diff=$((${V[$i]} - ${V_[$i]}))
        if [[ $diff -lt 0 ]]; then
            echo -1; return 0
        elif [[ $diff -gt 0 ]]; then
            echo 1; return 0
        fi
    done

    if [[ -z "${V[3]}" ]] && [[ -n "${V_[3]}" ]]; then
        echo -1; return 0;
    elif [[ -n "${V[3]}" ]] && [[ -z "${V_[3]}" ]]; then
        echo 1; return 0;
    elif [[ -n "${V[3]}" ]] && [[ -n "${V_[3]}" ]]; then
        if [[ "${V[3]}" > "${V_[3]}" ]]; then
            echo 1; return 0;
        elif [[ "${V[3]}" < "${V_[3]}" ]]; then
          echo -1; return 0;
        fi
    fi

    echo 0
}

#######################################
# Returns if application is installed
# Globals:
#   None
# Arguments:
#   None
# Returns:
#   Bool
#######################################
function is_installed() {
    if [ -d "${INSTALL_DIR}" ]
    then
        return 0
    else
        return 1
    fi
}

#######################################
# Prepares variables and other stuff
# Globals:
#   APPLICATION_RETURN_CODE
#   APPLICATION_START_TIME
#   APPLICATION_NAME
#   APPLICATION_MODE
#   APPLICATION_VERSION
#   APPLICATION_GIT_NAMESPACE
#   APPLICATION_GIT_REPOSITORY
#   APPLICATION_GIT_URL
#   APPLICATION_INPROGRESS_FILE_PATH
#   ANSIBLE_PLAYBOOKS_DIR
#   SEMVER_REGEX
#   INSTALL_DIR
#   TEMP_DIR
#   SCRIPT_PATH
#   BASE_DIR
# Arguments:
#   None
# Returns:
#   None
#######################################
function init() {
    # set default return code 0
    APPLICATION_RETURN_CODE=0
    # track start time
    APPLICATION_START_TIME=$(ruby -e 'puts Time.now.to_f');
    # define variables
    APPLICATION_NAME="valet.sh"
    # define default application mode for future usage
    : "${APPLICATION_MODE:=production}"
    # define default git relevant variables
    APPLICATION_GIT_NAMESPACE=${APPLICATION_GIT_NAMESPACE:="valet-sh"}
    APPLICATION_GIT_REPOSITORY=${APPLICATION_GIT_REPOSITORY:="valet-sh"}
    APPLICATION_GIT_URL=${APPLICATION_GIT_URL:="https://github.com/${APPLICATION_GIT_NAMESPACE}/${APPLICATION_GIT_REPOSITORY}"}

    # define default playbook dir
    ANSIBLE_PLAYBOOKS_DIR="playbooks"
    # define semver regular expression for checkout valid versions on upgrade
    SEMVER_REGEX="^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(\-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$"
    # define global temp dir
    TEMP_DIR="/tmp"
    # temporary application-in-progress file used e.g. by ansible or spinner function
    APPLICATION_INPROGRESS_FILE_PATH="${TEMP_DIR}/valet-sh.inprogress"
    # define default install directory
    INSTALL_DIR="$HOME/.${APPLICATION_NAME}";

    # resolve symlink if needed
    test -h ${BASH_SOURCE[0]} && SCRIPT_PATH="$(readlink "${BASH_SOURCE[0]}")" || SCRIPT_PATH="${BASH_SOURCE[0]}"

    # use current bash source script dir as base_dir
    BASE_DIR="$( dirname "${SCRIPT_PATH}" )"

    # check if git dir is available
    if [ -d "${BASE_DIR}/.git" ]; then
        # get the current version from git
        APPLICATION_VERSION=$(git --git-dir=${BASE_DIR}/.git --work-tree=${BASE_DIR} describe --tags)
        # set cwd to base dir
        cd ${BASE_DIR}
    fi
}

#######################################
# Prepares application by installing dependencies and itself
# Globals:
#   BASE_DIR
# Arguments:
#   None
# Returns:
#   None
#######################################
function prepare() {
    install_deps
    # install application if not done yet
    if ! is_installed; then
        install_upgrade
        # shutdown after initial installation
        shutdown
    fi
    # set cwd to base dir
    cd $BASE_DIR
}

#######################################
# Install ansible if not availabe
# Globals:
#   None
# Arguments:
#   None
# Returns:
#   None
#######################################
function install_deps() {
    # check if macOS command line tools are available by checking git bin
    if [ ! -f /Library/Developer/CommandLineTools/usr/bin/git ]; then
        # trigger git, this will prompt installation of Command Line tools
        git &> /dev/null
        # exit with error message, CLT should be installed by MacOS routine using the user prompt - this ensures clean install (without using a custom install routine)
        error "Please install Command Line tools first (using the newly opened propmt) and re-run $APPLICATION_NAME"
    fi

    # check if ansible command is available
    if [ ! -x "$(command -v ansible)" ]; then
        # test and trigger sudo for MacOS timeout (sudo)
        sudo true || error "Failed to sudo"

        spinner_toggle "Installing Ansible"
        touch "$APPLICATION_INPROGRESS_FILE_PATH"
        # if ansible is not available, install pip and ansible
        # Todo: Redirect output to logfile
        sudo easy_install pip &> /dev/null || error "Failed to installed pip"
        sudo pip install -Iq ansible &> /dev/null || error "Failed to install ansible"
        spinner_toggle
    fi

    # verfiy all dependencies
    verify_deps
}


#######################################
# Verify dependencies
# Globals:
#   None
# Arguments:
#   None
# Returns:
#   None
#######################################
function verify_deps() {
    # check if ansible command is available
    if ! ansible-playbook --version &> /dev/null; then
        error "Dependency not met: Failed to run ansible-playbook command"
    fi
}

#######################################
# Install and upgrade logic
# Globals:
#   APPLICATION_NAME
#   APPLICATION_VERSION
#   APPLICATION_GIT_URL
#   BASE_DIR
# Arguments:
#   None
# Returns:
#   None
#######################################
function install_upgrade() {

    # reset release tag to current application version
    RELEASE_TAG="$APPLICATION_VERSION"

    if [ "$APPLICATION_MODE" = "production" ]; then
        spinner_toggle "Installing $APPLICATION_NAME"
        touch "$APPLICATION_INPROGRESS_FILE_PATH"
        # create tmp directory for cloning valet.sh
        local tmp_dir=$(mktemp -d) || error "Failed to create temporary directory, try running script at different path"
        local src_dir="$tmp_dir"

        # clone project git repo to tmp dir
        rm -rf "$tmp_dir" &> /dev/null
        git clone --quiet "$APPLICATION_GIT_URL" "$tmp_dir"
        cd "$tmp_dir" || error "Failed to access temporary directory"

        # fetch all tags from application git repo
        git fetch --tags

        # get available release tags sorted by refname
        RELEASE_TAGS=$(git tag --sort "-v:refname" )

        # get latest semver conform git version tag on current major version releases
        for GIT_TAG in $RELEASE_TAGS; do
            if [[ "$GIT_TAG" =~ $SEMVER_REGEX ]]; then
                RELEASE_TAG=$GIT_TAG
                break;
            fi
        done

        # force checkout latest release tag in given major version
        git checkout --quiet --force "$RELEASE_TAG"

        spinner_toggle
    else
        # take base dir for developer installation
        src_dir="$BASE_DIR"
    fi

    # check if install dir exist
    if [ ! -d "$INSTALL_DIR" ]; then
        # install
        cp -r "$src_dir" "$INSTALL_DIR"
        # create symlink to default included PATH
        sudo ln -sf $INSTALL_DIR/${APPLICATION_NAME} /usr/local/bin/
        # output log
        out success "Installed version $RELEASE_TAG"
    else
        CURRENT_INSTALLED_VERSION=$(git --git-dir=${INSTALL_DIR}/.git --work-tree=${INSTALL_DIR} describe --tags)

        # compare application version to release tag version
        if [ $(version_compare ${CURRENT_INSTALLED_VERSION} $RELEASE_TAG) = 0 ]; then
            out success "Already on the latest version $RELEASE_TAG"
        else
            out success "Upgraded from $CURRENT_INSTALLED_VERSION to latest version $RELEASE_TAG"
        fi

        # update tags
        git --git-dir=${INSTALL_DIR}/.git --work-tree=${INSTALL_DIR} fetch --tags --quiet
        # checkout target release tag
        git --git-dir=${INSTALL_DIR}/.git --work-tree=${INSTALL_DIR} checkout --force --quiet $RELEASE_TAG
    fi

    # change directory to install dir
    cd "$INSTALL_DIR"

    # clean tmp dir
    rm -rf "$tmp_dir" &> /dev/null
}

#######################################
# Prints the console tool header
# Globals:
#   APPLICATION_NAME
#   APPLICATION_VERSION
#   APPLICATION_MODE
# Arguments:
#   None
# Returns:
#   None
#######################################
function print_header() {
    echo -e "\033[1m\033[34m$APPLICATION_NAME\033[0m $APPLICATION_VERSION\033[0m"
    echo -e "\033[2m  (c) 2018 TechDivision GmbH\033[0m\n"
}

#######################################
# Prints the console tool header
# Globals:
#   LC_NUMERIC
#   APPLICATION_END_TIME
#   APPLICATION_EXECUTION_TIME
#   APPLICATION_NAME
#   APPLICATION_VERSION
#   APPLICATION_MODE
# Arguments:
#   None
# Returns:
#   None
#######################################
function print_footer() {
    LC_NUMERIC="en_US.UTF-8"

    APPLICATION_END_TIME=$(ruby -e 'puts Time.now.to_f')
    APPLICATION_EXECUTION_TIME=$(echo "$APPLICATION_END_TIME - $APPLICATION_START_TIME" | bc);

    printf "\n"
    printf "\e[34m"
    printf "\n"
    printf "\e[1mDebug information:\033[0m"
    printf "\e[34m"
    printf "\n"
    printf "  Version: \e[1m%s\033[0m\n" "$APPLICATION_VERSION"
    printf "\e[34m"
    printf "  Application mode: \e[1m%s\033[0m\n" "$APPLICATION_MODE"
    printf "\e[34m"
    printf "  Execution time: \e[1m%f sec.\033[0m\n" "$APPLICATION_EXECUTION_TIME"
    printf "\e[34m"
    printf "  Logfile: \e[1m%s\033[0m\n" "$LOG_FILE"
    printf "\e[34m"
    printf "  Exitcode: \e[1m%s\033[0m\n" "$APPLICATION_RETURN_CODE"
    printf "\e[34m\033[0m"
    printf "\n"
}

#######################################
# Print usage help and command list
# Globals:
#   BASE_DIR
# Arguments:
#   None
# Returns:
#   None
#######################################
function print_usage() {
    local cmd_output_space='                                '
    printf "\e[33mUsage:\e[39m\n"
    printf "  command [options] [arguments]\n"
    printf "\n"
    printf "\e[32m  -h, --help            \e[39mDisplay this help message\n"
    printf "\e[32m  -v, --version         \e[39mDisplay this application version\n"
    printf "\n"
    printf "\e[33mAvailable commands:\e[39m\n"

    if [ -d "$BASE_DIR/playbooks" ]; then
        for file in ./playbooks/**.yml; do
            local cmd_name=$(basename $file .yml);
            local cmd_description=$(grep '^\#[[:space:]]@description:' -m 1 $file | awk -F'"' '{ print $2}');
            printf "  \e[32m%s %s \e[39m${cmd_description}\n" $cmd_name "${cmd_output_space:${#cmd_name}}"
        done
    fi

    if [ ! -d "$INSTALL_DIR" ]; then
        local cmd_name="install"
        local cmd_description="Installs valet.sh"
        printf "  \e[32m%s %s \e[39m${cmd_description}\n" $cmd_name "${cmd_output_space:${#cmd_name}}"
    fi
}

#######################################
# Prepares logfile
# Globals:
#   LOG_PATH
#   LOG_FILE
# Arguments:
#   Command
# Returns:
#   None
#######################################
function prepare_logfile() {
    # define log file
    LOG_PATH=${BASE_DIR}/log
    if [ ! -d "$LOG_PATH" ]; then
        mkdir "$LOG_PATH" || log error "Failed to create log directory"
    fi
    LOG_FILE="$( mktemp ${LOG_PATH}/XXXXXXXXXXXXX ).log"
}

#######################################
# Cleanup logfiles
# Globals:
#   LOG_PATH
# Arguments:
#   Command
# Returns:
#   None
#######################################
function cleanup_logfiles() {
    # cleanup log directory and keep last 10 execution logs
    if [ -d "$LOG_PATH" ]; then
        cleanup_logfiles=$(ls -d1 -t1 "${LOG_PATH}/*" | tail -n +11)
        test "$cleanup_logfiles" && rm "$cleanup_logfiles"
    fi
}

#######################################
# Executes command via ansible playbook
# Globals:
#   ANSIBLE_PLAYBOOKS_DIR
#   APPLICATION_RETURN_CODE
# Arguments:
#   Command
# Returns:
#   None
#######################################
function execute_ansible_playbook() {
    local command=$1
    local ansible_playbook_file="$ANSIBLE_PLAYBOOKS_DIR/$command.yml"
    local parsed_args=""
    local ansible_ret_code=0

    # prepare cli arguments if given and transform them to ansible extra vars format
    if [ "$#" -gt 1 ]; then
        for i in `seq 2 $#`; do  if [ $i -gt 2 ]; then parsed_args+=,; fi; parsed_args+="\"${!i}\""; done
    fi

    # define complete extra vars object
    read -r -d '' ansible_extra_vars << EOM
--extra-vars='{
    "cli": {
        "name": ${APPLICATION_NAME},
        "mode": ${APPLICATION_MODE},
        "version": ${APPLICATION_VERSION},
        "args": [${parsed_args}]
    }
}'
EOM

    # check if requested playbook yml exist and execute it
    if [ -f "$ansible_playbook_file" ]; then
        prepare_logfile

        spinner_toggle "Running \e[32m$command\e[39m"
        bash -c "ansible-playbook ${ansible_playbook_file} ${ansible_extra_vars}" &> ${LOG_FILE} || ansible_ret_code=$? && true
        spinner_toggle

        # log exact command line as typed in shell with user and path info
        echo "$PWD $USER: $0 $*" >> ${LOG_FILE}

        cleanup_logfiles

        # check if exit code was not 0
        if [ $ansible_ret_code != 0 ]; then
            out error
        else
            out success
        fi

    else
        out error "Command '$command' not available"
    fi

    # set global ret code like ansible ret code
    APPLICATION_RETURN_CODE=$ansible_ret_code
}

#######################################
# Error handling and abort function with log message
# Globals:
#   None
# Arguments:
#   Command
# Returns:
#   None
#######################################
function error() {
    # output error message to user
    out error "$*"
    # Todo: constants for return codes
    APPLICATION_RETURN_CODE=255
    # trigger immediate shutdown
    shutdown
}

#######################################
# Shutdown cli client script
# Globals:
#   APPLICATION_RETURN_CODE
# Arguments:
#   Command
# Returns:
#   None
#######################################
function shutdown() {
    # Tidyup spinner PID
    if [[ -n "$SPINNER_PID" && "$SPINNER_PID" -gt 0 ]]; then
        kill "$SPINNER_PID" &> /dev/null
    fi
    # Remove APPLICATION_INPROGRESS file
    rm -rf "$APPLICATION_INPROGRESS_FILE_PATH" &> /dev/null
    # exit
    exit "$APPLICATION_RETURN_CODE"
}

#######################################
# Main
# Globals:
#   None
# Arguments:
#   Command
#   Subcommand
# Returns:
#   None
#######################################
function main() {
    init
    print_header
    prepare

    case "${1--h}" in
        -h) print_usage;;
        -v) ;;
        upgrade) install_upgrade;;
        # try to execute playbook based on command
        # ansible will throw an error if specific playbook does not exist
        *) execute_ansible_playbook "$@";;
    esac

    print_footer
    shutdown
}

#######################################
# Run tests via bats
# Globals:
#   None
# Arguments:
#   None
# Returns:
#   None
#######################################
function run_tests() {
    # export all functions for testing purpose
    export -f out
    export -f version_validate
    export -f version_compare
    export -f is_installed

    # execute tests via bats
    bats tests
}

# start cli with given command line args
${MAIN_FUNCTION} "$@";
