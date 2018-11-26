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

# track start time
APPLICATION_START_TIME=$(ruby -e 'puts Time.now.to_f');

# define application to be auto startet in case of testing purpose for example
: "${APPLICATION_AUTOSTART:=1}"
# define default application mode for future usage
: "${APPLICATION_MODE:=production}"
# define default spinner enabled
: "${SPINNER_ENABLED:=1}"
# define application return codes
APPLICATION_RETURN_CODE_ERROR=255
APPLICATION_RETURN_CODE_SUCCESS=0
# set default return code 0
APPLICATION_RETURN_CODE=$APPLICATION_RETURN_CODE_SUCCESS
# define default setting for debug info output
APPLICATION_DEBUG_INFO_ENABLED=0;
# define user export path enhancement
# shellcheck disable=SC2016
APPLICATION_EXPORT_PATH='export PATH="$PATH:$HOME/.valet-sh"'
# define variables
APPLICATION_NAME="valet.sh"
# define default git relevant variables
APPLICATION_GIT_NAMESPACE=${APPLICATION_GIT_NAMESPACE:="valet-sh"}
APPLICATION_GIT_REPOSITORY=${APPLICATION_GIT_REPOSITORY:="valet-sh"}
APPLICATION_GIT_URL=${APPLICATION_GIT_URL:="https://github.com/${APPLICATION_GIT_NAMESPACE}/${APPLICATION_GIT_REPOSITORY}"}
# define default playbook dir
ANSIBLE_PLAYBOOKS_DIR="playbooks"
# define semver regular expression for checkout valid versions on upgrade
SEMVER_REGEX="^(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)(\\-[0-9A-Za-z-]+(\\.[0-9A-Za-z-]+)*)?(\\+[0-9A-Za-z-]+(\\.[0-9A-Za-z-]+)*)?$"
# define global temp dir
TEMP_DIR="/tmp"
# temporary application-in-progress file used e.g. by ansible or spinner function
APPLICATION_INPROGRESS_FILE_PATH="${TEMP_DIR}/valet-sh.inprogress"
# define default install directory
INSTALL_DIR="$HOME/.${APPLICATION_GIT_REPOSITORY}";
# resolve symlinked bash source if needed
test -h "${BASH_SOURCE[0]}" && SCRIPT_PATH="$(readlink "${BASH_SOURCE[0]}")" || SCRIPT_PATH="${BASH_SOURCE[0]}"
# use current bash source script dir as base_dir
BASE_DIR="$( dirname "${SCRIPT_PATH}" )"
# define log filepath
LOG_PATH=${BASE_DIR}/log

# check if git dir is available in base dir
if [ -d "${BASE_DIR}/.git" ]; then
    # get the current version from git
    APPLICATION_VERSION=$(git --git-dir="${BASE_DIR}/.git" --work-tree="${BASE_DIR}" describe --tags)
    # set cwd to base dir
    cd "${BASE_DIR}" || error "Unable to set cwd to ${BASE_DIR}"
fi

##############################################################################
# Toggles spinner animation
##############################################################################
spinner_toggle() {
    # check if spinner animation is globally enabled
    if [ "${SPINNER_ENABLED}" != "1" ]
    then
        return 0
    fi
    # start spinner background function
    function _spinner_start() {
        local list=( "$(echo -e '\xe2\xa0\x8b')"
                     "$(echo -e '\xe2\xa0\x99')"
                     "$(echo -e '\xe2\xa0\xb9')"
                     "$(echo -e '\xe2\xa0\xb8')"
                     "$(echo -e '\xe2\xa0\xbc')"
                     "$(echo -e '\xe2\xa0\xb4')"
                     "$(echo -e '\xe2\xa0\xa6')"
                     "$(echo -e '\xe2\xa0\xa7')"
                     "$(echo -e '\xe2\xa0\x87')"
                     "$(echo -e '\xe2\xa0\x8f')" )
        local i=0
        tput sc
        # wait for .inprogress flag file to be created by ansible callback plugin
        while [ ! -f "$APPLICATION_INPROGRESS_FILE_PATH" ]; do sleep 0.5; done
        while true; do
            printf "\\e[32m%s\\e[39m $1 " "${list[i]}"
            i=$((i+1))
            i=$((i%10))
            sleep 0.1
            tput rc
        done
    }
    # stop spinner background function
    function _spinner_stop() {
        kill "$SPINNER_PID" > /dev/null 2>&1
        wait "$!" 2>/dev/null
        SPINNER_PID=0
        rm -rf "$APPLICATION_INPROGRESS_FILE_PATH"
        tput rc
    }
    # check if spinner pid doen not exist
    if [[ "$SPINNER_PID" -lt 1 ]]; then
        tput sc
        # if function has $2 given with -f then force spinner to start on
        # toggle call by touching inprogress file on its own
        if [[ "$#" -eq "2" && "$2" = "-f" ]]; then
            touch "$APPLICATION_INPROGRESS_FILE_PATH"
        fi
        _spinner_start "$1" &
        SPINNER_PID="$!"
    else
        _spinner_stop
    fi
}

##############################################################################
# Logs messages in given type
##############################################################################
function out() {
    case "${1--h}" in
        error) printf "\\033[1;31m✘ %s\\033[0m\\n" "$2";;
        success) printf "\\033[1;32m✔ %s\\033[0m\\n" "$2";;
        task) printf "▸ %s\\n" "$2";;
        *) printf "%s\\n" "$*";;
    esac
}

##############################################################################
# Validates version against semver
##############################################################################
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
            return 0
        else
            return 0
        fi
    fi
    return 1
}

##############################################################################
# Compares versions
##############################################################################
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

##############################################################################
# Returns if application is installed
##############################################################################
function is_installed() {
    if [ -d "${INSTALL_DIR}" ]
    then
        return 0
    else
        return 1
    fi
}

##############################################################################
# Prepares application by installing dependencies and itself
##############################################################################
function prepare() {
    install_deps
    # install application if not done yet
    if ! is_installed; then
        selfinstall
        # shutdown after initial installation
        shutdown $APPLICATION_RETURN_CODE_SUCCESS
    fi
    # set cwd to base dir
    cd "${BASE_DIR}" || error "Unable to set cwd to ${BASE_DIR}"
}

##############################################################################
# Install ansible if not availabe
##############################################################################
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

        spinner_toggle "Installing Ansible" -f
        # if ansible is not available, install pip and ansible
        # Todo: Redirect output to logfile
        sudo easy_install pip &> /dev/null || error "Failed to installed pip"
        sudo pip install -Iq ansible &> /dev/null || error "Failed to install ansible"
        spinner_toggle
    fi

    # verfiy all dependencies
    verify_deps
}


##############################################################################
# Verify dependencies
##############################################################################
function verify_deps() {
    # check if ansible command is available
    if [ ! -x "$(command -v ansible-playbook)" ]; then
        error "Dependency not met: Failed to run ansible-playbook command"
    fi
}

##############################################################################
# Uninstall application
##############################################################################
function uninstall() {
    # TODO: call ansible playbook to uninstall all installed packages 
    #       and remove services first
    # TODO: remove PATH enhancements in zshrc and bash_profile dotfiles
    spinner_toggle "Uninstalling" -f
    # remove application itselfe
    rm -rf "${INSTALL_DIR}" &> /dev/null
    spinner_toggle
    out success "Successfully uninstalled ${APPLICATION_NAME}. Good bye :)"
    shutdown
}

##############################################################################
# Install meachanism
##############################################################################
function selfinstall() {
    # check if not installed
    if ! is_installed;
    then
        spinner_toggle "Installing" -f
        # remove old install directory (< version 1.0.0-alpha10)
        rm -rf "${HOME}/.valet.sh"
        # create tmp directory for cloning valet.sh
        local tmp_dir
        tmp_dir=$(mktemp -d) || error "Failed to create temporary directory, try running script at different path"
        local src_dir
        src_dir="$tmp_dir"
        # clone project git repo to tmp dir
        rm -rf "$tmp_dir" &> /dev/null
        git clone --quiet "$APPLICATION_GIT_URL" "$tmp_dir"
        # install
        cp -r "${src_dir}" "${INSTALL_DIR}"
        # get latest version
        LATEST_VERSION=$(git_checkout_latest_version)
        # remove tmp src dir
        rm -rf "${src_dir}" &> /dev/null
        # create PATH enhancement in relevant dotfiles
        touch ~/.bash_profile
        grep -q "${APPLICATION_EXPORT_PATH}" "${HOME}/.bash_profile" || echo "${APPLICATION_EXPORT_PATH}" >> "${HOME}/.bash_profile"
        grep -q "${APPLICATION_EXPORT_PATH}" "${HOME}/.zshrc" || echo "${APPLICATION_EXPORT_PATH}" >> "${HOME}/.zshrc"
        # execute PATH enhancement
        # shellcheck disable=SC1090
        source "${HOME}/.bash_profile"
        # stop spinner
        spinner_toggle
        # output log
        out success "Successfully installed version ${LATEST_VERSION}"
    fi
}

##############################################################################
# Upgrade meachanism
##############################################################################
function upgrade() {
    spinner_toggle "Upgrading" -f
    # get latest version
    LATEST_VERSION=$(git_checkout_latest_version)
    # stop spinner
    spinner_toggle
    # output specific upgrade status message
    if [ "$(version_compare "${APPLICATION_VERSION}" "${LATEST_VERSION}")" = "0" ]; then
        out success "Already on the latest version $LATEST_VERSION"
    else
        out success "Successfully upgraded from ${APPLICATION_VERSION} to latest version ${LATEST_VERSION}"
    fi
}

##############################################################################
# Fetches all tags from remote and checkouts latest semver compatible version
##############################################################################
function git_checkout_latest_version() {
    # fetch all tags from application git repo
    git --git-dir="${INSTALL_DIR}/.git" --work-tree="${INSTALL_DIR}" fetch --tags --quiet
    # get available release tags sorted by refname
    RELEASE_TAGS=$(git --git-dir="${INSTALL_DIR}/.git" --work-tree="${INSTALL_DIR}" tag --sort "-v:refname" )
    # get latest semver conform git version tag on current major version releases
    for GIT_TAG in $RELEASE_TAGS; do
        if version_validate "${GIT_TAG}"; then
            git --git-dir="${INSTALL_DIR}/.git" --work-tree="${INSTALL_DIR}" checkout --force --quiet "${GIT_TAG}"
            echo "${GIT_TAG}"
            return 0
        fi
    done
}

##############################################################################
# Prints the console tool header
##############################################################################
function print_header() {
    echo -e "\\033[1m$APPLICATION_NAME\\033[0m \\033[34m$APPLICATION_VERSION\\033[0m\\n"
}

##############################################################################
# Prints the console tool header
##############################################################################
function print_footer() {
    LC_NUMERIC="en_US.UTF-8"

    APPLICATION_END_TIME=$(ruby -e 'puts Time.now.to_f')
    APPLICATION_EXECUTION_TIME=$(echo "$APPLICATION_END_TIME - $APPLICATION_START_TIME" | bc);

    printf "\\n"

    if [ $APPLICATION_DEBUG_INFO_ENABLED = 1 ]; then
        printf "\\e[34m"
        printf "\\e[1mDebug information:\\033[0m"
        printf "\\e[34m"
        printf "\\n"
        printf "  Version: \\e[1m%s\\033[0m\\n" "$APPLICATION_VERSION"
        printf "\\e[34m"
        printf "  Application mode: \\e[1m%s\\033[0m\\n" "$APPLICATION_MODE"
        printf "\\e[34m"
        printf "  Execution time: \\e[1m%f sec.\\033[0m\\n" "$APPLICATION_EXECUTION_TIME"
        printf "\\e[34m"
        printf "  Logfile: \\e[1m%s\\033[0m\\n" "$LOG_FILE"
        printf "\\e[34m"
        printf "  Exitcode: \\e[1m%s\\033[0m\\n" "$APPLICATION_RETURN_CODE"
        printf "\\e[34m\\033[0m"
        printf "\\n"
    fi
}

##############################################################################
# Print usage help and command list
##############################################################################
function print_usage() {
    local cmd_output_space='        '
    local cmd_name="-x"
    printf "\\e[33mUsage:\\e[39m\\n"
    printf "  command [options] [command] [arguments]\\n"
    printf "\\n"
    printf "\\e[33mOptions:\\e[39m\\n"
    printf "\\e[32m  -h %s \\e[39mDisplay this help message\\n" "${cmd_output_space:${#cmd_name}}"
    printf "\\e[32m  -v %s \\e[39mDisplay this application version\\n" "${cmd_output_space:${#cmd_name}}"
    printf "\\e[32m  -d %s \\e[39mDisplay debug information\\n" "${cmd_output_space:${#cmd_name}}"
    printf "\\n"
    printf "\\e[33mCommands:\\e[39m\\n"

    local cmd_name="upgrade"
    local cmd_description="Upgrade valet.sh to latest version"
    printf "  \\e[32m%s %s \\e[39m${cmd_description}\\n" "${cmd_name}" "${cmd_output_space:${#cmd_name}}"

    if [ -d "$BASE_DIR/playbooks" ]; then
        for file in ./playbooks/**.yml; do
            local cmd_name
            cmd_name="$(basename "${file}" .yml)"
            local cmd_description
            cmd_description=$(grep '^\#[[:space:]]@description:' -m 1 "${file}" | awk -F'"' '{ print $2}');
            if [ ! -z "${cmd_description}" ]; then
                printf "  \\e[32m%s %s \\e[39m${cmd_description}\\n" "${cmd_name}" "${cmd_output_space:${#cmd_name}}"
            fi
        done
    fi
}

##############################################################################
# Prepares logfile
##############################################################################
function prepare_logfile() {
    if [ ! -d "$LOG_PATH" ]; then
        mkdir "$LOG_PATH" || log error "Failed to create log directory"
    fi
    LOG_FILE="${LOG_PATH}/${APPLICATION_START_TIME}.log"
    touch "${LOG_FILE}"
}

##############################################################################
# Cleanup logfiles
##############################################################################
function cleanup_logfiles() {
    # cleanup log directory and keep last 10 execution logs
    if [ -d "$LOG_PATH" ]; then
        find "${LOG_PATH}" -type f | sort -r | tail -n +10 | xargs rm -rf {}
    fi
}

##############################################################################
# Executes command via ansible playbook
##############################################################################
function execute_ansible_playbook() {
    local command=$1
    local ansible_playbook_file="$ANSIBLE_PLAYBOOKS_DIR/$command.yml"
    local parsed_args=""

    # prepare cli arguments if given and transform them to ansible extra vars format
    if [ "$#" -gt 1 ]; then
        for i in $(seq 2 $#); do  if [ "${i}" -gt 2 ]; then parsed_args+=,; fi; parsed_args+="\"${!i}\""; done
    fi
    # define complete extra vars object
    read -r -d '' ansible_extra_vars << EOM
{
    "cli": {
        "name": "${APPLICATION_NAME}",
        "mode": "${APPLICATION_MODE}",
        "version": "${APPLICATION_VERSION}",
        "args": [${parsed_args}]
    }
}
EOM
    ansible_extra_vars=("--extra-vars" "${ansible_extra_vars}")

    # check if requested playbook yml exist and execute it
    if [ -f "$ansible_playbook_file" ]; then
        # prepare log file
        prepare_logfile
        # start spinner in waiting mode
        spinner_toggle "Running \\e[32m$command\\e[39m"
        # execute ansible-playbook with given params
        ansible-playbook "${ansible_playbook_file}" "${ansible_extra_vars[@]}" || APPLICATION_RETURN_CODE=$?
        # stop spinner
        spinner_toggle
        # log exact command line as typed in shell with user and path info
        echo "${PWD} ${USER}: $0 $*" >> "${LOG_FILE}"
        # cleanup logfiles
        cleanup_logfiles
    else
        out error "Command '$command' not available"
    fi
}

##############################################################################
# Error handling and abort function with log message
##############################################################################
function error() {
    # check if error message is given
    if [ -z "$*" ]; then
        echo "no error message given"
        shutdown $APPLICATION_RETURN_CODE_ERROR
    fi
    # output error message to user
    out error "$*"    
    # trigger immediate shutdown
    shutdown $APPLICATION_RETURN_CODE_ERROR
}

##############################################################################
# Shutdown cli client script
##############################################################################
function shutdown() {
    # kill spinner by pid
    if [[ -n "${SPINNER_PID}" && "${SPINNER_PID}" -gt 0 ]]; then
        kill "${SPINNER_PID}" &> /dev/null
        wait "$!" 2>/dev/null
    fi
    # remove APPLICATION_INPROGRESS file
    rm -rf "${APPLICATION_INPROGRESS_FILE_PATH}" &> /dev/null
    # exit
    if [ "$1" ]; then
        APPLICATION_RETURN_CODE=$1
    fi
    exit "${APPLICATION_RETURN_CODE}"
}

##############################################################################
# Process all bash args given from shell
##############################################################################
function process_args() {
    # check if no arguments were given
    if [ $# -eq 0 ];
    then
        # just display usage in case of zero arguments
        print_usage
    else
        # parse options first and handle it
        while getopts "dvh" opt; do
            case $opt in
                d)
                    # enable debug info
                    APPLICATION_DEBUG_INFO_ENABLED=1
                    ;;
                v)
                    # immediate shutdown to display version only
                    shutdown
                    ;;
                h)
                    # print usage for help
                    print_usage
                    ;;
                *)
                    # error in this case
                    error "Invalid option: -${OPTARG}"
            esac
        done
        shift $((OPTIND-1))
        # handle remaining args if given
        if [ ! -z "$*" ]; then 
            case "${1--h}" in
                upgrade) upgrade;;
                uninstall) uninstall;;
                # try to execute playbook based on command
                # ansible will throw an error if specific playbook does not exist
                *) execute_ansible_playbook "$@";;
            esac
        else
            print_usage
        fi
    fi
}

##############################################################################
# Main
##############################################################################
function main() {
    print_header
    prepare
    process_args "$@"
    print_footer
    shutdown
}

# start cli with given command line args if autostart is enabled
if [ "${APPLICATION_AUTOSTART}" = "1" ]; then
    main "$@";
fi
