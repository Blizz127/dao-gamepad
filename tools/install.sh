#!/usr/bin/env bash
# Install or remove the dao-gamepad proxy DLL in a Dragon Age: Origins install.
#
#   tools/install.sh install   [GAME_DIR]
#   tools/install.sh uninstall [GAME_DIR]
#   tools/install.sh status    [GAME_DIR]
#
# Only bin_ship/dinput8.dll and bin_ship/dao_gamepad.log are ever touched. Install refuses to
# overwrite a dinput8.dll it did not put there, and refuses unless DAOrigins.exe is the pinned build.
set -euo pipefail

PINNED_EXE_SHA256=400c2c9e97bb1a534121553be66f202429ef6f7320c93c86f9b7a491864647bd
REPO_DIR=$(cd "$(dirname "$0")/.." && pwd)
DEFAULT_GAME_DIR="$HOME/.local/share/Steam/steamapps/common/Dragon Age Ultimate Edition"
MARKER_NAME=.dao_gamepad_installed

cmd=${1:-status}
game_dir=${2:-$DEFAULT_GAME_DIR}
bin_ship="$game_dir/bin_ship"
target="$bin_ship/dinput8.dll"
marker="$bin_ship/$MARKER_NAME"
built="$REPO_DIR/build/dinput8.dll"

sha() { sha256sum "$1" | cut -d' ' -f1; }

die() { echo "error: $*" >&2; exit 1; }

[[ -f "$bin_ship/DAOrigins.exe" ]] || die "no DAOrigins.exe under $bin_ship"

case "$cmd" in
install)
    [[ -f "$built" ]] || die "build first: make"
    [[ "$(sha "$bin_ship/DAOrigins.exe")" == "$PINNED_EXE_SHA256" ]] || die "DAOrigins.exe is not the pinned build"
    if [[ -e "$target" ]]; then
        [[ -f "$marker" && "$(sha "$target")" == "$(cat "$marker")" ]] \
            || die "$target exists and was not installed by dao-gamepad; refusing to overwrite"
    fi
    cp "$built" "$target"
    sha "$target" > "$marker"
    echo "installed $target ($(cat "$marker"))"
    ;;
uninstall)
    if [[ ! -e "$target" ]]; then
        echo "nothing installed"; rm -f "$marker"; exit 0
    fi
    [[ -f "$marker" && "$(sha "$target")" == "$(cat "$marker")" ]] \
        || die "$target was not installed by dao-gamepad (or was modified); leaving it alone"
    rm -f "$target" "$marker" "$bin_ship/dao_gamepad.log"
    echo "removed dao-gamepad from $bin_ship"
    ;;
status)
    if [[ -f "$marker" && -e "$target" ]]; then
        echo "installed: $target sha256 $(sha "$target") (marker $(cat "$marker"))"
    elif [[ -e "$target" ]]; then
        echo "foreign dinput8.dll present: $target"
    else
        echo "not installed"
    fi
    if [[ -f "$bin_ship/dao_gamepad.log" ]]; then
        echo "log: $bin_ship/dao_gamepad.log"
    fi
    ;;
*)
    die "usage: $0 install|uninstall|status [GAME_DIR]"
    ;;
esac
