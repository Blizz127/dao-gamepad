# Design checkpoint — DA:O Ultimate (Steam) native gamepad port

Status: PROPOSED (static analysis only; nothing written to the game folder; no runtime proof)
Date: 2026-10-03
Evidence: notes/phase1-recon.md (addresses are for Steam buildid 21245176,
DAOrigins.exe sha256 400c2c9e…647bd, analysed via the Steamless-unpacked copy 659ceab2…3ce).

## What exists where

| Layer | PC (Steam) | PS3 (eclipse.elf) |
|---|---|---|
| Controller device read | absent (DirectInput keyboard + mouse only) | present |
| Gamepad input codes `0x4xxxxxxx`, 36 names | present (`FUN_00882680`) | present |
| Console actions (radial target/party/conversation, analog target) | present (`FUN_00895f10`, ids 51–72) | present |
| Thumbstick / analog-target messages | present (`FUN_0078d1a0` family) | present |
| Default gamepad bindings | none found in data; not in KeyBindings.ini | compiled in (to locate) |
| GUI ⇄ gamepad layer (7 ExternalInterface handlers + dispatcher) | absent | present (`0x730bc8`… table, dispatcher `0x738e20`) |
| Console GUI movies (radialquickbar, battlemenu, combinedhud, container, skills, tutorial, load_controller, …) | absent | present (`guiexport.erf` V2.1) |

## Proposed components

1. **Loader** — proxy DLL loaded by the game under Proton (`dinput8.dll` proxy, forwarding to the real one;
   `WINEDLLOVERRIDES="dinput8=n,b"` in Steam launch options). Refuses to patch unless the exe sha256 matches
   the pinned build.
2. **Gamepad input backend** — wrap input-manager vtable slot [1] (`0xb2ed2c`, `Update` at `0x8804f0`):
   call original, then poll XInput and append events with code `0x40000000 | index` (index table in
   phase1-recon.md) to the manager's event vector, and maintain analog state for indices 0x20–0x23 and triggers.
   Only an `.rdata` pointer is changed; no `.text` bytes.
3. **GUI gamepad layer** (port of the PS3 design, re-implemented in the DLL):
   - listener stack, lock target, forward flag (PS3 GUI manager +0x4c/+0x5c/+0x1b semantics);
   - handlers `EnableGamepadEvents(movie)`, `DisableGamepadEvents(movie)`, `ForwardGamepadInput()`,
     `LockGamepadInput()` registered through the PC registrar `0x520280` (same call `FUN_00521af0` uses);
     handler ABI `void __cdecl (ctx, GFxValue* args, unsigned argc)`;
   - per frame: for each queued gamepad event, invoke `Gamepad.ReportGamepadEvent(index, state & 0xF0000)` on the
     topmost visible listener, continuing down only while the movie calls `ForwardGamepadInput()`;
   - `DispatchScriptEvent`, `DispatchTrainingEvent`, `IsShapeshifted`: implement after reading PS3 bodies
     (`0x736284`, `0x7361ac`; IsShapeshifted via the `0x2c16xx` table).
4. **Console GUI movies** — PS3 `.gfx` files extracted locally from the user's own dump at install time and
   placed in the game's override folder (never committed). Shared movies: decide per screen whether the PS3 or
   PC variant is used (mouse users keep PC screens when no pad is connected — OPEN).
5. **Default bindings** — read the PS3 compiled-in gamepad defaults and apply them as `Gamepad::*` entries
   (KeyBindings.ini `_1` slots for GUI commands; action-table defaults via the DLL). Location in PS3 code: OPEN.
6. **Intro skip** — `DragonAge.ini [Movies] DisableIntroMovies=1` after the first run (set manually today).
7. **In-game settings** — restore the cut Video-tab widgets (anisotropic filtering, refresh rate, trilinear,
   triple buffering, desktop gamma, shadows) whose labels still exist in `optionsmenu.gfx`.

## Open / unresolved before building
- How analog values reach the PC action system (no gamepad state table found yet). → runtime trace or
  PS3 `0x74328c`/`0x7442b8` (GUI manager reads analog ids 0x56–0x5b by value) to mirror.
- Where the PS3 GUI manager's event queue (+0x244/+0x248) is filled, i.e. which input events reach it.
- Whether PS3 movies load and render correctly in the PC Scaleform player.
- Whether SteamStub checks `.rdata` integrity at runtime.
- PS3 default gamepad binding table location.

## Acceptance levels (kept separate)
1. Build + unit tests (code-format helpers, ERF/GFX tools).
2. Runtime: game boots under Proton with the DLL; log shows hook installed; gamepad events reach the queue.
3. Visual: captures of radial quickbar / combat HUD driven by the pad.
4. Human: your own playthrough with a controller — the only "it works" gate.
