# Divergences from Stuart's source

Status: reference, exported from the working repository's notes
Last updated: 2026-10-22
Summary: Where the retail build differs from Stuart Gillam's published source, by file and address.

Each entry names the retail evidence that forced it.

- `MemoryManager.cpp`: the heap lock is a Win32 mutex, not the BTS spinlock. The constructor calls
  `CreateMutexA(NULL, FALSE, NULL)` (`004a1390`), `Shutdown` releases and clears the handle (`004a17b0`);
  `GRAB_MUTEX`/`RELEASE_MUTEX` take a `HANDLE`, so `Cleanup`'s unchanged `GRAB_MUTEX(&m_Mutex)` passes the
  handle's address (`004a164b`).
- `MemoryManager.cpp`: `ReallocTiny`'s allocation is on line 463 (retail pushes `0x1cf`), not 483.
- `MemoryManager.h`: 129 memory types (`MEMTYPE_LIMIT`), not 108; `MEMTYPE_DUMPTEMP` is still 100,
  `MEMTYPE_MEMBUFFER` is 17 and `MEMTYPE_TINY_HEAP` 126.
- `MemoryManager.cpp`: `Cleanup` is defined between `ReallocTiny` and `Shutdown` (its retail position,
  `004a1640`); `Init` allocates the tiny heap on line 379 (`0x17b`), not 399; `DumpMemory` allocates its buffers
  on lines 1800 and 1914 (not 1790 and 1898) and returns early, deleting the buffer, when the first
  `InitFromMem` fails (`004a2b4d`), which skips the reset of `mDumpingMemory`.
- `DXMemoryManager.cpp`: an allocation failure reports a localized fatal error per heap,
  `CONSOLE.FatalError(FALSE, id, -1)` with ids `0xcd`..`0xd0` (`005490e0`), where the source passed a colour to
  `RenderDiscFailureTextAndHang`.
- `game.h`: `GetFrameRenderFraction` is an inline field read (`GAME` + 0x3ac, `008a9e44`); GAME is a CDXGame at
  `008a9a98` with its random stream at + 0x304.
- `map.h`: `Collide` and `Normal` are `__fastcall` members (MAP at `006fadc8`); `GetWaterLevel` is an inline field
  read (+0x1034).
- `actor.cpp`: the developer-mode velocity warnings are live (`CDebugLog` call at `0040174f`), not commented out.
  `Move` binds `mPos` to a local vector reference before `+= mVelocity`, instead of Stuart's direct member
  expression. This reproduces the retail X-component load order (`00401757`, `0040175a`) and the whole body;
  it preserves the operations but does not establish the original variable spelling.
- `maths.h`: the Euler-angle `FMatrix` constructor, decoded from its inline copy in `CActor::Init`.
- `CLIParams.cpp`/`.h`: the retail file is the PC port's own revision, reconstructed from the bytes (all four
  functions match). It keeps Stuart's tokenizer, his if-per-option scan, his fields in their order and his
  constructor's statement order, and replaces his developer options with `-testeur`, `-getversion` (prints
  `Version %d.%02d.%02d` and exits with `(major*100+minor)*100+build`), `-e3`, `-defaultoptionsname`, `-cardid`,
  `-backbuffer2`, `-findgoodwater`, `-findbadwater`, `-timeout`, `-playabledemo`, `-res W H` (at least 640x480),
  `-32bittextures`, `-dxtntextures`, `-traceconsole`, `-landscape0..2` (the `landscape_method` tweak),
  `-autoconfigtest [folder]` (redirects `setuphistory.txt`) and `-soundbuffers`; `-level`, `-nomusic`,
  `-showdebugtrace`, `-nosound` and `-skipfmv` survive. `-forcewindowed` is honoured only while the byte at
  `00662f3e` is set, and `-e3` also makes the inactivity timeout 120 seconds. `LANG_ENGLISH` is written as 0 (the
  game's value; windows.h's is 9). The outside objects GetParams reaches are declared in the file until their own
  headers are reconstructed.
- `Career.cpp`/`Career.h` (Stuart's, the PC build's own changes applied): `CCareer` has one more two-int array
  after `mIsGod` (+0x249c, zero by default, read by the controls screen and mouse look), which moves
  `mInvertYAxis`, `mVibration` and `mControllerConfigurationNum` to +0x24a4, +0x24ac and +0x24b4 (their defaults
  unchanged) and makes the career 0x24bc bytes; its constructor sets the new array after `mInvertYAxis`
  (`0041b6a0`, whose relocations fix the order). `GetNumKilled` returns the low 24 bits of a kill counter
  (`0041c160`): the top bytes of the first two counters hold other data (the accessors at `004218f0`..`00421940`),
  and `UpdateThingsKilled` logs the masked total. `UpdateGoodieStates` reads the first goodie's state through
  `GetGoodieState(0)`, one inline expansion more than the macro; retail's inlining cutoff proves one extra
  expansion before goodie 72's rule, and this is the one place found for it (see the findings above). The goodie
  rules themselves are Stuart's, all 300.
- `Career.cpp` save path: the PC build compiles Stuart's console branch (buffer, `SWORD` version stamp
  `CAREER_VERSION + (sizeof(CCareer) << 4)`) with `CAREER_VERSION` 17, not 9 (`00623e24`). `Save` (`00421350`) no
  longer marks the career in progress; a second entry point does that and saves (`004213c0`, called only by the
  save screen). After the career, both write every active 32-byte key binding (table `008892d8`, ending at id -1)
  and then 0x56 bytes of PC options; `SizeOfSaveGame` (`00421430`) counts the same. `Load` restores the volumes
  in use for a career load and applies the saved bindings and options only for the defaults load, and resets a
  screen-position byte outside -64..64 (the screen position lives in the top bytes of the first two kill
  counters; `GetScreenPosX/Y`, called by CFEPOptions and CFEPScreenPos). Stuart's PC `career.dat` path is kept,
  disabled.
- `Career.cpp` options tail (retail only): `WriteOptions` (`00420b10`) and `ReadOptions` store 0x56 bytes: two floats
  (the first unnamed, then mouse sensitivity), the control preset and language as words, four mesh-quality levels, the
  tweaks `LANDSCAPE_LOWRES_GEOM`, `SCREEN_SHAPE` and `RENDERSTATE_DISALLOW_MIPMAPPING`, the packed display mode, the
  vsync flag, the tweaks `LANDSCAPE_MAXLEVELS_USER`, `USER_TEXTURE_RES_LOSS_SHIFT` and `USER_TEXTURE_ALLOW_32_BIT`,
  the current device's multisample type, flip-speakers, hardware sound, sound rate, sound device, 3D sound method
  (all `CLIPARAMS` fields) and two landscape-detail bytes. The tweaks' names are their own constructor strings.
  `d3dapp.h` is Stuart's framework header in its Direct3D 9 form, with `GetCurrentDevice()`.
- `ltshell.cpp` (in progress; Stuart's Direct3D 8 file ported to the retail Direct3D 9 shell): the functions not yet ported sit under `NOT_YET_RECONSTRUCTED`. Retail `WinMain` (`00512130`) is Stuart's with `MainLoop` and `SetupSystemMessageHandler` inlined, plus the PC port's additions: the version from the executable's version resource (the numbers `-getversion` prints), turning off the sticky/toggle/filter-key shortcuts (`ExitCode` restores them), a 32 MB heap instead of 96 MB, and loading `defaultoptions.bea` with `CAREER.Load(buffer, false)` followed by `CAREER.Blank()`: at startup only the key bindings, the PC options and the career fields `Blank` keeps (the volumes, invert-Y, vibration, controller configuration and the +0x249c pair) survive from that file. Its allocation is on line 741 (`#line`; the retail file's layout is not Stuart's). The exception handler compiles only its `fopen` of `OnslaughtException.txt` (`00512040`); `ExitCode` (`00512070`) also frees the patch cache and shuts down the two `CReconnectInterface` objects. Stuart's inline device-state helpers are out of line in retail (`00513820`..`00514030`), reached through `LT.GetDevice()` whatever the receiver, with retail additions: sampler states (`SSS`, which drops the LOD bias, refuses anisotropic filtering the card lacks and clamps its level, and shares the texture-stage cache), a cull-mode swap in `SRS`/`ForceRS` for mirrored passes (`0089d680`), `OLD_SCHOOL_ALPHA_REF` (the alpha reference repeated in the next byte), the colour-op choice under `USE_MODULATE_2X`, table or vertex fog by the card's caps, software vertex processing, vertex-shader and FVF caches (`mSoftwareVertexProcessing` `00889070` is Stuart's `mLastVertexShader` slot), `D3DXAssembleShader` pixel shaders, and `xKeyOnce` keeping a key readable for the rest of the frame (`sKeysRead`). `InvalidateAllStates` (`00513600`) resets those three scalar caches before the table fills, where Stuart's single reset came last. VC6 sinks the three stores below the `rep stos` fills, and only that order loads the fill value into `eax` before the first count.
- `Controller.cpp` is Stuart's file rebuilt around the PC port's controls (its allocation on retail line 967,
  `#line`). `SControlBinding` holds two 12-byte inputs (pad, push type, key, display character); each player reads
  the input with its own number and in a single-player game player 1 reads both (`0042e2c0`). New push types:
  `KEY_RELEASE` (10), four mouse axes (11 to 14; 13 and 14 are ignored for a player whose `gMouseAxisLocked` is set, `0066e8cc`),
  mouse button held (15), and mouse button or wheel once/released (16, 17). A held digital control sends ±1 by
  direction (left, up and forward are -1); everything else sends 1 where Stuart sent 0. The mouse axes are the
  cursor's distance from the window's centre times 0.0043333 and the sensitivity (`gMouseSensitivity` `006254f4`,
  7 by default), clamped to ±1; `UpdateMouseCentre` then draws the cursor 7/17 of the way back. Sticks and hat go
  through one 0.15 dead zone rescaled by 1/0.85 (a constant rounded once from double, `005d97cc`). Both shift keys
  together send `BUTTON_FRONTEND_CHEAT` (Stuart's two shoulder buttons). The DirectInput mouse code
  (`0042d310`..`0042d4d0`) is new; its buttons 1 and 2 are right and middle. Inactivity can also quit outside the
  playable demo (`gInactivityQuits`, `0066e94e`), and the timer stands at 0 through a non-interactive section.
- `PCPlatform.cpp` is Stuart's file with the PC port's changes (`new` lines 27, 79, 95 and 103 by `#line`): no
  GeForce 3 check (vertex shaders are on unless `mForcedShaders` says otherwise), setup-log lines around the
  shader init, no Xbox fonts loaded, a `CDXBitmapDebugFont` (RTTI) for the debug font, `Process` passing the
  first pass to `HandlingSystemStuff`, `DeviceFlip` writing a pending screen dump (`00441b80`), a plain `new`
  that goes to the memory manager (`MemoryManager.h`), and no `GetRegKey`. `GetScreenWidth` and
  `GetWindowWidth` are one body (`00515940`); `GetScreenHeight` is gone. `CPCPlatform` has no `mGeforce3`, so
  `mMemorySize` is at +0x14 and the fonts at +0x18..+0x2c. Stuart's inline `xKeyOnce` survives beside
  ltshell's out-of-line `xKeyOnceThisFrame` (`00513a90`).
- `PCMusic.cpp` is not in Stuart's release; it is rebuilt from its bytes (`005151b0`..`005154a8`). `CPCMusic` plays
  the tracks in `data\\music` through PCPlatform's streaming Ogg player (`005282b0`..`00528680`, plain cdecl
  functions), scales the volume by 1/127, and lists a folder with `FindFirstFile`. `console.h` gains
  `CConsoleMenu` (0x14 bytes, constructor `0042c420` out of line) for `MUSIC`'s menu. The object's maths
  initializers include a second zero vector (`005151d0`, data `00889a38`) whose header is not yet known, so they
  are unannotated.
- `PCMemoryCard.cpp` is Stuart's file (a resource hook only) with the PC build's saves: one card, always present and
  formatted with unlimited space, whose saves are `savegames\\<name>.bes` (`_mkdir`, `_findfirst`, `fopen`), with
  260-byte paths. `CreateSave` refuses an existing name unless overwriting is allowed (`MCE_FILEEXISTS`), creates
  the file, then finds its index by name (`_wcsicmp`), storing it only when `*save` is nonzero (retail tests the
  value, not the pointer). `ReadSave` closes its file twice after a complete read; `WriteSave` leaks the file when
  the write fails; `DeleteSave` returns 1 when `DeleteFile` fails.
- `FEPLoadGame.cpp` is Stuart's file (its `new` on line 179). The PC build returns to page 0 (`FEP_MAIN`), not
  `FEP_DEVSELECT`, on BACK and both failures (`00461d19`, `00462082`); a successful load shows its box with 60 as
  the seventh argument (`00461f7b`), then goes to the success page (`00461fb4`..`00461fc6`) where Stuart's box set
  an on-dismiss page; and after `SetAutoSave` it writes the loaded buffer as the default options file unless
  `0082b5b0` is set (`00461fcb`..`00461fe4`, `CFEPOptions::WriteDefaultOptionsFile` `0051f680`). Stuart's release
  has no front-end headers: `FrontEndPage.h` (page numbers from `CFrontEnd::Init`'s table at +0x214), `frontend.h`
  (the layout from the constructor `00465f10`), `FrontEndText.h`, `FEMessBox.h` and `MemoryCard.h` are rebuilt
  from the retail code.
- `PCController.cpp` is Stuart's file with the PC port's controls. His fixed `ControllerMaping` table is replaced by
  `CONTROL_BINDINGS` (`008892d8`, built by `00514210`): 47 bindings the career saves, the first sixteen
  configurable (mouse yaw and pitch, WASD, Tab cloak, space, mouse buttons for the gun pod, weapon and zoom, left
  Shift for the landing jets), then fixed keys for the menus, cutscenes, pause and the free camera, ended by an
  entry with id -1. Push types 13 to 17 are the mouse (axes plus and minus; button on, once, released). The
  analogue readers return 0 for a pad beyond `mJoypads` (the right stick's Y also when the pad has no Rz axis);
  the hat switch (`GetJoyPovX`/`Y`, new slots 13 and 14) is the sine and negated cosine of its angle; key reads
  take no pad number and go straight to LT (`xKeyOnce`, the new `GetKeyRelease` through `xKeyUp`) or
  `PLATFORM.KeyOn`; recording keeps only the three button words. `Controller.h` is the retail class: 0x178 bytes,
  no analogue floats or reverse-look flag, three constructor arguments (`0042d640`). The object's single maths
  initializer (`005141f0`, the zero vector) comes from `mathsconst.h`, included directly until the retail include
  that reaches it is known.
- `FEPSaveGame.cpp` is Stuart's file (its `new` on retail line 535, `#line`). The PC build skips `Process` on an
  inactive page (`00464744`), checks the overwrite's delete and recovers through the virtual keyboard
  (`004649a0`), adds a format question (9) where Stuart whinged about an unformatted card (`00464d1d`..`00464d42`),
  returns to `FEP_MAIN` wherever Stuart went to `FEP_DEVSELECT`, saves through `SaveAndMarkInProgress` (`004213c0`)
  with a buttonless 60-tick box and moves on at once (`004650e8`), and shows text `0xd6` after a save started from
  the options page (`gSaveFromOptions`, `006799d0`). `IsCheatActive` (`00465490`) is true under `-autoconfigtest`
  or `00679ec1`; otherwise it decodes the asked-for code from a six-entry table (`00629464`) by XOR with
  `"HELP ME!!"` (`00629a64`) and looks for it in the save name.
- `mesh.cpp` is not in Stuart's release; it is rebuilt from its bytes, with `CMesh` laid out whole in `mesh.h` and
  the allocation lines from retail's pushes placed with `#line`. The list head, default texture and report flag
  (`00704ad8`..`00704ae0`) are file globals, not static members: as static members they take three `_$E` numbers
  in every includer, which FEPGoodies' initializers (`0045ac20`, `0045ac30`) are numbered without. The
  random-point functions (`GetRandomVertex`, slot 8 `GetRandomSurfacePoint`) return `FVector` by value (`ret 8`).
- `FEPVirtualKeyboard.cpp` is not in Stuart's release; it is rebuilt from its bytes (0x6f8 bytes at
  `FRONTEND + 0x413c`, vtable `005db830`): three layouts of five rows of up to 14 keys, whose 252 stores
  `InitKeyboardLayout` makes in retail order. `TransitionNotification` inlines `SetDefaultName`'s body
  (`00520162`..`00520271`), so it is an inline `MakeDefaultName`. The command tokens are `VKT_` (windows.h owns `VK_`).
- `FEPSaveGame.cpp`: `CreateSave` compares save names with `_wcsicmp` (`00464ee6` calls `005d04ec`, which folds
  `A`..`Z`), not Stuart's `wcscmp`. The earlier match took `005d04ec` as `wcscmp` because no other object called
  either; FEPVirtualKeyboard's real `wcscmp` (`0055f2e8`) exposed the conflict.
- `MeshCollisionVolume.cpp` and `MeshPose.cpp` were absent from the earlier pinned release and initially reconstructed from bytes. Stuart's October14 source includes `MeshPose.cpp`; EvaluatePose now follows that source as recorded above. The reconstruction uses
  new `GeneralVolume.h` (the abstract volume, vtable `005d892c`: slots 1..4 collide with a mesh, cylinder, sphere
  and line, slot 5 double-dispatches), `Sphere.h` (0x1c bytes), `MeshCollisionVolume.h` (0x28 bytes) and
  `cylinder.h`. The pose cache (`004b4ab0`..`004b512f`) is its own object between MeshPart.obj and
  MeshRenderer.obj. `CMeshPart::GetTransform`'s seventh parameter is a `bool` (only `cl` is set, `004b510e`).
- `FEPDebriefing.cpp`, `FEPE3LevelSelect.cpp` and `FEPLevelSelect.cpp` are not in Stuart's release; they are
  rebuilt from their bytes (vtables `005db9c0`, `005db4fc`, `005db584`). Debriefing allocates its 100 effect links and
  positions from memory type 0x80, beyond Stuart's list (`00456798`, `004567e8`). The E3 page's PC constructor fills
  four levels (110, 200, 231, 311) and returns to the title after 750 idle frames. LevelSelect's constructor builds
  the grid from `CAREER`'s level structure, and its `TransitionNotification` clears only `mTransition[0..5][0..2]`
  (`00460534`..`0046054f`), so the source's bounds are swapped. `CParticleEffectLink`'s destructor is inline around
  `Unlink` (`004cb050`); its out-of-line copy is the `jmp` at `00405d80`.
- `MeshRenderer.cpp` is not in Stuart's release; it is rebuilt from its bytes, with `CMeshRenderer::Render`
  (`004b6260`: through the render thing's cached pose when it has one, otherwise part by part) and
  `CMeshRenderer::mRenderMode` (`00704e48`). The helper at `004b5250` is meant to wrap a value into 0..1, but its
  steps go the wrong way, so a value outside never returns.
- `unit.h` and `squad.h` are rebuilt from the retail RTTI and vtables: `CUnit` is 0x250 bytes, not 0x258 (CAirUnit's
  constructor `0050f0a0` puts its effect link at +0x250; CSubmarine and CSimpleBuilding, 0x254, derive from CUnit)
  and declares all 117 slots, named where Stuart's `CBattleEngine` overrides them and numbered otherwise. Every
  unit reports CUnit's class id (8) but names itself. `CSquad` is abstract (0xa4, class id 28). All 27 unit
  classes' vtables in WorldPhysicsManager.obj match. `SpawnThing` (`0050df80`) has one line per behaviour
  (retail lines 75..99); `SpawnSquad` (`0050f4b0`) makes a `CRelaxedSquad` for mechs and infantry, none for
  behaviours 4..20 and 22..25, and a `CNormalSquad` otherwise. `ThingType.h` adds the bits onsldef.msl names
  and four open ones (0x04000000, 0x10000000, 0x20000000, 0x40000000).
- `MenuItem.cpp` is not in Stuart's release; it is rebuilt from its bytes (including all five vtables; allocation
  lines 39 and 173). `CMenuItem`'s copy constructor copies only the text, enabled, colour and label fields
  (`004a315f`); `CGameMenu`'s slot 6 takes the committed `CScaleMenuItem` (`004a441f`), which `CPauseMenu` overrides
  (`004d1110`: god mode, music and sound volume). `CParticle::SetPos` reads `EVENT_MANAGER.GetTime()`: the
  particle time at `00672fd0` is the event manager's clock (`EVENT_MANAGER` `00672fc8`, `mTime` +8).
- `component.h` (CComponent, CGillMHead, CTentacle) is rebuilt from its vtables; with `SpawnCharacter` every retail
  function of WorldPhysicsManager.obj has been attempted.
- `MenuOptionsList.cpp` is not in Stuart's release; it is rebuilt from its bytes (11 of 15, both vtables). The list
  matches items by their text id (+0x08, `004a4ded`); its destructor deletes the items, releases the blank texture,
  then destroys the set (`004a46c5`..`004a470f`).
- `unit.cpp` is not in Stuart's release; it is rebuilt from its bytes (96 so far). `CUnit`'s members are laid out from
  its constructor (`004f7e90`), named as Stuart's `CBattleEngine` reads them (`mLife` +0xf8, `mAllegiance` +0x138,
  `mVulnerable` +0x15c, `mInfinateEnergy` +0x160) and by role elsewhere; the deploy state is +0x244 (3 deploying,
  4 deployed, 5 undeploying). `IsTargetAlligence` (`004fd3d0`) and `GetLaunchPosition` (`004fc3c0`) carry Stuart's
  names and signatures. A loop written with `for` was not inlined where the `while` form is (`Remove`, `004fd040`).
- `PauseMenu.cpp` (100 of 110, all 23 vtables, the 4,201-byte constructor with every page and item) and
  `FrontEndThing.cpp` (13 of 13) are not in Stuart's release; they are rebuilt from their bytes. `CGameMenu`'s only
  function is its constructor (`004d0e40`), inside PauseMenu.obj. `CRenderData` has a dword before `mRTID` and ends
  with a count its constructor sets to 1 (+0x424). `CMenuItem::mText` is signed; `CPauseMenu` takes a `bool`.
- `FEPMultiplayerStart.cpp` is not in Stuart's release; it is rebuilt from its bytes (8 of 9 and its leading maths
  pair, whose ownership Init proves by copying this object's `ID_FMATRIX`, `0089bbf0`). It and CFEPBEConfig use the
  front end's meshes 0 and 1 (`0089d900`, `0089d904`). `SFrontEndThingInit::mMeshName` is 200 characters.
  `CConfirmMenuOptionsList`'s destructor is implicit (retail's `~CSimpleGameMenu` calls `~CMenuOptionsList`,
  `004d17e0`).
- `FEPBEConfig.cpp` is not in Stuart's release; it is rebuilt from its bytes (17 of 23 and its leading pair). The
  configuration levels (`SBEConfigLevel`) carry the wingman flags at +4, +8, +0xc (Tara, Billy, Jason).
- `FEPWingmen.cpp` is not in Stuart's release; it is rebuilt from its bytes (8 of 10 and its leading pair); it
  shares FEPBEConfig's level format and frees entries through `0044fdf0`. `CFrontEndData::Shutdown` expands
  Stuart's `PARTICLE_MANAGER.Shutdown()` and `PARTICLE_SET.Shutdown()`.
- `eventmanager.cpp` and `scheduledevent.cpp` are Stuart's files unchanged (eventmanager.obj 19 of 19, with the
  `CScheduledEvent` constructor and reader destructor it carries). Their overflow list needs `OPtrSet.h`,
  `flexarray.h`/`.cpp` and `OPtrSet.cpp`, which are not in his release and are rebuilt from their bytes:
  `OPtrSet<T>` is a thin template over `GenericOPtrSet` (its own object, `004241a0`..`0042435b`, as `SPtrSet` is over
  `GenericSPtrSet`), itself a `CFlexArray` (flexarray.cpp, `00465530`..`004655cf`). `CFlexArray::DEFAULT_SIZE` (16)
  is a static const the other objects load from memory (`005db5f8`).
- The battle engine is Stuart's: `BattleEngine.h` is his full header (an offsetof probe matches every retail anchor;
  `sizeof` is 0x63c, the factory's allocation at `004bf0c7`), `BattleEngineConfigurations.cpp` matches 4 of 4 and
  `BattleEngineJetPart.cpp` is seeded from his file. `weapon.h`, `Equipment.h` and `Line.h` are rebuilt (`CWeapon`'s
  accessors are inline in retail). `UBattleEngineDataManager::sData` (`006602a0`) is initialized in
  BattleEngineConfigurations.obj's static initializers (`0040f3d0`..`0040f51e`), not in the data manager's object.
- `Player.cpp`, `Player.h` and `Camera.h` are Stuart's files (Player.obj 18 of 19; his CPlayer is exactly retail's 0x50
  bytes). Retail's `ReceiveButtonAction` inverts the pitch from the career's options instead of the controller's
  flag: `mInvertYAxis[mNumber-1]` when the walker is on the ground, otherwise a second PC option at +0x249c
  (`mInvertJetYAxis`, name open; `004d31d3`..`004d31fa`). `ConfigurationUp`/`Down` are empty and folded with
  `DebugTrace` (`0040c640`). `thing.h` includes `"monitor.h"` as Stuart spelled it: the path in its inlines' `__FILE__`
  is the retail string (`0062551c`).
- `Camera.cpp` is seeded from Stuart's file; the current score owns its progress, and the declaration
  experiments above record the remaining source-context question. `CInterpolatedCamera::Mirror`
  is unused and absent from retail; `0041b040`/`0041b060` are that class's inline `GetOrientation` and `GetZoom`.
  `CBSpline` has a virtual destructor (RTTI `005d8e00`). `FVector::operator+=` returns `void` and adds with `+=`
  (its out-of-line copy `0041ad10` matches; Stuart's own callers never chain it). `FMatrix::Normalise` is Stuart's
  re-orthonormalisation (`0041af95`..`0041afdb`).
- `BattleEngine.cpp` is seeded from Stuart's file; the current score table owns its matching progress. `CUnit`'s slots 78, 79, 88 and 101 are his
  `GetMaxLife`, `GetThreat`, `GetEmitter` and `ConfirmedKill`; `CInfluenceMap` is his `INFLUENCEMAP`
  (`0067a748`, InfluenceMap.h). The September 30 header recheck above additionally places slot 105
  OnScanner, Feature slot 71 IsLockable, and the formerly declaration-only auto-aim/weapon accessors.
  GetTargetablePos uses this reconstruction's established pointer virtual throughout; the source's
  reference call spelling must not bind to a separate nonvirtual method. The October 1 UpdateAutoAim
  reconstruction names the launch vector before the matrix product: this recovers retail's magnitude
  accumulation order and completes the entire section/relocation match, without changing shared maths.
- `InitThing.cpp` and `InitThing.h` are Stuart's files (InitThing.obj 20 of 20). His whole .cpp body after
  `SpawnInitThing` is `#ifdef EDITORBUILD`, so retail's Copy/Load members are his header's inlines, emitted after
  `SpawnInitThing` (CInitThing's own in BattleEngine.obj, CStartInitThing's in game.obj). `SpawnInitThing`'s
  allocations carry his line numbers (15..63), and its switch gives the object ids oids.h now holds (Tree 7, Spawner
  19, Building 25, Cutscene 26, Wall 33, SphereTrigger 36, SpawnPoint 41). `CSquadInitThing`'s `Copy(CInitThing*)`
  override is folded with `CInitThing::Copy` (its vtable's slot 0 is `0040e1b0`). `kNullEmitter` is 0 (the
  constructor's `mWaypointPath`, `0048ddc8`).
- `FEPDevSelect.cpp` is not in Stuart's release; it is rebuilt from its bytes (0x18 bytes at `FRONTEND + 0x39b8`,
  vtable `005db970`). The PC has one device, always present, and no hard disk (`IsHDDAvailable` `005019c0` returns
  FALSE). `ButtonPressed` reuses its `button` parameter for the card-present flag and card count (`00458a8a`,
  `00458ac3`); `CheckDevice` kills the box only for questions 4..6 or 9; `Process` answers question 7 (the PC's
  play-without-saving, `FEMB_Q_NO_AUTOSAVE`) with a one-case switch and presses SELECT every active frame.
- `FEPOptions.cpp` is not in Stuart's release; it is rebuilt from its bytes. The page runs the pause menu in
  options mode (`CPauseMenu` at `0089bc30`, retail line 406), goes to the credits when its result is 1, and
  otherwise `SaveDefaultOptions` saves the career through the save page when a slot is in use and writes the career
  and options to `defaultoptions.bea` (retail line 250; `WriteDefaultOptionsFile` `0051f680`). Entering it from a
  main menu keeps the volumes, both players' vibration and controller configuration, and the screen position.
- `WorldMeshList.cpp` is not in Stuart's release; it is rebuilt from its bytes (8 of 8). The table name
  `CWorld__SpawnInitialThings` (`0050dcb0`) is wrong: the function creates, initialises and shuts down one unit of
  each type not yet used, to load its resources.
- `world.cpp` (23 of 32) and `rtmesh.cpp` (17 of 22) are not in Stuart's release; they are rebuilt from their
  bytes, with the `CRenderThing` and `CRTMesh` vtables. Open: `CWorld`'s clear (`0050ada0`) calls a non-virtual
  scalar deleting destructor (`0050d680`) and `GenericSPtrSet::First` out of line where our build inlines both.
- `WorldPhysicsManager.cpp` (26 so far) is not in Stuart's release: the definition registries and destructors,
  resolvers, name lookups, `Add*ByName` and `MapMountName`; `WorldPhysicsManager.h` holds the definition classes
  (`CUnitData` 0x1ac) and `EUnitBehaviour` 0..25 from the physics-script keyword classes. `BattleEngineDataManager.h`
  is Stuart's, line-exact (its `new` lines 263 and 310).
- `FEPGoodies.cpp` is seeded from Stuart's file: his 232-entry goodie table matches retail's static
  initializer (`0045ac30`, 6,963 bytes) entry for entry through `text.stf`'s ids, and his class fits the 0x1dc
  layout exactly. The October 1 `GetMethod` match uses the existing direct PC text lookup rather than
  its forwarding wrapper; both emitted targets are the same. Render remains unmatched.
- `game.cpp` `RestartLoopRunLevel` (`0046dc30`): retail logs the post-load memory dump Stuart commented out
  (`0046dd37`), moves the playable-demo controls screen after `MEM_MANAGER.Cleanup` (`0046df25`) and keeps
  Stuart's Xbox `SetLoadingRange(100, 100)` there, flushes the controller once more after the wait (`0046e021`),
  sets the loading fraction to 1 only outside the demo, calls `PlayMusicForCurrentLevel` (inlined), plays the
  front end's select sound through `CFrontEnd::PlaySound(FES_SELECT)` with one `UpdateStatus` (`0046e1b7`), and
  after the intro FMV sets only the range (no `SetLoading(TRUE)`).
- `game.cpp` `DrawGameStuff` (`004714c0`): B grabs one frame under `-testeur` (or asks for a screen dump under
  `-autoconfigtest` or with every cheat on); the FPS trace runs every 100 frames and also goes to setuphistory.txt
  under the same two; the debug text is no longer drawn; the end-level fade keeps pace with the clock; the darkener is
  20 pixels bigger each way; the secondary objectives' overlap test compares in float (`004720d2`). A dormant
  watermark replaces the debug text: "AUTORUNNING UNFINISHED RELQ VERSION" or "UNFINISHED RELQ VERSION", stored
  XORed against a cover text ("Your graphics card is not fully supported, please") through keys built by two static
  initializers (`00470cc0`, `004710c0`) and unscrambled by `00472270`; its gate (`00679ec0`) is never set, so the
  release never shows it. `CDebugText::Out` (`00472240`) is the varargs member emitted with game.obj.
  `DrawTextShadowed` is Stuart's name for the shadowed draw with (0, 0, 1, 1), a direct call (a macro here);
  `WordWrap` fills 40 lines of 100 characters.
- `game.cpp` `RollCredits` (`004726b0`): two controllers, not four (`00472701`, `00472742`); the modulate state is
  set through `LT.SetModulate(0)` (`004727cf`); the credits draw at alpha 255.
- `game.cpp` `ReceiveButtonAction` (`0046f7e0`) is Stuart's except that the free camera needs cheat 4
  (`FRONTEND.mFEPSaveGame.IsCheatActive(4)`, `0046f82e`) where Stuart had `if (1)`.
- `maths.h`: `004062d0` is `FMatrix::MakeRotationF` (it returns with `ret 0xc` and no
  `this` in eax, so it is not a constructor), called out of line from 96 sites; `FMatrix(yaw, pitch, roll)` is written
  as a forwarder to it, which leaves every existing match unchanged.
- `game.cpp` `MainLoop` (`0046eee0`): retail resets the mouse's per-tick state first (`0046eee9`), takes Stuart's PS2
  attract-mode return on inactivity (`CLIPARAMS.mAttractMode`, `QT_QUIT_TO_FRONTEND`, `0046ef05`) and never calls
  `ProcessDebug` (no debug keys, no Escape quit). `Render` (`0046e460`): with `EXTRA_GEFORCE_FX_FEATURES`
  (`009c6480`) on in single player, a first pass renders into the landscape's reflection texture at 256x256 with
  `gMirrorPass` and `FORCE_OBJECT_IMPOSTERS` set, then the frame renders again to the screen (`0046e4bc`,
  `0046e8c5`); the views are skipped behind an opaque win/lose screen (`0046e5c8`); the mouse steers the walker's
  look before the single and two-player views (`0046e63e`, `0046e848`); the reconnection prompts take a third
  argument, 0. `mRenderFrameNumber` counts both passes. The engine's viewports are Stuart's (`CViewport` of signed
  ints, `mViewport[2]` at +0x438).
- `game.cpp` `Update` (`0046e910`) adds to Stuart's: an `-autoconfigtest` script on fixed frames (240..310, then
  10100..10170 and 20100 through a static offset) that pauses, works the pause menu, requests screen dumps
  (`00441b10`) and finally clears the flag and turns every cheat on (`gAllCheatsEnabled`, `00679ec1`); mouse polling,
  each player's `gMouseAxisLocked` from the battle engine's walker-on-ground test (`004080f0`), cursor recentring and
  the transient key clear before the event flush; a won level's countdown that holds while a controller is
  disconnected (`0046ec88`); a lost or drawn level's countdown that follows the system clock (steps under 5 s,
  stopping above `0.15f - CLOCK_TICK`, a constant folded in float: `005dbbf4` is 0x3dccccce, not `0.1f`); and a
  reconnection prompt that stays above the end-of-level menu (`0046edf3`). `ToggleFreeCameraOff` is Stuart's.
- `game.cpp` `Shutdown` (`0046c990`) is Stuart's. `ShutdownRestartLoop` (`0046ca70`) adds `ShutdownMouse()` last
  (`0046cd1f`). Its `ENGINE.ShutdownRestartLoop()` calls `0040c640`, the empty `DebugTrace`: the linker folded the
  two empty functions. Stuart's names settle three open ones: `CMesh::FreeLevelResources` (`004a5430`),
  `CVBufTexture::FreeLevelResources` (`00501360`) and `UPhysicsManager::ClearCachedEmitters` (`00510740`).
  `PARTICLE_SET.Shutdown` and `PARTICLE_MANAGER.Shutdown` are Stuart's inlines, which CFrontEndData::Shutdown
  also expands.
- `game.cpp` `InitRestartLoop` (`0046c430`): retail starts the mouse first (`InitMouse`, `0046c44e`) and recentres the
  cursor last (`UpdateMouseCentre(true)`, `0046c96f`); its allocations are 126 lines below Stuart's (retail lines
  505..513, placed with `#line`). `GAMEINTERFACE.Reset` and `Init` are one function (`004729e0`, folded by the
  linker). The engine's landscape is at +0x10 (`0046c453`), so the camera array there has at most three entries.
- `game.cpp` `RunLevel` (`0046e240`): the PC reloads the language's sample bank when sound is on (`0046e283`) where
  Stuart's other platforms load theirs; a resource-load failure is `FatalFileError("game resources", -1)`
  (`0046e30c`), and a level that quits with `QT_LOAD_ERROR` shows fatal error text `0xf5` (`0046e443`).
- `console.h`: `SetLoading`'s defaults are TRUE, TRUE. Every game.cpp call pushes x, 1, 1 (`0046e25a`,
  `0046cab1`, `0046dd86`) where `CFrontEnd::Init` pushes 1, 1, 0 and 0, 1, 0, so FrontEnd.cpp passes FALSE
  explicitly and Stuart's eight one-argument calls in game.cpp stay as written.
- `game.cpp`: on the PC, `CWaitForStart` releases control on START or button 18 (`BUTTON_MECH_FIRE_GUN_POD`), not
  `BUTTON_FRONTEND_MENU_SELECT` (`0046dbe6` cmp 0x40, `0046dbeb` cmp 0x12). Retail adds
  `CGame::PlayMusicForCurrentLevel` (`0046dc00`), Stuart's level-music switch as a function of `mCurrentLevel`,
  which the four sound-option menu items call (`004cf0d2`, `004cf162`, `004cf1d2`, `004cf282`).
- `game.h`: `IController` has Stuart's three pure virtuals (vtable `005d9388`, `_purecall` in slots 3 to 5).
- `game.h`: `IController` adds nothing to `CMonitor` (the 12-byte `CReconnectInterface` derives from it).
- `thing.cpp` is Stuart's file unchanged; its `new` lines 310, 625, 665 and 767 are the retail `__LINE__` values.
  Its headers are reconstructed: the retail `IRenderableThing` slot 21 is `GetBoundingBox` (CThing's override
  `004f3d20`, called through that table by `DrawDebugCuboid`), and `CInitThing`'s retail offsets are exactly
  Stuart's field order.
- `common.h`: `TRACE` is the varargs `DebugTrace` (`0040c640`); the retail callers never merge their stack
  pops around it, which VC6 does only for varargs calls.
- `DXMemBuffer.cpp`: the PC build packs `*.aya` files with zlib (`compress` `0055d5f8`, `uncompress`
  `0055d5f2`, the name test `_stricmp(name + len - 4, ".aya")` at `00547fce`). Each block is a 4-byte packed length
  and the packed data, through a static 0x102927-byte buffer (`008c029c`); a skip on a packed file reads and drops
  whole blocks instead of seeking. The read and write buffers are 1 MB (`00547d48`, `00547ddd`) and the buffer size
  rounds up to a whole megabyte; there are no CRC files (`00547ea8`, `00548cfb`), and bad data is
  `CONSOLE.FatalFileError(name, -1)` (`005480c5`). Files open with `FILE_ATTRIBUTE_NORMAL` only (`00547f33`), and
  `InitFromFile` records the name (`00547edd`) and allocates on line 287.
  The inherited literal `if (0)` direct/DMA-read block at pinned source lines 418–443
  is removed from `Read`: retaining it perturbs VC6 allocation despite its disabled path.
  The buffered path now matches the complete `00548570` section and references; this
  compiler result does not prove the original retail source's spelling.
- `common.h`: `PS2` is 3 and `XBOX` 2. `CResourceAccumulator::GetFileName` compares the target with 1, 3 and 2 for
  "PC", "PS2" and "XBOX" in Stuart's order (`004d6f77`, strings `006318d0`, `006318cc`, `006318c4`).
- `ResourceAccumulator.cpp`: `ReadResources` has a third argument. When it is set, only the version, target, size
  and mesh chunks are read (`004d7612`), and meshes are tested before textures (`004d75d3`). Loading resources
  (level -3) returns after its status line, as Stuart's commented-out `return` would (`004d7299`). The PC reads
  the vertex-shader chunk (`004d7776`). The loading fraction is always 0 (`004d794f`). The landscape damage is one
  object at `008aa9f0` (`004d78af`).
- `engine.cpp` is Stuart's file, line-exact (its `new` lines 135 to 171 are the retail `__LINE__` values), with
  `mathsconst.h` included after the last line so the object ends with its two initializers. Stuart's `engine.h`
  field order is the retail layout (constructor `00449820`); the PC's landscape, water, sky cube, light manager,
  gamut and mixer textures are reconstructed in `landscape.h`, `water.h`, `kempycube.h`, `Lights.h`, `gcgamut.h`
  and `maptex.h`. The landscape's damage marks are one object at `008aa9f0` (`0044a135`).
- `maths.h`: `FVector::Normalise` computes the length itself rather than through `Magnitude` (the inlining in
  `CEngine::SetupLights`, `0044a30c`); `CLight`'s constructor clears the direction through `FVector::Set`, the
  third of the three out-of-line `Set` calls there (`0044a3ae`..`0044a3fd`).
- `DXEngine.cpp` is Stuart's file with the PC's changes: a `CTweakSLONG OLD_WATER_TIMING` defined before `ENGINE`
  (its initializer runs first, `0053d310`); `CDXEngine` has no capture flag or `mTexOpaque` (see `DXEngine.h`) and
  `Init` creates no screen texture; `ShutDown` first calls a new `ReleaseDefaults` (the default texture and mesh,
  `0053d3a0`, which `CSystem::Shutdown` also calls, `004f01b0`); `PreRender` calls the device's scene functions
  directly and also clears the target in a mirrored pass (`0053e287`); `SetModulate2X` is `LT.ForceModulate(0)` or
  `LT.STS(0, COLOROP, MODULATE)` (`0053f040`). `PostRender` skips the HUD in a mirrored pass (`0053ecee`), raises
  `gDrawingEndLevelScreen` around the message logs and pause menu (`0053ee07`), drops Stuart's point filtering and
  HUD blur (`0053ed7e`, `0053ef2b`), sets the mip filter through a helper (`00551480`) and draws the interface
  only outside a mirrored pass (`0053efc4`). The debug drawing and `Render` are still parked.
- `Platform.cpp`: retail `CPlatform::Flip` has no stop-everything wait; after `DeviceFlip` it performs a requested
  display reset and, for a reset of kind 2, saves the options (a `new` on line 41, `004d25bf`). The file also
  holds `CPlatform::CreateDirectoryPath` (`004d2600`).
- `DXEngine.cpp` `Render`: the PC version sets the near plane to 0.1 first, mirrors the camera in the water plane
  and flips the gamut's view in a reflection pass (`0053e365`), draws the water before or after the world by
  `OLD_WATER_TIMING` and never in a reflection pass (`0053e6b4`, `0053e7cb`), sets the mip filter through helpers
  (`0053e728`, `0053e791`), skips particles and the sun in a reflection pass, and passes the sun's line test its full
  argument list (`0053ead2`). Stuart's screen capture is gone.
- `DXFrontend.cpp`: `RenderParticles` leaves the fog state alone (no `SetFogEnabled(false)` before the particle
  meshes, `00540ed2`); `RenderStart` calls `STATE.UseDefault()` once, then `RENDERINFO.Reset()` (`005508e0`), and
  clears the screen without the second `UseDefault` (`00540f82`). `RenderStaticScreen` is absent: its
  "Frontend screen not found..." text is not in the pristine executable.
- `EndLevelData.cpp`: the `END_LEVEL_DATA` initializer (`00449670`) inlines the constructor and writes the global's
  fields directly (objective loop at `0x672d78`, `mWorldFinished` 100, `mFinalState` 4, `mRanking` -1.0f); no
  out-of-line constructor exists.
