# Phase 1 recon — Dragon Age: Origins Ultimate (Steam) gamepad port

Status: IN PROGRESS (read-only; nothing written to the game folder)

## Pins
- PC: Steam app 47810, buildid 21245176
  - `bin_ship/DAOrigins.exe` sha256 `400c2c9e97bb1a534121553be66f202429ef6f7320c93c86f9b7a491864647bd`
  - PE32 i386, 10,594,144 bytes
- PS3 dump: `~/Games/ps3-dumps/DAO/` (copied from `gdrive:Dropbox/RetroBat/roms/ps3/Dragon Age Origins.ps3`)
  - Main binary appears to be `USRDIR/eclipse.self` (23 MB); `EBOOT.BIN` is 141 KB. UNVERIFIED which one holds the game.
  - Copy/checksum verification: PENDING

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

## Open questions
1. Is there a PC gamepad device backend (DirectInput joystick enumeration) or only the names? → Ghidra.
2. Who produces `Gamepad::*` events on PS3, and is the consumer side identical on PC? → diff handlers.
3. Which GUI movies exist only on PS3 (`gui.erf` / `guiexport.erf` diff)? → after copy verifies.
4. PS3 data endianness / ERF version vs PC.
