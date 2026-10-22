# Matching techniques

Status: reference, exported from the working repository's notes
Last updated: 2026-10-22
Summary: The working rules for reaching a byte match, each with the function that proved it.

- **Index of the October 2 rules** (each has its entry under "Near-misses, since matched" with the
  measurements; one line per rule, with the row that proved it):
  - A loop counter shared with an earlier loop blocks the later loop's hoisting and strength reduction (SwizzleTexture
    `0054f380`); a running index `T[k++]` places the strength-reduced step where it increments (SwizzleBlock).
  - User pointers set up before a loop's zero-trip test are stepped by hand (SwizzleTexture).
  - An expression argument to an inline adds one counted IL node (Mech `0049fdb0`); one shared call after the blocks
    replaces a copy in a stop/else arm (UnitAI `004feac0`).
  - Variable reuse decides frame slot classes; a missing or added conflict edge means a reused variable.
  - A value split between a named local and the written-out expression places an x87 copy (DXCompass `0053c510`);
    parameters adjusted in place rank older than locals (DXFrontEndVideo `00541790`); members written in the
    function text get early front-end symbols (RayHitsTriangle `004ee410`).
  - Value-returning accessors are the natural no-code id source, about one 32-id block per 8..26 sites
    (MCTentacle::Init `0049cc40`); two used named locals supply two ids (DrawDebugStuff3d `004e9f00`).
  - An OR can't be built in place from `* 0x10000`; only ADD consumers fold the copy (RenderDevice `004595b0`).
  - One header symbol count S decides BuildDeviceList, CPDTimeline and DrawDebugStuff together; keep S in {0, -1,
    -3} relative to the matched header package (the S = -1 header package matched debugmarker `00441ea0`).
  - Retail's call list reads constructions: `FMatrix m(a, b, c)` is the angle constructor with MakeRotationF and the
    row iterator denied as nested sites (GillMHeadAI, weapon `00509140`, Round Move); `ori * FVector(0, s, 0)` is the
    column-times-scalar retail pushes into one constructor (GillMHeadAI).
  - A matrix temporary of one statement shares the frame class a named matrix would block (GillMHeadAI).
  - The order in which shared products are first defined decides VC6's CSE order; define them first, in retail's
    order (UpdateFallingTree `004f6b80`); inline sinf/cosf and a named float are nodes that can move an 81-node cut.
  - A reference whose definition contains a load stays a pointer variable; one built from an accessor's result folds
    into displacements (UpdateFallingTree).
  - A parameter's web doesn't cross calls, so it keeps a callee-saved register even at negative priority; call-
    crossing locals are deferred (AddDamage `005475d0`).
  - A callee-saved register is pushed late iff its first web starts after the last conditional exit (153 retail
    epilogues).
  - The zero register coalesces into the variable initialised as the zero's last use (DXFMV Play `0053f190`).
  - A join that copies two registers into one and keeps implied tests is a separate tail variable (GetActualMaxRange
    `00509c80`).
  - The patch pointer read once into a named local (the read-form rule) fixes register roles (UpdateArea `005473b0`).
  - C2's global pass forward-substitutes an inline accessor's return symbol into call arguments only when the call's
    result is unused (CPDMesh `004c8ce0`).
  - VC6 doesn't reuse an expression across a call once a local's address has escaped; a value retail stores at its
    definition and reloads at its use is a spilled named local, not a CSE temporary (UpdateTileRange `0048ef00`).
  - A one-file `decomp.py check` can report `relocations` conflicts from COMDAT copies the full build attributes to
    other objects; the full score decides (UpdateFallingTree).
  - A 12-byte temporary class holding 4-byte slots at base and base+4 is a 2D value kept as a struct; "x on the FPU
    stack, y in memory" is a struct whose X is never stored (RenderRadar `00484c50`).

- Shared declarations can change VC6 register allocation in an otherwise untouched body: `DrawDebugStuff`
  (`00470650`) has flipped between a match and a one-byte miss (the two integer operands of its LEA at
  `00470825`) as headers changed; it matches on September 30. Count its actual current result, and never add
  dummy declarations to force a match.
- `CThing::IsOverWater` (`004f3de0`) matches through the spelling `(float)(double)MAP.GetWaterLevel()`, which
  gives retail's copy of the level through the FPU. The original spelling (perhaps a double-returning accessor) is
  unknown: a provenance question, not an unmatched function.
- Capture compiler diagnostics in separate anonymous files, not pipes. On this Wine setup CL exits roughly
  four seconds before inherited pipe writers close. Waiting only for CL preserves its error status and both
  diagnostic streams; all sections and relocations from `game.cpp` and `DXEngine.cpp` were unchanged, and a
  real failing VC6 compile still reported its errors. The prefix lock covers execution and diagnostic recheck.
- Stuart's files can be line-exact with the retail build (SPtrSet.cpp: its `new` lines 137, 183 and 227 are
  the retail `__LINE__` values). Seed a file verbatim, define the build macros (`TARGET == PC`) instead of
  deleting conditional blocks, and annotate with a trailing `// FUNCTION: 0x...` on the definition line so
  no line moves. Fix a diverging `__LINE__` with `#line` only where the retail value proves the original
  file differed.
- An annotation on a member defined inside a class body names that class's member (the harness qualifies it
  with the enclosing class, so `CComplexThing`'s inline `GetRealAnimIndex` never claims `CThing`'s). Overloads with
  the same parameter count take an explicit mangled symbol after the address.
- Codegen patterns seen in the front end, each checked against retail:
  - VC6's `floorf`/`cosf` are inline wrappers, so a call in an argument list is evaluated before any push
    (`CFEPBriefing::Render`).
  - An inline `bool` helper that should branch must return a constant from each branch. `return x == 0` gives
    `sete` (DXMemBuffer's `.aya` test shows the `sete` form).
  - A constant written as an inline float literal gives retail's `fld local; fmul [const]` order. A named
    global, `const` or not, is loaded first.
  - Float constants can be folded sums: `0x3e23d70b` is `0.15f + 0.01f` (`CFEPE3LevelSelect::Render`).
  - An if/else whose two calls differ in one argument cross-jumps into one shared call.
  - Registers `esi`, `edi`, `ebx`, `ebp` go to locals in descending use count, ties to the first definition. An
    inlined helper's parameters are those locals: reassigning them in a different order swaps their registers
    (`CDXMemBuffer::Close`).
  - Grade-letter constants such as 4.9999995 and 5.0000005 are `RangeTransition(t, 0.1f, 0.3f)` and
    `(t, 0.5f, 0.7f)`: VC6 folds the division by `end - start` into a multiply by its float reciprocal
    (`CFEPDevSelect::Render`).
  - A colour local such as `DWORD acol = alpha << 24` lets VC6 sink the alpha computation past the next call and
    forces the clamped value into memory; writing `(alpha << 24)` at each use keeps retail's register clamp
    (`CFEPDebriefing::Render`).
  - The inliner can refuse a nested inline: `FVector::Normalise` calling `Magnitude` left `Magnitude` out of line
    in `CEngine::SetupLights`, where retail inlines the whole length (`0044a30c`..`0044a326`) and instead calls
    `FVector::Set` out of line three times (`0044a3ae`).
  - Some register ties depend on how many inline functions the whole translation unit declares, not on the
    function's own code. `CGame::DrawDebugStuff` (`00470825`: which of two loads gets `edx`) matches with 3, 4 or 5
    extra unused inline members in an unrelated header and differs with 0, 1, 2 or 6; their names do not matter.
    Such a function can flip whenever any included header gains or loses an inline, so "register choice only"
    near misses may be header composition rather than wrong source. A full score after every header change
    catches the flips.
- An object's dynamic initializers come first in its code, in source order. The static each maths-constant initializer writes settles
  ownership: `00449730` writes `00672f38` inside engine.obj's data and `0044a740` writes `00672f78` beside
  eventmanager.obj's (`EVENT_MANAGER` `00672fc8`); DXEngine's pair `0053d220` writes `0089d670`, after `ENGINE` and
  `OLD_WATER_TIMING`. `objects.tsv`'s initializer column names the next object's first initializers.
- Loops keep their test at the top (unrotated) whenever the condition starts with a flag, even one never set:
  `BOOL done = FALSE; while (!done && i < n) { ...; i++; }`. `i < n && flag`
  and plain `for`/`while`/`goto` forms get rotated.
- `rcori.Transpose()` in `UpdateSoundPosition` calls column getters `004aa3f0` and `004b0c00` out of line.
  The first operates on standalone matrices at `004e16b2` and `004b08cf`; the earlier claim that it also
  represents a folded `CMeshPart::GetBasisX` is unproven. Stuart's `printf` in SoundManager.cpp resolves to the empty trace function
  `0040c640`, so the PC build compiled it as `TRACE`. Whether a callee is inlined follows VC6's auto-inline
  threshold on the callee itself; code-neutral statements and dummy inline members in the caller do not change it.
- `maths.h`: `FMatrix * FVector` sums each row as `X + (Z + Y)`, the best of all 24 orders (gains
  `GetInterpolatedAutoAimPos`, `BuildInterpolatedWorldTransform`, `CViewPointCamera::GetPos`); it costs
  `SelectNearestForwardTargetFromGlobalSet` (`00406da0`), 10 bytes of fxch scheduling.
- The retail frame size is evidence of a local buffer's size: `DeviceInit`'s text buffer is 217–220 bytes, not 256,
  and `CreateSoundBuffer` builds a `PCMWAVEFORMAT`, not a `WAVEFORMATEX`. VC6 reuses dead parameter slots
  for locals (the `Lock` length is the `size` parameter itself). A struct chosen in a `switch` becomes a GUID-style
  local: each case loads all four dwords into registers and the stores are shared. A ternary assigned to a `WORD`
  narrows to `mov ax,imm`; retail's `mov eax,imm` comes from an inline `if`/`return` returning `int`.
- Build objects are case-insensitive under Wine: after renaming a source file's case, delete the old `.obj` in
  `build/`, or the compile fails without an error message.
- The header-composition tie-break (`CGame::DrawDebugStuff`, `00470825`; `BuildDeviceList` in d3dapp.cpp) counts
  every declaration a file sees, not only inline functions: enum constants and plain member declarations flip it too
 .
- When retail stores the virtual table pointer before a member such as a type id, the member is set in the derived
  constructor's body, not through a base-constructor argument (every physics-script value and statement, `00431bb0`).
- A virtual table's slot 0 relocates to the `??_E` alias of the deleting destructor; annotate the `??_G` symbol.
- Inline functions in a header whose allocations carry the header's `__LINE__` (WorldPhysicsManager.h's setters,
  constructors and `Add` functions, lines 193..2438) take `#line` before the allocation; the original layout is
  unknown. Where retail inlines a setter in one caller and calls it out of line in another, that is VC6's inline
  budget, not two copies of the code (`CRoundData::SetMesh` `00437fe0`).
- A conditional expression and the equivalent if/else compile differently when an arm returns a structure:
  `p = cond ? a->GetRandomSurfacePoint(0) : mPos` keeps the FVector in memory, the if/else keeps it in registers and
  spills `this`.
- VC6 /Ob2 inlines within a per-function budget: constructors expanded in a long switch stop being inlined part-way,
  functions defined later in the same file are still inlined, and non-inline functions auto-inline where the budget
  allows (`CParticleSet::Create`, `CParticleDescriptor`'s constructor at `004cc850`: its fields are an initializer list,
  stored before the vptr).
- Header inlines an object emits are placed from its vtables and matched code (a
  sweep of 52 objects added 51, BattleEngine.obj 21). Each translation unit has its own copy of the header's static
  `ZERO_FVECTOR` and `ID_FMATRIX`, so an inline that reads one belongs to the object whose copy it reads: the
  copies at `0066ea10` and `00829dd0` place `0043e9c0` and `004bfa00`..`004bfa40` outside thing.obj.

- `CCareer::Load` (`00421200`) matches with its successful suggest-next-level path as an `if`/`else` and one
  final `TRUE` return. This reproduces the late `esi`/`edi` saves and dead-argument slot reuse; separate successful
  returns did not. The version rejection and saved-state behavior are unchanged.
- The three PC save-file scans (`005149c0`, `00514a80`, `00514be0`) match using an inlined first/next-entry
  pair whose exhaustion path closes the search handle. Keeping each successful scan inside its `if` and putting
  failure after it reproduces the shared cleanup. `CreateSave` has a 256-byte basename buffer beside its
  260-byte path buffer, and compares a copied first name before refreshing the name at the loop's end. These
  are compiled-code findings, not file-system or Windows runtime acceptance.
- A switch gets a direct jump table only when every id in its range has its own case; one shared case gives a
  byte-indexed table (oids.obj's SpawnThing keeps separate `return NULL` cases from id 2 up).
- `switch { case X: ...; default: Base::HandleEvent(); }` gives retail's `je`-to-case layout where if/else does not;
  `delete p; p = NULL;` (not SAFE_DELETE) gives an unconditional NULL store; a retail `test al,al` after a call means
  the callee returns `bool`, not BOOL (cutscene helper, 2026-09-29).
- Lookups that walk two pointers (an id word and a result word) keep both when the stride varies and merge them into
  one induction variable when it is constant (text.obj `004f24b0`, `004f2500`, `004f2580`).

- `#pragma auto_inline(off)` reproduces calls retail makes out of line where our build inlines them (vbuftexture.obj's
  four draws around GetNumIndexedPrimitives/GetNumPrimitives, VertexShader's GetEntry around GetDeclarationNames,
  MessageBox's StopCurrentPlayingSound); no natural source form tried did. Whether the original used the pragma is
  unproven; each use cites its retail call sites.
- CGame::DrawDebugStuff (`00470650`) is a threshold on the declarations game.cpp sees: after the UI and landscape
  merges it needed at least two more (1 more still differs, 2 and 3 match). Keep only real declarations; a full
  score after any header change catches a flip.
- A base class's offset follows its alignment: COggFileRead holds 64-bit Vorbis state, so it sits at +0x20 after
  a 0x1c-byte CWaitingThread in COggLoader (MessageBox.obj `004b6d30`).
- Only a `for` increment `i += 4, p += 6` moves the pointer as retail does; an explicit default repeating the last
  case leaves retail's lone `dec eax`; cases 0..3 each with their own return keep a jump table from starting at 4;
  `(a * K1) * K2` keeps both multiplies (shell helper).
- `&= 0xff - mask` gives retail's `or cl,0xff; sub cl,dl` where `&= ~mask` does not; `& ~0x8000` keeps two ANDs
  where `& 0x7fff` folds; `(t * 0.2f) * 255.0f` keeps both constants (cutscene helper).
- A float member copied through an inline accessor gives `fld`/`fstp`, a plain member read copies through integer
  registers; a destructor retail never stores a vtable in is the implicit one; list walks match only through
  `ListIterator<void>` (render helper).
- `float w = float(i);` as its own statement loads the int early and keeps it on the FPU; a block-scoped local
  inside a loop shares its stack slot with other locals (UI helper, `0047fc92`, `0048f620`).
- Stack slots: declaration order does not matter (`float a, b;` either way);
  spilled scalars are placed in first-read order, each taking the slot of a non-overlapping occupant that died
  most recently (LIFO), else growing the frame by a slot (fits 14 probes; e.g. a, b, c dead then s gives s = c's
  slot, not the lowest free one), so reordering reads can fix a frame. An address-taken struct in an early block shares its slot
  with later non-overlapping scalars and keeps the frame small; at function scope it keeps its own slot. In an early
  block, a 4-byte struct shares the first float's slot; an 8-byte struct takes the slot of the variable allocated
  just before it in read order (the last float's, if none is live across its block); 12- and 16-byte aggregates never
  share and sit above the floats (frame 4n + size). A float live across the struct's block pushes it past that float.
- RENDERINFO's initializer calls CLight's inline constructor out of line only when four more inline expansions
  follow: the matrices were D3DXMATRIX, each with an empty inline constructor, which an empty SRenderMatrix
  constructor reproduces. D3DX locals are built member by member, and chained zero assignments evaluate right to
  left (render helper).
- Regrouping the terms of maths.h's `FMatrix * FVector` (X + (Z + Y) against X + (Y + Z)) changes nothing: a full
  score gained and lost 0. The operand-order near misses in inlined matrix products come from elsewhere.
- A retail `fstp st(0)` epilogue means float locals kept on the FPU and popped at the end, not inline expressions
 ; `SINT index = mUnitData->mSmallExplosion;` before the call was the
  register lever in CTentacle::Move.
- Several objects can emit the same COMDAT; the checker compares each copy and keeps the best, as the linker kept one
  (`??_GDeviceObject` `00512dc0` is ltshell.obj's inline-destructor copy, not DXShadows.obj's).
- Loading a member into a local before the call (`SINT index = mUnitData->mExplosion;`, `CMeshPart *part = ...;`)
  fixed the register choice in four functions in one day.
- VC6's auto-inline limit is size-based and counts dead code: retail calls SMixerSlot::Init out of line where our
  smaller reconstruction inlines it; eight dead `if (0)` calls reproduce the refusal, four do not.
  Where no evidence shows the missing code, `#pragma auto_inline(off)` stands in and says so.
- One-byte empty initializers (MeshPart's cache statics, 004adf40..004adf70) carry no relocation, so `init:NAME`
  cannot place them yet.
- Inline-budget probes: appending test statements shows how many expansions tip a call out of line (Infantry's Init
  needs its two-expansion yaw, `init->mOrientation.GetColumnY().Azimuth()`, before retail's out-of-line
  CCollisionSeekingThing constructor appears). CEulerAngles takes `const float &`: CInfantry::Init reads the yaw through
  its address with no temporaries, and 00449560 is called with three addresses.
- `FVector v; v = FVector(...);` builds a temporary and copies it; `FVector v = FVector(...);` builds in place. Retail's
  temp-then-copy needs the assignment form. A column length written out as `sqrtf(v.X*v.X + v.Y*v.Y + v.Z*v.Z)`
  gives retail's `fst tmp; fmul tmp`, where an inlined `FVector::Magnitude()` keeps Z on the FPU stack.
- VC6 /Ob2 inlines breadth-first within a per-function budget: every call written in the body expands
  first, top-down, and only then the calls those expansions expose (FVector's constructor inside operator-, Magnitude
  inside Elevation). Later top-level content therefore pushes an earlier nested call out of line; trivial accessors are
  always inlined yet spend budget; the budget grows with the function's own non-inline code. This explains the guide
  slot 3s (AirGuide, CarrierGuide, GroundVehicleGuide...): retail's source used many more inline accessors than our
  reconstructions. /Ob1, inline_depth, dead statements and unused locals are not the lever.
- A char-valued `?:` stays byte-wide (`sete dl; dec edx; and edx, ecx`) only when both arms are char: write the zero arm
  `(char)0`; a plain `0` promotes to int and branches (CByteSpriteEncoder::EncodeFrame 004189f0).
- The declaration order of locals decides operand order in `lea` and in commutative `imul` of two members: declaring the
  row pointer after the loop counters, or reading the members through a copied pointer (`e = enc`), gave retail's order
  where reordering the expression did not (EncodeFrame, CByteSprite::Load 004184c0).
- In an override reached through a secondary base (a CMonitor::HandleEvent of a class whose first base is
  IRenderableThing), retail's `lea esi, [ecx-4]` and branchy null checks come from working through a local pointer to the
  whole object (`CScreenOverlay *so = this;`), not from `this` directly (004de7d0).
- A thing class whose destructor is out of line in its own file makes that object emit the vtable's inline functions,
  which is why retail places them there (CBuildingNamedMesh 004183d0); a class constructed inline elsewhere does not.
- Many unwritten addresses are out-of-line copies a written object already emits (an inline the budget left called, an implicit destructor, `CInitCSThing::Initialise`, `UPhysicsManager::GetExplosionIndex`): they need only an annotation.
- A lone 31-byte ZERO_FVECTOR initializer after an object's code (no ID_FMATRIX one) belongs to the object before it
  (Atmospherics.obj 00404cc0, PCPlatform, texture, DXMemoryManager, LandscapeTexture, maptex, mixermap). These
  and BattleEngineConfigurations, DXSurf, LandscapeVB, PCController and PCMemoryCard (and ParticleSet's second pair)
  register no ID_FMATRIX initializer, and retail holds no static copy of the matrix for them: mathsconst.h and
  mathsconst2.h leave it out under their `*_CPP` defines.
- Appending with `a[n++]` from `n = 0` differs from writing the first fixed slots and starting `n` at their count: VC6
  materialises the constant counter only where it stops being constant (CVertexShader::BuildRenderInfoShader 00503b20).
- A flag set by if/else and then tested on its own is laid out differently from one if/else that also makes the call:
  the arm that only stores lands after the function's first return (CVertexShader::RestoreDeviceObjects 00501ab2).
- Locals initialised in their declarations schedule their stores by declaration position: the D3DX buffers are
  cleared before the version string is copied (CVertexShader::CompileShader 00502462).
- Which import VC6 caches in which callee-saved register can flip when one call goes through an inline wrapper
 .
- A value assigned to a local before a call is evaluated first and takes eax; the later temporary takes ecx. An
  inline forwarding wrapper binds its parameters left to right to the same effect.
- `abs()` is an intrinsic here (cdq, xor, sub). Where retail tests and negates (test, jge, neg), the source wrote the
  magnitude by hand (CSeedUniformRandomNumberStream::Next 004de951).
- Any static whose class has an empty user constructor, a single FVector included, emits a lone-ret initializer
  that initorder:K places (Line.obj 004908c0..004908f0, DXSurf's STATICSHADOWS 00556420, SimpleBuilding 004dfd40).
  A POD static emits none: CFEPBEConfig's and CFEPWingmen's saved projection is a D3DMATRIX, not an SRenderMatrix.
  A function-local static's destructor thunk is registered with atexit instead and has no .CRT$XCU entry:
  localexit:CLASS::FUNC names it.
- An object whose methods all fold into identical bodies elsewhere (ICF) shows only its initializers and the COMDAT
  copies it contributed first: Line.obj is its maths pair, four empty initializers and FVector::operator-= (00490900).
- An inline that one object always calls out of line can be hidden from that object alone: PDSimpleSprite.obj calls
  CFloatRef::GetValue at 004c10c0 everywhere, so ParticleDescriptor.h guards its inline body from that object.
- Appending with `a[n++]` from `n = 0` and a light counted outside its limit test were the last two differences in
  CVertexShader::BuildRenderInfoShader; the software flag set by if/else and tested on its own fixed RestoreDeviceObjects.
- VC6 treats parentheses as a barrier for constant folding: `(x * 3.14f) / 180.0f` keeps two multiplies where
  `x * 3.14f * (1.0f / 180.0f)` folds. A keep/destroy branch takes retail's layout only through a
  `BOOL keep` flag the optimizer then removes. FMatrix::MakeFromDirection(dir, back) is what puts
  neg, cross and Normalise out of line in the mech's part orientations.
- `x = x / n` and `x /= n` spend the inline budget differently, and `a = b = k` stores b first.
  `pos = GetRenderPos(); pos += box->mOrigin;` calls first where the plain `+` form evaluates the box first.
- The permuter's first batch match (CComponent 00428500) was a semantic fix: retail computes `turn * ori` where the
  reconstruction had `ori * turn`. A near miss that looks like header operand order can be a reversed product.
- An if/else-if chain that shares one `return FALSE` saves ebx after the first test, as retail does; separate returns
  keep it saved from entry.
- IsDying's inline if/else compiles to `movsx eax, byte; and eax, 4; shr eax, 2`; `(mFlags & TF_DYING) != 0` loses
  the movsx, and `>> 2` forms give sar/and.
- An explosion index read into a local for the spawn call, while GetExplosionData re-reads the member, is retail's
  form. `mOrientation * FVector(0, 0.001f, 0)` with the zeros
  folded schedules like retail where three written-out column multiplies do not.
- Within one inline level, a site may expand only while everything expanded so far fits a budget that grows with the plain code before that site: early sites are denied first, statements added before a site let it expand, and accessors or helpers anywhere add consumption (retail World::Clear 0050ada0 calls the first two mThings.First() out of line and inlines the later one; A diagnostic, never committed: pad with `gpad[k] = Id(x);` statements until retail's out-of-line set appears, then find real code of the same cost. Whether a function defined in the .cpp is expanded into its caller depends on its size before inlining: InfluenceMap::Update expands into HandleEvent 0048c120 only once its link walk is a `static inline` helper. A data point on the order: inside a nested inline (the 9-float FMatrix constructor) the early row sites are denied first, while in a top-level run of row assignments (FMatrix::MakeRotation 004f8140 writing yaw rows into the reused pitch matrix) the later rows go out of line and row 0 stays inline, as in retail. Retail's row-0-inline identity in MCBuggy/MCTentacle GetPartTransform (004944d0, 0049e660) is such a top-level run into a matrix not freshly default-constructed there; its source is still open.
- A single-file check cannot see a cross-object symbol conflict. A call to the wrong library routine can still
  "match" when the checker maps the name onto retail's routine (PCMusicStream calling `_stricmp`/`strncpy` where
  retail calls the multibyte `_mbsicmp` 0055f8a1 and `_mbsnbcpy` 0055f807). Every other caller of the real routine
  then fails: main dropped to 4,891 with 10 conflicts. Run a full check before pushing anything that changes a
  library call or a header. The inherited eight table conflicts were resolved on September 30; the baseline
  is now zero conflicts, with table results finalized only after global discovery.
- A float member read through an inline accessor compares as a value (fld, fxch, fcompp) where a direct member read
  gives `fcomp mem`. A switch on an int
  loaded from a short member narrows to `mov ax / cmp ax` when the value dies at the compares; retail's movsx and
  cmp eax appear when a later test keeps it live.
  A float local on its last use compares the same way as the accessor read.
- Retail reloads pointers after calls where a reconstruction caches them in a local: CDestroyableSegment::Update
  00442d40 reads part->mBoundingBox again after each GAME.Random().
- A member loaded early onto the FPU and consumed later with `fsubr st, st(1)` is a float local read before the arithmetic. Both restore the file after measuring. Both take 8-digit addresses (0x004c9000). Bytes alone and raw instruction counts both rewarded edits that moved code away from retail.
- Compare each near miss's emitted size with retail's extent (`decomp.retail_functions()`): a diff over our own length can hide stubs. The earlier September 30 scan found a one-line placeholder for CTree::GetRenderOrientation 004f6560 and flagged 27 bodies, including then-short 00443a20 and 00540b60. Those descriptions are historical: the compiled-object census after the table corrections found no emitted unmatched body shorter than 60% of its recorded retail extent. That snapshot had six unplaced annotations; later callable-helper and resize corrections supersede that count. Substantial code is present; that does not establish exact matching or semantic completeness. The latest complete score log owns current placement results.
- **Budget tell:** when retail repeats a run of out-of-line maths calls once per repetition (per edge, per corner, per lookup) and ours inlines them, write the repeated block as a `static inline` helper. Its operators become nested sites, which the budget denies first. Try this before accessors. SelectClosestPointOnTriangleEdges 00479200 went from shape 393 to 14 with a per-edge helper, and PolyBucket's unpack-and-compare helper made FVector::operator/ 004d4b90 and operator== 004d4bc0 emit and match. The tell cuts both ways: where retail expands a repeated body fully, an existing helper can be what blocks it. StaticShadows Build 004ec2f0 went from shape 1,159 to 439 once its eight shadow corners were written out instead of going through a ShadowCorner helper.
- Retail's jet loop trigger is a window, 0.2 to 0.1 s after the hard-forward start, where Stuart's release tests only
  0.2.
- The pause menu keeps its fade and the time since opening in one variable (one stack slot, 004d137a, 004d143f), so
  while it is open the lists appear 0.4 s after opening, not when the fade passes 0.4. `(open / 0.2f) * 1.1f` keeps both multiplies apart.
- Goodies' scrolling text passes flag `0x10` at `0045fe3d`, unlike the earlier released-source call's default flags. The original `00540640` wrapper forwards it; `0054018c` skips Y flooring when the bit is set. The reconstruction now preserves fractional Y at this call. The wrapper's final float is depth `z`, not scale; both scaling arguments are separately fixed at 1.0. Reproduction ran two original wrapper-argument cases and sixteen original rounding cases, including the actual CRT floor/control helpers, against pristine SHA-256 `74154bfae14ddc8ecb87a0766f5bc381c7b7f1ab334ed7a753040eda1e1e7750`. Render remains unmatched; no game frame or full font rendering was tested.
- **Cockpit operand-order correction, September 30.** Both `ProcessWalker` and `ProcessJet` now compute `mOrientation * rotation`, not `rotation * mOrientation`. Walker's receiver/RHS at `004250ca`–`004250cc` and Jet's inlined products establish the order. A separate check reproduced 16 isolated original-code cases: corrected XYZ bits and A4/A8 agree, while all 12 nonidentity-base controls reject the old order. Identity conceals the error, and normal-play nonidentity reachability is unproven. Walker's IsWalking and IsOnGround queries are explicitly false in this witness; matrix padding, full locomotion paths and player-visible behavior are not claimed. A separate check additionally checks candidate bounds with poisoned tails, stack canaries, nonvolatile registers and the x87 control word. Both bodies remain unmatched.
- **Unit contact normalization now matches, October 1.** `CUnit::Hit` (`004fcc30`) now reproduces the complete 400-byte section and all nine relocations. Sharing a downward vector between both slope tests, with the first-contact dot retained in a named float, restores retail's Y spill and normalized X/Y stores. The former scalar-Z expression let VC6 remove them and change threshold decisions. A separate check freshly compiled both sources: all 166 previous Unit exact address/symbol pairs survive, one is added, and the other 214 callable sections retain bytes and relocation referents. It also reran all 13,839 earlier authored native threshold cases at PC24/53/64: no corrected decision differs; the threshold control still changes 5,646. This closes the reconstructed body's numerical defect, not collision-generation/reachability or player acceptance. The fixed sum still reads three normals even when the report count is two; the producer evidence remains relevant. Source spelling is reconstructed, not claimed recovered verbatim.
- **Damage report snapshot, October 1.** `CUnit::Damage` reads the report's part index before the slot-9 virtual query (`004f9d08` versus `004f9d1e`) and indexes with that saved value. The reconstruction now retains the snapshot. The surrounding explosion-bit tests make this subblock unreachable under ordinary stable memory, and the three inspected getters do not write or call out. A separate check reproduced 24 isolated subblock cases across retail, old and corrected candidates: ordinary controls agree; six deliberately intervened report-mutation cases reject the old order and agree after correction. This is dormant-code fidelity, not an observed gameplay bug. The full Damage body remains unmatched.

**Wheel-base lookup precedes transform argument capture, October 5 (no exact gain).** `CMCBuggy::UpdateWheel` (`004934f0`) now binds the actual `WheelBase` part before preparing its first `GetTransform` arguments. Retail calls the finder at `00493e46`, then freshly loads `mThing` at `00493e58`, then calls the transform at `00493e6b`. The former compound receiver expression captured that owner and pushed transform arguments before the finder. The isolated correction restores the observed sequence without changing the two calls or their arguments. A separate check freshly compiled both versions: all 30 exact identities, the vtable and 33 sibling callable graphs survive. The second matrix initializer also adopts retail's three 16-byte `FVector` constructor callbacks rather than one 48-byte `FMatrix` callback. A separate check independently matches the finder at `004aa820` (128 section bytes, one relocation) and the existing empty vector constructor at `00402d20` (16 section bytes, no relocations); the alias earns no extra credit. The target still fails complete matching: 3,392 section bytes against a 3,613-byte retail body, with 2,817 differing positions versus the former 2,828. This proves static call/argument ordering, not callback mutation, a runtime bug, numerical equivalence or recovered original variable spelling. The unchanged pristine specimen is SHA-256 `74154bfae14ddc8ecb87a0766f5bc381c7b7f1ab334ed7a753040eda1e1e7750`.

**HUD world-text selector correction, October 8 (no new exact match).** The pristine specimen (BEA.exe, SHA-256 74154bfae14ddc8ecb87a0766f5bc381c7b7f1ab334ed7a753040eda1e1e7750) guards the state-minus-one selector at 00483a3d..00483a49 and dispatches through the six entries at 00484324. States 1/2/3/4/5/6 select integer, absolute count/target, clock, percentage, relative count/target and fractional clock respectively. The source had labels 2/4/5/6 on the percentage, fractional-clock, absolute and relative blocks; they are corrected to 4/6/2/5 without moving blocks or changing constants. This also agrees with the existing state-2/state-5 dual-count drawing branch. Native comparison instructions use 1.0f at 00483e4e and the target times binary32 0.1 at 00483f05; this does not claim untested NaN handling or player observations. All 32 exact HUD controls remain; RoutePanel itself is still unmatched. A separate check independently read the native table, guards and format/threshold branches and rebuilt the corrected object.

**Independent Round matching recheck, October 8.** The reconstructed CRound::Move reproduces the whole 2,768-byte compiled section and all 72 references; the measured retail body contributes 2,757 score bytes. A rebuild of the entire committed tree retained all previous symbol/source rows. Changing only the source scaling hint from __forceinline to ordinary inline gives a shorter 2,752-byte section, 99 nonrelocated differing positions and 70 references; the other 102 Round controls remain. The full matching is a documented compiler stand-in result, not proof of the original source spelling or portable validity of the derived-type cast. Replace these concessions only when supported natural source reproduces the complete sections/references and preserves earlier matches.
