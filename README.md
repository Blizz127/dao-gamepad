# dao-gamepad

Native controller support for **Dragon Age: Origins – Ultimate Edition** (Steam, PC), ported from the
console versions, plus quality-of-life cleanup: start straight into the game (no launcher / config tool),
settings inside the game, intro movies once.

**Status: early.** Analysis is done (see `notes/`); the current DLL is a *log-only* stage-0 build that
verifies the game build and observes the input loop. It does not add controller support yet.

Targets Linux (Proton) and Windows 10/11.

## What's here

| Path | What |
|---|---|
| `notes/phase1-recon.md` | Static analysis of the PC and PS3 builds (input path, GUI ⇄ gamepad layer) |
| `notes/design-checkpoint.md` | The port design and open questions |
| `src/` | `dinput8.dll` proxy (32-bit, MinGW) |
| `tools/` | Read-only analysis tools (ERF/GFX readers, PPC address scanner, Ghidra scripts), `install.sh` |
| `tests/` | Unit tests for the tools (synthetic inputs only) |

No game files are in this repository. Console GUI assets are meant to be extracted locally from your own
copy of the game; nothing from the PC or PS3 releases is redistributed.

## Build and test

Requires `i686-w64-mingw32-gcc` and Python 3.

```sh
make        # build/dinput8.dll
make test   # unit tests
```

## Install (Linux / Proton)

```sh
tools/install.sh install     # copies build/dinput8.dll into bin_ship (pinned build only)
tools/install.sh status
tools/install.sh uninstall   # removes only what install put there
```

Steam launch options (load the proxy and skip the BioWare launcher; the launcher skip is unverified):

```
WINEDLLOVERRIDES="dinput8=n,b" bash -c 'exec "${@/DAOriginsLauncher.exe/bin_ship\/DAOrigins.exe}"' -- %command%
```

On Windows, copy `dinput8.dll` into `bin_ship` next to `DAOrigins.exe`; no override is needed.

Supported build: Steam buildid 21245176, `DAOrigins.exe` sha256
`400c2c9e97bb1a534121553be66f202429ef6f7320c93c86f9b7a491864647bd`. Any other build is left untouched.
