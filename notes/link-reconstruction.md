# Link reconstruction

Status: active
Last updated: 2026-10-16
Summary: how the link is rebuilt, what is proven, conceded and open.

How `tools/link.py` rebuilds the retail executable's link, which mechanisms are proven (with the evidence), what is
conceded, and what is open. This page describes the present state; Git keeps the history. Measurements are of
`BEA.exe` (SHA-256 `74154bfa…`, the pristine specimen) against a link of main's objects; they move with every
commit, so rerun the tools instead of quoting numbers from here.

## State of the executable

Measured 2026-10-16 (UTC) on the full working tree, which also holds the 33 functions of the four DirectX SDK sample files this tree leaves out: all 5,482 game functions match in both columns (this tree matches 5,449). "Before" is main; Regenerate with `python tools/decomp.py check`, `python tools/link.py --no-compare`, `python tools/alignedeq.py LINKDIR --data-events`.

| | before | applied |
|---|---|---|
| `.text` size against retail's | +80 bytes (the window is +99 / −3,996) | +80 bytes (unchanged) |
| `.rdata`, `.data` | at retail's addresses | at retail's addresses |
| `.data` + `.bss` size against retail's | −35,392 bytes | 0 |
| `.rsrc` | 0x9000 early (it follows the `.bss` size) | at retail's address |
| IAT blocks at retail's RVA | 6 of 14 | 14 of 14 |
| code equal at its own address (raw / rel32 operands masked) | 93.80% / 95.93% | 95.83% / 98.34% |
| `.bss` / `.rdata` words at their own address | 0 / 6 | 9,362 / 5,213 |

The concessions are the rows marked applied in the table below. The three C
objects retail's Rich header counts are rebuilt: the ADPCM tables, an unreferenced 872-byte `.data` block, and
PauseMenu's two COMMON buffers (Proven mechanisms). What then still separates the image from retail's, by owner:

- `.text` placement: ICF survivors and inline placement, 15,888 bytes moved over 424 items; in-object
  emission order, 7,408 bytes; 2,464 bytes of initializer funclets in other positions (VC6 emits a dynamic initializer
  where its static is defined, so retail's late ones mean later definitions).
- Library members: d3dx9's build is confirmed (below), so what is left there is member order; LIBCMT's member spans
  (about ±2,800 bytes).
- `.rdata` order: the RTTI locator walk, 96% of 32,024 bytes of churn (Open questions).
- `.data` and `.bss` order: the dynamic-init and function-local emission family, oids' vtable walk, and small items.
- Small sizes and derived fields: `.bss` objects (Lights +64, Shell +16, a few tails), headers and Rich, the import
  table's order (Open questions).

## Stage model

`tools/link.py` runs LINK.EXE 6.00.8447 (the pinned VC6 SP5 linker) under Wine in a private prefix, with
`/OPT:REF /OPT:ICF /FIXED /FORCE:UNRESOLVED /FORCE:MULTIPLE /VERBOSE`. Its inputs are pinned (`config/link-inputs.sha256`,
`config/link-sources.sha256`); it refuses a changed one. Each stage fixes one layer of the retail layout:

1. **Objects and imports.** The 14 import libraries (retail's descriptor order), the library members and the game
   objects. `linkcmp.py` reports import descriptor order, names, hints and IAT slots per DLL.
2. **Object order** (`config/link-objects.txt`). Six groups, each case-insensitive alphabetical: main game; ltshell and
   PC platform; front-end and PC misc; the DirectX sample framework; `MissionScript/`; the DX renderer. A few objects
   sort under another original name (renderinfo, renderqueue, screenfx, OPtrSet, NormalSquadTargetSelector,
   MCDestructableSegments, PDSimpleSprite, PCMusicStream); no-code objects (MemoryCard, Profile) sit alphabetically. Library members follow `config/link-library-order.txt` (313 members in retail's `.text`
   order: LIBCMT block from `0055d6a0`, NvTriStrip and STL from `0056eb50`, d3dx9, DxErr9, then the LIBCMT members
   only they need from `005d04ec`).
3. **COMDAT selection and order.** `/Gy` (implied by `/O2`) makes every function a COMDAT. Which object emits an
   inline or virtual function, and in what order, decides ICF input and layout. Rules measured and applied: out-of-line definitions emit in source order; a static function is deferred until after its first
   caller; an inline function needed out of line follows the first function that needs it; a vector deleting
   destructor is created where the front end parses the `delete[]`. `link.py --order FILE` passes `/ORDER:@FILE`.
4. **Identical-COMDAT folding (ICF)**, below.
5. **Data sections** (`.rdata`, `.data`, `.bss`), below.
6. **RTTI order**, below. **Resources and header**, below.

## Proven mechanisms

### ICF and Microsoft's qsort
LINK sorts its array of foldable contributions with MSVCRT `qsort` on (raw size, a 16-bit word = relocation count) and keeps the first identical copy in sorted order. Wine's builtin `qsort` orders equal keys differently (survivors differ in 171 of 248 groups), and `msvcrt` is a Wine known DLL, so a copy beside LINK.EXE never loads. `link.py` links in its own prefix (`link_prefix()`) whose `syswow64/msvcrt.dll` is the pinned native DLL (VC6 SP5, 6.00.8797.0, SHA-256 in `config/toolchain.sha256`) with `msvcrt=n,b`, and refuses to link unless the `+loaddll` trace shows the native DLL. `tools/icfsim.py` rebuilds the array (pass-1 order; one record per COMDAT at its first definer; associative COMDATs with their parent; no `_$E` names; no non-COMDAT `.text`) and predicts all survivors (249 of 249 on the frozen link). A fold also requires equal **compiler COMDAT checksums** (aux bytes 8..11 of the section symbol): identical bytes with different checksums do not fold (the `~CProfileFn`/`~CMechEntryProfile` case). Retail's fold groups are the function names that share a retail address; a group folds only inside one COMDAT class (inline = selection 2, map flag `i`; non-inline = selection 1, flag `f`), so an inline definition is placed in the object that emits its class table (WorldPhysicsManager.cpp, rtmesh.cpp, ParticleSet.cpp, Unit.cpp). Survivors depend on the whole array (deleting one record changes 97..155 of 249), so `icfsim.py --report` measures convergence instead: (a) size keys, (b) inline-emission placement, (c) library records. An example of that sensitivity: making `CRoundData::Unknown40d0f0` a plain function folds weapon.cpp's identical `IsBallistic` into it, which brought the game code's end to retail's (+0, library at `0055d6a0`) and `.text` bytes equal in place from 121,284 to 210,130. The same change flipped the survivors of 12 other groups, among them d3dx9's `sse`/`sse2` `D3DXVec3TransformNormal` (retail keeps the `sse2` copy), so `.text` stayed +64. On nine groups with a known retail object the survivor was right in 5 (4 before).

### Library identity: d3dx9
The pinned `d3dx9.lib` is the DirectX 9.0 SDK's (`D3DX_SDK_VERSION` 9), byte-identical to `Lib/d3dx9.lib` in
`dx9sdk.exe` (SHA-256 `a22ca24c…`). Retail's whole D3DX code range `0x574270..0x5be622` has 27 unpaired bytes, all
relocation artifacts; `.rdata` has 2,170 unpaired bytes in 1,224 runs, and 70 data sections compare with no mismatch.
What still differs is member order (Data placement, below).

### Function emission order inside an object
C2 writes an object's functions in definition order. A `static` function comes out after its first caller, so a retail
address before the caller means the original was external. Inline functions needed out of line (by a vtable, a call
the inliner declined, a `delete []` helper) are deferred and come out in a batch after the **later of their first user
and their own definition point**, in the order of their definitions in the translation unit (include order). So an `inline` function defined after its user comes out after its definition: `CFEPBEConfig::GetCurrentLevel`
defined last, `CGroundVehicleGuide::GetPath` declared in its class and defined after `Unknown3`
. A class's vtable brings out its in-class inline virtuals (inherited ones included) and then `??_G` after
the first function whose vptr store survives optimization: a derived constructor that expands its base's constructor
does not emit the base's vtable group, because that store is dead (probed). Moving definitions never moves `??_G` (Open
questions). Several of retail's late groups are a function that was inline in the original, so its copy heads the
trigger's batch: `CParticleDescriptor`'s constructor, `CRTTree::GetRTRadius`,
`CRTMesh::GetRTRadius` and `CSquad::SetAIState` (squad's order also fits the open case in Open questions), each with
unchanged code. An out-of-line function that callers inline and `/OPT:REF` then drops still places what it pulls in
(`??_G`, vector constructor helpers) right after itself. `FollowParticle` in ParticleDescriptor.cpp is
such a function, reconstructed from placement: defined after `TransmitFoR`, it places
`CParticleEffectLink::SetPos` and `SetOrientation` there, as retail does (object 320 to 48 misplaced inline bytes).
Being one more foldable record, it moved about 1,070 names' survivors: misplaced 208 to 202 and the summed region
deviation 8,112 to 7,392, but the game code's end went from +0 to −16 and the nine known groups from 6 to 1 right.
Small virtuals defined `inline` in the `.cpp` before the constructor come out in its vtable group, ahead of `??_G`,
as retail's CRound and CNormalSquad do.

### Precompiled header
Retail compiled with a PCH made from `common.h` (`/Yc`, then `/Yu`). Under `/Yu` an object's uninitialised and
dynamically initialised definitions come out in **reverse** definition order and its explicitly initialised ones
(`= 0`) follow in definition order; without it the uninitialised ones follow a name hash. `decomp.py` builds
`src/pch.cpp` on demand; `config/no-pch.txt` lists the 18 sources built without it, each with its reason.

### C runtime: Visual C++ 6.0 SP5 LIBCMT
The Rich header records the CRT at compiler build 8047 (167 C, 10 C++ members). Only SP5's `libcmt.lib` (2000-08-23, in
SP5's `vs6sp5.exe`) has them; the SP6 file (build 9782) and the RTM file (8168) do not. `libcpmt.lib` is identical.

### NvTriStrip
Retail links the old four-argument NvTriStrip API (void `GenerateStrips`, 24-byte faces, no restart) from NVIDIA's
prebuilt `nvtristrip.lib`, and so does this link: 71 of retail's 72 functions (`0056eb50..00574250`) are identical
with relocations masked. The one residual is `NvStripifier::RemoveSmallStrips` (see "NvTriStrip's release" below).

### Shader-fragment specimen data
The NVIDIA shader-fragment library (five `NVFO` blocks from `0x634550` to `VertexShadersEnabled` at `0x63c108`) is
unreferenced initialised data inside `VertexShader.obj`'s `.data`. It is not source we can write; the build derives it
from the pinned specimen into the ignored `src/data/NVShaderFragments.inc` (`link_specimen_data()` in `decomp.py`) and
`VertexShader.cpp` includes it.

### Initializer order
Retail's `.CRT$XCU` table (`00622000`, 706 slots) has 288 `ZERO_FVECTOR` and 271 `ID_FMATRIX` initializers and 19 empty
ones. Thirteen objects register no `ID_FMATRIX` (their `*_CPP` guards in `mathsconst.h`/`mathsconst2.h`), and
`STATICSHADOWS` belongs to `DXSurf.obj`. `.CRT$XI` holds `___onexitinit`, `___inittime`, `___initstdio`,
`___initmbctable` and `__CxxSetUnhandledExceptionFilter`.

### Data placement (`.rdata`, `.data`, `.bss`)
- `.bss` uses the PCH rule above. `tools/dataorder.py` measures order from the map and `linkcmp --write-expected`: exact
  addresses, longest in-order run, per-object order, within-object pairs, interleaving, and `--objects N` first breaks.
  Fixes it drove (definitions moved to the object whose address holds them).
- Inline virtuals emit only with their class table, so `.rdata` constant pools and vtables land with the emitting object.
- An object's own constants lead its share of `.rdata`, ahead of its vtables and constant pool, and an unreferenced
  constant survives only with external linkage (VC6 drops an unreferenced `static const`). So retail's "AnonymousCPU"
  (13 bytes at `005dacfc`, between CPhysicsStateType's vtable and Cutscene's locator; no code refers to it) is the head
  of `Cutscene.obj`'s `.rdata`, not a missing CPU-detection object as once guessed: the source defines it there as an
  external `const char[]` (name ours), and it links at retail's offset.
- A global that is a field of another object is spelled as the field; its address then moves with its owner.
- String literals are pooled COMDATs (`/Gf`, part of `/O2`; retail pools too) placed after the object's own data, in
  reverse order of first reference. So a text retail keeps among the literals was a literal at its use, not a named
  array: the particle shader texts and the watermark texts. A `static const` table is `.rdata`; retail's
  writable copy is plain `static`.
- The `.data` tail after the last game object (C runtime, d3dx9, NvTriStrip) is 912 bytes shorter than retail's: a
  library question, not source. d3dx9's part is member order: retail's
  `0x65e2dc..0x65e510` holds cparse's tail, then cpslegacyprogram (`g_SwizzleL` at `0x65e388`), cpsprogram (`0x65e44c`)
  and the d3dxmathsse/quatsse constants (`0x65e4e4`). All of it is in ours, later, because
  `config/link-library-order.txt` lists neither cps object. The order fix is pending: some placements flip operator
  delete's ICF survivor or grow `.text` by 0x40.

### COMMON allocation and the three C objects
LINK 6 allocates COMMON symbols (C tentative definitions) at the end of `.bss`: in reverse input order of their defining
objects, by a name-derived order within one object (not alphabetical: `aa`, `ab`, `ba`, `bb` come out in order, but
`sModeText` before `sJoystickText`; probably the symbol hash), and those defined by members LINK pulls from a library
after every object's. Size, definition order and first reference do not matter. Retail's tail fits: PauseMenu's two buffers first, then the C
runtime's commons, with `__onexitend` and `__onexitbegin` last (`009d460c`, `009d4610`, the end of `.bss`).
The Rich header's 3 C objects (build 8966, the game's compiler) are three data-only objects, each placed where the
link-order model puts it:
- `adpcm.c`: the IMA ADPCM reference tables (`indexTable`, `stepsizeTable`), which only
  `CPCSoundManager::DecodeADPCM` reads. Retail holds them after pcsoundmanager's last literal and before Credits'
  strings, where pcsoundmanager's own data cannot go.
- `splinebasis.c`: 872 unreferenced bytes at `00652f68..006532d0`, after DXWater's last literal (21 bytes padded to 24)
  and before the C runtime's data: two doubles, 22 ints and 96 doubles in rows of four (spline- or
  interpolation-basis-like), read from the specimen. Its functions were dropped by `/OPT:REF`; the purpose, the file
  name and the layout are our reading.
- `pausecommons.c`: PauseMenu's text buffers as C tentative definitions. Our compiler never makes a C++ global a
  common. The names are ours, chosen so LINK's order within the object is retail's (`gJoystickText`, `gModeText`;
  `sJoystickText`/`sModeText` come out reversed). `gModeText`'s 80 characters are inferred from the gap retail leaves
  before `__pioinfo` (`009d32a0`); a 32-byte common we lack would fit the same gap.
With all three, our Rich header counts 3 C objects as retail's does, and every symbol of the tail from `gJoystickText`
to `__onexitbegin` that retail locates (22 of 29) sits at one constant offset from retail's address.

### `.bss` order
Retail's `.bss` order inside an object follows the PCH rule above, and ours follows the same rules, so a mismatch is usually a wrong
initializer form or definition point in our source, or a creation point only a header body can supply; the exceptions are
listed as open below. Measured with single-object
compiles.
- **The rule.** Group 1 (uninitialized and constructor-initialized objects) is laid out in reverse symbol creation order.
  A symbol is created at its definition, or earlier at a function-body mention while it is only `extern`-declared (header
  inline bodies count, called or not); a class static is created at its class definition when an in-class accessor names it;
  a function-local static at its first use or at a declaration with an initializer. A bare `extern` declaration creates
  nothing, and a mention after the definition changes nothing. Group 2 (after group 1, in definition order) is constant
  initializers and POD brace aggregates: `int x = 0`, `T* p = NULL`, `POD o = {0,0,0}`, and an aggregate or array of
  non-class type with a dynamic initializer (`float o[3] = {(float)n,0,0}` keeps its funclet and stays in group 2). Every
  class-with-constructor form stayed in group 1: in-class, out-of-class inline and non-inline constructors, copy-init from
  another object, `static`, `const`, `volatile`, `extern` then define, anonymous namespace, conditional initializer, template,
  virtual and derived classes, classes with destructors, arrays of class.
- **Header inline bodies that create a symbol earlier in ours than in retail**:
  - FastVB is fixed. Retail lays `mIB` out before `FASTVB`, so `mIB` was
    created later. CFastVB's constructor, which names `mIB`, moved from the class to an inline definition in
    `FastVB.cpp` after `FASTVB`. It still expands into `FASTVB`'s initializer, because VC6 compiles a file's dynamic
    initializers at its end: an inline constructor defined after its object is still inlined there (probed).
  - pcsoundmanager is a third witness-coupled case. Retail creates `SOUND` after `sPitchVarianceEnabled`, but after
    `ID_FMATRIX`, which arrives through `Game.h`'s include chain. That chain brings `WorldPhysicsManager.h`'s
    `CFeatureData`/`CHazardData::Resolve` bodies, which name `SOUND`. Removing them gives retail's `.bss` and loses
    `CD3DApplication::BuildDeviceList` (bdl); moving `BattleEngine.h`'s `PlayHudSample` (Stuart's placement) is
    harmless.
  - DXLandscape is an object-boundary question: retail's statics sit in two regions, `008aa9xx` and `008c02xx`.
  - ltshell has no evidence-based header form: Stuart's in-class `SRS`/`STS` bodies would create `mRenderStates`
    first, the reverse of retail's order, and retail has `SRS`/`STS` out of line.
  - DXImposter's `sCount` comes from `imposter.h`'s inline destructor, which other objects need; the object also has the
    open forward-funclet shape.
  - BattleEngineConfigurations and BattleEngineDataManager belong to class (B): their header accessors fit retail, and
    only ZERO_FVECTOR's early creation differs (next item).
- **Open: maths-constant creation points.** Retail's ZERO_FVECTOR/ID_FMATRIX are created at different moments per object.
  Early (last in memory): PCMemoryCard (ZERO after `sFindData`, `sFindHandle`; include at line 281), BattleEngineConfigurations,
  LandscapeTexture, DXMemoryManager (include at line 267). Late or split: MeshRenderer (ID, ZERO, then the file's own vector),
  PCMusic (MUSIC after ID, ZERO), d3dutil and dxutil (ZERO before ID, the reverse of `mathsconst.h`'s definition order),
  debugmarker (ID, DEBUGMARKERS, ZERO, DBT), MapWhoEntry and ParticleSet (the `mathsconst2.h` pair created before the first
  pair). One early `extern` plus an inline body naming ZERO_FVECTOR gives the early cases (PCMemoryCard probe: `.bss`
  `sFindData`, `sFindHandle`, ZERO, the funclet still after the code, code identical), but the d3dutil/dxutil order needs
  ID_FMATRIX mentioned first, so more than one mention site is implied.
- **Class (C), the first-defined constructed object laid out first**: debris DEBRIS_ZERO, renderinfo,
  renderqueue, DXTexture TEXTURE_ZERO, System SURF, VertexShader, PCRTID RENDER_DATA, game `wait_for_start`, DXImposter.
  Retail's initializer table (`.CRT$XCU`, read from the specimen's `.data`, entries named by our `init:` annotations)
  lists each object's initializers in its code order for 6 of the 8 checked, as ours always does. There the leader is
  not created late: it is the one symbol nothing mentions before its definition, and the object's other symbols were
  created earlier by mentions (in-header accessors ours lacks, as VertexShader's four class statics imply; the maths
  constants' early creation, class (B); System's statics created through their uses). So it is the creation rule, not a
  separate mechanism.
  - Open, a registration order our compiler never produces: VertexShader's VERTEX_SHADER_MENU initializer is first in
    code (`00501650`) but registered (and its symbol created) last; renderqueue's `00551590` is second in code but
    registered after its maths constants; and RENDERINFO_ZERO and RENDERQUEUE_ZERO are registered outside their objects'
    runs, ahead of DXPatchManager's PATCHMANAGER. DXTexture's entries interleave with DXSurf's, which our annotations
    share (an annotation question first).
  - Falsified for it: `__declspec(selectany)` (VC6 refuses it for a dynamically initialized object, error C2496); a
    static member of a class template (a communal symbol with a guarded initializer, merged across objects and laid out
    at the `.bss` tail); and every single-file form tried.
- **Open: a constructor-class object laid out after an explicitly initialized static.** DXMemoryManager: retail has
  `MEM_MANAGER`, `mInit` (`= FALSE`, group 2), then ZERO_FVECTOR. The mini TU (`int a1; int b = 0; OBJ; int a2;`) gives
  `a2, OBJ, a1, b` for every constructor-class OBJ. Tried without effect: `#pragma init_seg(compiler|lib|user)`,
  `#pragma data_seg` (the object leaves `.bss`), a namespace, `extern "C++"`, `extern "C"`, `/Gy-`, `/Od`, `/Ox`, `/O1`,
  `/Gm`, plus the form matrix above.
- **Rejected: extern then late definition.** `extern const FVector ZERO_FVECTOR;` early with a mentioning inline body and
  the definition left at the late include gives retail's `.bss` order for PCMemoryCard, but the late `const` (or `static
  const`) definition after an `extern` has external linkage in VC6 (`?ZERO_FVECTOR@@3VFVector@@B`), so every object using it
  would export the name and collide at link (LNK2005). Not the original form.
- **Class statics** land after the file's group-1 objects when an in-class body (an accessor or an inline constructor)
  names them, since that creates them at the class definition (BattleEngineConfigurations, FastVB before ,
  ResourceAccumulator); otherwise a class static is created at its definition like any symbol (a probe: `struct K { static int ks; }; static int pa; int K::ks; static int pb;` gives `pb, ks, pa`, and an in-class `Get()`
  naming `ks` puts it last).

### Float constants
A float literal compiles to a COMDAT constant named for its value as the compiler computed it, an 80-bit number
(`__real@4@...`, or `__real@8@...` for a double). Every object that uses it defines it and the first definer in link order
keeps it, so the object holding a constant names the objects whose code used it (`tools/constowner.py`).
- A division by a constant compiles to an `fmul` by the reciprocal computed in double precision: `x / 255.0f` names
  `__real@4@3ff78080808080808000`, while `x * (1.0f / 255.0f)` is folded in float (`__real@4@3ff7808081...`), and no
  product or cast spelling gives the division's name. The code and the stored bytes are the same; only the name, and so
  the holding object, differs. A division by an inexact divisor names even an exact value apart: `x / 0.05f` is
  `__real@4@40039fffffd800000800` (19.9999997), stored as 20.0f.
- So a value retail keeps at two addresses had two spellings, and each instruction's retail operand says which: 92 sites
  divide where they multiplied (speeds per 20 Hz tick, Stuart's `/20.0f`, including `CLOCK_TICK` products; percentages
  `/ 100.0f`; `/ 0.05f` and `/ 0.1f` for the second copies of 20 and 10).
- `x * c1 * c2` folds into one constant; `(x * c1) * c2` keeps two multiplies (DXWater's grid fade).
- A `static const float` is an item of the object's own `.rdata`, which links before its COMDATs; a literal sits with the
  code's constants after the vtable.

### RTTI order
`/GR` places the complete-object locator before each vtable. Locator order follows class declaration order in the
object (reverse of declaration for small objects; a hash walk past about 14 classes), so some headers and `.cpp` files
declare classes in retail's order. Under the PCH, vtable order matches retail; a TU's own classes follow declaration
order, header-pulled classes keep PCH order.

### Class names from the RTTI census
Retail's RTTI type descriptors are the strongest name evidence there is: 667 `.?AV`/`.?AU` names in retail and 667 in our image
after the source took retail's: our `CTexture` is retail's `CDXTexture` (the PC texture, vtable `005e59a0`), our `CTextureCore`
is retail's `CTexture` (the base record at offset 8, with `DeviceObject` at 0, as retail's R1 base-class descriptors show), our
`CAsyncCache` is `CXBOXAsyncCache`, and `CRenderMethod` is a `struct` (`.?AU`). Renaming changes no code byte (a masked compare
of all 329 objects shows only the six renamed type-descriptor strings differ) and gave the two classes their vtable matches in
`config/classes.tsv` (`CDXTexture @ 005e59a0`, `CXBOXAsyncCache @ 005e4f5c`). Re-run the census after any class rename:
compare the `.?A[UV]...@@` strings of the specimen's `.data` with ours.

### Resources and header
The resource file rebuilt from retail's `.rsrc` is pinned and linked like a library; `linkcmp` compares the tree (12 of 12
leaves, image equal with RVAs rebased). Header fields are compared per field (34 of 42 equal on the current link).

## Data layout: what remains

`tools/alignedeq.py` measures it. `LINKDIR` is a `tools/link.py` output; run a check first, the tool reads the objects
under `build/` for relocations.

- Plain `alignedeq LINKDIR`: each retail-paired function (4,615) compared with retail's at its own address over
  retail's extent. Three numbers: raw 93.78%, REL32 operands masked 95.93%, every relocated word masked 100.00%. The last
  one is "code identical except addresses"; at 100.00% the remaining differences in `.text` are all addresses (calls and
  jumps by placement and library layout, absolute words by data layout). The masks are our objects' COFF relocations (retail
  has no `.reloc`), found through the object folders, split by function inside a plain `.text` section, and followed through
  ICF folds (a folded name takes the relocations of the name at its address that has an object section).
- `--breakdown`: the unequal relocated words by what our word points at. REL32: other game object 16,721 of 17,400, library
  1,391 of 1,427, same object 416 of 2,738, import thunk 61 of 61. DIR32 (the ~51 KB of the 4.07% step): `.bss` 15,931 words,
  `.rdata` 8,562, `.data` 6,554, code (function pointers) 1,111. No call is wired wrongly: of the 19,700 unequal words that
  point into `.text`, 17,449 target the function retail's word points at, none a different one. Calls differ because caller and
  callee sit at different shifts, data words because every data section is shifted.
- `--data-events`: pairs our data with retail's through the code's own DIR32 references (our word against retail's word),
  groups targets into runs of constant ours-minus-retail offset, keeps the heaviest run of runs whose offset never increases
  (a missing byte only pushes later data lower) as the chain, and prints each boundary's step and symbol. A prefix fill curve
  says how many referenced words become equal after N bytes are inserted in address order. Words off the chain are references
  to data retail places elsewhere (a second ladder, or placeholders).

State:

| Section | Referenced words | Chain | Steps | What would make the chain equal |
|---|---|---|---|---|
| `.bss` | 15,931 | 11,440 words in 53 runs | 35,456 bytes retail has that we lack; the first ~500 bytes carry 2,903 words, ~17.5 KB (through PCPlatform and ltshell) 11,424 | the placeholder class (concession): DXSurf 16.3 KB, ltshell `mRenderStates` 6.6 KB, Profile 6.1 KB are big holes with 34 reference words, the staircase of steps up to 1.6 KB carries the words |
| `.data` | 6,576 | 5,512 words in 56 runs | 208 bytes of 4..16-byte steps (the chain begins at +32; the lowest referenced datum is at +0 in both images, so that is not extra bytes) | the causes below |
| `.rdata` | 8,568 | 6,334 words in 21 runs | IAT (the chain begins at +28 by permutation, not bytes; 16 bytes of zero dwords after zlib's slots against ours 4), dxguid -1,036 | the causes below |

Causes found (each checked against the specimen):

- **Import address table.** Same 14 DLL blocks in the same order and the same slot counts. Retail has one extra zero dword after KERNEL32's 112 slots (MSVFW32's null thunk: blocks sort by DLL name and MSVFW32 sorts between KERNEL32 and USER32, the ghost of the dropped AVI recorder) and 12 more zero bytes after the last block, so the first vtable pool sits 16 bytes lower in ours (every `actor.obj` `.rdata` word, ~6,300). The 12 are not further DLLs: `.rdata` starts on a 16-byte boundary after `.idata$5`, so with the one thunk `.idata$5` ends at `0x5d83c4` and `.rdata` starts at `0x5d83d0` (the import stand-in row). The slots inside a DLL are permuted (KERNEL32 112 of 112 positions, USER32 35 of 37, GDI32 16, WINMM 8, binkw32 12, zlib 2, ogg 11, vorbis 13, VERSION 2). The "28 bytes too many at the start" of the `.rdata` fill curve is this permutation seen through the `__imp_` references, not bytes.
- **dxguid.** (dilib4 landed: dinput8's `dilib4.obj` after `dxerr9.obj` in `link-library-order.txt` places `c_dfDIJoystick2`, whose object formats sit at `005cfa30` (retail `005cfaa0`) and its DIDATAFORMAT before dxguid, moves the late-LIBCMT tail from -0xac3 to -0x7c and shrinks the dxguid step from -1,064 to -544; `.text` +16, so the +99 window has 19 bytes of slack. The figures below are from before it.) Not missing GUIDs: retail's dxguid block (16 symbols, 256 bytes) equals ours byte for byte. The -1,036 step is
  d3dx9/dxerr9 order ahead of it: the dxerr9 strings (3,497 publics) sit 3,328 bytes lower in ours, the d3dx9 init/
  cpslegacyprogram block (3.2 KB) is about 99 KB earlier in retail, and a 1,040-byte table of 12-byte records (flag, 0, 0, ending
  in a pointer into `.text`) lies right before dxguid in retail and after it in ours (476 bytes match).
- **`kWeaponCoolRate` copies.** `weapon.h` defines `static int kWeaponCoolRate = 1;`, so every translation unit that sees
  it carries a 4-byte copy at the head of its non-COMDAT `.data`, used or not. That makes the copies a per-unit witness of
  which retail objects saw `weapon.h`. Most of the -4/-8 steps in `.data`'s offset chain were copies retail has and we lacked.
  The fix adds `#include "weapon.h"` to the 13 objects where retail's word is byte-visible and only one candidate object fits
  (Building, gcgamut, mapwho, Submarine, Tentacle, screenfx, radar, WarspiteDomeAI, BattleLine, explosion, FearGrid, DXHud,
  DXImposter). It also moves PDSimpleSprite's mid-file `game.h` includes to the top, so its copy precedes `TRAIL_DETAIL` as in
  retail. All code is byte-identical. Effect: `.data` constant-offset runs 114 -> 97, words at retail's own address 1 -> 229,
  negative chain steps 34 -> 20 (216 -> 136 bytes). The chain-words figure falls (5,689 -> 5,381) because raising later offsets
  towards 0 while earlier steps stay open moves words off the heaviest non-increasing run: the equal-word and fill numbers are the
  progress measure. Open, end stage:
  - Retail lacks the copy in FrontEndData, MotionController, DXFMV and DXShadows (byte-checked; for MotionController, Stuart's
    Music.cpp reaches `weapon.h` through `career.h`, so the extra copy is MotionController's). Each needs an include that brings
    `weapon.h` in, so this is evidence that retail's FrontEnd/game header graph differed for those units.
  - Four one-word gaps have two candidate objects each: DiveBomberGuide/Dropship, HiveBossGuide/HLCollisionDetector,
    MCMine/MCSentinel, NormalSquadTargetSelector/Geometry. The image bytes are the same either way, so the attribution would be a
    guess.
  - The remaining +-4 jitter around 8-aligned items (`??_R0`, doubles) is alignment phase: it follows any offset = 4 mod 8.
- **RTTI creation order.** `Bomber.obj` has CBomberAI before CBomberGuide (retail the other way), `collisionseekingthing.obj`
  CSphere before CMeshCollisionVolume. The descriptors are byte-identical; the order follows type-record creation (above), and
  `tools/rttiorder.py search` improves each (2 of 3, 3 of 5) without reaching retail.
- **Literal creation order.** `actor.obj`'s float pool starts 1.0f, 0.0f, 1.0e-4 in retail and the reverse in ours (the three
  constants of thing.h's inline bodies; 2,183 references). Header-content evidence, parked.
- **A literal's first definer is a dropped function.** The shared `"\n"` literal sits at retail `0x622d9c`, in the tail of
  `animation.obj`'s pool, before `CAtmospherics`'s descriptor (ours: after it, in Atmospherics.obj, costing a pad); `animation.obj`
  has no live user. `"meshtex\\default.tga"` (12 users, none in `console.cpp`) is kept at retail `0x625498` in `console.obj`'s
  pool, ours in `debugmarker.obj`. Both are COMDAT literals whose first definer in link order was a function `/OPT:REF`
  removed (the `Cutscene::Save` pattern); Stuart's release has neither `animation.cpp` nor `console.cpp`. Evidence only.
- **Missing initialised statics.** Controller's four statics were reordered (`mNumMappings` after the two options); fixed.
  Retail's Controller and gcgamut pools carry further words (an initialised 7-bool array before `cg_renderimposters`,
  `1`s before type descriptors) that are copies of `kWeaponCoolRate` or statics not found yet.
- **One constant, two names.** `2.55f` was `__real@4@4000a333330000000000` (Carver, DXCockpit) beside BattleEngine's double-named
  `__real@4@4000a333333333333800`; retail has one copy shared by the three. Respelled as BattleEngine's `255.0f-(mStealth/100.0f*255.0f)`
 : `.rdata` chain 6,334 -> 6,813 words, `.data` 5,520 -> 5,697, and CPhysicsScriptStatements' -8 is gone.

Fixed: Controller, the 2.55 constant. End-stage: the `.bss` placeholders (35,456 bytes behind
the first ~17.5 KB staircase), the IAT tail and slot order, d3dx9 member order (the 1,040-byte table, the cps
members), RTTI creation order, the weapon.h include sets, the dropped functions in animation and console.

## Tools

| Tool | Use |
|---|---|
| `tools/link.py` | the pinned link; |
| `tools/linkcmp.py` | header, sections, symbols at retail addresses, order metric, imports, resources; `--write-expected` writes the symbol→address file the other tools read |
| `tools/icfsim.py` | ICF simulator; `--report --expected X.json` measures convergence |
| `tools/rttiorder.py` | `survey`: each object's `??_R4` order against retail's; `search OBJ`: the creation-order declaration line (reverse-retail, then greedy), compiled from a copy under `build/`, accepted only with the line count kept and code identical |
| `tools/dataorder.py` | data-section order measure (`.rdata`, `.data` incl. `.bss`) |
| `tools/rtti.py` | locator order |
| `tools/inventory.py` | the whole-exe difference inventory: every differing byte charged to an item (paired by code, data relocations, library bytes, EH tables and content) and the root causes per area, with net/abs/items; headline `.text` size against retail; |
| `tools/datacontent.py` | every initialised data symbol the matched code reaches (pinned through code relocations, then data relocations), compared with retail over its exact COFF size: content differences and wrong references |
| `tools/iatsim.py` | predicts the import address table from link.log: pass-1 import loads sorted by DLL name with Microsoft's qsort, discarded imports removed, each DLL's null thunk last. All 14 DLLs of our exe reproduce; with retail's per-DLL pull order inside our interleave only 4 of 12 do, so the retail array differs beyond order (see Open questions) |
| `tools/witness_scan.py` | header-count witnesses (DrawDebugStuff, BuildDeviceList, CPDTimeline, FEPGoodies::Render): current state, and the window of extra dead declarations each tolerates; the first two are periodic in the declaration count with period 64 (one declaration = one 32-id block, 2048 ids). Run `--state-only` on any merged tree before a full check (3 s per witness) |
| `tools/alignedeq.py` | shift-aligned code equality (raw, REL32-masked, all-relocations-masked); `--breakdown` classifies the unequal relocated words by target; `--data-events` lists the constant-offset runs of `.rdata`/`.data`/`.bss` against retail, with the chain, steps and the fill curve |
| `tools/constowner.py` | which object holds each float constant: every constant the matched code references pinned at its retail address, retail's owner from the pinned items around it, ours from the map; mismatches classed "emission" (both use it) or "missing code" (retail's owner has no use of it in our source), and names that retail keeps at two addresses with our sites by the copy they address (the third section, "one name, two retail copies"; `--sites` lists every site, `--json` writes all three). |

## Concessions

Each is labelled where it lives and removed when its question closes.
- **`clock.obj` library-order line** (`config/link-library-order.txt`): forces LIBCMT's `clock.obj`
  into the link at `0055e42a` because retail's `.CRT$XI` table holds `___inittime`; retail's referrer is unknown.
- **Specimen data**: the shader-fragment block comes from the specimen, not source (above).
- **Import thunks as an object** (`config/link-thunks.txt`, `tools/link.py` `thunk_object`; LINK CONCESSION): retail's 32
  import thunks (`jmp [IAT]`, `0055d5e0..0055d69a`) sit directly before its first CRT member, because retail loaded those
  import-library members before the CRT members. Ours are command-line objects and LINK loads library members only after
  every object, so the thunks would land at the end of `.text`. link.py writes a COFF object defining each thunk symbol as
  `jmp [__imp_SYMBOL]`, in retail's order (a test checks the list against the specimen), and links it before the first
  library member; the import libraries then supply only the `__imp_` data. Effect: the library region (first CRT member to
  the funclet block) is 192 bytes shorter (+496 to +304 against retail's 473,200); pull order, import-address-table and
  annotated-function counters do not move. Still with the libraries, as in retail: `Direct3DCreate9`, `DirectInput8Create`
  and `_RtlUnwind`.
- **Objects linked after the library members** (`config/link-objects.txt` "[after libraries]", `tools/link.py`
  `late_objects`; LINK CONCESSION, for our tooling): retail searched LIBCMT as a library, so its C runtime commons came
  after every object's. We link the extracted members as objects after the game's, which by the reverse-order rule
  would put their commons ahead of PauseMenu's. `pausecommons.c` therefore links after the members. Leaving the
  common-defining members to library search instead moves their code (`.text` equal in place 222,265 to 113,021) and
  was rejected.
- **`linklib/provisional.cpp` and `linklib/aliases.tsv`**: link-only definitions (e.g. `SYSTEM` at `00896ca4`) and weak
  aliases for second names whose owner or layout is open. Never part of the score.
  Its two initializer funclets (`_$E10`, 32 bytes, and `_$E13`, 208 bytes, 240 bytes in all, linked after the last CRT member)
  belong to `SYSTEM`'s real defining object (the missing-objects question); they and the three-versus-two thunk are what
  remains of the library region's excess over retail's after the thunks above (304 = 240 + 6 + padding + the library members'
  net +3 and NvTriStrip's +16).
- **mixermap's dropped `delete []` witness**:
  retail emits `SMixerSlot`'s constructor (`00523200`) and destructor (`00523210`) between `SMixerSlot::Init` and
  `CMixerMap::Destroy`. The constructor is a plain out-of-line definition after `Init`. The destructor cannot be: a plain
  copy folds by ICF into `CText::Shutdown` (`004f2170`, the same bytes in retail, where the two are not folded), so retail's
  was inline, and an inline destructor comes out after its first user. A function between them needed it out of line
  and `/OPT:REF` dropped it; its original is unknown, so an unreferenced `delete []` stands in. Code-neutral: every
  object but mixermap.obj is byte-identical (Map.obj renumbers two local labels), all 5,482 of the full working tree match, `.text` size unchanged;
  mixermap's five functions are in retail's order (placement events 281 to 268 overall, partly ICF survivor reshuffle).
- **Layout stand-ins** in source, each marked `STAND-IN (layout)` .
  - `MemoryManager.h` makes the replacement `operator new(size_t)` and `operator delete(void *)` extern inline only in the
    objects whose copy retail keeps (`COLLISIONSEEKINGTHING_CPP`; `ENGINE_CPP` and four more), `static inline` elsewhere.
    VC6 emits an extern inline replacement new/delete as a COMDAT in every object that sees it, and plain selection keeps
    the first definer: with plain `inline` and no switches the survivors move to `activereader.obj` (delete, `004010c0`) and
    `actor.obj` (new, `004010d0`) against retail's `collisionseekingthing.obj` (`00426fd0`) and `engine.obj` (`00449d40`)
    (measured). ICF cannot fold them into place either, since it folds only COMDATs of the same selection.
    Re-measured (2026-10-16): with plain `inline` new/delete and no switches, all 5,482 functions of the full working tree
    still match, but the survivors are the first definers again (delete `activereader.obj` `004010c0`, new `actor.obj`
    `004010d0`); the fold work does not change it, so the switches and the six non-PCH objects stay.
- **PENDING, not committed: unreferenced `.bss` placeholders.** See the candidate list below. They are applied last,
  after the `.bss` order and size work, so they fill only what is left.

## Link concessions (candidate)

Not yet decided: each keeps one thing out of retail's position to hold another that matters more.
- **mixermap and texture keep `mathsconst.h` at the top** (`005233c0`, `004f2c40`). Retail's `.bss` puts `ZERO_FVECTOR` as if it were defined before `MIXERMAP` (mixermap) and before `CTextureCore::mFirst` (texture), while retail's initializer table and code put its initializer after theirs. On our compiler (`/Yu common.h`) a `.bss` slot follows the definition, not the first declaration: an early `extern` declaration, even one referenced before a late definition, still lands the object as if defined late; an early definition gives retail's `.bss` order. So no source form gives both; the include stays early (retail's `.bss` order held) and those two initializers (`005233c0`, `004f2c40`) stay out of position. `BattleEngineConfigurations` and `PCMemoryCard` have the same conflict and currently take the other side: the include stays late (retail's initializer position held) and their `.bss` order stays out of retail's.
- **The `.bss` emission-order family** (about 46 objects, plus 12 built without the PCH).
  - Explained since (2026-10-16): the first group is reverse symbol creation, not definition (`tools/bsscreate.py`; the
    `.bss` order section above). "First-defined lowest" is class (C) above; DXWater's function statics were explicitly
    initialized in retail; a function-local static is created at its first use.
  - Probes, under `/Yu common.h`:
    - A study tried static, const, extern-then-define, static member,
      unnamed namespace, references, intervening functions, constructor spellings, PCH-resident definitions, and
      the real include text. All gave pure reverse definition order, with initializer order equal to definition
      order, so retail's debris (`.bss` D, I, Z with initializers D, Z, I) cannot be produced under both rules at once.
    - a local static is created at its first use, or at its declaration if that has an initializer.
    - Our DXWater already defines its data where retail's initializers place it.
  - Line: ours holds four unreferenced `static FVector` (`Line.cpp` sUnknown0..3, 64 bytes,
    no pins) before ID_FMATRIX and ZERO_FVECTOR; retail starts the object with the constants (ID_FMATRIX at 006fad18) and
    runs 176 bytes to map.obj, so its statics, 48 bytes more than ours, follow the constants. The inventory's "Lights +64" is
    this object's span, not Lights' (its `.bss` is exactly the constants' 64 bytes); most of the other "ours larger" `.bss`
    rows (Shell, MenuItem, FEPControls/FEPCommon, CRT members) are the same pin-to-pin attribution, not storage.
  - Objects: Atmospherics, BattleEngineConfigurations, Career, Credits, DXImposter, DXLandscape, DXMemoryManager,
    DXMeshVB, DXParticleTexture, DXSurf, DXTexture, DXWater, FEPControls, FEPMain, FastVB, Font, LandscapeTexture,
    LandscapeVB, MapWhoEntry, MeshRenderer, MessageBox, PCController, PCMemoryCard, PCMusic, PCRTID, PDSimpleSprite,
    ParticleManager, ParticleSet, PauseMenu, ResourceAccumulator, SimpleBuilding, System, VertexShader, console,
    d3dapp, d3dutil, debris, debugmarker, dxutil, game, ltshell, pcsoundmanager, renderinfo, renderqueue, text,
    vbuftexture.
  - Objects built without the PCH (`config/no-pch.txt`) follow a name hash instead: BattleEngineDataManager,
    DXMeshRenderer, InitThing, MCMech, IScript, ScriptObjectCode, PCMusicStream, PCPlatform, SoundManager,
    collisionseekingthing, engine, mesh.
  - Open question: these are two systematic emission rules that our C1XX/C2 8966 does not follow from any source form
    tried. Retail's Rich header records its game objects at the same build (11, 8966), so the likelier cause is a
    compile option or input difference (how the PCH was created, include structure, or an option not yet tried), not
    a different compiler. Already probed with no change: /Z7, /Zi, /Gy-, /Od added to the pinned flags (a four-object
    dynamic-init probe stays pure reverse order, and the local static stays at its definition point).
  - Kept as they are; order only, no code or size effect.
- **Unreferenced `.bss` placeholders** (applied last). Four retail ranges, 33,752 bytes, that no code in the
  specimen addresses.
  - Evidence that nothing references them:
    - Our matched functions' `DIR32` relocations give every operand position exactly; none falls in these ranges.
    - A raw 4-byte scan of all of retail's `.text` and `.rdata` finds only misaligned byte patterns there, each
      checked against its instruction.
  - Planned form: one labelled static array per item (`STAND-IN (link layout)`), at the position the PCH rule
    gives it (under `/Yu`, uninitialised definitions land in reverse definition order).

  | Retail range | Bytes | Where it sits | Planned form |
  |---|---:|---|---|
  | `009cc248..009d08b4` | 18,028 | After `DXWater.obj` (the last game object in both images), before the CRT's `.bss` (`fpinit` `___fastflag`). `DXWater`'s own `.bss` is 168 bytes in both images, so this is not a missing `DXWater` array. | Its own placeholder object linked between `DXWater` and the CRT (a data-only object; no game object of ours follows `DXWater`). |
  | `0083e6b0..008406b8` | 8,200 (`0x2008`) | After `TokenArchive.obj`'s `ZERO_FVECTOR`/`ID_FMATRIX` (its first definitions, so its last `.bss`), before `tree.obj`'s `sOrientations`. | An array defined last in `tree.cpp`, so it lands first in tree's `.bss`. The other possibility is that `TokenArchive.h` defines it before `mathsconst.h`. Stuart's release has neither file. |
  | `0082b6a0..0082ce84` | 6,116 | After `CPolyBucketIndexList::sIterator`, before `profile.obj`'s `PROFILE_ENTRIES`. | An array in `PolyBucket.cpp` placed by the PCH rule. Stuart's release has no `PolyBucket.cpp`. |
  | `00889b28..0088a0a8` | 1,408 (`0x580`) | Inside `PCPlatform.obj`, between `GetSysTimeFloat`'s function-local `first_seen` and `PLATFORM`. | An array in `PCPlatform.cpp`. Stuart's file has only `PLATFORM` and the two function-local statics. |

  In-object items, also applied last. These are unreferenced bytes inside objects whose other statics code does
  reference. Each referenced symbol's retail slot (to the next referenced address in the same object) exceeds our
  exact COFF size, and nothing addresses the difference:

  | Object | Bytes | Where in retail |
  |---|---:|---|
  | `ltshell.obj` | 552 | Around the AVI-capture statics: 256 after `gDeviceHasLargeTextures`, 48 between `sAviFrame` and `sAviStream`, 256 after `sAviStream` (alignment `-4`s offset the total). Probably the `.bss` of capture start and stop code that `/OPT:REF` dropped (an `AVICOMPRESSOPTIONS` is 44 bytes, 48 aligned), unproven. |
  | `d3dutil.obj` | 304 | After its `ID_FMATRIX` (a non-PCH object). |
  | `d3dutils.obj` | 191 | After `GRID_INDICES` (an empty class whose initializer is a lone `ret`). |
  | `PCMusic.obj` | 152 | After `MUSIC`; matched code reads its fields only up to `+0x38`, inside our 64-byte object. |
  | `Line.obj` | 112 | After its `ZERO_FVECTOR`. |
  | `iscript.obj` | 36 | After `gEventArg`. |
  | `SimpleBuilding.obj` | 32 | 16 after each of `ID_FMATRIX2` and `ZERO_FVECTOR2`. |

Measurements: main;

## Convergence counters (whole-array, tracked, not gated)

These depend on every record of an array matching retail's, so a single correct commit can move them either way; they
measure how close the link is, and no commit is judged by them alone. Values:
- **ICF fold survivors** (`tools/icfsim.py --report`): 246 of 246 fold groups predicted; (a) size keys 0 of 4,608 differ
  (was 1 before the Load composite); (b) emission 0 extra, 0 missing; (c) library records 2,817 from 285 members, identity
  with retail's library builds not yet known. Annotated functions at the retail address in `linkcmp` (a whole-array hash of
  these survivors) read 5 of 4,975; 4,339 in retail's order.
- **`operator delete`'s survivor**: retail keeps engine's `??3@YAXPAX@Z` (`00449d40`); ours keeps activereader's copy
  (`004010c0`). The fold pair (`??3@YAXPAXW4EMemoryType@@PADI@Z`, first defined by activereader, and engine's
  `??3@YAXPAX@Z`) shares its key (16 bytes, 2 relocations) with 31 other records, and the unstable sort decides which comes
  first. Engine's won until ParticleDescriptor's FollowParticle was made a plain function, which changed the
  array's composition (bisected over the aroot chain, full check at every step). A whole-array effect: nothing in
  ParticleDescriptor is wrong and no local form restores it. Survivors in retail's object overall: 110 of 195 groups
  with a known retail survivor.
- **Import address table** (`linkcmp` imports): the descriptor order is equal; 0 of 14 DLLs equal in names, order, hints and
  IAT slots. The IAT is Microsoft's `qsort` over the pass-1 loads, so changing the pull order reshuffles it (an import batch moved the pull order, the `.idata$6` name strings, from 20 to 38 names at the exact retail position and
  longest in-order run 140 to 146, while the IAT position count fell 26 to 15 of 226). Pull order is the layer to improve.
- **Initializer table** (`.CRT$XC*` between `___xc_a` `00622000` and `___xc_z` `00622b0c`, measured):
  the same in both images: 706 slots, `ZERO_FVECTOR` 288, `ID_FMATRIX` 271, empty (`ret`) 19, other 128, with no slot
  empty in one image and filled in the other; 24 slots hold a different kind at the same position (initializer order).
  The `.CRT$XI`/`XP`/`XT` tables and the pad to `00622b80` sit at the same addresses too.
- **`.bss`**: objects with at least two placed symbols out of retail's relative order 39 of 286.

## Open questions

- **Deferred inline placement, left open.** Fixable, not done: `CMemoryBlock::SetBaseSet` (an `inline` definition in `MemoryManager.cpp` after `DumpMemory`; MemoryManager.h is in the PCH. `~CMemoryManager` after `LogDebugStats` in DXMemoryManager (this move broke dmg before; use the witness search). Evidence only: BattleEngine's `FVector::Normalise` after `GenericSPtrSet::First/Next` means the pointer-set header came before maths in retail's TU (Stuart's `thing.h` includes `PtrSet.h` second; ours includes `mathsconst.h` first, and moving it re-orders every TU's maths statics); gcgamut's `RequestShadow` before `MagnitudeSq` means a later, dropped function pulled `MagnitudeSq` out of line; collisionseekingthing's eager `operator new` sits at the object's end in retail; PolyBucket's five items (operators, `COSet`/`CArray` members). With others: the `??_G`-alone items (InfluenceMap, PauseMenu), MessageBox's `~COggLoader`, ParticleSet's `CPDTimelineEntry` constructor (beside the cpd witness).
- **Remaining `.bss` order after the placeholders.** The DX front group sits 40 bytes low because IScript's order is
  hash-based off the PCH (building it under `/Yu` gives retail's order but drops `ISCRIPT_CPP`: the decision table's
  conflict row); ltshell's statics before `LT` need header bodies (Stuart's DX8 `ltshell.h` shape); renderinfo's and
  renderqueue's statics are created by header bodies retail had.

- **About 134 C++ objects are missing from our link.** The Rich header records 464 C++ and 3 C game objects at build
  8966; our Rich header counts 330 C++ objects and 3 C ones (the three rebuilt C objects, Proven mechanisms). The
  missing ones carry no code, no initializers and no `__FILE__` users: every source path retail's data names (151
  `.cpp`/`.c` and 11 header names) is in `src/` and in our image. So they are not recoverable from
  the matched code; their names would explain the `.bss` gaps and the pulled-import count (242 vs 253).
  Nor does the image hold anything else of theirs: RTTI type names (667)
  and vtables (724 complete-object locators) are the same sets in retail and ours, every game initializer in retail's
  `.CRT$XCU` table (706; the other 8 are the C runtime's) has a counterpart in `src/`, so none of them includes the
  headers that bring the per-object maths constants, and `.data`/`.rdata` show no span retail holds that our objects do
  not. Only `.bss` does: 34 objects' spans are larger in retail (36,952 bytes; the largest are after DXWater, 18,028,
  before the C runtime; TokenArchive, 8,200; PolyBucket, 6,116; PCPlatform, 1,408). A missing object holding only
  unreferenced `.bss` would look the same as those, so the image cannot tell them from the placeholder concessions,
  which stay. The missing objects are therefore empty as far as the image shows: stubs, header-only files, or files
  whose content `/OPT:REF` dropped.
- **RTTI record order (`.rdata$r`, `??_R*`) is permuted by any declaration-count change in widely included headers.**
  Measured on `mapwhoentry.h`: 16 objects reorder only their `.rdata$r` and `.data` `??_R0`..`??_R4` sections (e.g.
  FrontEnd, 124 of 387 sections). An id-neutral variant (labels renumbered in 0 objects) still permutes 15, so the
  order follows the change, not the id count. Tracked as a convergence item, not gated per commit.
  Preprocessor conditionals count too (PCController.h reverted): wrapping in-class bodies
  in `#ifdef`/`#else`/`#endif` reorders FrontEnd's `??_R1`..`??_R4` records although the same tokens reach it, and an
  empty first branch does as well; nine blank lines or stripped comments do not. A `_CPP` guard therefore costs RTTI
  order in every includer.
  InitThing (on the PCH) has its ten complete-object locators in retail's order in neither build:
  retail SphereTrigger, Hazard, Cutscene, Feature, Wall, Squad, Spawner, Tree, Unit, InitThing; without the PCH Tree,
  Hazard, Feature, Unit, SphereTrigger, Cutscene, Wall, Squad, Spawner, InitThing; with it Spawner, Unit, Tree,
  SphereTrigger, Cutscene, Wall, Squad, Hazard, Feature, InitThing.
  Rule search: renaming every class leaves the
  order unchanged, adding classes never reorders the earlier ones, and unrelated struct declarations ahead of the
  classes move it. Our `InitThing.h` and `InitThing.cpp` already follow Stuart's declaration and function order.
  Creation, not allocation size, decides the walk:
  - With one out-of-line constructor per class, records follow function-definition order. When one function brings out
    many classes' records (a factory), the order is close to creation order descending.
  - A forward declaration `class F;`, or an elaborated `class F *m;` member in an earlier class, creates F's record and
    moves it. A cast in an inline body after F was declared, or `class F;` after the classes, does not.
  - Pad structs shift the start: with 0 or 1 pads the first class comes first and the rest descend; with 2 to 12 pads
    the order is pure descending.
  - From about 14 classes up, chained buckets show (at 20 classes, records 15 apart share a bucket, newest first). No (c
    ± t) mod M model fits all cases, which is consistent with buckets keyed by where each record was allocated, with
    allocation following creation.
  - InitThing reaches retail's order. Forward-declaring its ten derived classes right after `Common.h`, in the reverse
    of retail's order (Unit, Tree, Spawner, Squad, Wall, Feature, Cutscene, Hazard, SphereTrigger, Start), gives
    retail's 11 locators exactly, with all 24 functions byte-identical when the file's line count is kept. No header we
    have or Stuart released mentions most of them earlier, so retail's creation order implies earlier mentions in a
    header `InitThing.h` includes before its definitions (or in the precompiled header).
  - InitThing carries that line as a labelled reconstruction (it replaces the blank line after the includes; all ten
    names are needed). It is the one applied case.
  - Survey: 90 objects have two or more pinned locators. With InitThing's
    line, 29 are in retail's order and 61 differ (355 of their 734 locators on in-order runs; 28 and 62 without it). Searching
    each with at most 30 compiles, the reverse-retail declaration line alone makes 11 exact: WorldPhysicsManager (32 to
    70 of 70), oids (13 to 40 of 40), BattleEngine, Camera, Cockpit, NavigationMap, PCRTID, Start, DXShadows, PCMusic
    and rtmesh. It improves 10 more, among them CPhysicsScriptStatements (134 to 239 of 294), FrontEnd (9 to 25 of 27),
    PauseMenu (10 to 26 of 27), DataType (2 to 6 of 7) and ParticleSet (7 to 12 of 14). In all, 585 of the 734 locators
    land on in-order runs. These counts are order-only; `search` accepts a variant only if the file keeps its line count
    and every function stays byte-identical.
  - The other 40 do not move. 34 of them already have their functions in retail's order, and their locators come out
    after several different functions, not as one batch: retail brought those records out at other points, which is a
    separate question. The remaining 6 (Building, DiveBomber, GroundAttackAircraft, MessageBox, world, Unit) also have
    inline or fold items out of order.
  - End-stage plan: the declaration line fits any batch walk, so it proves retail's creation order but not where the
    original's mentions were. Like a placeholder it is a fitting knob, honest and code-neutral. The 11 exact objects and
    the near-misses are held for the end stage, after header reconstruction has had the chance to make some of them
    natural or unnecessary.
  So RTTI order is header-content evidence, as the `.bss` order is (both follow creation), not a necessary concession.
  It is 97% of `.rdata` order churn.
- **(11, 8047) 9 versus 10.** Retail has ten C++ CRT members; we link nine (ehvecctr, ehvecdtr, frame, handler, hooks, trnsctrl, typinfo, unhandld, validate). Adding `new.obj` or `delete.obj` makes ten with no code (their COMDATs are dropped) and one multiply-defined line, but retail's `.text` has neither's bytes (0 and 1 coincidental hit) and the game defines operator new/delete itself, so nothing would pull them: left open, no Rich-only pull.
- **Import `.idata$5` input.** Within a DLL the IAT is Microsoft-`qsort`ed pass-1 load order, but our pull order puts
  only 20 of KERNEL32's 112 entries in retail's order, and USER32, GDI32,
  binkw32 and vorbis differ too: retail has another `.idata$5` input (unknown objects or another sorting runtime).
- **Ghost import DLLs and the dropped AVI recorder** (evidence for the import residual). The Rich header counts import members loaded in pass 1: retail 253, ours 239 (our 226 kept plus 13 discarded imports), so retail loaded about 14 more imports than ours and `/OPT:REF` dropped them. Retail's `.idata$6` holds the DLL-name strings `comdlg32.dll` (`0x620e16`, between GDI32's and ADVAPI32's blocks) and `MSVFW32.dll` (`0x620f24`, between DSOUND's names and AVIFIL32's) with no descriptor and no import: a name string survives only if a member of that DLL was loaded, so retail loaded at least one member of each and dropped them all. The pinned LIBCMT, LIBCPMT, d3dx9, DxErr9 and NvTriStrip libraries contain none of the dialog, codec or AVI function names, and Stuart's tree has no AVI or commdlg code, so the loads came from game code that retail dropped. The fit: our `ltshell.cpp` has one AVI call (`AVIStreamWrite`, with the statics `sAviStream`, `sAviFrame`, `sAviFormat`, `sAviBuffer`) and an unreferenced `.bss` range beside them, and VFW.H's `static DWORD dwICValue` serves the `ICGetDefaultQuality`/`ICGetDefaultKeyFrameRate` macros (`ICSendMessage`, MSVFW32). Probable dropped names (inference, not evidence): AVIFIL32 `AVIFileInit`, `AVIFileOpenA`, `AVIFileCreateStreamA`, `AVIMakeCompressedStream`, `AVIStreamSetFormat`, `AVISaveOptions`, `AVIStreamRelease`, `AVIFileRelease`, `AVIFileExit`; MSVFW32 `ICSendMessage` (`ICCompressorChoose`); comdlg32 `GetSaveFileNameA`. A sort search around `AVIStreamWrite` (about 3,000 placements of such ghost records) reaches only 5 of 12 testable DLLs against 4 without them, because retail's cross-DLL pull interleave is not observable. Measured (a throwaway link): it gives Rich (1,0) 253, both ghost strings and an equal IAT directory, and moves game code's end (+48 → +32) and d3dx9's span (−2,819 → −2,739) toward retail, so retail's fold array likely held such a function; per-DLL order is unchanged and `.text` grows +64 → +128 (`COMDLG32.LIB` alone changes nothing).
- **Dynamic-initializer order** in objects with many initialised globals (e.g. Debris), and the `ID_FMATRIX` gaps.
- **Initializer funclet placement.** VC6 emits a dynamic initializer exactly where its static is defined (probed); 14
  objects have retail's later. FrontEndData's (after Init and Shutdown) point at a separate light `FrontEndData.h`, which
  Stuart's `Frontend.h` names but his release lacks; ours gets the constants with `frontend.h` (held: a header split).
- **Deleting destructor (`??_G`) placement.** VC6 emits `??_G` right after the first function that uses the class's
  vtable, after its in-class inline virtuals, and no definition placement moves it (probed). Where retail's `??_G` sits
  one function later, the function in between was often inline in the original and heads the same batch (Function
  emission order, above; CRTTree, CRTMesh, ParticleSet; CSquad fits either reading). Three cases contradict that:
  - `CRTCutscene`: ctor, the vtable group, `Unknown27`, `??_GCRTCutscene`, destructor. Retail folds `Unknown27`
    (`004dbc20`) with `CInfantryUnit::GetImposterFrames`, an out-of-line function, so it was not inline. Its `??_G`
    alone comes out a function late.
  - `CScaleMenuItem`: `Clone`, the `(DWORD, …)` constructor (`004a3510`), `??_GCScaleMenuItem`. That constructor's users
    are in PauseMenu.cpp, so as an inline it would not be emitted in MenuItem.obj.
  - `CUnit`: ctor, `FMatrix::MakeRotation`, `_GetClassName`, `GetMaxVelocity`, `??_GCUnit`. CUnit's own virtuals come
    late too, and `MakeRotation` cannot be inline (an explicit `inline` expands both calls in the constructor).
  Not `operator delete` (probed 2026-10-16): RTCutscene.cpp and MenuItem.cpp compiled with the PCH, without it,
  with delete extern inline (`ISCRIPT_CPP`), declared only, and defined out of line all emit `??_G` in the trigger's
  batch, ahead of the next function. Still untested: a class-specific `operator delete`, and how the destructor is
  declared in the class (implicit or not `virtual` in the derived class).
  COggLoader (MessageBox.obj) shows the timing side of it: retail's batch for `gVoiceLoader` is `??1`, `??0`, `Run`,
  `??_G` and comes out after the global's exit funclet (`004b6cc0`), while ours comes out after the init funclet with
  `??1` last. Retail's destructor was implicit (an explicit one changes code) and `Run` was an in-class inline (now
  placed). InfluenceMap has the same shape: CInfluenceNode's in-class virtuals sit where retail has them (after `Load`),
  and only its `??_G` and `??1` come late (after `IsEmpty`). No source form found for either.
- **Witness-coupled inline placement**. Retail's emission order says some header inline bodies sat after their
  class or out of it, while our witness functions need the in-class form, so a single move shifts a witness and moves
  that cancel have to land together.
  - Landed: PCController's six joystick and key inlines defined after
    `ReadControllerState`, where retail emits them (`005147b0..00514890`), together with WorldPhysicsManager's feature
    and hazard `Resolve` bodies moved into its `.cpp` and BattleEngine's `PlayHudSample(CEffect *)` defined inline in
    its `.cpp`. The PCController and WorldPhysicsManager moves each shift a witness alone (`CGame::DrawDebugStuff`,
    `CD3DApplication::BuildDeviceList`); landed together, all witnesses pass at k = 0.
    An earlier `PCCONTROLLER_CPP` guard worked too, but its `#ifdef`/`#else` directives moved the RTTI walk in four
    objects (reverted ).
  - Pending: Cockpit's render overrides after the class need three more declarations
    (DrawDebugStuff at k >= 2, BuildDeviceList at k >= 3); DXImposter's destructor move is neutral; three of Stuart's
    `ltshell.h` declarations balance the pair. Retail's survivors `00405910..00405930` are BattleEngine.obj's copies of
    CCockpit's overrides, in non-declaration order; the in-class form in that order changes `CPDTimeline::Unknown10`
    (`004c2640`).
  - Dropped: `~CMemoryManager` moved into DXMemoryManager.cpp (where retail emits it last) needs six balancing
    declarations, and alone it breaks `CDamageTexture::Load` (damage.obj `00440c70`, 219 bytes). That is a fifth
    witness (`dmg`): it passes for every declaration count 0..63 and reacts to the precompiled header's
    content (`MemoryManager.h` is in it), so `witness_scan` checks it as a state.
  - PolyBucket: retail's batch after `Build` is the constructor, `Unpack`, then FVector's `operator/` and `operator==`,
    so `Unpack` was defined before those operators in retail's file. That cannot happen while they live in `maths.h`
    (PolyBucket.h needs `maths.h` first): evidence that the operators came from a later header. No single move tried.
  - The balancing pool: 25 genuine bodiless Stuart declarations our common headers lack. Some sit under `#ifdef` and
    cannot be used, since a directive moves the RTTI walk.
  Which witnesses need which in-class bodies may be the clue to the original header layout.
- **NvTriStrip's release.** Retail links NVIDIA's prebuilt `nvtristrip.lib`: its two objects carry comp.id (49, 9044), Visual C++ 6 with the Processor Pack, which retail's Rich header lists twice (the (25, 9466) pair is something else). The residual is `NvStripifier::RemoveSmallStrips` (retail 654 bytes, this release 672): retail's exact release is not found. A C3-engine copy has retail's `RemoveSmallStrips` but differs in `FindAllStrips` and three `std::set` instances; both functions sit in the same member (`nvtristripobjects.obj`), so the two libraries cannot be combined member by member.
- **Which copy survives for `~CLine` and `??_GCLine`.** Not an emission question: BattleEngine.obj defines and selects both, and they fold with the `CCylinder` copies there, while retail's survivors are collisionseekingthing's `CSphere` copies (`00426340`, `00426360`). It is fold order, part of the ICF array convergence above.
- **Fold survivors: convergence status (measured 2026-10-16).** LINK makes 249 fold groups; retail's survivor is known
  (every name in the group at one retail address) for 195. As measured, 103 of those 195 keep their survivor in
  retail's object; the class-group order commits moved no survivor. Reordering every object's records by retail address
  in `icfsim`'s model would give 120 (it fixes 41 groups and breaks 24), so in-object emission order is worth at most
  about +17. The other 51 groups stay wrong under either order: mostly large groups of small bodies (return-a-constant
  slots) across BattleEngine, AsmInstruction and the front-end objects. No remaining mismatch traces to a record order
  that can be named. Survivors behave like a hash of the whole qsort input. About half the game records (4,898 of 9,698)
  have no retail position because `/OPT:REF` dropped them or they folded away, and 1,838 of the fold groups' 2,201
  members are such invisible copies, so their place in retail's array cannot be observed. Fold-survivor identity
  therefore stays a convergence item, and a link option cannot buy it cheaply. LINK 6's `/ORDER` does not place a
  function at an address: it moves every listed COMDAT to the front of `.text` in list order, and the rest follow
  (measured, throwaway). Listing the 195 groups' members (1,879 names) drops `.text` bytes equal in place
  from 225,583 to 181,785. Listing every annotated function in retail order (4,877 names, 189 KB) gives 4,560 functions
  in retail's order but 130,953 bytes in place, with 2 functions at their retail address, and it cannot name statics
  (LNK4037). `/ORDER` changes no fold selection (the same object kept in 249 of 249 groups), section address or library
  layout. It is useful only as a last step, once everything else sits at retail's addresses. A link-only alias list
  renames symbols without moving the kept copy (not measured).
- **Float constants held by another object than retail's** (`tools/constowner.py`, measured).
  - No use in our source of retail's owner. Each is a function we have not written, one `/OPT:REF` dropped, or a spelling
    the tool cannot see:

    | Retail address | Value | Retail owner | Ours held by (our users) |
    |---|---|---|---|
    | `005dc648` | 70 | MenuItem or MenuOptionsList | PlaneAI (CPlaneAI, CThunderheadGuide) |
    | `005dc240` | 1.1 | Lights or Map | MenuOptionsList (CMenuOptionsList::Render, CPauseMenu::Render) |
    | `005dc244` | 1/512.1 | MenuOptionsList or MapWho | Map (CMap at `00490a40`) |

    The last two sit around Map, MapWho and MenuOptionsList, whose `.rdata` order may differ from link order; they are
    probably one question.
  - One spelling or the other, not yet decided (both sides use the value, written as a division on one side and a
    product on the other; Stuart's source has neither file): Animal's 1/32767 against MeshCollisionVolume, MeshPart,
    PolyBucket and StaticShadows; BattleEngine's 2.55 against Carver and DXCockpit; FEPBriefing's 1/480 and 1/640 against
    DXSpriteRenderer; gcgamut's 1/60 against DXLandscape and MessageLog.
  - Names retail keeps at two addresses whose sites still share one name of ours (`constowner.py`, "one name, two retail
    copies"): 68 (`005dbe60`, Hud), 160 (`005db490`, FEPControls), 1/64 (`005dbb4c`, FrontEnd and Hud) and 1/127
    (MusicMenu at `005dc7a0`, PCMusic at `005e4978`), each beside the copy every other user addresses. A division by the
    inexact reciprocal explained 10 and 20 (above); 68, 160 and 1/64 have no such divisor in the code as written (an int
    literal, a cast or a folded expression give the one name, a double gives `__real@8`, a `const float` is the object's
    own `.rdata` and changes the code), so their second spelling is open. 1/127 is inexact: one of its two sites is
    probably the float-folded `(1.0f / 127.0f)`, not yet decided.
