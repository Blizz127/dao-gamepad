# Phase 1 recon — Dragon Age: Origins Ultimate (Steam) gamepad port

Status: IN PROGRESS (read-only; nothing written to the game folder)

## Pins
- PC: Steam app 47810, buildid 21245176
  - `bin_ship/DAOrigins.exe` sha256 `400c2c9e97bb1a534121553be66f202429ef6f7320c93c86f9b7a491864647bd`
  - PE32 i386, 10,594,144 bytes
- PS3 dump: `~/Games/ps3-dumps/DAO/` (copied from `gdrive:Dropbox/RetroBat/roms/ps3/Dragon Age Origins.ps3`)
  - Main binary appears to be `USRDIR/eclipse.self` (23 MB); `EBOOT.BIN` is 141 KB. UNVERIFIED which one holds the game.
  - Copy verified: `rclone check --one-way` 0 differences, 12,671 files, 15,914,309,014 bytes.
  - `eclipse.self` sha256 `39be921e5c89274a15585b67790b75eec9437cbb9f5890262e05ff35fea43b15`
  - Decrypted (RPCS3 0.0.43 `--decrypt`, on a copy in work/ps3bin) → `eclipse.elf`
    sha256 `95f4c2cb16bcd7b5ca52abf0efb75fa8df5f1684b82f8eb5cf4977da641216bc`
    (ELF64 MSB PowerPC, Cell LV2, static, stripped). EBOOT.BIN (launcher) was not decrypted; not needed yet.

## PC executable findings (static strings + PE imports only)
- Imports `DINPUT8.dll` (`DirectInput8Create`); no static XInput import. Dynamic XInput load: UNVERIFIED.
- Input namespaces in strings: `Keyboard::` (139), `Gamepad::` (36), `Mouse::` (12).
- Full `Gamepad::` set present: DPad*, Start, Back, Left/RightThumb, Left/RightShoulder,
  Bottom/Right/Left/TopAction, Left/RightTrigger, ThumbLX/LY/RX/RY, 8-way Left/RightThumb directions.
- Console-style input names present: `RadialTargetMode`, `RadialTargetingX/YAxis`,
  `RadialPartySelectMode/X/Y`, `ConversationRadialSelectX/Y`, `LinearAnalogTargetMode/X/Y`,
  `AnalogScrollValue`, `LeftThumbstickMessage`, `RightThumbstickMessage`.
- RTTI: `MemberFunctionMessageHandler<GameModeExplore, ActivateAnalogTargetModeMessage>` —
  a game-mode handler for analog targeting is compiled in.
- No PC data/ini/xml file references `Gamepad::` or the radial names (grep over install dir).

## DRM / static-analysis blocker
- `DAOrigins.exe` is SteamStub-wrapped: `.text` entropy 8.00 (encrypted), entry point 0xded2ee in `.bind` (entropy 8.00).
- Consequence: Ghidra finds 0 code xrefs to any input string (incl. `Mouse::*`, which is certainly used).
  UTF-16 name strings live in `.rdata` (e.g. `Gamepad::DPadUp` @0xb2f3c4) but nothing readable points at them.
- Byte search (on-disk, partial because .text is encrypted): GUID_SysKeyboard/SysMouse/XAxis present;
  GUID_Joystick/RzAxis/POV absent. Suggestive only — UNVERIFIED until .text is decrypted.
- Static analysis needs a decrypted copy under `work/` (installed exe stays untouched). Done via Steamless after user approval (see Steamless section).

## Settings observed after first launch (Proton prefix, Documents/BioWare/Dragon Age/Settings)
- `DragonAge.ini [Movies]`: `DisableIntroMovies=0`, `FirstRun=0`, intros `dragon_age_ea_logo.bik`, `dragon_age_main.bik`.
- `[VideoOptions]` came out 800x600, GraphicsDetailLevel=0, AA 0 — likely Proton mis-detection.
- `KeyBindings.ini`: `<Action>_0` / `<Action>_1` slots, values like `Keyboard::Button_F1`, `Shift + Keyboard::Button_F1`.

## Added scope (user request 2026-10-03)
- Intro movies: play once, then skip (candidate: `DisableIntroMovies` after first run; UNVERIFIED).
- Fold `DAOriginsConfig.exe` settings into the in-game options menu (graphics, sound, ...).

## In-game options vs config tool (static, PC only)
- `guiexport.erf` → `optionsmenu.gfx` (CFX/zlib Scaleform v8). Video and Audio tabs exist in-game.
- Widgets present (`Opt*_mc`): Resolution, Fullscreen, VSync, Gamma, Antialiasing, GraphicsDetail,
  TextureQuality, SoundFXVolume, MusicVolume, DialogVolume, DisableSound/Music/Dialog, UseStereoSound, Subtitles.
- `DragonAge.ini` keys with NO in-game widget: AnisotropicFilteringLevel, RefreshRate, UseTrilinearFiltering,
  UseTripleBuffering, UseDesktopGamma, EnableShadows, DisableMRT, DisableAspectRatioCorrection, DisableIntroMovies.
  (Label strings LOC_ANISOTROPIC_FILTERING / LOC_REFRESH_RATE / LOC_TRILINEAR_FILTERING / LOC_TRIPLE_BUFFERING /
  LOC_USE_DESKTOP_GAMMA / LOC_ENABLE_SHADOWS do exist in the movie — cut widgets? UNVERIFIED.)
- `DAOriginsConfig.exe`: native MFC, no readable ini key strings; what it exposes is UNVERIFIED (needs a run or .rsrc dialog dump).

## Steamless
- v3.1.0.5 zip sha256 e3e2d22e098ff3fb359b2876aa2bed9596f0501e6ff588cbffae90a76d2dc4f5 in work/tools/steamless.
- Under GE-Proton11-7 wine-mono: CLI failed to load Steamless.API from Plugins/.
- Retry with API dll copied beside the CLI was blocked by the permission classifier, then run after
  explicit user approval (2026-10-03).
- Result: SteamStub Variant 2.1 removed; `.bind` dropped; `.text` decrypted (entropy 8.00 → 6.49; entry now in .text).
  Output `work/bin/DAOrigins.steam.exe.unpacked.exe` sha256
  `659ceab2b629dac9cad02591e9b8573b2b680b679fcfce6df8fc5a21a2d653ce` (analysis copy only).
- Installed exe re-hashed after the run: unchanged (`400c2c9e…647bd`).

## GUI comparison (PC guiexport.erf V2.0 vs PS3 guiexport.erf V2.1)
- PS3 ERF V2.1: ASCII header, 44-byte entries (char[32] name, offset, stored, size), per-entry zlib.
- gui.erf: same 259 names on both. guiexport.erf: PC 118 / PS3 185 entries, 105 shared.
- PS3-only movies: radialquickbar, battlemenu, combinedhud, container, skills, tutorial, load_controller,
  logininfosharing, newcontentavailable. PC-only: cutscene, itemexamine, navbar.
- Every shared movie differs in size except the fonts → PS3 ships console variants throughout.
- Both use Scaleform CFX v8 (zlib SWF). Loading PS3 movies in the PC player: UNVERIFIED.

## Engine API used by the movies (tools/gfx_calls.py, AVM1 walk)
- Movies call `flash.external.ExternalInterface.call(name, ...)`; dispatcher first args are dynamic (wrapper fn).
- PS3-only engine calls: EnableGamepadEvents, DisableGamepadEvents, ForwardGamepadInput, LockGamepadInput,
  DispatchScriptEvent, DispatchTrainingEvent, IsShapeshifted.
  - PC exe: 0 occurrences of each (positive controls CanLevelUpFromCharacterSheet / IgnoreItemRequirements /
    GetAbilityAttributes each appear once as UTF-16).
  - PS3 eclipse.elf: each present once as UTF-16BE. → PC engine lacks the menu↔gamepad layer.
- PS3-only message-like AS strings present in PC exe: CycleFullScreenGUILeftMessage / RightMessage only.
  Missing on PC: ReportGamepadEvent (ASCII in PS3 elf), DispatchScript/TrainingEvent; others look AS-internal.

## Decrypted PC exe (Ghidra project DAO_PC_UNPACKED)
- 123 code xrefs to input strings now resolve (vs 0 on the encrypted exe).
- `FUN_00882680`: input-name registry. Each `Gamepad::*` (36) and `Mouse::*` (12) name referenced twice,
  inserted into two global maps (`0xc3b6fc`, `0xc3b7d4`) via `0x881c70` / `0xa5fee0`. Too large for one decompile.
- `FUN_00895f10`: action table, 76 analog/state actions name→id (0 AccelerateCharacterLateral … 75 Pre_Selection),
  incl. 51 AnalogScrollValue, 52/53 ConversationRadialSelectX/Y, 58–63 RadialPartySelect*/RadialTarget*,
  70–72 LinearAnalogTarget*. Full list: work/pc-actions.tsv.
- `FUN_0078d1a0` (+0x77f290/0x77f370, 0x77af00, 0x6e30d0, 0x6dc900): Left/RightThumbstickMessage and
  ActivateAnalogTargetModeMessage message plumbing.
- None of the 76 actions appear in KeyBindings.ini (that file holds GUI commands). No data file in either version
  (loose files or ERF/zlib entries; RIM not parsed) contains action-binding text → defaults are likely compiled in.

## Step 1 — PC input path and injection point (DAO_PC_UNPACKED, static)
- DirectInput setup `FUN_0087f890`: DirectInput8Create, then CreateDevice for GUID_SysKeyboard (→ this+0x20)
  and GUID_SysMouse (→ this+0x24) only. No joystick device, no XInput anywhere. → PC has NO gamepad backend.
- Input manager vtable `0xb2ed28` (4 slots): [0] 0x8804d0 dtor, [1] 0x8804f0 Update(arg), [2] 0x87e350, [3] 0x87df20.
  Update: zero this+0x14/+0x18 → keyboard poll `FUN_0087fcf0` → mouse poll `FUN_0087ff40` → `FUN_0087ddc0`.
- Input code = device<<28 | modifiers | index. Devices: 0x1 keyboard (138 names, DIK scancode index),
  0x2 mouse (12), 0x3 cursor (2), 0x4 gamepad (36). Modifiers: Shift 0x100000, Ctrl 0x200000, Alt 0x400000.
  Builders: 0x880570/0x880740 (kbd), 0x880590/0x880760 (mouse), 0x8805b0 (cursor), 0x8805d0 (gamepad).
- Gamepad index table (from FUN_00882680): 0 DPadUp,1 DPadDown,2 DPadLeft,3 DPadRight,4 Start,5 Back,
  6 LeftThumb,7 RightThumb,8 LeftShoulder,9 RightShoulder,0xa BottomAction(A),0xb RightAction(B),
  0xc LeftAction(X),0xd TopAction(Y),0xe–0x15 LeftThumb 8-way,0x16–0x1d RightThumb 8-way,
  0x1e LeftTrigger,0x1f RightTrigger,0x20 ThumbLX,0x21 ThumbLY,0x22 ThumbRX,0x23 ThumbRY.
  (Indices 0–9 = XInput button bit order → Xbox 360 heritage.)
- `FUN_008807e0` treats gamepad 0–0x1f as digital, 0x20–0x23 as analog; binding text (`FUN_00881090`) supports 0x4.
- Events: 16 bytes {code|mods, code, DI timestamp, DI sequence}, appended to the manager's vector via the generic
  push_back `FUN_0087ebd0`. Key state also kept in per-device tables (kbd: this+0x3d+scancode, 0x80 = down).
- Image base fixed 0x400000, DllCharacteristics 0 (no ASLR) → static addresses valid at runtime.
- Proposed hook: replace vtable slot [1] pointer (0xb2ed2c, .rdata) with wrapper: call original Update, then
  read XInput and append gamepad events / update gamepad state. No .text bytes patched.
- UNRESOLVED: how analog values (ThumbLX etc.) are carried/queried — no gamepad state table found yet on PC.
  Whether SteamStub checks .rdata integrity at runtime: UNVERIFIED.

## Step 2 — PS3 GUI ⇄ gamepad layer (eclipse.elf, rizin + tools/ppc_addr_refs.py)
- PS3 builds addresses with `lis` + `addic` (not addi) — scanner handles addi/addic/ori and D-form loads.
- ExternalInterface handler table registered via `0x72ffd0(this, name, &opd)`, names at 0x135xxxx, OPD at 0x158a7d0+:
  AddTokenObserver 0x7356b4, AddTokenObserverWithID 0x7357e0, GetValue 0x735924, GetNumber 0x735ba0,
  GetString 0x735df8, ReplaceDesignerTags 0x735e18, SendTelemetryInfo 0x735f4c, SendMessage 0x736008,
  FilterKeyboardInput 0x7360a4, EnableGamepadEvents 0x736104, DisableGamepadEvents 0x736130,
  ForwardGamepadInput 0x73615c, LockGamepadInput 0x736184, DispatchTrainingEvent 0x7361ac,
  DispatchScriptEvent 0x736284, GetCurrentModuleName 0x736328, GetMainModuleName 0x7364b0.
  IsShapeshifted registered near CanLevelUpFromCharacterSheet at 0x2c16xx.
- All four gamepad handlers use the GUI manager singleton `*(0x15ae8c0)` (47 code refs):
  Enable → `0x73bce4` push movie onto vector +0x4c; Disable → `0x738284` erase + clear lock +0x5c if equal;
  Forward → `0x73bd28` set byte +0x1b = 1; Lock → `0x73bd34` +0x5c = vector.back().
- Dispatcher `0x738e20(mgr, a, b)`: iterate listeners newest→oldest, skip hidden (movie+0xb5) / non-locked,
  clear +0x1b, invoke `Gamepad.ReportGamepadEvent(a, b)` (string 0x13524d0) via `0x73cbd8`, stop unless +0x1b set.
- Caller: GUI manager frame update (starts 0x738fb8): caches analog input values (ids … 0x56–0x5b) as floats at
  +0x1e8… and notifies observers on change; drains 8-byte event vector +0x248, a = word0 & 0xFFFF (button index),
  b = word1 & 0x000F0000 (state flags), then dispatches; clears vector (+0x244).

## PC GUI handler registration
- `FUN_00521af0` registers handlers: `push fn; push name; mov ecx, esi; call 0x520280`
  (e.g. SendMessage → 0x51c800, FilterKeyboardInput → 0x51c760).
- Handler ABI: cdecl `(ctx, GFxValue* args, unsigned argc)`; FilterKeyboardInput checks argc == 1, reads args[0]+8,
  forwards to `0x5110f0` on global `0xc31264` (PC GUI manager candidate).

## Open questions
1. Is there a PC gamepad device backend? Static signs say no (no XInput string, no GUID_Joystick); confirm by
   tracing who produces Gamepad::* input codes in DAO_PC_UNPACKED.
2. Who produces `Gamepad::*` events on PS3, and is the consumer side identical on PC? → diff handlers.
3. Which GUI movies exist only on PS3 (`gui.erf` / `guiexport.erf` diff)? → after copy verifies.
4. PS3 data endianness / ERF version vs PC.
