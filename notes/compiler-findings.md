# Findings that shape the source

Status: reference, exported from the working repository's notes
Last updated: 2026-10-22
Summary: What the compiler, linker and retail evidence showed about the source's form, by finding.

**A dropped CCutscene::Save reconstructed from literal order, October 15.** Each function emits the string
literals it references first (reverse reference order, functions in source order), and retail's Cutscene literals
need a function before Load that first references the cutscene path, "1.00", `__FILE__` and the chunk tags CUTE,
CPOS, TRKS, EFAD, TDAT, SDAT in that order; Load's `#line 203` leaves room for it. `src/Cutscene.cpp` carries it,
labelled RECONSTRUCTED (dropped by /OPT:REF): its body is inferred from Load, not byte-verified, since nothing calls
it and only its literal references reach the image.

**Procedural-particle callback and rounding constraints, October 9.** A `004c9000` donor reproduces 105 ordered callee targets and the sphere distance's 32 FP
instructions, but that does not establish callback identity or whole behavior. Fresh pristine
inspection found cylinder distance grouped `(Z² + Y²) + X²` instead of `(X² + Z²) + Y²`,
and three start/end colour callback pairs reversed. Independent rational rounding controls
produce a one-binary32-ULP difference at x87 precision 24, 53 and 64. The callbacks can
reach the retail RNG; a static CRT-state-28 witness produces different colour values.
These are bounded instruction/arithmetic findings, not observed gameplay or a measured game CW.

One cylinder-only first-weighted-product spelling preserves its first R32
publication before the second callback and its wide final sum. Independent ordinary compilation
reproduces the sphere's 32 FP instructions, cylinder end-arm's 21 FP instructions, native
cylinder-distance operation order, and all 76 GetValue receiver orders. Its emitted view
constructor has all 32 bytes and empty relocation lists equal to native `00401ec0`, including
seven alignment NOPs; a proven alias restores all 105 callee bindings. That alias adds
zero unique-function credit and does not prove linker folding or original type ownership.
All 34 existing unique controls survive (35 symbol rows with the alias).

The full body still fails: 6,928 section bytes against the 6,956-byte native body, frame `0x16c` against `0x150`. No candidate is adopted and the score remains 5,470/5,482. Direct distance respelling loses two required calls; a local distance helper alters the sphere FP sequence and is rejected. Combining it with the colour spelling provides no new match. The older vertex-scope family remains a settled negative; new frame experiments need a measured change in actual lifetime/interference.

**Stack-layout replay corrected, October 9 (no function match).** The pinned VC6 C2 (`d50100ac2380d58f3f6f756961fb1319d35f5248e5fa6cafb866ca657e5dda4a`) sorts only local classes, after testing that their extent exceeds `0x80`. The replay previously included parameter classes in the unstable quicksort; removing them afterwards still left equal-density locals in the wrong order. The corrected layout reproduces all 19 local class memberships, sizes and homes in the retained ordinary multiplayer H9 candidate, with its 44 symbol weights and 251 reference events unchanged. Separate checks compared those homes against the actual ordinary object, not the older incompatible `varmap` object. Five authored tests cover parameter exclusion, unstable ties and the sorting threshold. Parameter precreation, fitting and unsharing/repacking remain limits of the generic packing model. H9 still has a `0x168` frame against retail's `0x164`; this tool correction does not establish a source or function match.

**Weapon fixed-pitch equality corrected, October 6 (no new function match).**
Pristine `BEA.exe`, SHA-256
`74154bfae14ddc8ecb87a0766f5bc381c7b7f1ab334ed7a753040eda1e1e7750`,
uses different admission masks in `CWeapon::Unknown507ab0` (`00507ab0`):
the early yaw gate at `00507dc8` tests AH with `1`, while the later fixed-pitch
gate at `00508712` tests AH with `0x41`. Both compare the absolute wrapped
difference against mode offset `0x84`. For ordered values yaw excludes
equality and pitch accepts it. Both masks also admit unordered status;
this is static instruction evidence, not proof of reachable NaNs or a retail
runtime observation. Reusing the strict yaw helper for pitch was wrong.

A reconstructed pitch-only helper uses negated greater-than, preserving the existing wrap operation and inputs. Its original name and ownership remain unknown. This is a natural predicate correction, not a compiler stand-in. A separate check independently compiled it with the pinned tools: exactly one byte changes (`TEST AH` immediate `01` to `41` at candidate `005089b6`), all 112 target references and 169 other sections remain unchanged, and all 55 local exact identities and five vtables are preserved. The helper fully inlines. The complete function remains 4,288 section bytes versus 3,582 retail body bytes, with 3,613 differing positions; no whole-function gain is claimed.

**Mech Body ground projection corrected, October 6 (no new function match).**
Pristine `BEA.exe`, SHA-256
`74154bfae14ddc8ecb87a0766f5bc381c7b7f1ab334ed7a753040eda1e1e7750`,
uses `(Z*pz + Y*py) + X*px` in all three Body rows at
`00499fa4..0049a02e`. X stays wide on x87 while Y/Z round to binary32;
position is then added and FootXYZ is published as binary32. The previous
generic matrix/vector expression associated Y/Z differently and retained
Z instead. A complete consumed destination writer now reproduces all 34
native FP instructions under an explicit map of five local homes. The
actual key-position input and callback phase are unchanged; Pad is neither
read nor written. Helper ownership and original spelling remain unknown;
this is pinned VC6 output, not a portable C++ rounding guarantee. The Leg
projection uses different groups and is not replaced with this operation.

A separate check independently recompiled the documented source and inspected the
pristine arithmetic and the new division dependency. Forty-four continuing
local exact identities and 49 sibling graphs are unchanged. The previous
local `+=` alias disappears because its erroneous out-of-line calls now
inline, as retail does (zero native `+=` calls). Three scalar `/=` calls
now appear at retail's corresponding operation; the emitted 32-byte body
independently matches pristine `004944b0`, with no relocations. Both retail
addresses were already matched elsewhere in the corpus, so this alias
exchange receives zero credit. Disappearance through correct inlining is
not a changed-body regression; the complete score must still preserve all
previously matched unique addresses and continuing emitted exact bodies.

The complete `UpdateBone` (`00499e30`) remains unmatched: 7,200 section bytes versus 7,540 retail body bytes, 132 target references, unresolved constructor/budget, frame and scheduling differences. A direct-expression alternative grows to 7,488 bytes and recovers another inline boundary, but reverses the first Y/Z pair in all rows; its earlier exact-34 claim would be invalid. No runtime observation or whole-target match is claimed.

**Buggy ground projection corrected, October 6 (no new function match).**
Against pristine `BEA.exe`, SHA-256
`74154bfae14ddc8ecb87a0766f5bc381c7b7f1ab334ed7a753040eda1e1e7750`,
Body's ground point in `CMCBuggy::UpdateWheel` (`004934f0`) associates each
matrix row as `(X*px + Z*pz) + Y*py`. At `004936cd..00493734`, X remains
wide on x87 while Y/Z are published as binary32; position is then added and
the three ground coordinates are published as binary32. The generic matrix
return had X/Y association and retained Z instead. A complete destination
writer now reproduces all 36 native FP instructions under an explicit map
of five local homes. Inputs remain the caller-owned position/orientation
and freshly loaded `part->mKeyPositions[0]`; no callback moves and Pad is
neither read nor written in this phase. The helper's name/ownership and the
original source spelling remain unknown; this is the pinned VC6 output,
not a portable language-level rounding guarantee.

A separate check freshly compiled baseline and proposal, inspected the pristine instructions independently, and retained all 30 prior exact identities, 33 sibling graphs and the vtable. This is a **local numerical correction**: integer setup scheduling differs, and the complete function still fails (3,424-byte section versus 3,613-byte retail body). One later subtraction now expands as native requires; another and the early identity-construction boundary remain wrong. The 78 target references are not a full relocation proof. Whole-function coverage receives zero credit. No retail game was launched or runtime acceptance claimed.

**Static-shadow occupancy query matches, October 3.** `COccupancy::BuildStaticShadows`
(`004bd9e0`) reproduces all 1,424 section bytes (1,410 body bytes), 36 relocations and its
80-byte exception-handler/data graph with seven references. The collision report now initializes
its first scalar before constructing six normal vectors, as the pristine executable
(SHA-256 `74154bfae14ddc8ecb87a0766f5bc381c7b7f1ab334ed7a753040eda1e1e7750`)
shows at `004bd159`, `004bdd63` and `0050b073`. Empty vector construction writes no components;
caller-specific resets remain outside that constructor. This changes no report layout.

The ordered line/sphere test uses two explicitly labelled source stand-ins, `ShadowHits` and `CollisionHit`. They normalize actual used BOOL results and retain short-circuit order, reproducing retail's comparisons and its ten SetCell calls plus one ClearCross call. A direct test after the construction correction differs in four bytes; separately normalized tests choose the wrong ClearCross expansion. The combined wrappers emit no standalone code or extra callback. Their names and original source organization are unknown and remain revisitable. Fresh builds of the occupancy, world, seeking-thing and mesh-collision objects preserve all 120 prior exact rows and add the query. The other occupancy builder and world line query still do not match.

**ReadVersion203 matches through a local matrix reconstruction, October 3.** `CMeshPart::ReadVersion203` (`004af470`) now matches all 1,856 compiled bytes and 25 relocations (1,848 recorded body bytes). A local plain column reader and transpose-result type preserve retail's constructor expansion. The copied matrix-vector operation transfers one redundant parenthesis pair from the Z product to Y in rows 1 and 2: the plain local owner left 18 bytes, each isolated transfer left nine, and the balanced combination matches while preserving the later pointer arithmetic. This type/helper ownership and spelling are explicit, revisitable source stand-ins; the original interfaces remain unknown. No state, runtime effects, shared-header, compiler or scoring changes were added. The extra constructor is called: all 96 bytes independently equal retail `00401f10` and the existing FMatrix constructor, and its alias is explicitly annotated without unique-function credit. A separate check freshly rebuilt baseline and candidate, preserved all 51 prior exact rows and 59 other callable graphs, then ran the complete integrated score. All earlier symbol/source rows and virtual-table verdicts survive, with no relocation conflicts. ReadVersion204 remains unmatched.

**RenderPart2D matches with a documented stand-in, October 3.** A separate check freshly compiled `0054b800`: all 1,920 section bytes (1,912 body bytes plus padding) and 39 relocation meanings match the pristine specimen. The unreachable `if (0) mc->AdjustFrame(part, &t);` emits no call; its intermediate address escape keeps retail's otherwise-unused fraction store at `0054b8e9`. Loading the triangle table before adding the index also recovers `0054b9ed`. The plain form has 1,440 differing positions. This is an explicitly authorized fallback, not recovered original source: the original address-taking operation remains unknown and the stand-in should be replaced if a better source form is found. All sibling callable graphs survive. The full integrated score preserves every previous exact row and all 891 vtable verdicts, with no reference conflicts. A separate check also freshly reproduced the preceding MakeRotation `004f8140` match.

- **Throwing array construction iterator identified, October 3.** The pinned VC6 LIBCMT symbol `??_L@YGXPAXIHP6EX0@Z1@Z` owns entry `0055dc20`. Independent archive extraction and fixed-owner symbol reconstruction prove eight complete code/data regions (748 bytes and 27 relocation words), including its cleanup, scope tables, exception handler and unwind support. The `RtlUnwind` import is checked against its PE thunk/IAT; the deeper `terminate` body remains an explicit frontier. Caller-consistent inference is no longer sufficient to substitute another iterator for this identity. Positive-entry and wrong-destructor/stale-annotation controls pass with all 42 decomp tests. The integrated full score preserves every prior symbol row and both coverage counts; this adds no game-function match.

**Emitter update matched, October 3.**
`CPDEmitter::Unknown10` (`004c1a90`) reproduces its complete 1,584-byte
compiled section and all 35 relocation meanings (1,582 scored game bytes).
The existing child `GetLife` read preserves the life-product load order;
`RandomScaled` borrows its scale and snapshots it before `rand`; the shared
frame transform borrows the destination position it updates. There are no
extra RNG calls, padding, artificial side effects or compiler changes.
A separate check independently rebuilt the source: all 83 earlier exact annotations
and 101 other complete callable/reference graphs survive. The unmatched
trail update (`004c36b0`) changes from 2,544 to 2,560 section bytes and gains
one out-of-line vector constructor, for 14 direct calls against retail's 15.
That change receives no matching credit or runtime-equivalence claim.
The complete integrated stock score preserves all 5,409 earlier symbol/source
rows and all 891 vtable results, adds only the emitter, and has no relocation
conflicts: 5,369 of 5,482 functions and 1,123,749 of 1,367,287 game bytes.
These are reconstructed matching interfaces, not recovered original source
spelling, linked-game acceptance or Godot parity. No original game code ran.
Specimen: `BEA.exe`, SHA-256
`74154bfae14ddc8ecb87a0766f5bc381c7b7f1ab334ed7a753040eda1e1e7750`.

**Influence-map loader matched, October 3.**
`CInfluenceMap::Load` (`0048b010`) now reproduces its entire 1,504-byte
compiled section and all 77 relocation meanings (1,500 scored game bytes).
The reconstructed fourth serialized node word, constructor argument and
member use `float`; link weights retain `SINT`. Retail snapshots all four
node arguments before its base calls (`0048b152`–`0048b1c4`). The former
integer-node model held the fourth argument in a register and produced a
different frame/register allocation. The float model closes that difference.
Coordinate assignments in the constructor body also reproduce version zero
scheduling: X is stored before the derived vtables, Y and radius after them
(`0048b404`–`0048b427`). Both all-body assignments and X-only initialization
match; the simpler all-body form is retained.
The fourth node word purpose and unique original source type remain unknown: a
matching representation/constructor model is not proof of original spelling
or a semantic weight interpretation. Its observed stores have no known
type-consuming use. No original game code was executed.
baseline/candidate/restored checks preserve prior exact controls and
complete sibling/reference graphs in InfluenceMap and world. A fresh final
stock build reproduces the gain. Full integrated stock score preserves every
previous matched address, adds only this loader and has no relocation conflicts:
5,368 of 5,482 functions and 1,122,167 of 1,367,287 game bytes.
Specimen: `BEA.exe`, SHA-256
`74154bfae14ddc8ecb87a0766f5bc381c7b7f1ab334ed7a753040eda1e1e7750`.

**Font UV rounding boundary restored, October 3.**
The by-value vertex helper had undone the earlier binary32 endpoint boundary
in `CDXBitmapFont::DrawTextScaled` (`00540010`). The helper again takes UVs by
reference and copies their representations into the existing vertex fields.
Retail stores `ty2` at `00540311`, reloads it at `0054032d`, then subtracts
`ty1` at `00540331`; the fresh compiled candidate likewise stores and reloads
that endpoint before subtraction. No new memcpy call is emitted. The old
by-value draft kept excess x87 precision across that operation.
baseline/candidate/restored stock builds preserve 15 exact controls and
all 17 other callable graphs. The function remains unmatched (1,584 section
bytes against the 1,581-byte retail body); its mixed integer/x87 vertex
transfers, width lifetime and remaining instruction choices still need work.
The integrated score preserves every prior matched address: 5,367 functions,
1,120,667 game bytes and no relocation conflicts. This is a static precision
correction, not a whole-function match or rendered-output acceptance.
Specimen: `BEA.exe`, SHA-256
`74154bfae14ddc8ecb87a0766f5bc381c7b7f1ab334ed7a753040eda1e1e7750`. No target code was executed.

**Ground guidance and console payloads, October 3.** The ground-guide turn gate (`0047d750`) compares with the exact double promotion of `0.6f`, loaded by `FCOMP` at `0047df57` from `005dbdb8`; the earlier `2.0` draft was wrong. Console variable-setting diagnostics (`0042a7b0`) now match the strings at `00625138` and `006250e0`: the matrix-form message ends with a period/newline, and the postfix example is `.yx` with a final period. These are independent specimen-backed payload corrections. Both bodies remain unmatched; no new exact function is credited. baseline/candidate/restored builds preserve 63 console and 12 ground-guide controls. The full integrated score preserves every prior matched address, 5,367 functions and 1,120,667 game bytes, without relocation conflicts. Specimen: BEA.exe, SHA-256 74154bfae14ddc8ecb87a0766f5bc381c7b7f1ab334ed7a753040eda1e1e7750. Only static analysis and stock compilation were used; no target code ran.

**Unmatched-body source corrections, October 3.**
Fresh instruction and literal inspection corrects `CHud::RenderTargetIndicator`
(`00482590`): the imposter uses U1-U0 and V1-V0 spans, DrawSprite's actual
U0/U1/V0/V1 argument order, and the retained `0x3fffffff` colour assignment.
The objective panel (`00483530`) uses signed font-height conversion, measures
only active world text slots, and shifts each flashing colour by eight before
subtracting its final channel. The former expressions instead used that
channel in the shift count. These corrections are instruction-backed;
remaining draw-branch, traversal and temporary differences stay open.

`CDXLandscape::AddDamage` (`005475d0`) compares with binary32 `0x3c23d70b`
at `005d8c60`. Natural `0.1f * 0.1f` produces the retail literal; the former
`0.01f` is one ULP lower. With initial last position zero, x=1053/32768 and
y=3103/32768 give exactly representable squared terms and sum `0x3c23d70a`:
the old draft falls through, while retail takes its early return. This is a
static arithmetic witness, not a game execution. Ten instruction-byte
differences remain, and the unchanged checker still refuses the whole function.

A line-collision ordering correction was independently rebuilt: `004ad830` acquires the packing pointer
after StartLineTriangleSearch and retains its render-thing local. It remains
unmatched. object checks preserve all 31 HUD, 56 landscape and 33
collision exact controls; the full integrated score preserves every prior
match and vtable with no relocation conflicts. **No new matches are credited**:
5,367 functions and 1,120,667 game bytes remain exact; 115 functions remain.
Specimen: BEA.exe, SHA-256
74154bfae14ddc8ecb87a0766f5bc381c7b7f1ab334ed7a753040eda1e1e7750. No target code was executed.

**Emitter reconstruction retained without match credit, October 2.**
`CPDEmitter::Unknown10` (`004c1a90`) now uses an earlier `emitter-position-destination` draft, re-derived under current headers.
The positive emission guard contains a real initial-velocity vector and
separate borrowed position references for outward velocity and world placement.
Its complete 1,584-byte section has two remaining differences, the life-product
operand bytes at `004c1ed2` and `004c1ed5`; it is still unmatched.
The inlined `TransmitFoR` Y/Z sums now have retail's `(Xx + Zz) + Yy`
association instead of `(Zz + Yy) + Xx`, which can change finite rounding.

A separate check independently verified all 35 references and preserved 99 other callable graphs and 80 exact controls. The old draft's historical Timeline regression does not occur with current headers. Full scoring preserves every prior match and vtable with zero reference conflicts. A separately tested complete life-transfer helper was graph-neutral and was rejected. No target execution, new match credit, original-source spelling or full equivalence is claimed.

**Polygon-bucket loading matched, October 2.**
`CPolyBucket::Load` (`004d59f0`) now matches its complete 1,072-byte
section and all 55 direct references (1,063 body bytes). Its cell-list reader
uses the stored entry count for the borrowed slice and read length. After
reading each list, the consumed-list counter advances before publishing the
list into the cell table. Separate loop counters remain intact. No shared
header or compiler change was needed.

A separate check independently rebuilt the source, preserved 38 other callable graphs and 29 exact controls, and verified the complete target plus its exception stub, exception metadata and folded placement-delete body: 66 references across four sections. The integrated score preserves every prior match and vtable with zero reference conflicts. This establishes compiled identity; no target execution or runtime loading acceptance was performed.

**Mesh-part collision and landscape shadows matched, October 2.**
`CMeshCollisionVolume::TestSweptSphereAgainstPart` (`004ac4a0`) now matches
its entire 576-byte section and all 16 references (575 body bytes). Its three
vertex queries use the real `CPolyBucketVertex::Unpack` interface. The
unchanged, already exact method body is available inline in `PolyBucket.h`;
the separate line-collision queries are unchanged.

`CDXLandscape::RenderShadowMap` (`00546490`) matches its complete 1,136-byte
section, all 81 direct references and both local exception sections (1,126
body bytes). A whole-grid index-buffer pointer preserves the value lifetime;
the two bindings use a local adaptation of the pinned source shell's
`D3D_SetIndices` operation, with the real shell receiver and D3D9 interface.
Adding that operation to `ltshell.h` disturbed two unrelated matches, so the
final source keeps the adapter in its consuming CPP. No header-symbol padding
or compiler changes were used.

Separate stock builds and reference checks preserved all prior matches and vtables, with zero relocation conflicts. Collision retained 42 other callable graphs; landscape retained 65, including unchanged shader constants verified against the specimen. The complete integration adds two functions and 1,701 body bytes. No target code was executed; this does not establish rendered or player acceptance, or original source spelling.

**Unit damage handling matched, October 2.**
`CUnit::Damage` (`004f9a90`) now reproduces the complete 2,592-byte section
and all 53 direct plus eight exception-related relocation meanings (2,586 body bytes). The source consistently
uses the existing mesh `GetPart` interface at its three part queries, retaining
the collision report index across the virtual mesh query. Character-specific
text lookup stays in each character branch, and the initial text ID follows
the random-line selection. These source ownership corrections restore retail's
control flow, value lifetimes and instruction order without padding or compiler
changes. This covers the routine's shield, damage, repair and destruction paths;
its caller/callee runtime context has not been exercised.

**Mesh optimizer and Wingmen light arguments refined, October 2.** `CMesh::OptimiseParts` (`004ab360`) reuses an earlier completed counter for child keys, retains the sole root child as a value, and records progress before removal bookkeeping. These natural source lifetimes reduce the 2,560-byte section from 119 to 69 differing positions.

Wingmen's preview lights (`00522190`) now retain the actual float products `0.8f/0.4f/0.2f * 0.6f`, following the pinned source's colour construction. The previous rounded decimal literals were one float step below retail. A separate check freshly reproduced precisely nine corrected non-relocation bytes and checked the three retail calls and the callee's RGB argument stores. All 460 references, 50 sibling graphs and 24 exact annotations remain unchanged. Neither function is a whole match; neither receives matching credit. Mesh stack homes and transform scheduling, and Wingmen camera rotation, remain open. No game or target code was executed.

**Briefing renderer matches, October 2.** `CFEPBriefing::Render` (`00451d50`) reproduces all 1,760 section bytes (1,748 body bytes) and all 129 references. The selected level is read directly for the language-specific layout test; its retained snapshot begins at the level-name lookup. That expresses distinct layout and lookup uses while VC6 still emits the one retail load. Used layout values also persist across the video and text stages: the row coordinate, pixel scales and each line's reveal value. No artificial operation, padding, compiler change or shared header edit is involved. No target code was executed.

**Polygon debug drawing matches, October 2.** `CPolyBucket::DebugRender` (`004d5e30`) reproduces all 896 section bytes (885 body bytes and eleven alignment bytes) and all 37 references. Unpack first converts each signed packed coordinate to a float value, then scales that same value in place by the packing scale and reciprocal before adding its origin. The arithmetic sequence remains unchanged; these are used coordinate values, without artificial operations or redundant grouping. The earlier bracket-dependent draft was rejected before publication. The replacement's standalone Unpack body remains exact, while its inlined copy now gives retail's drawing order. Fresh baseline/candidate builds preserve all 28 earlier exact annotations and 38 sibling callable graphs; independently bound reference targets and literal contents reproduce the whole linked section. Build and Load remain unmatched and unchanged. No target code was executed.

**Projectile initialization recovered without padding, October 2.** `CRound::Init` (`004d8410`) now matches all 1,600 section bytes (1,591 body bytes and nine alignment bytes) and every one of its 46 references. Both actual position reads use the existing `GetPos()` interface: the beam start and the straight-flight origin. No dead calls, unused values or fabricated side effects are added. This legitimately restores the credit withdrawn earlier today when the unsupported `if (0) mPos.Magnitude()` calls were removed; they remain absent. A separate check freshly compiled unpadded baseline and candidate, independently bound all targets, including recursively owned tables/EH and the COFF weak destructor alias, and compared the complete relocated section. All 102 previous exact annotations, 148 sibling callable graphs and the vtable results survive. A further ordinary orientation-accessor probe produces the same complete match but is unnecessary and not adopted. No target code was executed.

**Dive-bomber long-range controller matches, October 2.** `CDiveBomberAI::Unknown446150` (`00446150`) reproduces all 688 section/body bytes and all 19 references. One working range value starts with the target radius and becomes the surface gap; the breakaway displacement scales the local forward vector before the orientation transform and then reflects Z. Those genuine value boundaries restore the retail x87 operations, stack slots and final out-of-line `Unknown446400` call. A separate check freshly compiled baseline and candidate and independently bound every reference using other exact callers/callees or literal contents, then compared the complete relocated section. All thirteen previous exact controls and sixteen neighboring callable graphs remain unchanged. No target code was executed.

**Damage-texture load matches, October 2.** `CDamageTexture::Load` (`00440c70`) reproduces all 576 section bytes (483 body bytes, 85 switch-table bytes and 8 alignment bytes) and all 22 references. The source shares its source and destination cursors across inversion, mip filtering and rescaling; each four-pixel filter uses an indexed running sum, and width is halved before deriving the level buffers. A separate check freshly compiled baseline and candidate, independently bound calls, literals, switch targets, static offsets and exception metadata, and compared the whole relocated section. All ten earlier exact annotations, eleven sibling callable graphs and the exception graph survive. The corrected void interface is preserved. No game code was executed.

**Hive Boss match and unsupported-credit withdrawal, October 2.** Hive Boss `00480080` now reproduces its complete 416-byte section, 401-byte retail body and all eight references. A displacement value is shared by the terrain query and conditional accepted position. This lets the compiler retain coordinates across the call and construct the output separately, as retail does. A separate check independently compiled baseline/candidate, bound all references and compared the fully linked bytes; all 15 earlier exact rows and sibling graphs survive.

**Historical withdrawal of projectile initialization `004d8410` (subsequently recovered through position accessors above).** A review identified two unsupported `if (0) mPos.Magnitude()` statements added; a reproduction confirmed their effect and removed them. They manipulated inline decisions without a documented retail/source purpose and violate the no-padding rule. The honest reconstruction is now 1,536 section bytes against retail's 1,591-byte body. It remains in the denominator and needs further work. All 148 sibling callable/reference graphs, 102 other exact annotations and vtables are unchanged. The old source remains in Git history; no retail data or evidence was deleted.

The full score adds the 401-byte Hive Boss match and removes the unsupported 1,591-byte projectile credit: no net function gain, 1,190 fewer credited bytes. Every other earlier match and all vtable results survive, with zero relocation conflicts. This is a correction to the claimed baseline, not a smaller target. No target code was executed.

**Three complete rendering matches, October 2.**
Fresh stock builds reproduce these complete sections and every relocation:
- Mesh-part rendering `004b6350`: 2,144 section bytes, 2,134 body bytes and
  35 references. One colour helper owns the fallback, optional virtual query
  and collision override; zero-radius debug axes use direct stores. The query
  remains before the override. All 19 earlier exact rows and 21 sibling graphs
  survive. Two still-unmatched render callees were bound by independently exact
  owner/field routines and original argument/dispatch instructions; they gain
  no matching credit. Exception sections were linked and compared recursively.
- Static mesh-buffer construction `0054c0a0`: 2,176 section bytes, 2,162 body
  bytes and 40 references. Actual position/normal records, texture slot
  references, signed strip bounds and failure/release order recover the main
  body; separate strip/upload counters and vertex/index Lock outputs close
  the final stack gap. The passive stack-packer trace predicted the class
  conflicts. All 14 earlier exact rows and 22 sibling graphs survive.
- Multiplayer grid `0051d160`: 2,304 section bytes, 2,299 body bytes and
  128 references. The description helper owns its wrapped-line buffer, the
  page owns the measured text extent, and the link endpoint is materialized
  before its alpha guard. Cell angle and interpolation use their actual
  value lifetimes. All 10 earlier exact rows and 11 sibling graphs survive.

A separate check independently compiled each baseline and candidate, bound literals and reference targets, and compared the fully linked sections with pristine `74154bfa...`. No original or reconstructed game code was executed. The combined score keeps every previous symbol/source row and vtable result, with no relocation conflict.

**Infantry damage match and bounded source corrections, October 2.**
Infantry damage (`00489650`) now matches its entire 1,264-byte compiled section,
1,257-byte retail body and all 45 relocations. A mutable impact vector, the
existing motion setter, the ammunition forward-axis product and `Azimuth()`
recover retail's value lifetimes and normalization. A separate check independently
compiled baseline/candidate and bound every reference through exact independent
callers/callees, actual literal bytes and pinned identities. All 32 previous
exact annotations, 44 sibling callable graphs and eight vtables remain.

Four additional source corrections receive no match credit:
- Dive-bomber attack (`00445ad0`) uses horizontal separation for the second,
  20-unit continuation test. Its first, 15-unit test uses full separation.
  Original x87 stack recheck proves the distinct operands; all 13 exact
  controls, 16 sibling graphs and 35 reference meanings remain.
- Multiplayer preview (`0051e1b0`) uses RGB-vector times `0.6f` for its three
  lights. Nine prior immediate operands were one ULP low. Fresh compilation
  changes exactly those nine bytes; the retail PUSH operands and complete
  64-byte `CLight::Init` body bind them to diffuse RGB. All 19 exact controls,
  43 sibling graphs and 228 target references remain.
- Static mesh buffers (`0054c0a0`) use the vertex count at part `+0xa8` for
  both fixed per-piece index strides, not the triangle count at `+0xb0`.
  Allocation sizes, saved stack values and both stride consumers were re-read
  from the pristine instructions. All 14 exact controls, 22 sibling graphs
  and 40 target references remain.
- Mesh contact projection (`004acf30`) adds the X/Y dot products before Z.
  The prior grouping added Z/X before Y. Only 17 instruction bytes change;
  the remainder of the section, 32 references, 43 sibling graphs and all 32
  exact controls remain. A finite cancellation witness distinguishes the
  groupings at x87 precision widths 24, 53 and 64. This proves an isolated
  arithmetic distinction, not full-call reachability or universal equivalence.

These four whole functions remain unmatched. No original or reconstructed game code was executed. Each cites pristine `74154bfa...`.

**Debriefing exact match and two source corrections, October 2.**
Debriefing rendering (`00456dd0`) matches its complete 3,872-byte section,
3,870-byte retail body and all 262 relocations. Each bracket transition keeps
its normalized progress value through alpha/rotation; the grade text is read
before the font call; the real landing scale is initialized before the flash
default. Those source boundaries recover the final binary32 store/reload and
all value lifetimes. A separate check freshly compiled baseline/candidate and linked
all 262 references using independent exact callers/callees, full literal
contents and the pinned CRT identity. All 13 old exact rows and 15 sibling
graphs remain; there is one new exact function.

Two additional corrections receive **zero** matching credit:
- Dropship ground alignment (`00448930`) computes `side ^ normal` at both
  low-altitude sites. The old `normal ^ side` reversed the signed component
  numerators. A separate check decoded the original x87 expression stack and accounted
  for every argument push at `00448f21..00448f67` and `00449352..00449398`.
  All six exact controls, six other callable graphs and 76 target reference
  meanings survive. The full candidate remains 2,912 bytes versus 3,087 retail
  body bytes; no gameplay or universal floating-point equivalence is claimed.
- Height-field mixing (`0047eff0`) starts a run only on a positive difference, but subsequently blends zero differences until a negative difference or row exhaustion. Retail's initial `JLE` (`0047f340`) and continuing `JL` (`0047f350`) differ intentionally. The previous single loop skipped every zero. A static equal-texel witness after a positive run gives `0x10070707` from input `0x10080808`, whereas the old source left it unchanged. All 13 exact controls and 14 sibling graphs remain. The full candidate is still unmatched: 1,792 versus 1,876 retail body bytes.

**E3 page match and shadow receiver correction, October 2.**
The E3 level-select renderer (`00459ee0`) now reproduces its complete 2,368-byte
section (2,365 body bytes) and all 137 relocations. Shared ring angle/scale values
inside the mutually exclusive cases, named row/column link values, and reuse of
the actual decorative fade retain retail's value lifetimes. A separate check freshly
compiled baseline and candidate, independently bound the calls/data/literals,
and linked the whole section to the pristine specimen. All 14 sibling callable
graphs and the vtable survive; this is one new exact function.

Separately, static-shadow construction (`004ec2f0`) now retains the pointer returned by `GetCollisionPart` for both triangle searches and packing access. Retail saves EAX at `004ec447`, reloads it at `004edd47` for the first search, uses its polybucket at `004edd6d`, and reloads the same stack home for the next search at `004edeff`. The exact getter (`004b0cd0`) returns a separate `+0x124` part for type 6, so discarding that result was a source defect. The original render part still owns transforms, bounds and the temporary bucket. All 29 previous exact rows and 33 other callable graphs survive. The 7,488-byte candidate still differs from the 7,620-byte retail body: it receives **zero** new matching credit.

- Named mesh movement (`004bbda0`): 688 section bytes, 683 body bytes, 14
  references. One integer-angle rotation core is available inline to its actual
  consumers through `maths_integer.h`, with the existing external entry retained
  in `Unit.cpp`. The constant yaw is four units of a 4096-unit turn. A global
  inline-body draft had regressed five consumers; the selective definition
  preserves all five and the whole-project prior matches. The helper/header
  names are reconstructed. General-angle `004f8140` remains unmatched (640
  compiled bytes against 857 retail body bytes); neither general-angle x87
  equivalence nor historical source spelling is claimed.
- Overlay light requests (`004903a0`): 560 section bytes, 529 body bytes, 19
  references. The five cases derive strength fade from the assigned lifetime
  and RGB steps from zero minus each assigned diffuse channel. This recovers
  the retail arithmetic and store order instead of substituting fixed rates.
- Game interface rendering (`00472f10`): 4,528 section bytes, 4,527 body bytes,
  238 references. Separate integer joypad-origin coordinates and page-local
  text extents recover retail's actual stack lifetimes; viewport and font
  values retain their observed evaluation boundaries.
- Mesh normal calculation (`004b1eb0`): 1,568 section bytes, 1,559 body bytes,
  13 references. Accumulation copies the returned vectors, including their
  fourth dword, and reads positions/vertices through the owning arrays. The
  previous cached lookup and `+=` reconstruction lost those operations and
  the corresponding inline boundaries.

All four retain their complete section padding/tables and every relocation;
no comparison tolerance, compiler flag, extra operation or denominator changed.
The fresh objects preserve 11, 13, 23 and 59 sibling callable graphs,
respectively. An independent read-only review checked the rotation definition's
C++ ownership and arithmetic organization before integration.

A separate source correction changes the sprite fade divisor from 225 to 226
(`004c6b28`: multiplier `0x487ede05`, signed shift and sign correction).
A separate check independently re-read the pristine instructions and proved the signed
quotient identity, checked boundaries and all 256 illustrative byte-alpha inputs.
All 29 exact controls, 35 sibling graphs and 170 ordered reference bindings survive.
The full sprite renderer remains unmatched and receives no score credit; the
static calculation does not establish a runtime alpha range.

**Three whole-function matches, October 2.**
A separate check reproduced and independently bound every reference in:
- Ground vehicle movement (`0047d1c0`): 496 section bytes, 483 body bytes and
  eight references. The actual BOOL tilt predicate retains its complete result;
  late construction/assignment of the used side vector restores the retail
  constructor boundary. Eleven other callable graphs remain unchanged.
- Weapon launch positioning (`0040c990`): 1,888 bytes and 56 references, plus
  the complete 77-byte exception code/table and seven auxiliary references.
  `CWeapon::Gravity` names its existing mode pointer before loading the round.
  The original Stuart caller remains unchanged. This fixes the allocation of an
  existing load; no extra operation, forced register or caller workaround is used.
  The earlier `GetCockpit()` partial is unnecessary. All 253 sibling graphs survive.
- Submarine guidance (`004ef590`): 1,072 section bytes, 1,042 body bytes and
  28 references. The forward vector precedes the yaw matrix, and those transform
  temporaries end before movement status is published. Eleven other graphs survive.

A separate trail correction (`004c36b0`) routes sine through the second normalized basis and cosine through the first. The whole trail function remains unmatched and receives no score credit.

**Engine effects match; three reconstructed source errors corrected, October 1.**
`CBattleEngine::HandleEngines` (`0040ebf0`) now reproduces all 704 section bytes
(703-byte body plus NOP) and 19 independently bound references. The inactive effect
cleanup traversal has its own source helper, borrowing the caller's existing
iterator. It adds no operation, iterator copy or emitted callable. The unchanged
position wrappers now receive enough inline budget to expand both `CFoR::SetPos`
bodies while retaining the two retail `SetCurrentPos` calls. A separate check freshly
compiled the correction, bound each reference using unchanged exact baseline
witnesses, and preserved 253 other callable graphs and 11 vtables. A compiler
helper boundary is reconstructed; its historical spelling is not established.

Three independent corrections remain explicitly outside the match count:
- Wingmen preview (`00522190`) composes `pitch * yaw`, replacing the reversed
  multiplication. Retail's constructed matrix rows and argument stack at
  `005228c6..00522945` multiply pitch rows by yaw columns; those operations are
  not interchangeable. The renderer remains unmatched; 50 sibling graphs and
  24 exact annotations survive.
- Message-box YES/NO layout (`0044d6f0`) converts the text-height product before
  adding the row height. Three complete relocated arithmetic spans now reproduce
  retail FILD/FIADD rather than an integer ADD before conversion. The whole
  renderer remains unmatched; all 61 target reference identities and ten exact
  sibling results survive.
- Palletizer (`0054e9d0`) allocation metadata now pushes retail source line 238,
  replacing 237. Only the immediate byte at `0054e9db` changes; all 26 target
  references and 11 sibling graphs remain unchanged. The whole function is open.

**Thunderhead guidance and landscape tile updates match, October 1.**
`CThunderheadGuide::Update` (`004f4e40`) reproduces its complete 896-byte section
and all 24 references; `CLandscapeTexture::UpdateTile` (`0048ea80`) reproduces
896 bytes and 32 references. Their counted retail bodies add 1,768 bytes.
The guidance correction retains the velocity value from its initial publication
through the later rotated, scaled forward-vector assignment; the virtual speed
value remains unscaled. This restores the retail calls and temporary lifetime.
The texture update prepares the high-resolution target before testing its lock
result; managed and scratch textures own their lock calls, each resolution arm
owns its upload guard, and tile inputs precede the dirty store.

A separate check freshly compiled both corrections and checked complete relocated sections
against pristine `74154bfa...`, preserving respectively 11 and 24 sibling callable
graphs. Thirty texture references also have exact independent section/caller
witnesses. Its two unchanged blit calls use the established `0047eff0` entry and
thiscall/ret-0x28 ABI; that callee remains unmatched. No claim of a matched callee
or runtime acceptance follows from these caller checks.

The same integration corrects `CMCMech::Init` (`00498c40`) to subtract Footbase
position from Leg position: retail output arguments bind those values to
`esp+0x114` and `esp+0x104`, then `00499558` subtracts the former from the latter.
Only four displacement bytes change; its 50 sibling graphs, 43 prior exact
annotations and 122 target references are preserved. This function remains
unmatched and receives no matching credit.

**Texture remapping, pod aim and segmented-unit initialization match, October 1.**
Three source corrections reproduce complete compiled sections and every relocation:
`CMesh::OptimiseTextures` (`004a5670`, 704 bytes / 3 references), `CPod::Aim`
(`004d3730`, 352 / 7), and `CDestructableSegmentsController::Init`
(`00444660`, 736 / 43). Their counted retail bodies add 1,775 bytes.

The texture walk uses ordinary while/early-continue iteration exits, each advancing once. No additional operation executes. Pod uses the real displacement's Azimuth and MagnitudeXY and rotates the scaled forward axis, restoring its math scheduling and existing out-of-line rotation call. The segment controller consumes part-count and two emitter-number values at their actual publication, lookup and warning boundaries, without caching its loop bound. No compiler setting, artificial side effect or comparison rule changes.

A separate check freshly rebuilt each baseline and candidate, linked every section against pristine `74154bfa...`, and preserved respectively 42, 13 and 48 other callable graphs. These are compiler/static results; no target game code was executed.

**Ground-attack flight matches, October 1.** `CGroundAttackGuide::Unknown3`
(`0047c200`) now reproduces the complete 1,088-byte section and all 41 relocation
meanings, including its 14 padding bytes. Named flight-velocity components keep
the negated course store before preparation of the next velocity query. A height
reference and a complete bank-sign consumer preserve retail's Z/Y product pair
followed by X, including operand load order. This applies the same measured
scheduler-region cause that closed the dive-bomber guide, using ordinary source
values without compiler-setting changes or artificial side effects.

A separate check freshly rebuilt baseline/candidate and compared both complete linked sections, retaining all seven previous exact sibling graphs. The object now has 8/8 exact callable functions. This is compiled/static evidence, not a claim of player-visible runtime acceptance.

**Ground-unit movement matches, October 1.** `CGroundUnit::Move` (`0047c970`) now reproduces its entire 1,296-byte section and all 25 relocation operands. Existing state accessors, a separate step-loop counter, in-place cached-velocity scaling before X/Y publication, and phase-first bob addition restore the retail call and value lifetimes. No shared particle header change was needed. A separate check freshly rebuilt baseline/candidate and retained all 17 other callable/reference graphs, 13 earlier exact annotations and both vtables.

Two separately checked corrections remain partial and receive no match credit. Tentacle `UpdateBone` (`0049d280`) uses a nonzero roll, not pitch: the trig values and nine stores at `0049d4d0..0049d5db` establish the matrix axis, and multiplication at `0049d5e2` introduces no transpose. All 38 other callable graphs, 33 exact annotations and the vtable survive the one-line correction. Occupancy-cell lookup now borrows the position vector; a separate by-value destination predicate keeps its copy conditional on an existing path. These reconstruct all 272 bytes of `0047d8c0..0047d9d0`, including the path call, while all 137 SquadNormal graphs and 15 other GroundVehicleGuide graphs remain unchanged. No outlined lookup ABI was recovered; the full guide is still unmatched.

**Both buffer-resize functions match, October 1.** `CVBufTexture::ResizeIB`
(`005007f0`) and `ResizeVB` (`005005e0`) now reproduce their complete 464/528-byte
sections and all 20/24 relocation meanings. Both reuse the incoming size parameter
for the rounded capacity and write capacity once after the outer branches. The
index-buffer path also removes a redundant null guard around `delete`; the
zero-capacity cleanup and vertex-buffer delete guards remain intact. This shared
source-lifetime correction closes both earlier register/stack/control misses.
No new pragma, compiler setting or synthetic side effect was introduced.

A separate check freshly compiled the baseline and each accepted change, preserving all 35 other callable/reference graphs and all 34 previous exact annotations in the object; its focused check is now 36/36. Entire linked sections, including padding, match the pinned pristine specimen. These are static compiler/byte comparisons; no device or retail runtime was run.

**Menu help classification and source corrections, October 1.** `CFEPCommon::RenderHelpText` (`00453140`) now matches all 560 section bytes and 38 relocation meanings, including its jump table. The selected switch cases own their back-button classification; the existing range test remains on the default/fallthrough path.

Three separately proved source corrections receive no match credit. `CDamageTexture::Load` (`00440c70`) no longer invents a TRUE result: retail returns the destructor's residual EAX, and its direct caller discards it. The reconstructed void interface does not prove original source spelling. `CreateMipmaps` (`00559410`) keeps width after device-limit reduction; retail's store at `00559485` normalizes to frame slot +30, subsequently restored at `00559b40/4d`. `UpdateFallingTree` (`004f6b80`) now uses the six off-diagonal sine signs stored at `004f6ed4/e6/ee` and `004f6f0c/18/20`; its matrix multiplication and copy introduce no transpose. All three remain unmatched, and no runtime acceptance is claimed.

- **Spawner clearance and wave start match, October 1.** `IsSpawnPositionClear` (`004e44d0`) matches its whole 256-byte section, 249-byte body and nine relocations through a parameterized behavior query. `DoSpawn` (`004e3c60`) matches its 816-byte section, 811-byte body and 21 relocations through returned offset ownership and a by-name squad factory. These are functional source interfaces, with no padding or fabricated effects; the original helper names are unknown. A separate check freshly reproduced both gains and all 36 unchanged sibling graphs. The newly emitted FVector constructor was already globally exact and adds no unique credit. The final complete score preserves all 5,296 symbol/source rows from the 5,256-function baseline, adds only these two functions and light processing, preserves all 892 vtable results and has no relocation conflicts. The separate spawn-wave function `004e3f90` remains unmatched.

- **Cache-texel loop guards corrected, October 1.** `00541f50` uses nonzero countdown guards. Fresh stock compilation changes exactly five JLE opcodes to JE, matching the independently located retail guards. All other target bytes and twelve sibling graphs, ten exact controls and the vtable survive. The full function remains unmatched and earns no additional credit.

- **Light-request processing matches, October 1.** `CLightManager::Process` (`004905f0`) matches its whole 400-byte section, 399-byte body and all 15 relocations. Iterating the embedded slots with an explicit pointer, advancing it before the counter, and advancing the destination slot before the request reproduce retail's traversal lifetimes. A separate check freshly compiled both versions: all 13 sibling graphs and eleven prior exact controls survive. The full integrated score adds only this address, preserving all 5,296 prior symbol/source rows and all 892 vtable results, with no reference conflicts. `UseReq` remains unmatched; no game or graphics-device run is claimed.

- **Segment-controller allocation filename corrected, October 1.** Opening `monitor.h` before the other controller headers preserves retail's lowercase allocation filename at `0062551c`, including Init's operand at `004447fd` and its unwind operand at `005d219c`. All 49 callable instruction sections, 32 exact controls and four vtables survive; only one literal byte changes. Init still has 36 instruction-byte differences and earns no matching credit. Its earlier six-byte draft also failed this literal comparison, contrary to that draft's old all-relocations claim.

- **Landscape-shadow renderer matches, October 1.** `RenderLandscapeShadows` (`00553960`) matches its complete 2,064-byte section, 2,059-byte body and all 197 relocations. This brings the fourth device-pointer push into the preceding scheduling region and recovers retail's instruction order. No compiler flags, padding or fabricated side effects are involved. The reference recheck checks 109 independently witnessed placements, 73 references to already exact callees, eleven literal payloads and four proven library references. Full byte identity settles the compiled renderer under the checker contract, not its original spelling or live graphics output.

- **Dropship landing-turn threshold corrected, October 1.** Move (`00447120`) compares the wrapped heading difference with double-promoted `0.1f`, not double `0.1`. The constant at `005d8c38` is `0.10000000149011612`. The one-token correction preserves all 45 callable instruction sections; only the target's threshold reference at section+51a changes. All 44 other callable graphs, 36 exact controls and six vtables survive. A separate check freshly compiled both versions and executed the retail/candidate 111-byte heading fragments (`004475dc`–`0044764b`) with separately bound constants. Across 87 authored finite cases using PC24/53/64 nearest rounding, the old form makes twelve different decisions (six each at PC53/64); the correction makes none. Inverting the threshold branch flips all 87 decisions. Register, stack and x87 guards pass. These are fragment results, not full Move or observed game states; the later speed-sum association and stack lifetime still differ, so no exact-function credit is added. The complete integrated score preserves all 5,255 exact addresses, 5,295 symbol/source rows and 892 vtable result rows, with no conflicts.

- **Mesh detail and render-interface identities corrected, October 1.** Render (`004dcba0`) divides surface detail by `zoom * 10`, not `distance * 10`. Retail stores camera zoom at frame `E+8` (`004dcc2b`), distance at `E+c`, then pushes EDI before the detail load `[esp+c]` (`004dcdcc`). The previous "swapped stack slots" explanation concealed a real input discrepancy. Its snow pass dispatches slot24/+60 twice, not slot27/+6c. The console strings `cg_snowlayerenable` and its description independently identify the guard; the result feeds `SNOW_DENSITY` and a flags10 render. Imposter callers `00488aad`/`0055a66a` use slot27 to index 24-byte frame records. CTree's slot27 (`004f6540`) returns its address-derived quartet and resets its orientation-selection flag. The source identities were transposed: slot24 is now `GetSnowDensity`, slot27 `GetRenderImposterNo`, with declarations, overrides and frame-index callers updated coherently. This names the measured roles; Stuart's original base-interface header is absent, and historical spelling remains inference. A separate check builds each caller correction independently: 46 other graphs and all 35 reference meanings survive. The identity-only rename preserves all 556 callable graphs across eight objects and 214 exact results after the explicit symbol substitution. The full renderer remains unmatched; the zoom correction removes retail's otherwise-unread square-root FST, whose exception/status effects remain open. No live receiver, draw or camera acceptance is claimed.

- **Map fallback logger and argument corrected, October 1.** Trace `00490a40` calls `LOG.AddMessage` (`00441740`, receiver `0066f580`), not the empty `DebugTrace` (`0040c640`). The first floating argument reloads the saved line length from frame+28 after sixteen argument-stack bytes; it is not position.Y. A separate check freshly builds the old/corrected caller, exact logger, initializer and existing logger caller; the 90-byte format at `0062d964` and all 22 explicitly paired operand references agree. The corrected source preserves seventeen other exact callables and both vtables. The whole 976-byte section remains unmatched, including step rounding, the nested vector constructor and recursive return handling. No logging or game I/O ran. The complete main build retains 5,255 exact addresses, all 5,295 symbol/source rows after the one CTree symbol rename, and the same 892 vtable result rows. No new match is claimed. Only Map and CRTMesh's unmatched status rows change; all other whole-corpus status rows agree with the previous build.

- **Buffered resource reads match, October 1.** `CDXMemBuffer::Read` (`00548570`) matches its complete 688-byte section, 686-byte body and sixteen relocations. Removing the literal `if (0)` DMA/direct-read branch inherited from Stuart's `5352a81c` source changes VC6's allocation/scheduling while retaining the actual buffered copy/refill/EOF path. A separate check freshly builds both versions and binds ten references through prior exact controls, five through PE imports and one through the exact `.aya` literal. All 21 other callable graphs remain unchanged; the only additional section change is Read's FPO record. `InitFromFile` remains at its twenty stack-slot differences. This does not establish runtime Windows file I/O or save compatibility.

- **Render descriptors and texture initialization match, October 1.** `InitRenderData` (`00515fb0`) matches all 1,184 section bytes, its 1,181-byte body and 89 relocations. Entries 0, 8 and 22 now finish their own metadata before copying their default names. A separate check independently binds all 68 global references through previously exact bodies and checks all 21 literals, preserving 42 other callables and three exact vtables. `CTexture::InitDeviceObjects` (`00557a90`) matches its complete 2,896-byte section, 2,489-byte body and 193 relocations. Scoped animated/static status buffers, an existing device accessor, a named mip filter and the success-query scope reproduce the retail lifetimes. All 44 other callable graphs survive. A separate check checks internal branches/tables, literals, import slots, annotated callees and prior exact references; the two newly encountered library identities also match the pinned LIBCMT/OLDNAMES and D3DX bodies. Those library dependency graphs are not re-audited here. CTexture still has no unique retail vtable in the current mapping. These are compiled matches, not device execution, resource acceptance or recovered original source spelling.

- **Compressed texture fallbacks corrected, October 1.** Both fallback tables in `LoadFrame` (`00557300`) map DXT1 to R5G6B5 and DXT2 to A4R4G4B4; DXT4 stays DXT4. The former `To16Bit` omitted the first two compressed cases. A separate check reads the actual jump tables at `005579a0`/`005579cc` and all six branch values, then checks the fresh compiled switches. All 41 exact controls, including initialization above, and 44 other callable graphs survive. LoadFrame remains unmatched; no converted texture or device behavior is claimed.

- **Compass cosine materialization corrected, October 1.** The retail weapon panel stores cosine to float32 at `00485c5f` and reloads it before multiplying by -45. A source-local direction value restores this boundary; the old scalar expression retained the extended result. A separate check freshly compiled both forms and executed the original and reconstructed arithmetic fragments for 8,118 finite-yaw cases at authored PC24/53/64 nearest modes. The former 1,749 displacement differences become zero; flags also agree. Replacing FCOS with FSIN rejects 8,115 cases. Stack, register, x87 control/stack and exception guards pass. All 37 other callable graphs and 26 exact controls survive; no callable is added. The complete renderer still has 53 differing positions and gets no match credit. Device calls, preceding orientation retrieval, live control words and visible behavior are outside this experiment.

- **Infantry orientation fallback corrected, October 1.** Damage (`00489650`) used the translation unit's `ID_FMATRIX`; retail selects `CThing::sIdMatrix` at `0083d9c0`. The complete initializer `004f3310` independently binds that global, while the exact Infantry initializer `00488ae0` binds its distinct local identity matrix to `0067a688`. The existing `CThing::GetOrientation()` API supplies the correct fallback. A separate check rebuilt the before/after objects: the 1,264-byte Damage section is unchanged, and only relocation `+0x288` changes identity. All 44 other Infantry callables and 110 exact results across Infantry/Thing survive. Their initialized matrix values agree; this is an ownership correction, not an observed gameplay difference or new exact function.

- **Dive-bomber bank sign corrected, October 1.** Binding destination height by const reference changes six component operands in `00446840`, restoring the bank dot product's retail `(Z+Y)+X` order instead of `(Y+X)+Z`. A separate check compiled both versions and replayed the original and candidate `[00446b64,00446b93)` fragments in native i386 code. All 336 authored finite cases agree after correction; before it, 37 PC24, 21 PC53 and nine PC64 cases choose the opposite bank sign. A reversed-branch control changes every sign while preserving the surviving heading. Register/stack guards and x87 control, TOP, tag and exception checks pass. Preceding callbacks, angle clamping, live input reachability and live control-word configuration remain outside the experiment. All nineteen other callable graphs, 41 guide reference identities and thirteen exact controls survive. The full guide remains unmatched.

- **Particle update and sphere-trigger reset match, October 1.** `ProcessParticle` (`004cb920`) matches all 272 section bytes (266-byte body) and eight relocations. A frame-step responsibility contains separate position and owner-registration steps, preserving the original displacement constructor call. Its matched instructions close the prior admitted 16/48-case rounding gap; no additional runtime sampling is claimed. All 31 other callable sections/references survive, including allocation. Sphere-trigger `Hit` (`004e5700`) now matches all 320 bytes (315-byte body) and 22 relocations; a containment-frame helper keeps reset and clock update together and leaves the nested iterator callable. A separate check also verified its 62-byte EH section (seven references) and 56-byte unwind data (four references), preserving all thirteen other sphere callables and all fifteen Radar callables. Newly emitted shared helpers earn no extra unique credit.

- **Unit provider selection matches, October 1.** `004fb840` now matches all 1,104 section bytes, its 1,099-byte body and 27 relocations. Local spawner-field accessors and a target-owned selection block recover the iterator's actual stack lifetime after the active-weapon guard. The selection phases and scoring stay in retail order. The added iterator implementation was already globally exact. The remaining Unit/UnitAI misses stay open. These matches establish static compiled identity, not gameplay or original helper spelling.

- **Mech debris Z arithmetic corrected, October 1.** Scaling the three components through the existing vector setter keeps Z on x87 until its doubled, biased value is stored, as at `004a000c`–`004a0059`. The old vector-expression spelling rounded that intermediate. Inserting only the intermediate float materialization reproduces the former results. At PC53 nearest and all three integer components -99, old Z is `bdd0a3d6`, versus retail/corrected `bdd0a3d7`. The full function remains unmatched (768 section bytes versus 752 body bytes); PRNG calls, full game state and live control-word reachability were not exercised. All nineteen exact controls and twenty other callable graphs survive.

- **Debriefing foreground scale and palette ownership corrected, October 1.** Retail's two debriefing foreground bracket calls read raw scale from the original stack slot after the shadow call's eleven arguments; only the shadow uses the 1.05 multiplier. In `Palletize`, the darkening loop at `0054ed80`–`0054ee33` reads and writes the receiver's internal palette, then exports it at `0054eeb5`; the former draft darkened the output buffer that the later copy overwrites. Fresh builds reproduce both operand corrections and preserve all other callable graphs (25 across the modal/debrief pair and eleven palette callables) and their twenty/nine exact controls. Neither complete renderer/converter matches, and no visible frame or conversion ran.

- **Hive-boss cylinder transforms match, October 1.** Copy-initializing the twelve branch-local Euler matrices reproduces `004976d0`: all 2,480 section bytes, its 2,469-byte body and all 100 relocations. The six branch and multiplication orders stay intact. Default construction plus `MakeRotationF` fails, while a named blend changes no code. This establishes the compiled transform, not live animation or original source spelling.

- **Word wrapping and message-log input match, October 1.** `CMessage::WordWrap` (`004b6f70`) now reproduces all 496 section bytes, its 489-byte body and four relocations. The reveal-count lifetime, positive-length scope, punctuation suppression and line-transition order matter. `CMessageLog::ReceiveButtonAction` (`004b9ec0`) reproduces all 416 section bytes, its 409-byte body and thirteen relocations: the shared distance helper checks the selected/top equality before initializing its own cursor, after the caller updates selection. Passing a cursor captured before the selection update was the former mismatch. A separate check freshly rebuilt both; all 44 and 22 other callable sections/references respectively survive, along with five and two vtables. The log panel remains unmatched. No UI was run.

- **Other-particle render pass matches, October 1.** `RenderOther` (`0054f7e0`) matches its entire 656-byte section/body and all 51 relocations. Source-local state, camera-basis, descriptor-dispatch and restoration responsibilities keep the two matrix products, cross product and both normalizations out of line. Directly initializing the back vector also removes its temporary copy. These boundaries are reconstructed; the names are not recovered source text. All eleven other retained callable sections/references are unchanged; the unused vector constructor disappears from this object. Its address remains exact elsewhere, and the two math helpers add no new unique credit. Omitting descriptor grouping or restoring default-then-assignment construction fails. No device or particle scene was executed.

- **Shadow projection ownership corrected, October 1.** At `005532c8`, retail copies sixteen dwords from absolute `009c7c14` to `009c6994`. Exact initializer `00551ef0` binds SHADOWS to `009c7550`, and exact `TestDraw` binds RENDERINFO to `009c65c0`: the source is the global `SHADOWS.mProjection` (+`6c4`), not the method receiver's matrix. A separate check reproduced the new reference while preserving all 107 previous reference identities/addends, 44 exact controls, 62 other callable sections and three vtables across the two affected shadow/patch objects. `RenderTextures` stays unmatched (4,400 section bytes, 108 relocations), so this adds no match credit or runtime claim.

- **Buggy and tentacle transforms match, October 1.** A source-local root-basis setter and `origin.Set(0,0,0)` reproduce both `GetPartTransform` methods: buggy `004944d0` and tentacle `0049e660`, each with a 1,136-byte section and 33 relocations. Their retail bodies are 1,127 and 1,131 bytes respectively. The first identity row expands while the next two constructors remain calls; initializing the origin through its setter also retains the later interpolated position's constructor expansion. The basis helper alone fails that last boundary (budget 45 versus size 47); the paired form reaches 47 and matches. These helper names are reconstructed. A separate check freshly compiled both objects and read back all 66 relocations. All 74 other callable sections and recursive references survive, including the exact tentacle spline. Both Init functions remain open; neither motion nor rendering ran.

- **Declaration shader constants match, October 1.** Reusing the existing fragment-token accessor for constant-register lookup restores the last light constructor's out-of-line vector setter at `0050342a`. Its three observed inline budgets are 125, 81 and 37; only the last 44-unit setter stays out of line. The snow-wind calculation separately needs one promoted Y square followed by float X/Z accumulation and reciprocal scaling. All 34 other callable sections and references remain unchanged. Accessor-only, ordinary float-Y and matrix-conversion alternatives fail; a named double Y also reproduces the accepted section. This closes the former shader-constant near miss, without proving original source spelling or GPU behavior.

- **Menu language-pulse arithmetic corrected, October 1.** The pulse in `CFEPMain::Render` (`00462d40`, fragment `0046319e`–`004631d3`) multiplies the counter by two separate float coefficients before `fsin`; the former `sin` expression folded them together. The reconstructed `sinf` expression preserves the observed multiplication. The fresh object and native fragments agree with retail across 120,012 authored counter/control-word cases, where the old source differs in 44. At counter 3235, CW `037f`, retail/corrected color is `ffcbcbcb`, versus old `ffcacaca`. All 15 exact controls and 16 other callable sections/references survive. This is not a whole-function match or a visible-menu result: live counter/control-word reachability, transitions and rendering remain untested.

- **Unit-definition destruction matches, October 1.** Grouping the existing effect-name releases and external-cursor pair cleanup into separate inline responsibilities reproduces `~CUnitData` (`005110f0`): all 688 section bytes, including its 675-byte body, and 60 relocations. The six set-iterator calls remain out of line; the two pair-iterator calls at `0051131d` and `0051133f` now both reach `00409760`, with the iterator on the stack. Effect-name release order remains `0,1,2,3,4,6,7,8,9,10,11,12,5`. Helper names are reconstructed boundaries, not recovered original names. A separate check reproduced the actual shared-header edit, preserved all 347 other callable sections/references in this object, and retained all prior exact symbols and vtables in the six-file consumer check. The newly emitted `GenericListIterator::First` was already exact elsewhere and adds no unique-function credit.

- **Fourth gamut plane uses the shifted first apex, October 1.** In ComputePlanes (`004742a0`), retail stores the first plane's shifted apex Z at `00474b77`, then reuses it in two fourth-plane numerator terms (`00474d74`, `00474d9f`). The other terms still use the fourth apex (`00474d83`, `00474db1`). The former uniform macro incorrectly used the fourth apex for all four terms. Exposing that first-Z input restores the dataflow and the 10,112-byte section size; the body remains unmatched, with 527 differing positions. A separate check independently rebuilt the correction, read all 196 float relocations from the pristine executable and preserved the other 16 callable sections and their references. Reproduced full-body Unicorn runs use 18 prepared finite inputs, including first/fourth zero determinants, at control word `027f`, without calls or stubs. Corrected slopes and spans agree in all 18; the old draft agrees in 2 and 8 respectively. One witness changes 24 output-span bytes. These are bounded emulation results, not native-game observations or equivalence proof; normal summation order and stack/register differences remain.

- **Render-state reset matches, October 1.** Existing three-component setters for both billboard axes and a named remaining-array copy size reproduce `CRenderInfo::Reset` (`005508e0`): all 560 section bytes, including 547 body bytes and padding, with no relocations. A separate check compared the entire section directly with pristine bytes and preserved the other 45 callable sections and references across renderinfo/DXPatchManager. The matrix-array copy is the retail forward overlapping copy; its emitted behavior is not a portable `memcpy` guarantee.

- **Particle allocation matches, October 1.** Shared hard-limit and pool-rejection exits, with the observed reclaim type switch, reproduce `AllocateParticle` (`004cb5c0`) across its full 864-byte section, including switch data/padding, and all 40 relocations. The fresh build preserves all 31 other callable sections and their targets. ProcessParticle was still unmatched at this checkpoint; its later complete match is recorded above. No allocator or live particle system ran. The earlier native displacement comparison identified a ProcessParticle (`004cb920`) defect: 16 of 48 prepared cases differ because the draft retains an unrounded Z product. At CW `037f`, position `(-1,-1,-1)`, velocity bits `3f800001` and time bits `3f7fffff`, retail produces three zero coordinates while the draft produces Z bits `337ffffe`. A separate check reproduced the admitted arithmetic and original constructor only; life, callbacks, allocation and real frame inputs are excluded. The subsequent complete match restores the original constructor boundary rather than adding an arbitrary rounding operation.

- **Render, texture and interface boundaries match, October 1.** The fresh stock builds reproduce five complete sections, with every relocation: main Render (`0053e2e0`, 2,528 bytes, 182 relocations), texture Activate (`005588f0`, 1,536/89), text measurement (`00540680`, 448/6), reconnect Render (`00527990`, 704/38), and console MenuSelect (`0042bb30`, 144/0). Main Render needs both a copied float fog return and the direct particle creation entry; either alone fails. Activate preserves matrix lifetimes and return paths, then copies the near-plane getter result through a float-return helper: the product and subtraction both resolve far/near to `0089cdd4`/`0089cdd0`, closing the prior relocation conflict. GetTextExtent uses the canonical texture lookup. The reconnect prompt groups its measured width/height in `SIZE`; console selection factors its admitted path and keeps resets within each destination branch. These reconstruct value lifetimes and inlining boundaries, not original source spelling. Other callable sections and references remain unchanged in each object. No window, renderer or graphics device ran.

- **Trail renderer name gate corrected, October 1.** The final name comparison in `004c8520` calls the case-insensitive CRT entry `00568390` at `004c8ca7`, after the separate case-sensitive `mName[5] == 'T'` filter. The reconstructed `strcmp` was wrong. A separate check reproduced the 32-byte corrected gate and all three references, and 16,407 bounded native ASCII cases using only the locale-zero comparator and a count-only RenderAll stub: 8,191 old differences become zero. For example, `blue Trail large` passes; a lowercase quick-filter `t` does not. All 35 other callable sections and 29 exact controls survive. The full trail remains unmatched; non-ASCII, nonzero locale and real rendering are untested.

- **Display enumeration and render helpers match, October 1.** Returning the complete saved-mode key makes `BuildDeviceList` (`00529350`) match all 5,344 section bytes and 233 relocations. Existing canonical buffer-acquisition/format entries close `RenderArrow` (`0053df40`, 736 bytes, 19 relocations) and `DrawDebugCuboid` (`0053d760`, 2,016 bytes, 56 relocations). Extra reconstructed forwarding boundaries had changed VC6 expansion and value lifetimes; replacing every wrapper was ineffective, so these are local corrections. `InitDeviceObjects` (`0054d210`) also matches its 480-byte section and 25 relocations after retaining its result across both return paths. No device ran.

- **Trail basis normalization and cross product corrected, October 1.** In-place division in `004c36b0` preserves the stored components and live x87 magnitude at both normalization sites. A separate check reproduced 1,636 old differences becoming zero on 3,594 authored cases. Expansion to 14,412 cases across all four rounding modes leaves twelve inherited signed-zero differences, versus 7,490 before the correction, with no new disagreements. For CW `037f`, step `(-0,1,+0)` gave side.Y `-0` where retail gives `+0`. A subsequent source correction restores the actual `step` cross `(0,0,-1)` operation, including retail's signed-zero subtractions. A separate check reproduced 19,296 native cases covering threshold neighbors, signed zeros, finite/exceptional inputs and all twelve precision/rounding combinations: the prior 108 discrepancies become zero, while the divide-to-multiply negative control differs in 14,509 cases. All 99 other callable sections, 80 exact controls and both vtables survive. XYZ bits, exception flags, x87 stack/control and stack canaries are observed; opaque vector padding is not. The complete function remains unmatched. Full step derivation, allocation, live control words and trail rendering remain open.

- **BE configuration input gate and light colors corrected, October 1.** Retail `004505b0` calls the down-arrow rectangle handler only inside the counter/flash predicate; the up handler is unconditional. A separate check reproduced 256 isolated gate cases: the prior draft makes 44 extra calls, while the corrected call traces and five arguments agree. Reconstructed vector color scaling also restores all nine retail RGB argument bit patterns, one ULP above the former decimal literals. Full Render remains unmatched; the no-op callback test does not establish mouse/device behavior.

- **Texture projection constants and mipmap width corrected, October 1.** The projection scales at `005e59d0` and `005e59cc` are float bits `3e9c18fa` and `bee38e39`. Adequate decimal precision corrects eight constant references without changing Activate's instructions. Source mipmap width uses arithmetic shifts at `0055994a` and `00559b1c`; changing its local to signed changes exactly two compiled instruction bytes. Mipmap construction remains unmatched. The earlier frozen Activate draft had zero non-relocation differences but two reversed ENGINE operands; the complete match recorded above supersedes that draft.

- **Unit turning and mech initialization match, October 1.** Binding the current and target pitch fields by reference retains the retail lifetimes around Unit's virtual movement-multiplier query. `Unknown77` (`004fa4b0`, Euler smoothing and matrix construction) now matches all 848 section bytes and 27 relocations. This is not a change to GetCentrePos or the main Update method. The mech constructor (`004983b0`) matches all 352 section bytes and ten relocations after using the existing three-component vector setter; it writes no fourth component. A separate check freshly compiled both and checked the complete existing object set: every earlier match and vtable result survives. Original source spelling, live turning feel and mech behavior are not established by these matches.

- **Texture deserialization and state cleanup match, October 1.** `Deserialize` (`00559be0`) uses the exhausted descending row counter when selecting the frame to unlock: it reproduces retail's frame-zero unlock even when another frame was locked. The complete 1,296-byte section, including switch tables and padding, and all 74 relocations now match. `Deactivate` (`00558fb0`) uses the SDK identity-matrix helper and separate alpha-cleanup tails in modes zero and four, matching all 1,008 section bytes and 95 relocations. The unchanged CTexture vtable check still reports no unique retail table; neither source cleanup nor a matching constructor resolves that separate limitation. No resource file, graphics device or game was executed for these matches.

- **World squad registration appends, October 1.** Fresh pristine decoding confirms `Init` (`004e5e70`) calls `004e5b20` at `004e61dc`, with receiver `008550a0`. The draft called `Add` instead: that prepends, while `Append` links after the current tail. The correction affects world registration, not squad-member insertion. The rebuild preserves every callable byte and changes exactly the final Init relocation, at compiled offset 901, from Add to Append. The complete body remains unmatched; this call correction adds no score credit or runtime claim.

- **Polygon side-normal arithmetic corrected, October 1.** `OptimizePolygons` (`004b31f0`) now forms the side-normal squared length as `(Y² + Z²) + X²`, preserving the float magnitude store at the retail `004b3727..004b3745` calculation. A reconstructed source-local vector helper changes only six operand bytes in the 2,432-byte compiled section; all 33 relocations and the other 60 callable sections retain their meaning. The fresh object equals the frozen corrected object and preserves all 50 MeshPart matches. Replaying the existing 43,062 authored arithmetic cases removes all 1,340 old magnitude differences; corrected captured output equals retail, while the square-root/absolute-value mutation differs in 42,830 cases. The whole function remains unmatched (131 non-relocation differences), and cross-product reachability, normalized outputs, polygon collapse and live precision are unmeasured. No original helper identity is claimed.

- **Destructible-part break and rubble handling now match, October 1.** A controller-owner getter and named child pointer reproduce the remaining source lifetimes in `CDestroyableSegment::Break` (`00442b20`). The fresh complete build adds its 544-byte section (534-byte body) and all eleven relocations, with every previous match retained and no relocation conflicts. The getter returns the existing owner field at controller +0x10; the interface spelling is reconstructed. The part/owner/mount snapshots and independent removal cursor from the earlier callback correction remain intact. `SpawnRubble` (`00442f60`) also matches its complete 1,168-byte section (1,153-byte body) and all 43 relocations. A reconstructed inline box-point calculation retains bounding-box reloads after each RNG call, and the existing engine damage wrapper plus vector-expression lifetimes reproduce retail's expansion. Neither helper spelling claims recovered original source. The 98 other baseline callable sections in the two affected objects retain their bytes and recursive relocation meaning; the two newly emitted helper copies were already globally matched and add no unique credit. The full corpus also preserves earlier exact functions. This closes Break's fourteen-byte setup gap, not the earlier experiment's untested live mutation, particle, allocation or unwind paths.

- **Battle-line pulse rendering matches, October 1.** Keeping the clamped strip level separate from the branch-local strip-index product, and naming the even strip's shared origin, reproduces the source lifetimes in `CMessageBox::RenderBattleLinePulse` (`004b82b0`). The fresh compile matches all 1,360 section bytes (1,353-byte body) and all 59 relocations. Its other 44 callable sections retain their bytes and relocation meaning. This is a static code match, not a fresh rendering observation.

- **Swept-triangle travel gate corrected, October 1.** A reconstructed inline predicate taking the squared limit by reference and returning `squaredLimit <= move.MagnitudeSq()` restores the store-before-call and ordered comparison in `00478510`. Retail stores float32 at `00478b21`, calls the byte-matched magnitude helper at `00478b37`, then admits only ordered greater-or-equal at `00478b3c..00478b45`. The former body delayed squaring until after the call and admitted unordered results. The inverted branch flips all 54 decisions. Explicit PC24/53/64 and masked special values are test conditions, not a live-game claim. A fresh source compile equals the tested candidate across every callable section and relocation; only the target body changes, and all 21 exact Geometry functions survive. The helper has no separately emitted function or identified original name. Full triangle-entry reachability, other arithmetic and complete function matching remain open.

- **Animal destruction and player charge update match, October 1.** Reusing the animal destructor's traversal local makes its initially empty-list branch reload the head at `00404044`, as retail does, instead of jumping to `0040408e`. The complete `00404010` section is 144 bytes with seven relocations. The original assignment that clears every animal's leader is preserved. In the shared `FullyCharged` predicate, retaining the `GetMaxCharge()` call then returning `!CanCharge() || (mCharge >= max)` makes Jet's `00411bf0` match its entire 640-byte section and seven relocations. This reproduces the nested expansion boundary without inline directives; it is not proof of the original source text. The fresh whole-corpus check preserves every preceding matched address, symbol and source owner, gains only these two functions, and reports no relocation conflicts. Neither is live gameplay acceptance.

- **Sphere relative-speed association corrected, October 1.** The expanded original-code comparison exposes a second arithmetic issue in `004e4e00`: retail forms `(X squared + Z squared) + Y squared` at `004e4fa3`; the previous candidate formed `(Z squared + Y squared) + X squared`. A separate check reproduced 23,160 finite complete-entry calls with five actual retail helpers: 132 baseline output differences, all PC24, and none after the correction. A speed-block-only diagnostic removes the same 132. Explicit speed arithmetic plus existing `Normalise()` calls preserve the exact scale helper; the shallow 81-byte normalization block and deep 68-byte zero/reciprocal tail reproduce retail after constant resolution. The deep X/Y operand order still differs, and its method substitution is not a separately proven deep-path repair. The full response remains unmatched (1,536-byte section, 1,537-byte retail body). Defined outputs, ABI/stack/canaries, untouched volumes/report and x87 environment are checked; 21 coarse admission mutations and a missing-constructor refusal are detected. Copied vector padding, aliasing, general equivalence and actual world/device state remain outside this evidence. This supersedes the earlier 43-byte near-miss's relative-speed expression, while preserving the earlier separation-order correction.

- **Compass fixed offsets precede heading displacement, October 1.** Explicit grouping in `CHud::RenderWeaponPanel` (`004858d0`) restores the original coordinate association at `[00485ccc,00485d37)`: Y adds -128, then 48, then dy; X adds 17, then 48, then dx to its base. A separate check verified the retail fragment/constants and reproduced all 6,171 native finite-state cases: the old source differs in 146 PC24 cases; the correction matches all 15 outgoing argument words at PC24/53/64 with the tested nearest rounding. The fresh integrated object equals the frozen tested object across every callable section and relocation. Other 37 HUD sections and all 55 exact functions in the affected three-object check survive. No new exact match is claimed: the full function still has different global-load order, cosine materialization and scheduling. Upstream trigonometry, device precision, rendering and complete caller reachability are untested.

  - The segment query uses sign-conditioned magnitudes and a shared false return, retaining the retail
    X/Y endpoint asymmetry and the previously corrected visited-cell indexing.
  - Sprite setup captures the signed masked random integer before reading its float centre. Trail
    colour packing assigns one result in the blend arms and returns it once. Interpolation gives each
    weighted start/end channel its own float product before adding and converting to an integer.
  - Blob height keeps the two render-position temporaries in the retail call expression; camera distance accumulates Z squared, X squared, then Y squared. The shadow-info pointer advances with the index. A scalar `D3DMATRIX` construction reproduces the view matrix's interleaved stores, including the final row's Y zero before its X zero.

- **September 30 three further complete matches.** A separate check recompiled the relaxed-squad centroid (`004ea980`), trail-point allocator (`004c35d0`) and physics-profile reload (`00510800`). The final complete score adds exactly these three addresses to the preceding 5,011-function baseline, retains every earlier matched address and canonical identity, and has no relocation conflicts. The focused reload check has 260 exact results and its previously recorded partial-object `ZERO_FVECTOR` conflict; that conflict does not involve Reload and is absent from the full build.
- **Trail-point arithmetic has a concrete numerical consequence.** The full 224-byte section at `004c35d0` matches, including its allocation-call relocation at `+0x96`. Its 209-byte retail body combines squared displacement as `(dz*dz + dy*dy) + dx*dx`; the old source emitted `(dz*dz + dx*dx) + dy*dy`. Native execution of the unchanged arithmetic slice at `[004c3602,004c363e)` finds 36 integer-count differences in 140 cases across six selected x87 modes (840 executions per image). All differences are under nearest-even rounding, twelve at each of PC24/53/64; none occur in the tested toward-zero cases. With PC24/RN, current-position bits `[3f800000,39800001,39800001]`, previous position zero and segment length 2.0, retail converts to zero and the old source to one; the following `+3` predicts three versus four points. The corrected slice agrees throughout. Five simple controls per mode, divisor mutation and truncated-input refusal pass, as do return/register/stack/control-word checks. The game's actual mode, complete allocation and visible effect were not tested.
- **Relaxed-squad centroid and return boundaries.** In-place normalization reproduces the 224-byte section at `004ea980` (221 body bytes, three zero-literal relocations); a separate result temporary had changed the stack layout. Eight original-code Unicorn cases with no modeled callees establish that cleared readers are skipped, null node payloads terminate traversal, duplicate unit pointers contribute twice and an empty contribution set returns the squad position. The 16-byte return's fourth word is uninitialized local-stack content on the contributing path in these probes, but is copied from the squad on the fallback. Two arithmetic/read mutation controls are detected; no live roster or update-timing claim follows. `Unknown72` remains appropriate: the original method name is not recovered.
- **Physics-profile reload result lifetime.** A `BOOL loaded` local reused for both file admissions makes `00510800` match its 656-byte section (642 body bytes) and all 55 relocations. Retail compares EAX against the zeroed EBX at `0051085e` and `0051095c`; the old direct conditions emitted TEST EAX,EAX. Pinned Stuart `Career.cpp:1044-1045` supplies this local-result idiom, not the unreleased Reload source. Focused exact results increase 259 to 260 and all other results/vtables remain unchanged. No runtime file-loading experiment was performed.
- **Emitter and effect lookups retain part pointers, September 30.** The serialized emitter's `+0x40` word is a presence marker; when nonzero, the following word is an index which the loader resolves to `mParts[index]` (`004ab275`–`004ab29d`). Runtime `+0x40` and the two emitter-part getters therefore carry `CMeshPart*`. CRTMesh's `+0x3c` array and FindEffect slot 19 retain that pointer identity; `+0x38` is still an emitter ordinal and `+0x40` a numeric effect ID. The two observed callers pass part pointers, and FindEffect returns the first pointer-equal entry or -1. The pose caller now resolves to the existing seven-argument `CMeshPart::EvaluatePose` body rather than an undefined alias. Its original source name and complete body match remain open. All 378 focused exact results survive the type correction.
- **Mine hit admission now matches, September 30.** Using the existing `GetAllegiance()` accessor for the other unit reproduces the complete 64-byte section at `004ba990`, including both call relocations. This is a compiled match, not live combat acceptance.
- **Segmented-core fallback, September 30.** `GetCoreFall` (`00445010`) now matches its complete 96-byte section, including the zero-literal relocation to `005d856c`. Its absent-segment fallback previously calculated an unused mesh part which VC6 discarded. An explicit missing-part zero return retains retail's mesh-table and indexed-part reads (`0044503e`, `00445044`); the compiler folds the redundant branch. This establishes the emitted behavior, not the unavailable original source spelling. A separate check recompiled the integrated object: 32 exact results, all 31 previous results and four vtables retained; `Init` is still a 36-position miss.
- **Device startup boundaries, September 30.** Fresh original/candidate execution at `0052af00` agrees on 23 authored cases under explicit API/application callback models, with nine refusal or mutation controls. Six device-lost results select safe mode before call seven, but a mode pointer captured earlier in that iteration still supplies the old dimensions, format, depth and behavior flags. An ordinary friendly-mode fallback starts another iteration and uses the new mode. Init failure calls application slots 5 then 6, reloads the current device, releases/nulls it and preserves the original init HRESULT. There is no separate RestoreDeviceObjects call here, contrary to an old public contract. Create and Reset success were both executed through the modeled fullscreen software-device path. Six existing FindMode loops and their preferred-format exit trampoline also match 528 bytes without relocations; changing those loops is not justified. Neither enclosing function receives exact credit. PC24/RN is an emulator setting; real driver/window/card-file effects, HAL-to-REF recursion, cursor/query paths, app virtual bodies, unrestricted memory reads and complete startup remain outside this bounded comparison.

- **Mesh-part stream loading now matches, September 30.** `CMeshPart::LoadFromStream` (`004b27a0`) had eleven differing stack displacements. Five separate chunk reads reused one function-wide index in the reconstruction; giving each index its own lexical lifetime reproduces retail's use of dead argument homes. The complete 2528-byte section and every relocation now match (2514 retail function bytes). Localizing only the final collision-part index worsened the result and was rejected; no padding, casts, compiler flags or synthetic helpers were introduced. A separate check recompiled the result with the current shared headers. The collision-report tag correction merges five duplicate symbol spellings and changes some representative emitting objects; it loses no identity.
- **Source/interface omissions are distinct from code-generation misses, September 30.**
  - Restored Stuart's `MemoryManager.cpp:1622-1659` TagMem/UnTagMem definitions, retaining their
    MEMORY_TAGGING guards. The selected retail configuration emits `ret` for variadic member
    TagMem (the receiver is a stack argument, caller cleanup) and `ret 4` for thiscall UnTagMem.
    DebugTrace and ScreenFX::Render also reach the empty `0040c640` body and now have out-of-line
    definitions. DebugTrace's original object home is unknown; the existing reconstructed DebugLog
    owner is used. No trace is redirected to AddMessage, which would recurse. All five added bodies
    below are folded aliases, not five new unique functions.
  - Consolidated fourteen GetAnimatedFrame calls onto the existing GetTexture implementation
    `00558690`, preserving its `IDirect3DTexture9*` return and ordinary base-interface upcast.
    The old declaration did not have a separate implementation. Stuart's GetSurfaceLevel caller
    supports the texture-specific interface; the checked retail callers forward the same pointer.
  - `CRenderMethod::SetMethod(int)` now implements the raw +0c store at `00528b50`. Landscape's
    `0054565c` call uses it, as water already did. The old float Set selected `00527d00`, which
    additionally changes mAccepted at +10; that was a behavioral error. Console float Set is unchanged.
  - Unified the collision-report forward declaration with its actual struct definition so world's TestAtOffset call resolves to the existing Geometry implementation; no layout changed. Career's warning likewise now names existing SetSetupMessage (`0042115a` to `004d1710`, argument f6). All 302 prior unique exact functions in the twenty-object interface control set survive. Its 483 common emitted functions have identical instructions and relocation sites; compiler-local labels resolve identically. Fifteen direct-call identities change (fourteen texture aliases and the landscape setter); one additional symbol spelling corrects CCollisionReport's class/struct tag. Five restored/added folded bodies also match fully. Career/PauseMenu's isolated 160 exact controls survive with identical instruction bytes. These corrections improve source completeness without establishing a linked executable.
- **Released-source calls exposed unfinished header reconstruction, September 30.** The two `GetTargetablePos` calls in HandleAutoAim selected an undefined nonvirtual reference overload, whereas retail calls the existing virtual slot 90 at 0040b95c and 0040be40. They now pass the output address to the established pointer virtual; machine code does not distinguish the original pointer/reference spelling. Unit slot 105 is OnScanner (0040b9cb), including its Component, Mine, Carver and Submarine overrides, and Feature slot 71 is IsLockable (0040bbbc). The former separate nonvirtual declarations were wrong. IsBig and IsLockable inline the unit-data +124/+114 reads, with false/true defaults respectively for null data; IsLockable must not call virtual CanBeLocked, whose Carver override has additional conditions. Feature allegiance is the +ec read; weapon IsSmart and AdjustAim read data +30/+28 through weapon +a4. These source-named calls were re-derived from the pristine instructions, not inferred from their old labels. Nine undefined direct-call sites across HandleAutoAim and GetLaunchPosition are now removed; the expected virtual dispatches and inline reads are present. All 984 match rows in the twelve-object before/after control set survive after the declared method renames. The partial build's one static ZERO_FVECTOR ambiguity is also present in the unchanged baseline. Both large callers remain unmatched, with 2320/1904-byte candidate sections: this is a structural correction, not another exact-match count or whole-function runtime validation.
- **Ground-guide caller context recovered, September 30.** Existing guide/unit accessors and direct initialization of the displacement vector restore retail's first four calls in `0047d750`: vector constructor at `0047d79c`, IsDeploying at `0047d812`, Magnitude at `0047d850` and `__CIasin` at `0047d86e`. A separate check recompiled and checked each relocated instruction against the pristine bytes; the constructor receives the same three stored float arguments and constructs the live displacement instead of an additional temporary/copy. All 26 exact functions in the four-guide control set and both vtables survive. Carrier's failed forms were restored. No shared header, ABI or field layout changed. The whole ground method remains unmatched (2,688 section bytes versus 2,640 retail bytes, 2,097 differing positions); the later occupancy-grid call still occurs three bytes earlier. This establishes call-boundary fidelity, not original source spelling, whole-function equivalence or runtime acceptance.
- **Segment approach recomputation corrected, September 30.** Retail `00478cff..00478d2d` uses unrounded displacement differences for its first facing dot while also storing float32 copies. At `00478d3a..00478d54` it reloads those copies for the threshold/division dot. Caching one dot for both decisions lost this distinction. The source now performs the facing expression separately, then constructs the stored delta and recomputes the approach. A separate check reproduced 57 finite ordinary-entry prefixes at PC24/53/64: all corrected outcomes, normals and admitted distances agree; the previous candidate differs twice and a naive split expression eight times. For normal `(0.6f,0.8f,0)` and Y displacement `0xbbcccccc`, the old float store can round its magnitude up to the `0.005f` admission boundary at PC53/64; retail refuses it. Separately, start Z=1 and end Z=`-2^-24` expose why the second dot must reload the float32 delta. Two memory controls refuse undeclared reads/writes. The final body remains unmatched (672 section bytes versus 1,014 retail body bytes); all other emitted Geometry callable sections/relocations are unchanged and its 18 exact functions remain exact. The 27 earlier contact-slice cases also still agree. These are prefix/slice observations, not complete prism/report behavior or the game's live FPU mode. No new exact credit is claimed.
- **Sphere tangency exposed a materialization defect, September 30 (closed by the current exact body).** A separate check reproduced 51 complete finite `CSphere::CollideWithLine` (`004e4b90`) cases with the actual constructor and magnitude helpers, no stubs, explicit relocation bindings and memory/ABI guards. Twelve admission differences occur at PC53/64; PC24 controls agree. With radius 1 and segment `(1,1,0)` to `(-0.5,1,0)`, retail returns true after materializing the scaled vector, while the candidate retains closest-point X=`-2^-25` and returns false. Named temporaries, compound operators and cast-only experiments did not recover the boundary reliably; no forced source correction is retained. Nine controls detect invalid dependencies/execution and strict-versus-inclusive tangency. Both entries reject radial endpoint-only contact when the closest projection lies beyond the segment. Degenerate outside/tangent division, nonfinite inputs and live FPU state remain outside the probe. That dated experiment earned no match credit. The October 1 fresh check reproduces the subsequent fix already integrated: `004e4b90` now matches all 480 section bytes and four relocations. The old defect is not a current near miss; its frozen cases remain historical evidence.
- **Cylinder discrepancies bounded, September 30.** A separate check reproduced 55 finite collision/line cases (`0043fe20`, `00440510`) with seven complete byte-verified retail helpers, no stubs and nine successful controls. Defined outputs agree across two authored stack fills at declared PC64/RN. Six exact integer-copy sites read uninitialized FVector padding; that padding is recorded but excluded from defined-output comparisons. Response-enabled admission can reject separating overlap accepted by the coarse test; the deep-overlap branch moves both positions without populating the report normal. The line's quadratic uses the full 3D direction length and need not return the ideal geometric cylinder contact. Both large bodies remain unmatched; no source change was warranted by these samples. This does not establish equivalence, native exception behavior or live FPU settings.
- **Callable polygon resize recovered, September 30.** Explicitly instantiating the existing `CArray<CPolyBucketVertex>` class in PolyBucket.cpp emits the retail-referenced `ReSize` copy at `004d6210`: all 48 section bytes and relocations to `MEM_MANAGER` and `ReAlloc` match. Retail Build calls this body at `004d4592`, while the exact standalone `COSet::Add` embeds it. A separate check reproduced 27 focused matches, preserving all 26 previous ones. The six other newly emitted, unannotated template members earn no match credit; Build remains unchanged and unmatched. This supplies the witnessed callable definition without inventing a use; retail's original instantiation spelling is unknown. Member-only explicit instantiation emitted nothing with the pinned compiler.
- **Segment contact rounding corrected, September 30.** At `00478df9..00478e31`, retail multiplies each displacement component by the stored distance, adds the start coordinate, then stores float32. The reconstructed scaled-vector temporary rounded Y/Z products before the addition. Explicit component expressions restore the observed boundary. A separate check reproduced 27 finite slice cases at declared x87 precisions 24/53/64: six old divergences, all corrected results agreeing. For start `(1,-1,-1)`, delta `(-3,3,3)` and float32 distance `1/3`, retail's Y/Z are `2^-25` at PC53/64, where the old code produced zero. Three ordinary retail entry runs reach that contact calculation; they stop before prism admission. Zero/unit/half-distance and PC24 controls agree. This does not establish the game's live FPU mode, denominator rounding, prism decisions, report writes or whole-function equivalence. The segment body was 624 compiled bytes at this intermediate correction; the approach correction above supersedes that candidate and preserves these contact results. All 18 existing Geometry matches survive.
- **Two callable helpers recovered, September 30.** The sprite-specific reciprocal magnitude `004c78d0` now matches its entire 48-byte section and constant relocation. Writing the actual sum, square root and reciprocal in that helper preserves a callable body, whereas delegating to Magnitude inlined only the outer reciprocal wrapper. No intermediate float spill is added. The constructor `004d0db0` now matches its entire 48-byte section and base-event relocation after moving its body from PauseMenu.h into PauseMenu.cpp; it initializes the event and stores the item at +8. The complete sprite renderer and pause ButtonPressed bodies remain unmatched. The full build has 5,007 exact functions, with no lost previously matched addresses or symbols. A separate direct-expression GetColumnX experiment matched `004aa3f0` but lost the exact bomber guide `00416970`; moving the old float locals into that caller did not recover it. Both changes were rejected and restored.
- **RemapKey's size gap bounded against original execution, September 30.** Retail `004541e0` contains ten duplicate-binding scans and 18 calls to `00454e90`; the candidate calls that helper throughout. The old comment saying both retail remappers do so was wrong. Two natural expansion experiments preserved all 31 existing FEPControls matches but failed to reproduce the selected inlining, and were restored. Both bodies execute at the retail address with six actual retail helpers and no stubs. Final authored binding/capture/preset state and selected dispatch/callback/preset event order agree; exact write order and every helper-call order are not compared. A captured-polarity mutant wrongly clears a real binding and is detected. Ten refusal controls exercise bound relocations, output preservation, forbidden calls, escaped/incomplete execution, wrong BSS reads and bounded initialized-stack access. ApplyControlPreset covers only its preset-zero early return; device/UI behavior, nonzero presets, RemapKeyTrap and saved settings-file compatibility remain outside this evidence. The 1,968-byte candidate still differs from retail's 3,089-byte body.
- **Key-capture reconstruction bounded, October 1.** A fresh `RemapKeyTrap` (`00456190`) comparison agrees on 482 authored cases: both input slots, mouse remapping, key-down/release admission, Escape, ignored Windows keys, character capture and ignored event values. Original key-sink, remap and preset helpers execute; sound is explicitly disabled and original `toupper` takes its C-locale path. Complete authored binding/capture/preset state, key-sink pointer, low-byte return and selected event order agree. Ten controls detect changed state, undeclared memory, invalid execution and unavailable dependencies. The fresh run and an independent read-only instruction/relocation review support this bounded result; neither establishes physical input, sound, other locales, serialized saves or equivalence. The isolated candidate inlines all binding setters and does not execute the original setter range it overlaps. Its full 1,248-byte section remains unmatched; all 31 exact FEPControls controls survive.
- **Ballistic feasibility uses two different target positions, October 1.** A fresh native reproduction of original Weapon B (`005088b0`) confirms predicted endpoint XY for range, but owner/target current Z for height. In 14 scenarios / 84 calls, vertical prediction changes endpoint height without changing admission; horizontal recession can refuse. Raising current target height can refuse even with an unchanged aim point. Seek does not bypass ballistic range refusal, and that arm skips the world query; zero-gravity and beam controls reach its explicit rejecting substitute. Actual endpoint/motion/math code executes with recording providers, PC24/53/64 and two CRT modes. This is original-code evidence, not a candidate comparison, real geometry or gameplay acceptance. Complete recorded outputs reproduce after rebasing only declared stack pointers.
- **Sphere response squared-distance order corrected, October 1.** A separate check freshly compiled and reran both complete `004e4e00` entries natively with five actual byte-verified vector helpers. The old `MagnitudeSq()` spelling emitted `(Y² + Z²) + X²` at the initial separation and reused deep-contact distance; retail adds XY before Z (`004e4f2d`, `004e52ca`). Expressing XY magnitude plus Z squared restores that association. It removes all 148 observed PC24 movement/position differences (77 deep response, 71 shallow threshold) from the same 4,512 authored cases; PC53/64 still have no sampled differences. Inputs and retail outputs are unchanged. Three coarse-tangency controls still change results, and removing an admitted dependency fails as expected. Native register/stack, x87-state and untouched-input checks pass; copied uninitialized vector padding is excluded. This corrects a demonstrated reconstruction error, not a claim of general equivalence, live-world reachability or a measured running-game control word. The 1,552-byte section still differs at 43 nonrelocation bytes; remaining operand scheduling and normal/relative-speed expressions are unresolved. All 17 exact address/symbol controls (15 unique functions) and the 19 other callable bodies remain unchanged. The line test `004e4b90` is already exact.
- **Cylinder radial rounding corrected, October 1.** Direct `sqrtf(X*X + Y*Y)` restores retail's Y-square store/reload at `0043ff2e..0043ff42` and reuse of the stored squares in deep normalization. A separate check freshly compiled and executed the complete response with seven admitted retail helpers: 77 finite fixtures at PC24/53/64 and two stack fills give 462 cases. Defined-output differences fall from 84 to eight, with identical inputs, original outputs and negative controls; the eight remaining discrepancies are unchanged translated-origin initial-Z cases at PC53/64. Retail rounds Z at `0043ff1a`, whereas the candidate retains excess precision before height subtraction. A broader depth-reordering draft was rejected: three added moving-tie fixtures expose a return-value error after its initial 444 cases agreed. No general equivalence or live-world reachability is claimed. The response remains unmatched (1,664 section bytes against a 1,731-byte retail body, 29 relocations). Twenty other retained callable sections and their relocations are unchanged. The formerly emitted `FVector::Normalise` is now inlined here; whole-build verification checks its existing exact emission elsewhere. The line test `00440510` already matches all 1,456 bytes and 21 relocations.
- **Goodies requirement text matches, October 1.** Calling the existing PC text lookup directly in `CGoodieData::GetMethod` (`0045a940`) closes the remaining register/scheduling differences. `GetString(DWORD)` is a forwarding wrapper to `GetStringById(DWORD)`; both direct calls retain target `004f2580`. A separate check reproduced all 736 section bytes (726-byte retail body) and 60 relocations. All 23 prior exact pairs and 31 other callable sections/relocation destinations survive; compiler-local label renumbering changes no destination. The same substitution in Render's helper produces no change, so that rejected draft is not retained. This proves the compiled body, not a unique original spelling or rendered-menu acceptance.
- **Radio-message construction matches, October 1.** The constructor `004b71e0` now uses the already-initialized portrait-frame member for its first-speaker table read. This restores retail's late `[edi]` load after the constant member stores. A separate check freshly compiled all 288 section bytes (277-byte body) and 16 relocations exactly; all 35 prior exact pairs and 44 other callable sections remain unchanged. An independent flat-storage view also compiles to the exact constructor, after resolving its renamed exception-handler labels, demonstrating why a match does not recover unique original source spelling. The read still precedes the portrait-table clear; no initialization or runtime acceptance is invented. The portrait renderer remains unmatched.
- **Options-list return preserves the pre-callback title, October 1.** Retail `004a4c57` loads the title after DeferredRender but before confirmation/action callbacks; the two return paths use that saved pointer. The reconstruction previously reread the field afterward. A local snapshot corrects the order. A separate check reproduced 27 isolated integer-tail runs: all nine corrected cases agree with retail, while six explicit changing-dependency cases distinguish the old result. Callback arguments, order, resulting memory and stack/canaries agree. These are controlled substitutions, not proof that real callbacks change the title. All 18 exact controls and 22 other callable sections/relocation destinations survive. The initial snapshot correction alone left Render unmatched.
- **Options-list rendering now matches completely, October 1.** A natural panel-sizing helper, a width-only `SIZE` lifetime, a caller-scoped later title `SIZE`, and a named title X restore retail's iterator calls and stack reuse. A separate check reproduced all 1,216 section bytes, including nine padding bytes and 41 relocations; all 18 prior exact controls and 22 other callable bodies and relocation targets survive. The two newly emitted First/Next sections also match, but already have exact owners elsewhere. This is reconstructed source, not proof of its original spelling. Thirty-six bounded prefix runs (retail, prior snapshot-only source, accepted source) also reproduce a consequence of the frame correction: null text makes the real GetTextExtent leave `SIZE` unwritten, so retail's earlier height scratch supplies its first word. Five of six authored null-title states differed before; the corrected code agrees in all twelve tested states. Normal live reachability is unproved, and the emitted match does not make an uninitialized C++ read portable. No drawing occurs.
- **Imposter quad texture coordinates and precision corrected, October 1.** The AddQuad caller `00543845..0054386e` supplies frame offsets `+00,+08,+04,+0c` as `u0,v0,u1,v1`. Retail assigns `(u0,v0),(u1,v0),(u1,v1),(u0,v1)` to the four corners; the earlier reconstruction reversed V. It also rounded the first `pos-right` vector to float32 before subtracting up, whereas retail `00543069..00543090` retains those intermediates on x87. The corrected helper removes that materialization. A separate check freshly compiled and ran 828 native i386 cases at PC24/53/64, both buffers, two fills and three buffer offsets: old differences 774, UV-only 288, corrected zero. Four actual byte-matched helpers run on prelocked sufficient-capacity buffers; locking, resizing and error providers refuse. An arithmetic control differs in 474 cases; missing-constructor and excluded-provider controls fail closed. All 25 exact controls and 29 other callable bodies/targets survive. A subsequent natural three-component aggregate with parenthesized values restores the remaining first-corner and later instruction scheduling: all 880 section bytes and 20 relocations now match. A separate check repeated the 828 native cases with no differences and preserved every prior exact control. This proves the emitted body, not the original source spelling or live rendering.

- **Text measurement boundaries rechecked, October 1.** GetTextExtent `00540680` returns false without writing output for null text or SIZE. Empty text succeeds with zero width and one row's height. Newline resets width/adds height but still measures its remapped glyph; CR skips it. Width and height use `FISTP qword` followed by the low dword, honoring the existing rounding mode. A separate check freshly compiled DXFont/Font and reproduced 1,032 native original/candidate cases using actual byte-matched character-map/remapper helpers, PC24/53/64 and all four rounding modes. Results, exception flags, input/map state, ABI and x87 state agree. Three mutations differ in 144/24/726 cases; missing remapper and excluded texture initialization refuse. No real font assets, arbitrary aliases/remappers, malformed text, nonfinite values, GDI/D3D or visual acceptance is established. That earlier candidate differed at 87 positions; the subsequent direct texture-entry correction now matches all 448 bytes and six relocations, as recorded above. The 14 prior exact controls survive.

- **Imposter rotation and centre offset corrected, October 1.** In Render `00543300`, the update at `00543878..0054388f` passes the current orientation as the argument and the turn matrix as the receiver to the byte-matched matrix product `0040d320`. The old reconstruction reversed them. `turn * ori` reproduces the actual operation: 48 native cases execute the original turn setup, update and complete helper with eight finite orientations, PC24/53/64 nearest and two fills; differences fall from 36 to zero. The box-offset first row also used the wrong addition association. Explicit `(X+Y)+Z` row accumulation reproduces the whole relocated 125-byte block `0054342a..005434a7`; 102 native authored cases with the actual constructor improve from 12 differences to zero. A separate check freshly compiled the combined correction, not just the intermediate helper drafts. All 26 exact controls and 29 other callable bodies/relocation targets remain unchanged. Full Render is still unmatched (1424-byte section, 1467-byte retail body, 25 relocations). Row padding, arbitrary inputs, providers, the complete rendering call and actual GPU/world appearance remain outside these comparisons.

- **Font vertex stream corrected, October 1.** DrawTextScaled `00540010` emits glyph corners TL, TR, BR, BL with their corresponding UVs (`0054047e..005405b9`), while the previous source emitted BL, TL, TR, BR. Actual FastVB indices `0051a5d7..0051a5f3` select `(0,1,2),(2,3,0)`, so this changes the stored stream and diagonal. It is not a proven flipped glyph or visible defect in an affine textured rectangle. A separate check reproduced 468 native loop comparisons with actual character-map/remapper helpers and explicit loop-entry frame adapters: 404 old differences become 32 after the corner correction. Those remaining witnesses expose retail's float32 `ty2` store at `00540311` and reload at `0054032d`; the candidate retains excess precision. With unit UVs, V inset `2^-25` and starting Y `.5`, PC53/64 produce retail bottom Y zero versus candidate `-2^-25`. Nonzero inset reachability remains unproved. A half-pixel mutation differs in all 468 cases; a missing remapper refuses. Prefix/floor/viewport, buffer lock, submission, arbitrary inputs and live rendering are excluded. The 1552-byte candidate remains unmatched against the 1581-byte retail body; 14 exact controls and 17 other callable sections/relocations survive.

The subsequent stored-UV correction removes those 32 witnesses. Giving the local vertex writer const references and copying the four-byte UV representations to its existing fields restores the candidate's float32 `ty2` store/reload before height calculation (`0054030e/0054032c`). There are no new destinations or calls: all 19 direct targets remain, no memcpy call is emitted, and all 14 exact controls/17 other callable sections and relocation targets survive. Retail uses mixed integer/x87 UV transport, so this is a reconstructed representation boundary, not a claim of the same store sequence or original helper spelling. Fresh native runs give 404/32/0 differences for baseline/corner-only/final source. A control that removes only retail's `ty2` rounding reproduces the old candidate's complete normalized outputs in all 468 cases, including exactly its 32 discrepancies. The full function remains unmatched; aliases, NaN payloads, unmasked exceptions, prefix/device work and live reachability remain untested.

- **Debug-arrow arithmetic corrected, October 1.** RenderArrow `0053df40` now invokes the actual format setters directly, removing reconstructed forwarding-wrapper inline cost. The first vertex sum's X component remains extended until the origin is added, as at `0053e120..0053e149`; Y/Z retain their measured float32 boundaries. A separate check freshly compiled and reproduced 18 native finite cases at PC24/53/64 nearest: six old X discrepancies become zero, with unchanged Y/Z. Adding just the premature X store/reload to retail reproduces all old outputs. The actual constructor executes in the baseline, with guard/ABI/FPU checks; upstream normalization, providers, GPU output and live precision are excluded. All 30 exact controls and 36 other callable sections and relocation targets survive. The complete 752-byte section remains unmatched (188 differing positions, 19 relocations; retail body 734 bytes). Three decoded callers belong to the squad debug method at `004e9f00`; selected-squad dispatch at `00470681` reaches its vtable slot. Ordinary player activation is unproved. The retail six-word index construction leaves element 4 unwritten; AddIndices copies all twelve bytes and Draw submits them. Cached-buffer acquisition does not initialize that caller stack slot. This static retained defect is preserved, not repaired or claimed to cause a visible failure.

- **Resource-reader boundaries rechecked, October 1.** Fresh Read `00548570` compilation and original-code comparison agree in 200 authored cases, including EOF, pointer/count advancement, packed refills and optional check-byte handling. The exact Skip body controls 192 nonnegative cases; 80 ready-memory states also have an independent byte-copy/state oracle without providers. Eight negative controls reject altered EOF/check-byte/refill behavior and missing dependencies. Refill cases use explicit ReadFile/GetLastError/Python-zlib models; original C-locale stricmp and the import thunk execute, but Windows I/O and the original DLL do not. Negative signed sizes are eight separate malformed observations, not admitted valid requests. The 8-byte test capacity, authored check stream and allocation assumptions do not establish normal file/save compatibility. No source correction is demonstrated; Read remains unmatched (688-byte section, 460 differences), with 13 exact controls preserved.

- **Particle-reference allocation corrected, October 1.** ReadToken `004f57b0` requests the optional float-reference suffix length plus two bytes (`004f5a0e..004f5a19`), not plus one as reconstructed. A separate check reproduced the actual allocator-call arguments on 85 float-reference prefixes and 85 plain-reference controls; the corrected request agrees throughout. Five negative controls detect the removed increment, wrong suffix origin, escaped/incomplete execution and an unadmitted read. Prefix entries follow classification/conversion and stop at allocator entry: neither scanf, file reading nor allocation executes. This establishes the request, not a buffer overflow, bucket-size difference or visible effect. The 960-byte section remains unmatched (543 differences); all 15 other callable sections/targets and exact controls survive. The fresh instruction read also corrects the old public parser description: the integer format is `%i` at `00633a24`, not `%d`.

- **Library-binding correction, October 1.** The checker formerly accepted `CFeature::Move` (`0044cc10`) with an `acos` call because its nonrelocation bytes matched and every reconstructed `__CIacos` witness implied `0055dcb0`. That entry is actually `__CIasin`; `__CIacos` is `0055f380`. Each complete 203-byte section from pinned LIBCMT `asin.obj`/`acos.obj` matches outside its relocation fields, with distinct arithmetic, endpoint handling and linked operation-name strings. Swapping the members fails 47/51 nonrelocation bytes. LIBCMT SHA-256: `a541c95e5ffdd6d5573d1976f5e5d0038f2c4fb0bcb02975c68948bf1d6e452a`. A separate check reproduced the library comparison and decoded the actual calls: Feature `0044cc84` and Explosion `0044bb13` call asin; all three Shadow `004ee852/004ee85f/004ee86e` calls use acos. Feature and Explosion source now use asin; only those two relocation symbols change across their 36 callable sections. Feature regains its match under the stricter checker; Explosion remains unmatched. StaticShadows source is unchanged. Checker and differential resolver share the four proven intrinsic/normal entries, overriding stale discovery and source annotations; wrong-name and wrong-ABI controls reject the former false acceptance. Other library identities still need independent admission. No linked game, visible toppling/explosion or whole-CRT runtime acceptance follows.

- **Fmod entry identities constrained, October 1.** A fresh fixed-owner certificate reconstructs 5,340 bytes across twelve complete VC6 library code/data regions, including 131 relocation words, without masking. All 22 direct relocations in the 50-byte fmod member and its 80-byte operation table bind to symbols defined in checked owners. `_fmod` at `0055e3e0` loads two cdecl doubles; `__CIfmod` at `0055e3ea` consumes x87 operands. Their ten-byte wrappers look identical when relocation fields are masked but jump to different dispatchers. Both identities now constrain checker/discovery/resolver behavior; swapped-ABI and stale-discovery controls refuse substitution. Fresh FEPCommon callers `00452df0` and `00452fd0` retain their whole-section/relocation matches and correctly call the intrinsic entry. No new source mismatch was found. Four deeper exception-runtime callees remain an explicit inherited-evidence frontier; this is not complete CRT execution proof. 56 matcher/resolver tests pass.

- **Pow, floor and ceil bindings constrained, October 1.** A separate check reproduced complete pinned LIBCMT ownership for `__CIpow` (`0055fa40`), normal `_pow` (`0055fa59`), `_floor` (`0055dfe7`) and `_ceil` (`0055eb3d`). Thirty-five complete linked code/data regions (7,738 bytes) and all 201 relocation words agree. Every one of the 41 direct entry-owner relocations lands in a freshly checked owner; five deeper exception/errno endpoints remain an explicitly pinned inherited frontier. The checker now constrains these identities rather than accepting caller consensus alone. Floor/ceil have distinct instructions and rounding-control data; the normal/intrinsic pow entries have different calling conventions. Swap and stale-annotation tests reject substitutions. No new game-function credit or complete CRT/runtime-equivalence claim follows. The complete integrated score with these bindings and the visibility correction below retains all 5,211 exact addresses/5,251 symbol rows, with no gained/lost match or relocation conflict;

- **Auto-aim visibility caller corrected, October 1.** `HandleAutoAim` (`0040b6d0`) relied on unchecked shared defaults, passing collision level 2, ignore mask 0 and map flag 0. Actual retail pushes at `0040becc..0040bed8` pass 1, 4 and 1. The caller now supplies those values explicitly. The dispatcher uses level 2 to enter the mesh-volume path unconditionally; otherwise collision flags and mesh permission decide. It excludes candidates intersecting the ignore mask and forwards the map flag to `00490a40`; this recheck does not assign additional meaning to that flag. A separate check freshly compiled before/after, reproduced native caller-suffix execution through the actual exact line-copy constructor, and captured all dispatch arguments and report initialization. Only legitimate report-frame offsets differ between retail and corrected output. The old candidate provides the consequential negative control. All 190 exact controls and 253 other callable sections/relocations survive. That visibility-only draft remained shorter than retail; the complete target now matches as recorded below. Visibility outcomes and live acceptance remain open. The unplaced `GetThingOverCrossHair` source body has no established retail address; its defaults are unchanged. This is bounded caller execution and callee static evidence, not complete collision or auto-aim equivalence. A separate native execution of the original 29-byte map predicate (`00490ba7..00490bc3`) confirms that only flag 1 enables `position.Z >= map+1034`; flags 0, 2 and -1 bypass it. Across 168 finite authored cases under masked PC24/53/64, changing the admitted flag to 2 changes sixty decisions. This is the additional water-level branch; terrain sampling, recursive traversal, level loading and the composed visibility result remain unexecuted.

- **Complete auto-aim target search matched, October 1.** `HandleAutoAim` (`0040b6d0`) now matches its entire 2,304-byte section (2,290-byte body), all 79 relocations, its eighteen-byte exception body and forty-byte unwind metadata. A typed reference adapter restores the two existing slot-90 output calls' source boundary; naming the first Z-squared value preserves extended Z, binary32 X/Y, `(Z² + X²) + Y²` and the separate later Magnitude call. These local interfaces are reconstructed, not recovered names. The fresh build preserves all 190 earlier exact controls and 253 other callable sections/relocations. Exception dispatch is freshly identified from pinned LIBCMT: 209 complete primary bytes/four bindings, with three supporting owners' 27 deeper relocation fields and an indirect callback explicitly outside that certificate. Native range slices now agree in 1,179 authored finite cases: 22 old discrepancies become zero. The adapter-only draft still fails six association witnesses, including two at PC24; zeroing either small coordinate removes those differences. Z-reload and inverted-upper-bound controls disagree eight and 944 times. This compiles the complete target but executes only its range slice; filters, callbacks, later angles, live FPU state and player acceptance remain separate.

- **Nearest-visited fallback matches, October 1.** `004beb30` tests the right-side cost cell with the preceding top/bottom loop's completed X iterator, not the radius. Its bounds and returned endpoint still use the radius. Preserving that retail quirk closes the complete 512-byte section (497-byte body) and all 18 independently anchored address words. A separate check freshly rebuilt both versions and reproduced 26 complete native integer cases: 19 old endpoint differences become zero. Changing only the original index register from EBX to radius EBP reproduces the old results in all 26. The 49 other callable sections remain unchanged; only this procedure's associated debug length also changes, from 508 to 497. Out-of-allocation probes, invalid starts, overflow and live pathfinding remain excluded.
- **Projected-texture component count corrected, October 1.** At `00558e7c`, texture Activate's mode 3 passes `0x104` to stage zero's `D3DTSS_TEXTURETRANSFORMFLAGS`, through `00513820`. The reconstruction passed `0x103`. The pinned SDK defines these as COUNT4 versus COUNT3, both with PROJECTED; Direct3D's fixed-function contract divides by the last selected coordinate. The corrected constant changes one instruction byte and retains all 37 exact controls, all 88 target relocations and 160 other object sections. The full function remains unmatched; no device, shader configuration or rendered projection was executed.
- **Loading-screen text ID corrected, October 1.** The nonzero controls-pause flag must select `07dea02c` (`FETX_PRESS_START`), not the mistyped `07dae02c`; zero selects `003848a7` (`IG_LOADING2`). The original selector at `0042cd4b..0042cd67` and the fresh correction agree for all 256 byte values with two register/carry seeds; the old selector differs on every nonzero value. Eighteen executions of the actual `004f2580` lookup against the six individually hashed language tables confirm the consequence: the correct ID is present, the old ID is absent and returns the text-pool prefix `**Undefined String**`. English selects `Press START button`. The lookup itself recompiles exactly; only missing-ID logging is a declared recording provider. Mode 3 replaces this pointer afterward, and bottom-text/font gates precede it. The renderer, actual loading route and presentation were not run. The two-byte correction preserves all 61 exact console controls, all 147 target relocations and all 318 other object sections; the entire renderer remains unmatched.
- **Flak distance corrected; lifespan rounding remains open, October 1.** SpawnRound `005069f0` now materializes all three displacement components through the independently exact subtraction helper and groups the squared-distance sum. Its new 3,776-byte section remains unmatched against the 3,772-byte retail body. All 43 earlier exact controls, five vtables and 61 other callable bodies/recursive relocations survive; the emitted subtraction copy is already matched elsewhere and adds no unique function credit. A separate 2,187-case signed-zero/Inf/qNaN/sNaN run also agrees; the candidate reverses the inner Y²/Z² operands, so that bounded agreement is not a universal NaN-payload claim. Matrix construction changed from an out-of-line vector to inline writes; 3,009 guarded finite matrix cases retain all nine outputs/observed exceptions, while an altered multiply changes 3,006. The error-product binary32 store at `00507481` is still missing: all 439 previously discrepant lifespan results persist in 7,245 cases; 45 zero-inaccuracy controls agree. No full burst, RNG, live FPU state or shipping-state reachability claim follows.

- **Pause confirmation diagnostic corrected, October 1.** `ButtonPressed` (`004d0810`) now passes source line 1635 for the YES item's allocation, matching the original push at `004d0a21`. The fresh before/after builds differ by that one byte across all 453 COFF sections, with every relocation unchanged and 118 exact controls preserved. The 1,520-byte target remains unmatched; no menu execution follows.

- **Pod Aim's failure path reproduced, October 1.** A separate check freshly compiled Pod and ran 5,940 complete native original/candidate Aim calls with actual Pod Gravity and Euler helpers, across PC24/53/64 and three finite stack seeds. Receiver/data/ABI/FPU checks and all observed values agree. When no trial improves the initial 99999.0 error, the original reads an unwritten pitch; 2,061 authored cases take this path (including 1,161 positive-speed cases), and their 687 seed groups produce different XYZ. The fourth velocity word is always copied from unwritten stack storage. Doubling the angle step changes 2,208 observations; missing-vtable and truncated inputs fail. RTTI proves CPod ownership and the actual +b4 gravity slot. The 368-byte candidate remains unmatched against the 343-byte body; 13 exact controls survive. Finite agreement is not equivalence, shipped-state reachability or player acceptance.

- **Segment-break snapshots corrected, October 1.** Break `00442b20` now retains the selected mesh part across effect callbacks, snapshots owner/mount at retail's points, and walks the temporary removal set's own cursor. A separate check freshly rebuilt both sources: 41 exact controls, four vtables and fifty other callable sections/recursive relocation identities survive. The target improves from a too-short 528-byte section to 544 bytes, at that stage retaining fourteen integer-setup differences against the 534-byte retail body. The later lifetime correction above closes those differences and matches the entire section. Four old callback-trace discrepancies in fourteen guarded cases disappear after the correction. Explicit FindEffect interventions change the part table/index; controls change the captured part's children pointer/count. Original empty set/scheduling dependencies execute, while virtual effects queries are declared providers. A second run poisons provider caller-saved registers/flags with identical observations. Nonempty spawner removal, particle kills, allocation, unwinding and shipping mutation remain untested.

- **ReadToken composition reproduced, October 1.** A separate check freshly compiled TokenArchive and compared twelve authored ASCII streams, 38 complete calls per side, with original ready-memory ReadLine/ReadString and the original C-locale CRT. All observations agree: returns, complete named buffers, output bytes, file state, ordered token lookups and scanner results. Six refusals and three causal interventions also agree. The candidate executes its own code, dispatch tables and actual BSS ordering at separate addresses; all 49 relocations are explicitly bound. Original GetTokenName is used only after its current 1,280-byte section and 250 relocations freshly match. Changed name data and the wrong numeric format are rejected. After a valid float, `File_Version +.` returns TRUE with the previous output, while a missing second word returns FALSE. Header then blank/EOF can return TRUE with a stale header token; this is a call-boundary observation, not proof that callers continue after EOF. The allocator-refusal case reaches the same seven-byte request for `Smoke`. The 960-byte ReadToken section remains unmatched; all fifteen exact controls survive. No actual file/refill, allocation, descriptor publication, save compatibility or equivalence claim follows.

The complete original simple-sprite loader `004c05c0` also reproduces the downstream stale scalar store: `Final_Radius 1.5`, `Life_Pct +.`, separator writes 1.5 at descriptor `+74` and returns TRUE. Missing Life_Pct's value returns FALSE from ReadToken but the caller still stores 1.5 and completes. Five streams/fifteen reads, five refusal controls, a reset-output intervention and two provider-register controls pass. Actual reader/scanner/null-texture SetUV execute; one exact caller-specific 1,000-byte scratch allocation and its paired free are modeled. First malformed uninitialized outputs and missing terminators are refused, not manufactured into successful loads. No shipped-content or descriptor-publication claim.

- **Static-shadow plane admission corrected, October 1.** RayHitsTriangle `004ee410` accumulates its numerator D + Z + Y + X, not the reconstruction's D + Y + X + Z. Sequential updates to D change only six operand bytes, preserving 22 relocation identities and 33 other callable sections. All 28 exact controls remain. Fresh native execution from entry through `004ee57d` compares 650 finite triangle/endpoint fixtures at PC24/53/64: 1,950 cases per image. The old source has 472 parameter/intermediate discrepancies and 152 admission-decision differences; the correction has none. An inverted threshold branch changes 1,269 decisions. This stage stops before intersection and angle processing, executes no math helper, and does not establish complete hit results or visible shadows. The whole 1,168-byte section stays unmatched with 38 differing positions.

A subsequent full native entry/return run admits the actual acos and finite-domain CRT precision handlers. Across 2,025 cases, including 75 ordinary inside/outside/edge/vertex/parallel controls, the old source differs on 100 final BOOL results; the correction differs on none and all output records agree. Inverting the final angle test changes 913 results; an unadmitted inverse-trig target refuses before output. Explicit image-initial CRT state, finite nonaliased geometry and masked precision modes remain limits. Nonfinite/domain/unmasked paths trap; there is no live rendering or arbitrary-input equivalence claim.

- **Walker slow movement executed, October 1.** All four original directional bodies and fresh candidates agree in 408 native finite cases at PC24/53/64, using actual RTTI-bound ground and AddVelocity helpers and the original Euler constructor, with no providers. Zero-initial-velocity paired cases confirm quarter scaling for Forward/Backward/Left (135 pairs) and unchanged right strafe (45 pairs). Airborne/active-dash early-return cases, full object/input checks, ABI/x87 guards, a scale mutation and bad-vtable/truncated-input refusals pass. Physical input, charging, dash activation and subsequent movement remain untested. The other three directional sections are exact; Right retains ten differing positions and gets no new credit. Three const-reference source forms are rejected because all leave that miss unchanged.

- **Mesh-part destructor boundary, September 30.** Retail calls the five-byte destructor wrapper `004a51f0` from `CMesh::~CMesh` at `004a5141`, but calls `FreeResources` directly from `CreatePolyBucket` at `004ae40e`. Declaring the destructor in mesh.h and defining it before its callers in MeshPart.cpp reproduces both choices without inline pragmas or artificial references. The complete mesh destructor and wrapper now match; the already exact bucket creator is preserved. This establishes the compiled call boundary, not the lost header's original spelling or placement. The same recheck corrects the stale `004aa3f0` annotation: sound and mesh callers pass standalone 48-byte matrix values, proving first-column extraction. It now annotates the reconstructed `FMatrix::GetColumnX`; its body remains a near miss, and an original method name or folded CMeshPart alias is not proven. Unplaced diagnostics now display an explicit symbol instead of the unrelated next source definition. The 26 authored matcher tests pass. The full build has 5,005 exact functions, preserving every earlier matched address and symbol.
- **Virtual-table conflicts re-derived and corrected, September 30.** Five omitted overrides changed behavior: destructible-segments controller slot 9 returns TRUE (inherited by HiveBoss), WarspiteDome slot 8 returns TRUE, GillM and ThunderHead slot 10 return FALSE, and E3LevelSelect slot 1 searches its 50-by-6 level grid rather than doing nothing. RTTI and the actual slots identify the owners; the tiny target bodies and the complete shared `00460490` body establish the implementations. Seven additional empty/success overrides give distinct class method identities to the separate retail addresses used by Trees, FrontEndVideo, Main/DemoMain, DevSelect, ScreenPos and Unknown pages. These latter bodies are behaviorally identical to their base implementations; one global symbol still cannot resolve to two addresses. This is a reconstruction of the observed table layout, not proof of unreleased header spelling. The full build preserves all 5,003 exact functions, removes all eight previous conflicts and validates 890 of 892 emitted table copies. The remaining source names differ from their retail RTTI names: source CTexture is retail CDXTexture (`005e59a0`, exact constructor relocation `00556cf3`), and source CAsyncCache is retail CXBOXAsyncCache (`005e4f5c`, constructor relocation `00539c8a`). The texture's non-polymorphic +8 base is retail CTexture, called CTextureCore in the reconstruction. Fresh constructor, hierarchy and slot reads identify these tables; the exact-name checker intentionally does not count them. These are source-name mappings, not absent or multiply identified retail tables. Exact constructor code is separate from correct table contents. The old checker published table verdicts before all symbol constraints were known, so its earlier per-table matches overstated their consistency. It now finalizes after table discovery, binds each admitted table to its RTTI address, and refuses malformed or unexplained slots and unknown secondary-base offsets. Twenty-five authored matcher tests and 17 differential-harness controls pass.
- **ReadOptions remains unmatched, but its inspected decisions agree in 50 bounded cases.** The original reader and the frozen 1,072-byte reconstruction execute separately at `00420d70`; every relocation is anchored to retail immediates/calls. Mode-key truncation, duplicate/absent/zero modes, adapter/device selection, raw sound settings, callback order and the `source + 0x56` return agree under declared tweak, preset, language and audio models. Negative controls refuse bad execution boundaries/dependencies and detect suppression of sound restart. This neither resolves the shorter emitted body nor establishes buffer admission or complete save/device compatibility; see the existing Onslaught save/settings contract for exact scope and reproduction. The October 1 follow-up runs 217 complete-reader native cases with the actual `CTweakSLONG::Set` (`00528ad0`): all authored global/input/ABI/x87 observations agree. Integer-to-binary32-to-qword-low32 conversion changes 145 cases, including round-to-nearest 16777217 to 16777216 and 2147483647 to `80000000`. Reset compares that converted result to the old live value; branch inversion changes 216 outcomes while the device-null control stays unchanged. All 47 exact file controls survive. Preset/language/audio reload still use explicit recording models; these extremes are not evidence of normal menu reachability or complete compatibility.
- **September 30 near-miss corrections, reproduced on the integrated tree.** Box distance (`00479770`)
  requires parentheses around the square products; preserve the original triple-outside `Z+Z` term.
  Collision response (`004264a0`) reuses the collision-level local for the later collision-test result;
  this preserves retail admission, movement and hit callbacks and closes its comparison instruction.
  Actor movement (`004015e0`) binds the position to a local vector reference before adding velocity.
  These are exact emitted bodies and relocations, not proof of original variable spelling.
- **Mouse recentering (`0042da00`) was not solely a stack-layout miss.** An adjacent `POINT` snapshot
  closes the layout, but relocation checking then rejects the old reciprocal of `1.7f`. Retail constant
  `005d97c4` is float `0x3f169697`; compute `1.0/1.7` then round to float. Reciprocating `1.7f` yields the
  adjacent `0x3f169696`. The corrected 272-byte section and every relocation match; Controller.cpp is
  32/32 in the focused check. This establishes the compiled arithmetic, not physical input acceptance.
- **Pointer-set growth (`004241f0`).** Keep growth-disabled failure separate from the subsequent capacity
  loop in `MakeRoom`. Nesting the loop under the size test produces a different comparison; merely
  reversing that test lets VC6 fold away a retail gate. The flattened guard matches `append`; a full build
  preserves all previous matches. Declaring the insertion source immediately after its destination, before
  the stopping pointer, also closes `insert_at` (`00424260`, 256-byte section and both resize-call relocations).
  `remove` still differs by 31 bytes; a guarded-copy lead remains eight bytes away and is not accepted.
- **Differential checks are bounded falsifiers.** `tools/equiv.py` executes each body at the retail address
  in separate emulator images, eliminating a false self-call/address-alias divergence. It observes x87
  return/control state and callee-saved registers, and refuses unsupported ABI/stack observations,
  unresolved dependencies, faults and incomplete coverage. The matched `00411b70` control completed
  45 trials with all four blocks reached. That is sampled agreement under stubs, not an equivalence
  proof. Authored negative controls cover equality boundaries and earlier false-agreement paths.
  The byte matcher also refuses a compiled prefix shorter than the admitted retail body before it can
  infer relocation targets; the full September 30 build found no credited short sections.
- **The scale-menu highlight (`004a37c0`) now matches.** Keeping its two alpha products in separate float
  locals prevents VC6 from combining them, preserves the two retail DWORD constants, and matches the entire
  848-byte section and all 42 relocations. This is an arithmetic/source correction, not a visual acceptance run.
- **Named-mesh getter (`004183f0`): secondary-interface `this` matters.** Both named-mesh RTTI records place
  `IRenderableThing` at complete-object +8; its slot 11 reads `[ecx+0xd8]`, which is `mMeshNo` at complete-object
  +0xe0. The render-factory call chain supplies that secondary pointer. An ordinary inline getter matches the
  full section; the old movement-timer/layout warning was incorrect.
- **Elevation's float argument (`004704a5`–`004704af`).** Use the pinned VC6 `asinf(float)` wrapper in `FVector::Elevation`, not a cast on the result of `asin`. Retail's free-camera inline copy keeps magnitude on x87, rounds `Z/m` to float, reloads it and calls `_CIasin`. The old reconstruction rounded magnitude first and passed an unrounded quotient. Twenty-four isolated finite-column cases (chosen PC53/PC64 nearest modes) reproduced retail's call argument with the new wrapper; the old code differed in twelve, with exact-axis controls agreeing. Only the arithmetic slice ran, stopping before asin: no live camera, FPU mode or visual claim or proof of the original header spelling. The standalone `0040d1a0` still matches; the header-only complete rebuild preserved all 5,002 earlier matches and gained none. Restoring Stuart's original `FMatrix m = FMatrix(...)` in `ToggleFreeCameraOn` then closes its frame/stack differences: the prior reconstruction split declaration and assignment. Together these changes match the whole 416-byte section and all relocations. All 89 checked game.cpp functions and seven vtables match; the final full build adds `00470430` without losing any earlier function. This restores released caller source rather than adding a compiler-shaping workaround.
- **Three previously matched bodies were missing from the score's table.** `EnumAxesCallback` (`00513040`,
  219 bytes), the reconnect-interface constructor (`00527950`, 16 bytes), and the landscape-view constructor
  (`00544710`, 88 bytes) now have specimen-backed table corrections. They add three functions and 323 bytes to
  both numerator and denominator; they are not new implementations. The address-based denominator also still
  contains 32 six-byte import thunks (`0055d5e0`–`0055d69a`), which are linkage glue, not missing gameplay methods.

- **How a value is read decides reordering, copies and folding** (September 30):
  - VC6 moves a load above a preceding store only when it can prove the two do not alias. A direct read of another
    field of the same object is proven distinct and is hoisted; the same field read through an inline accessor on a
    member object is not, so the source order stays. `CVM::CallEvent` (`00539990`) and `CallFunction` (`00539a60`)
    match with `mStackBase = mStack.Size();` after `mPC = 0;`.
  - Reading a just-stored member back through a `const T &` reference keeps retail's register copy of the stored
    value and a test the compiler would otherwise fold: the range check in `CPolyBucket::AdvanceLineSearch`
    (`004d5650`) and the test of a flag just cleared in `CRenderInfo::Apply` (`00550d50`).
  - The tells: a register copy of a value that was just stored (`mov eax,ebx` before a compare), an unfolded test of a
    known constant, or a load retail keeps in place that ours hoists. Try a reference read, a reference-parameter
    helper or an accessor for that member first. The reverse also holds: if retail hoists a load that ours keeps in
    place, ours may read through an accessor or pointer that retail did not.
  - An expression tree can pick operand order: `i < len + 1` for the loop bound where `size = len + 1` gives
    retail's `[ecx+eax]` store address in `CSpawnerBasedOn::Apply` (`00439e70`).
  - VC6 reuses a register that holds a known 1 (a masked flag that tested equal to 1) in place of the constant 1 in a
    later compare or return only when that register is live across a call. An early read that keeps the value live
    does it; a dead or unused copy is removed before register allocation and does not. Reading `mForThing` into a
    local before the tests matched `CCollisionSeekingInfantryBloke::Unknown8` (`00425a10`).
- **Value copies and pointer locals** (September 30):
  - A member read into a plain value local before a call changes the scheduling of what follows the call where a
    reference or a direct read does not: `WCHAR *name = mCurrent->mName; mPortrait = GetPortrait(name);` matched
    MessageBox TryAdvance and `char *pathName = path->mName;` before `_stricmp` matched
    WaypointManager FindNearest. Keep such a local on the line it replaces so no later
    `__LINE__` moves.
  - Where retail keeps a member's address live across a call (`lea esi,[this+N]`, then `[esi+4]`), bind it in a local
    pointer: `CParticleEffectLink *link = &mEffect;` matched CHazard::Init (`0047e530`) and brought retail's zero
    register with it.
  - A single-use pointer local is forwarded to `this+N` but still advances the scratch-register rotation, so it fixes
    a one-instruction addressing difference a direct member store does not. It reproduces
    the compiler's shape, and the source comment says so.
- **Retail's maths.h brackets each product in its sums** (September 30). Same code, but the parentheses are a value
  barrier and IL tuples, so they move where the `faddp` lands among integer code, the scheduling regions and the
  inline budget:
  - `MagnitudeXY` and `MagnitudeXYSq`, `sqrtf((X * X) + (Y * Y))`: 5 matches (CMech::SetAnimMode
    `0049fba0`, CSquadNormal `004e84e0`, CSubmarine::Move `004eee80`, IScript UpdateWaypointFollowing `00538470`,
    CInfantryUnit::SetAnimMode `00489090`), which no tuple count or term order had moved.
  - `MagnitudeSq`; `Magnitude`, `Normalise` and FMatrix × FVector, each
    row `(R.X * v.X) + (R.Y * v.Y) + (R.Z * v.Z)`: 24 matches on 5,063 and near-miss bytes down 1,874. The old FMatrix × FVector
    order `X + (Z + Y)` had been tuned to the unbracketed helpers.
  - Cofactors and Determinant bracket each product too: the determinant's copy
    `0049bc40` matches. GetColumnX declares its locals `z, y, x`, the order its out-of-line copy `004aa3f0` loads them
   .
  - The brackets cost inline budget. With them `Normalise` tests `if (m)`, not `m != 0`: the cheaper test keeps
    CDXFrontEnd::RenderParticles (`00540c30`, Stuart's code as released) inlining SetLightEnable(2) as retail does.
    Normalise through `Magnitude()` or `sqrtf(MagnitudeSq())` is worse (about +2,000 near-miss bytes), and so is every
    partial bracketing of its sum.
  - The dot product is bracketed too: it matched DeclareOnGround `0040c750` once CMap::Normal's forwarder was in, and
    retail's one out-of-line copy (`0040d180`, which PointInsideTrianglePrism calls) sums Z, Y, X as it does. Not bracketed: `InvMagnitude` (no effect either way); the cross product (partial brackets
    matched MakeFromDirection `0049e4b0` before Normalise was bracketed, then cost CFallingTree's constructor
    `004f5f60`); elements of FVector `+`, `-`, `*`; FMatrix × FMatrix; brackets
    around a returned constructor call.
  - Measured on the new header and rejected: FMatrix × FMatrix with bracketed
    products (-10), built element by element or from named rows (-5); FMatrix × FVector re-associated,
    `(X) + ((Y) + (Z))`, `((X) + (Y)) + (Z)`, `(X) + ((Z) + (Y))`, whole rows bracketed or one product bare (-9 to -21,
    though each bare-product form gains UpdateAutoAim `0040b120` or the Transpose copy `004c5280`); Magnitude
    re-associated (-10 to -17); the dot product bracketed (no change then; +1 after the CMap::Normal forwarder); FVector's constructor as assignments (no change) or
    through `Set` (-78). The four Stuart-verbatim near misses that differ only in maths.h scheduling or term order
    are open.
  - Also measured and rejected: MakeRotationF with each product bracketed instead of the tuple form (-4 to
    -6), NormaliseIfLong's sum bracketed (no change); and per-file compiler flags: the 13 files with the most near misses
    compiled with /Ob1, /O1, /G6, /Op or without /QIfist all lose matches (/G5 is identical to the default).
  - Release ASSERT/SASSERT: `((void)0)` and `{}` change nothing, `((void)(x))` loses CGame::RestartLoopRunLevel
    `0046dc30`; the empty definition stays.
  - Historical particle lead, now resolved: CParticleManager::ProcessParticle (`004cb920`, 266 bytes)
    calls FVector's constructor out of line inside the inlined `operator*`. Flat caller-budget and
    unlink/depth probes did not explain it. The October 1 complete match above demonstrates nested
    frame/position ownership reducing the constructor's budget; the earlier inference that inline
    budgeting could not explain this function was too broad. Other constructor-call gaps still need
    their own evidence; the historical count of 44 is not a current queue.
  - A header change like this moves every function tuned on the old form: re-measure near misses on the new header
    and drop probe forms that no longer pay (CTentacle::GetTargetablePos `004f0d90` matched through a reference read
    under the old FMatrix × FVector and is 12 bytes off under the new one).
- **`__FILE__` spells the source as retail's build named it.** The allocation and assert strings are the file names
  VC6 was given: `C:\dev\ONSLAUGHT2\Unit.cpp` and `...\mapwho.cpp` (our unit.cpp and MapWho.cpp were renamed, which
  matched CUnit::UpdateTransform `004fc4e0`), and for a header the spelling of the `#include` that opened it in that
  object (retail has `array.h`, `monitor.h`, and both `MissionScript\..\Monitor.h` and `...\monitor.h`). A function
  whose only difference is such a string shows as `relocations` with the note "string at ... differs".
- **Bytes can coincide while relocations swap**: bracketing `HUD_OFFSET_X + HUD.mViewportX + 165.f` reorders the `fld`/`fadd` so that the two loads' bytes line up while the globals they name are swapped.
- **Static names decide their layout**: VC6 lays uninitialised statics out in an order its symbol
  table takes from their names, not their declarations, and loads a `bool` global as `mov eax,[m]; and eax,0xff` on a
  4-byte boundary but as `xor edx,edx; mov dl,[m]` off one. Our names are labels, so renaming DebugLog's `sDump*` to
  `sScreenDump*` put the flag one byte past its neighbour as in retail and matched ProcessScreenDump `00441b80`. When a
  near miss differs only in how a byte or word global is widened, compare its retail address mod 4 with ours.
- **Two symbols, one folded body (ICF)**: when retail calls a small function out of line from some
  callers in a file but expands it in others, and neither the cap nor the budget explains it, or when two identical
  `case` blocks stay apart (VC6 merges them unless their callees are different symbols), retail's source had two
  identical functions that the linker folded into one address. We declare a second copy under a reconstruction name:
  CRoundData::IsBallistic beside `0040d0f0` (the range and aim callers use it) and CText's second lookup
  beside `004f2580` . Their real names and homes are unknown; the comments say so.
- **One tail after an if/else**: where retail's found and created paths end in the same store and
  return, write them once after the `if/else` (`if (!v) v = new ...; else v->mRefCount++; if (!unique) ...; return v;`);
  VC6 threads that tail into each path itself (CVBufTexture::GetOrCreate `00501280`).
- **Verbose spellings are inline cost**: `if (c) return TRUE; else return FALSE;` in the four CanStep inlines
  and a five-point stencil written with aligned `+ 0` terms in ClearCross cost the nodes that make retail's callers
  expand the first 8 of 24 sites and call the rest (NavigationMap Flood `004be420`, Rasterize `004bd5c0`).
- **Outcome flags give retail's exit-block order**: nested `if/else` lays
  the innermost `else` out first, so the three waypoint-step Unknown8s came out fight, reschedule, stop where retail
  has fight, stop, reschedule. Two flags set on the way down (`fight`, `noWaypoint`) and one final `if/else if/else`
  chain in retail's order do it: VC6 threads the flags away and the chain's leaf order becomes the block order (shape
  37, 35 and 23 to 0 at CUnitAI `004feac0`, CDiveBomberAI `004457d0` and CGroundAttackAI `0047b570`). All 216
  if/else/early-return renderings of the decision tree collapse to four layouts, none of them retail's.
- **Block-scope locals share slots; a function-scope local does not**: one `float fraction` declared at the top of ClipSegmentAgainstAABB3D `00478160` kept a frame slot of its own, where retail shares the slot with `y` in some branches and `z` in others. Declaring `float fraction = ...;` inside each branch matches, because the locals of sibling blocks share slots.
- **A byte-wide `not` and `movsx` is a branch that sets FALSE or TRUE**: `visible = !(flags & 1)` compiles to `not eax; and eax,1`, while `if (flags & 1) visible = FALSE; else visible = TRUE;` gives retail's `not dl; movsx eax,dl; and eax,1` (CStaticShadows::UpdateVisibility `004ebfb0`; CSimpleBuilding::ClipToGround `004dfcb0`'s `if (IsDying()) return FALSE; return TRUE;` is the same idiom). No other retail function has the pair.
- **Try every order of a block of independent statements**: in CGridIndices::Build `00440ad0` the source order of six index stores decides where the scheduler puts three LEAs. All 720 orders compiled as 720 small functions in one file (2 seconds; It suits near misses whose remainder is the order of independent statements; it did not help ltshell `00513600`, mapwho `00492860` or HeightField `0047e8e0`.
- **An accessor can decide registers, not just budget**: reading the parts through
  `mMesh->GetPart(i)` matched CMeshPart::LinkDamageLevels `004b1d30`, where member reads left the register
  allocation and the schedule different.
- **Named locals and copy-initialisation spend budget**: in MCWarspiteDome::GetPartTransform
  `0049efe0`, dropping the `f` and `m` locals freed enough budget for retail's out-of-line calls to come back (`now`
  and the barrel's second matrix), and copy-initialising the recoil vectors (`FVector old = FVector(...)`) spent a
  little more, so both constructors are called as in retail. MCWarspiteDome.obj matches 28 of 28.
- **MakeRotationF constant-argument widths, rechecked October 5.** Current MCTentacle::UpdateBone `0049d280` calls `rot.MakeRotationF(0, 0, -1.57f)`. Its stock and retail trig loads both use QWORD zero and the double representation of the already-rounded float `-1.57f` (`-1.5700000524520874`). The former claim that these loads distinguish `(float)cos(double)` from the current `cosf` source is unsupported: current wrappers already emit them. Original spelling remains unknown and the complete UpdateBone still fails.
- **An earlier reference decides the operand order after Normalise**: VC6 orders a commutative x87 operation's operands by value
  rank, so after Normalise's `fdivr` a component `C *= m` is emitted reciprocal-first (`fld st(0); fmul [C]`) when
  `C`'s value was referenced before `m` existed, and `C`-first (`fld [C]; fmul st,st(1)`) when its first reference is
  in Normalise's own square root. Retail uses both forms about equally (41 and 38 sites). The earlier reference can
  emit no code: a dead read; a budget-refused constructor whose `this` is the vector, which leaves its first statement
  (`X = x`; HandleLocks `00406560`); or a return forwarded through an inline wrapper. Retail's map.h has
  `FVector CMap::Normal(const FVector &pos) { return CHeightField::Normal(pos); }`: Stuart's callers still call
  `0047ec60` with their local as the hidden result, but the result's X now counts as referenced, which matched Slide
  `00413b90` and CBattleEngineWalkerPart::Move `00413760` and took DeclareOnGround `0040c750` from 18 to 13 bytes
  (its integer-copied `velocity` stays X-first, as retail's does). While a vector is memory-resident, a component read
  as a float afterwards is reciprocal-first too; through a pointer or reference every component is. The reconstructed
  NavigationMap calls `MAP.CHeightField::Normal` directly, because the wrapper's inline site costs two of its matches.
- **A copy where retail reads a value**: a by-value copy of a value just before its use moves frame slots and scratch registers without emitting code, and found six matches in an evening. Each copy points at a natural form, which is what to commit: the time scaled in its own statement, `t *= 20.0f;`; `GAME.FloatRandom()` instead of the spelled-out random factor; SetWorld's by-value arguments as locals; the aim copied into a `target` local; A 16-byte FVector copied from a static through a local is carried in four registers instead of three.
- **Split an `||` whose branch assigns**: `if (A || B) { portrait = i; found = TRUE; }` as `if (A)
  {...} else if (B) {...}` gives `portrait` two assignments in the loop, which ranks it above the parameter `name` for a
  callee-saved register as in retail (CMessageBox::GetPortrait `004b7ab0`). A dummy read of the variable retail keeps in
  a register flipping the allocation is the diagnostic; the split is the natural source.
- **A switch on consecutive values can be an offset test**: the loop-head registers of
  CCredits::RenderCredits `0051a030` follow the IL shape of a section dispatch further down; `int kind = section - 2;
  if (kind != 0) { switch (kind) {...} } else <case 2>` gives retail's `sub eax,2; je; dec eax` and its registers where
  `switch (section)` cannot. A grammar over all 68 non-matching functions with a switch found no other case.
- **A near miss can be a wrong reconstruction**: matching corrected two behaviours. CDropship::Move
  `00447120`: at its top speed the dropship flies along its heading at its current speed, `FVector(0, speed, 0)` (after
  `fcompp` retail's stack holds the speed, `00447842..00447865`), where our text used the limit. CMCMech
  ProcessMovement `004988b0`: retail tests `force` in both places and never reads `fixed_step`, so a forced rebuild
  takes the 0.05 s step. CHud::RenderTargetIndicator `00482590`: retail tests
  `stricmp(mesh->GetName(), "m_thunderhead.msh")` and lights and turns every target except the Thunderhead, which takes
  the imposter; ours used strstr and the inverted branch. A sweep of differing call lists and immediates finds these.
- **A unit vector where retail builds one**: retail computes a heading or ground-tilt axis as `ori * FVector(0,
  1, 0)` (pushes of `0x3f800000`, 0, 0 before the FVector constructor `00401ec0`) where `ori.GetColumnY()` builds no
  constructor; it matched CMine::Init `004ba150` (with the side copy taken where retail loads it) and moved
  CGroundVehicle::Move `0047d1c0` (136 to 27), CAnimal::Move `00404210` and CCarrierGuide `00421f90`. A scan of all near
  misses for that signature found no other site our source spells differently.
- **A parameter that retail never writes**: CPDSimpleSprite::SetUV `004c0940` stores its case values into a new local that lives in the home slot the parameter frees; assigning the parameter itself kept it in a register. Its missing `default` is retail's too: other sizes leave the shift unset.
- **Some edits only help in pairs**: CDXBattleLine::BuildMesh `0053a5e0` matched only with both
  counts read into locals interleaved with their stores; either alone left the score unchanged, which is why greedy
  searches missed it.
- **An inline body in a widely included header can move unrelated code**: adding any inline member with a
  body to Equipment.h or weapon.h swaps two loads in CPDTimeline VFunc_10 `004c2640` (a tie-break in IL numbering);
  declarations, typedefs and comments change nothing. Declare a new accessor in the class and define it inline in the
  one .cpp that uses it (CWeapon::Fire `00506010`), unless a full check shows the in-class form moves nothing (mesh.h's
  key accessors for InterpolateKeys `004b0d00`).
- **Explicit comparisons are inline nodes.** `m != 0` against `if (m)` (Normalise above), `unit != NULL` putting a
  helper over the plain inline cap so it is called out of line as in retail, and `strnicmp(...) == 0` in FindTexture are the same code with different node
  counts. When a budget or cap is off by a few nodes, the spelling of a test is the first natural knob.
- **Scheduling regions**: VC6 schedules a long basic block
  in regions of about 82 instructions and never moves an instruction across a region edge. Code earlier in the same
  block counts toward the region, and code in an earlier block does not. Forms that add IL tuples without adding
  instructions move the edges: parentheses around a whole expression or right-hand side (+1), `cosf`/`sinf` (+1 per
  call), an inline wrapper returning through a local (+2); natural grouping, copies, references, `this->` and
  declare-then-assign add nothing. Retail's `MakeRotationF` expansion appears to carry about 18 more tuples than
  ours (the camera near misses in FEPBEConfig, FEPWingmen and MPStart, `CTentacle::GetHeadOri`, `CActor::Init`);
  its form is still open. Not every placement difference is a region edge: in `IScript::UpdateWaypointFollowing`
  (`00538470`) the flag test stays before the magnitude's `faddp` with 0 to 24 extra tuples in front of it, and no
  tuple-only form of `FVector::Magnitude`/`MagnitudeXY` moves that family.
- **Tail copies and spills follow the source's nesting**: VC6 copies a small tail (a couple of stores and the
  epilogue) into each failing test of a final check, and the copies' layout follows how the tests are nested. Nested
  `if`s give retail's three copies in NavigationMap StepDown (`004bed30`); an `&&` chain lays them out differently.
  The same choice decides spills: `if (a.MagnitudeSq() > r) { if (b.MagnitudeSq() > r) {...} }` keeps both squared
  sums on the FPU where `&&` spills one term.
  Writing a trailing store in both branches reproduces an extra epilogue copy.
- **Hoist or sink the statements both branches share**: CFEPLanguageTest::ButtonPressed `0051c090` differed only in two
  registers (retail's zero constant in ebx and `old` in edi, ours the reverse) and matched once the DOWN case's two
  statements common to both branches (`mScroll = 0; FRONTEND.PlaySound(FES_MOVE);`) were written once after its
  if/else; the UP case keeps both copies, as retail's code shows. The scan tries hoisting 1..k common trailing
  statements out of every braced if/else and sinking the one or two statements after one into both branches.
- **Give a derived counter its own variable**: `Init(i + 1, 3 - i)` made VC6 derive the count from `i` and keep a callee-saved zero in ebp across the first allocation's checks; `SINT detail = 3; ... Init(i + 1, detail); detail--;` matches CLandscapeView::CreateMipLevels `005447e0`. A stray function-wide zero register can mean retail kept an expression of the loop index as an induction variable of its own.
- **A shared tail needs one return**: `if (n > 0) Ask(); else { PlaySound(); Message(); } return
  true;` lets VC6 keep one copy of the message tail and jump back to it from the other branch, as retail does
  (FEPDevSelect::UseDevice `00458710`); a `return` in each arm keeps the later copy instead.
- **Accessors instead of members**: reading a unit through `CGuide::GetUnit()` at every site (or `GetPos()` for `mPos`) spends inline budget and changes the value ranks where a direct member read does not: InfantryGuide FindTarget `0048ace0` and CFeature::Move `0044cc10` match, and the guide slot-3 functions move a long way toward retail. It is not universal (MechAI's `GetForUnit()` was worse). With them `leader->GetAllegiance()` matched CUnitAI::Unknown4 `004ff4f0`, the accessor's expansion rotating the scratch registers to retail's, and CMine::Move `004ba4d0` went from 12 to 6 bytes; `mMesh->GetPart(i)` matched CMeshPart::LinkDamageLevels.
- **`fmodf` is one tuple, like `cosf`**: math.h's inline `fmodf` adds one IL tuple over
  `(float)fmod(...)`, which moves a scheduling-region edge (CFEPCommon::RenderSmallBEALogo `00452df0`).
- **A double local beside a float call**: `double yaw = d.Azimuth();` passed to AngleDifference(float) loads the current yaw first and keeps the heading in memory, as retail does, where a `float` local reverses them (CBomberAI `00416590`, CDiveBomberAI `00445f40`; the round trip through double is exact).
- **Strength-reduced loops**: where retail sets a loop's pointer up after the loop test (`jle`,
  then `mov esi,ebp`), the source indexes (`for (i = 0; i < n; i++) SAFE_DELETE(pieces[i]);`) and the pointer is the
  compiler's induction variable. A user pointer (`p = pieces; ... p++`) is set up before the test (DXMeshVB
  DeleteDeviceObjects `0054d3f0`).
- **Inline `cosf`/`sinf` leave a signature**: before `fcos`/`fsin` retail copies the argument through an integer register (`mov edx,[obj+off]; mov [esp+N],edx; fld [esp+N]; fcos`), the float-parameter copy of the inline `cosf`; `(float)cos(member)` loads the member straight onto the FPU. MakeRotationYawF uses `cosf`/`sinf` (CTree::Init `004f6080`); pitch and roll with `cosf` lose (the DrawDebugStuff declaration tie, CMCMech::UpdateBone -95), so retail wrote them differently from yaw.
- **Evaluation order around an out-of-line constructor**: an accessor argument is evaluated before an
  out-of-line FVector constructor, while retail reloads the member after it; only a direct member read gives that
  order (CSquadNormal TeleportOrientation `004e96f0`, with CNormalSquadMember a friend of CNormalSquad).
- **Scratch registers are handed out round-robin**: per function,
  VC6 gives successive register temps eax, ecx, edx, eax, ... and the counter survives calls and later blocks. A load
  that is pushed, an address taken for a call (`lea`) or an arithmetic temp advances it; a compare against memory, a
  call result, a constant push or store, and an unused inline declaration do not. So a near miss whose registers agree
  up to some point and are consistently rotated after it has one temp more or fewer before that point (mod 3).
- **The zero register needs live zero uses**: retail's `xor ebx,ebx` with `cmp [m],bl`, `push ebx` and
  `mov [m],ebx` appears once a function has about two more live zero uses than ours (zero stores, zero arguments or
  returns). Dead stores, unused `= 0` locals, explicit `== 0` compares and duplicate stores do not count. Where retail
  has a zero register and ours has immediates, look for two missing live zero uses in our source.
- **Parentheses are a value barrier for FPU code**: a parenthesised subexpression is kept as a value. `a +=
  (l->mNode->mThreat[0]);` loads the term and adds it below the stack top (`fld; faddp st(2)`, InfluenceMap
  CalculateInfluence `0048c3b0`); `(p.Y -= 44.f)` used as a value stays on the stack; and dropping them in
  `(y - 18.f) - s.Y` lets VC6 load `y` after the first push (DXBattleLine Render `0053abe0`). A named result also
  changes addressing: `FVector n = MAP.Normal(pos); n.Elevation()` addresses the stack local instead of the returned
  pointer (NavigationMap ClearSteep `004bc8d0`).
- **MakeRotationF carries retail's scheduling tuples**: `cosf`/`sinf` and bracketed values emit the
  same code as `(float)cos` and bare expressions but add about 22 IL tuples, which moves the scheduling-region edges
  after an inlined rotation to where retail has them: 5 matches (CActor::Init `004011e0`, CComplexThing::Init
  `004f3fd0`, CFEPGoodies::ButtonPressed `0045cde0`, the segments' GetPartTransform `00494ce0`, IScript
  TeleportOrientation `00536a60`) and ten near misses much closer, with CBattleEngineJetPart::Move (`00410c50`) 68
  bytes worse. The count is pinned from both sides (one tuple fewer gives 3 matches, more trade them for PanCamera or
  StrafeRight). The spelling reproduces the tuple count, not retail's text.
- **FPU latency gaps hold at most two integer instructions in retail**: in inlined Magnitude/MagnitudeXY
  `fmul ... faddp` gaps, ours packs up to four independent integer instructions into the first gap where retail puts
  two in each, and retail never places a dependent load and its consumer inside such a gap. No /G option or c2
  switch changes it; moving the statement that feeds the integer instruction does, within limits (CExplosion::Hit
  `0044bf10`). Open; likely the region model at a finer grain.
- **Stack slots and FPU values**: VC6 packs a dead named FVector into a later aggregate's slot; an array
  (`FVector ends[2]`) keeps them apart where two locals share, which matched `CMCMech::GetFootHeight` (`00499bc0`).
  The value of a parenthesised assignment stays on the FPU stack (`float dy = (p.Y -= 44.f);` squares it with
  `fld st(0); fmulp`, `AddOverlayPoint` `0053b5f0`); without the parentheses VC6 reloads it. For a sum of two HUD
  fields VC6 loads the right operand first, so retail's order reads `mViewportY + mViewportHeight`.
- **VC6's inline decision, measured**. This supersedes the budget bullets below, which are
  observations it explains.
  - Each callee has a fixed size cap: a plain function (auto-inlined under /Ob2) expands only up to about 105
    expression nodes (roughly one per operator, operand, call and statement), an `inline` or in-class one up to
    about 6.3 times that. The caller, the site's position, the number of sites, loop depth, constant arguments and
    definition order do not change it. A callee over its cap is a call everywhere.
  - Each caller then has its own budget, about max(700, 2.2 x the caller's own nodes). A second caller in the same
    file is unaffected.
  - Sites are spent first-in-first-out over the top-level sites in source order, then last-first over the sites
    exposed inside expanded bodies. So the later top-level sites and the earlier nested sites stay calls.
  - Test: when retail calls a matching callee that ours expands, add 1-3 trivial nodes to a copy of the callee. If
    that pushes it out, retail's source was just over the plain cap. `strnicmp(...) == 0` for `!strnicmp(...)` and
    `strlen(n) != 0` give the same code with more nodes. That fixed `CMesh::FindTexture` (`004aa410`; `CMesh::Load`
    15,663 to 14,899 differing bytes) and `ClearDuplicateBinding` (`00454e90`; RemapKey 1,654 to 1,204 and
    RemapKeyTrap 1,278 to 883).
  - A caller's own code buys budget, so "needs more budget spent elsewhere" is a statement about the caller's own
    size.
  - A block whose operators retail calls out of line while a later copy of the same code expands them was a nested
    body. Nested sites are denied before later top-level ones, so the first block belongs in a static helper.
    gcgamut RenderThings (`00476fe0`) gained RequestShadow's out-of-line copy (`00477b70`) that way. A `static`
    function with exactly one call site in the file is judged against the inline cap, not the plain one; with two
    sites it is back to the plain cap, so a helper's call-site count can flip its caller's code.
  - Same-code source forms the node counter sees: a brace block ~2, a cast ~1, `+ 0` ~2, an unused local
    ~3, a dead store ~3, a local copy, self-assignment or return through a local ~4, `if (0)` ~12. One brace block per
    triangle put `InitBoxTriangles` (`004ac000`) just over the plain cap, so `TestSweptSphereAgainstBox` (`004ac140`)
    calls it as retail does.
  - A declaration in a loop condition spends less than declare-then-assign: rewriting nine
    `T *x; while (x = list->First())` loops as Stuart writes them, `while (T *x = list->First())`, changes no code
    but freed the budget for the earliest nested site, so `UPhysicsManager::ClearAndFreeAll` (`00510a90`) matched
   . The same rewrite made `~CUnitData` (`005110f0`) worse, so it is a lever, not a rule.
  - Retail's direct calls to `00406040` from the compasses are `CBattleEngine::GetInitialLife()`, a non-virtual
    accessor in Stuart's BattleEngine.h whose body the linker folded with `GetMaxLife` (virtual slot 78): using it
    took Compass (`00427210`) from 1,351 to 1,241 differing bytes and DXCompass (`0053c510`) from 1,609 to 1,583
   .
  - Raw node costs of maths.h's forms: FVector constructor ~26, `+` ~34, `* float` ~30,
    `+=` ~22, dot ~26, FMatrix*FVector ~108 in every grouping (~120 with a named result), FMatrix*FMatrix by element
    ~424, `FMatrix /=` ~72 per element. Grouping and term order cost nothing; named results and extra statements do.
    No single change to maths.h's forms improved the budget test set (the core, `CMesh::Load`, `004b5330`,
    `004c5d50`, `005528b0`): the remaining budget gaps are differences in retail's callers, not in the header.
  - Open: RemapKeyTrap (`00456190`) inlines 5 of its 16 `SetControlBindingInput` sites in retail, one per switch
    block (source sites 4, 6, 9, 12, 14). Every synthetic mimic spends in source order, so retail's source probably
    differs at those sites.
- `FVector::operator-=` returns void, like `+=` and `/=`: its out-of-line copy (`00490900`, Line.obj's COMDAT)
  sets no `eax`. The smaller void body changed CPDMesh::Unknown10's (`004c4dc0`) spending until the transposed
  matrix became a named local: `FMatrix t = ori.Transpose(); ground = t * ground;`.

- The linker folds identical functions (`/OPT:ICF`): every empty function, `DebugTrace` and `~CMemoryHeap`
  among them, is the one `RET` at `0040c640`. Such calls stay in the source as calls to empty functions.
- Unreferenced functions are removed (`/OPT:REF`), and each object's functions keep their source order, so an
  object's retail layout gives its definition order (`Cleanup` sits between `ReallocTiny` and `Shutdown`).
- Objects are linked in alphabetical order of their file names (`tools/objmap.py`, `config/objects.tsv`).
- Link phase:
  - A definition placed after its caller in the same file is still auto-inlined, because VC6 compiles the bodies at
    the end of the file. Where retail keeps the call (a folded body or an empty hook), bracket the definition with
    `#pragma auto_inline(off)`. Without it, CRenderInfo::ShaderFailed disappeared into Apply (`00550d50`) and
    MergeAnyPart into CanMergeInOptimizePass (`004bb040`).
  - A line added near the top of a file shifts `__LINE__` in every later `new(MEMTYPE_X)` allocation and so changes
    code: a `#define ENGINE_CPP` first line changed CEngine::Init (6 bytes) and SetViewpoint (1 byte). Put such a
    define on an existing blank line (or behind a `#line`). The engine hooks were moved to their callers for this
    reason before it was understood; engine.cpp could hold them.
  - A declaration made visible in a file can move that file's declaration-order ties even when nothing uses it: an
    `SPtrSet<CWaypoint>` member in world.h changed CGame::DrawDebugStuff and CFEPGoodies::Render, so the member stays
    `SPtrSet<CThing>`.
  - A global whose implied address falls inside a placed object's extent is a field of that object reached
    through a second name (CLIPARAMS, CAREER, TEXT, LT, SHADOWS and others), not storage. Its users spell the
    field.
- VC6 stops inlining in a function once it has made a fixed number of inline expansions, counted in the source (an
  inline that calls another inline costs two) whether or not they produce code. `CCareer::UpdateGoodieStates`
  (`0041c470`, 17,977 bytes) inlines every accessor until goodie 72's rule and calls the out-of-line copies after
  that (`00421970`, `00421980`); one expansion more or less before that point moves the cutoff and changes the
  code. So a long function's early statements can be fixed by where its code stops inlining.
- A byte match is not enough: every relocation must land where retail's does, and a symbol that two matched
  functions place at different addresses fails them all (`check` reports the conflict and the function behind each
  address). Swapping two stores that load the same register can match every byte and still write the wrong
  fields; CAREER's initializer did until the conflict showed it.
- An object's dynamic initializers are emitted where their globals are defined, which puts them first in almost every object (FrontEndData.obj is the exception that proves it: Init `004687e0` and Shutdown `004691c0` come before its pair `004692a0`, whose identity matrix `00679b48` Init copies, because its include follows them). In the order their globals are defined: the per-file maths constants from `mathsconst.h` (a zero-vector and an identity-matrix initializer), then the object's own globals (thing.obj's `CThing::sIdMatrix`, CLIPARAMS, CAREER, LT, `CONTROL_BINDINGS`); a global defined further down the file is initialized there (ltshell's `OLD_SCHOOL_ALPHA_REF` at `00513d60`). Objects that do not include the header have no pair: activereader, MemoryManager and SPtrSet start directly after the previous object's functions, and the pairs that follow them are actor's (`004010c0`), MenuItem's (`004a3010`) and squad's (`004e5cb0`). SquadNormal's next pair starts at `004e6780`; the base squad's debug drawing binds its own identity matrix to `0083d148`. The zero-vector and matrix data of those pairs is referenced only by the initializers, so relocations cannot tell which object owns a pair; position and code references decide.
- How a member reaches the device changes register allocation. ltshell's state wrappers read LT's device through
  Stuart's inline `LT.GetDevice()`; the same code written `LT.m_pd3dDevice` swaps the roles of `eax` and `ecx`, and
  `CreatePixelShader` loads the device once only through `GetDevice()`. A copy of a parameter (`DWORD v=value`)
  likewise gives the cull-mode swap in `SRS` its own register.
- `/Ob2` inlines ordinary functions defined later in the file too: the screen-position accessors at the end of
  Career.cpp (`004218f0`..`00421940`) are inlined into `Load` and still emitted. Where retail calls a small function
  it could have inlined, something barred it: `CD3DApplication::GetAdapterInfo` and `CDisplayModeKey::Set`
  (`00420cd0`, `00420d10`) are called, not inlined, by `WriteOptions`, and only `#pragma auto_inline(off)` around their
  definitions reproduces that. Whether the original used the pragma is open.
- A copy written as `memcpy` of a fixed size compiles to integer moves, a float assignment to `fld`/`fstp`; the
  options tail is written and read with `memcpy`, and old and new settings are compared with a 4-byte `memcmp`.
- VC6 does not always inline a class's own inline constructor: built from `FVector`'s dot product,
  `FMatrix * FVector` calls the out-of-line `FVector(x, y, z)`; retail inlines it (CThing::GetCentrePos, `004f3ac0`),
  which the product written out in full reproduces.

- A class-static `SPtrSet`'s atexit destructor thunk carries a guard bit (WorldMeshList `0050d980`; the same shape
  at `0040f500` and `00505940` marks those sets as class statics too).
- The inline-depth limit sends `First()` out of line when it is reached through an inline helper (`0050da8a`),
  while `Next()` stays inline. `SAFE_DELETE` and a plain `delete` give different register roles.

- A `float` parameter stays on the stack where an `int` one is hoisted into a register (world's `SetTextTime`).
  A `SAFE_DELETE`-shaped delete of a class with an inline destructor calls that destructor out of line
  (`~CMeshPose` `004dcb00`).
- `CMonitor()` initializes its deletion list in the initializer list: retail stores +4 before the vtable pointer
  (`0050b808`).

- The inline budget is spent from the end of a function: when a function has more inline expansions than VC6 allows, the earliest call sites are the ones left out of line. It explains the out-of-line `First` in the first loops of `0x510800` and `0x5110f0`, world's non-virtual `??_G` (`0050d680`), and Career's goodie cutoff. A reconstruction with too few or too many expansions later in a function shows up as mismatches at its top. `UPhysicsManager::SpawnCharacter` (`0050fa40`) confirms it in the other direction: retail calls `CActiveReader`'s constructor out of line for CGillMHead and CTentacle but inlines it for the last case, CComponent, and the build matched only once CTentacle got the vector member (+0x2c0) whose empty inline constructor spends the budget. Dead code counts too: an `if (0)` around the tail calls still keeps `First` out of line (`tools/tests/inline_budget.cpp`).
- `~GenericSPtrSet` is inline (`{ RemoveAll(); }`): CWorld's destructor calls `RemoveAll` (`004e5c60`) directly.

- `CComplexThing` ends at +0x7c (0x80 breaks actor.obj); `CHazard` and `CExplosion` each carry their own 4 bytes
  at +0x7c.

- An aggregate array's dynamic initializer is two functions: the wrapper `.CRT$XCU` calls (a lone `jmp`) and the
  body that builds the array (FEPGoodies' `goodies`: `0045ac20`, `0045ac30`). The harness names them
  `init:NAME` and `initbody:NAME`; the compiler's `_$E<n>` numbers shift with every header change.

- A shared inline's cost is what sends it out of line in larger callers: `CParticle::SetPos` calls `SetCurrentPos`
  (`00403650`) from each branch, and that doubled cost is why retail calls `SetPos` out of line (`004097a0`) in big
  functions.
- Open: in two `ButtonPressed`s (FEPBEConfig, FEPWingmen `00521d20`) retail leaves the last call site's inner
  `Next`/`GetCurrentLevel` out of line and keeps earlier ones inline, so the budget is not a plain count from the end
  in every case; depth or size weighting is the next hypothesis to test.
- Inline budget measurements: call sites before a probe cost nothing; each
  later top-level statement with an inline call costs one unit whatever the callee (`Z() + Z()` counts two), and a
  direct `First` goes out of line at 21 later sites; trivial forwarders are never refused, only the innermost
  non-trivial callee; the deeper the non-trivial nesting the sooner refusal comes (a list walk's `First` at 3, its
  `Next` at 5, the walk itself at 14); switch cases are processed in source order; within a loop the initial `First`
  is refused before the increment's `Next`. Open: whether depth or size weights the units.
- Float codegen: a helper that assigns to its parameter instead of a new local keeps callers from reusing a
  common subexpression across calls (`RangeTransition`); a colour blend with a literal folds to `or 0xffffff` but
  through a `DWORD` variable gives `and 0xff000000; xor 0xffffff` (retail has both); `x / float(n)` is `fidiv` while
  retail's `fild`+`fdivp` needs a float local; `a * K1 * K2` folds to one constant but `(a * K1) * K2` keeps both;
  a function's own read-only floats outside the shared pool reproduce as `extern const float` globals.
- Inline wrapper layers cost budget beyond their own call: flattening one turned `GetNumJetWeapons` into a match, and
  `TEXT.GetString` (a wrapper) against `GetStringById` decided `GetConfigDescription`. VC6 folds
  `x*6.f*0.5f` to `*3` but keeps `(x*6.f)*0.5f` as two multiplies; jump-table case bodies follow source order.
- `/Ob2` inlines a function into a caller earlier in the same file (`CGame::PreRun`, defined after
  `RestartLoopRunLevel`, is inlined there, `0046e040`; `CGame::IsMultiplayer` into `Update`), and the linker's
  `/OPT:REF` drops the out-of-line copy when nothing calls it. So a retail function with no copy is not
  necessarily `inline`: Stuart's plain definitions of `PreRun`, `InitOneOffResources` and `InitRestartResources`
  match as written.

- VC6 evaluates an inline accessor's call before a plain memory operand, so a retail `fld a; fadd b` that the obvious
  source reverses often means `a` was read through an inline getter; `CGame::Render` needed the reverse,
  `mPlayer[n]` rather than `GetPlayer(n)`, to match its registers.
- The physics script (CPhysicsScript.obj, CPhysicsScriptStatements.obj, reconstructed from RTTI and the factories'
  switches; no Stuart source). Every keyword is a class (RTTI names 245 of them) with Apply, GetSize and Load; a
  statement (unit, weapon, weapon mode, round, spawner, explosion, component, feature, hazard) holds a list of them.
  Identical bodies fold across classes (one `return 4`, one float Load, one string Load). The unit, weapon and
  weapon-mode lists size themselves with a null check the other six lack (`0042f280` vs `004301e0`). Retail keeps
  its bugs: a unit's BasedOn copies its source's weapons and spawners without adding them and fills the spawners
  from the finished weapon loop's pointer (`00433bc1`); CWeaponBasedOn sits in the weapon-mode family but copies a
  weapon (`00435840`); a spawner's BasedOn copies only when the spawner's own Delay is set (`00439f76`); the unit
  Alligence and explosion Shockwave values are read and never applied (`004014c0`). The CUnitData, CWeaponData,
  CWeaponModeData, CRoundData, CSpawnerData, CExplosionData, CFeatureData and CHazardData fields are named by the
  keywords that set them.
- The particle system's data: TokenArchive.obj reads the particle editor's text archives ("ParticleSystemEd_File_(C)2000_
  Lost_Toys_Ltd", one "token value" line each, 124 tokens by name, `004f52b0`); references to other descriptors are
  collected as fixups and resolved by bsearch once the set is loaded (`CTokenArchive::HandleRelocation`, a name its
  caller's trace spells). The editor's writers format each line into a local buffer and write nothing. ParticleSet.obj
  keeps the descriptors in one list sorted by name (`CParticleSet::Create` refuses a duplicate) and builds the
  thirteen descriptor classes (RTTI names; their fields are named by the tokens each class's Write emits). A colour
  read without a reference is scaled from 0..255 (`004f5a73`). Retail `Create` leaves the result unset for an unknown
  type (`004cc7d6`).

- `CSpawner` and `CSpawnerThing` are distinct retail classes. The factory at `0050f970` allocates `0x3f8`
  bytes and calls `004e37f0`, which installs vtable `005dee94`; its RTTI names `CSpawner` with
  `CMonitor`/`IListener` bases. The object-id factory instead allocates `0x46c` at `004bf465` and installs
  `005dd16c`/`005dd0f4`, whose RTTI names `CSpawnerThing` with `CComplexThing` bases. The monitor-based
  declarations in unit, WorldPhysicsManager and DestroyableSegment now use `CSpawner`; their layouts are unchanged.
- Cutscene track flag bit 0 disables landscape rendering: `CCutscene::Update` at `0043f88a`..`0043f894`
  tests that bit, uses `SETNE` and stores the result to `ENGINE.mRenderLandscape` (`0089ce48`). The flag's
  earlier header comment described the opposite behavior.
- The save-version initializer matters independently of matching `Load`/`Save`: retail's `00623e24` holds 17.
  The reconstructed definition still held Stuart's 9 despite the divergence already being documented below;
  it is now 17, verified in the emitted `Career.obj` data as well as the pristine specimen. The options slot at
  `00631e88` is the existing float `MESH_LOD_BIAS` (retail initial value 1), not a separate integer variable.
  Serialization still copies its four bytes unchanged.
- Console completion and status-line lookup call case-insensitive `_strnicmp` at `0056e170`
  (`0042b2be`, `0042b2d6`, `0042b2ff`, `0042b3b1`, `0042b73f`). Destruction calls case-sensitive `strncmp`
  at `0055e560`. Combining the objects exposed the mistaken shared symbol even though their individual
  instruction bytes matched. The two routines now have distinct declarations and callers.
- `CMissile` overrides `SetThingType` with the Actor implementation: its slot 38 at `005e3c3c` points to
  `00401540`, which ORs `0x80000003`; Round's slot at `005de8c4` instead points to `004d8320`, which ORs
  `0x80000007`. The explicit Actor-qualified override preserves this difference without changing the layout.
- A particle's first position update copies the new position into `mStartPos`, then reads it back into
  `mOldPos` (`004e4913`..`004e494d`). The chained assignment in `CParticle::SetPos` reproduces that order and
  makes both `CSpawnPoint::SpawnBattleEngine` (`004e47e0`) and `CFEPDebriefing::Process` (`00456930`) exact.
  Respawn retains the optional air/ground effect selection, the initializer reset after the virtual Init call,
  and the authored side/configuration selection.
- The sphere trigger's containment list holds deletion-aware `CActiveReader<CUnit>` objects, and its `+0x88`
  field is a float clock value, not an integer (`Hit`, `004e5700`). Its lifecycle methods and `Hit`
  now match; the October 1 containment-frame boundary above resolves the iterator-inline gap.
  `oids.cpp` uses the reconstructed header.
- Both squad slot-67 implementations (`004e6da0`, `004ea780`) return an `FVector` through a hidden output
  pointer, with a unit pointer and two integer arguments. They are not void methods with four public arguments.
  The mission-script caller uses that ABI without treating the hidden pointer as an explicit parameter.
- Base squad lifecycle, counter creation and callbacks now have complete byte matches. `HandleEvent`
  (`004e65e0`) passes event 4002 as a `CScheduledEvent*`; both derived squads reuse that same event when
  rescheduling (`004e70e2`, `004ea764`). The callback at `004e6660` belongs to the squad and sets its `+0x88`
  clock to event time plus five seconds; the inherited `CUnit` label is misleading. Init remains unmatched.
- Normal-squad lifecycle, formation admission and event dispatch now match. Its owned member records are
  20 bytes and contain deletion-aware unit readers. Event 4002 reuses the incoming event: a true return from
  the controller at `004e7110` selects `NextFrame`, while the other path schedules at current time plus
  `GAME.FloatRandom() * 0.01f + 0.99f`
  (`004e7070`). The main controller body remains open; these matches do not establish complete squad AI.
- `CWorldLineColReport` stores the hit pointer at `+0`, the part at `+4`, the hit type at `+8`, and distance
  at `+0xc`. The earlier header exchanged pointer and type; its constructor's two zero writes had concealed
  the mistake. `CWorld::FindFirstThingToHitLine` (`0050b030`) writes and returns the enum at `+8`; the ray
  consumer checks that enum before reading the pointer (`00426be5`, `00426bec`).
- `CCSRay::Init` (`00426a40`, 482 bytes) is an initializer, despite the inherited `CreateEffect` label. It
  initializes the base seeker, translates a copied line into world space, queries the world, and dispatches
  slot 6 only for a thing hit with a persistent seeker. It then deletes the temporary line. Collision-seeker
  setup, delayed readiness, shape replacement and sector-distance calculation also match; slot 10 takes a
  sector by reference and returns an integer, rather than the former void/no-argument declaration.
- All three projectile-seeker bodies (`00425b50`, `00425c60`, `00425e30`) now match, including their complete
  relocations. Candidate filtering projects onto an unbounded trajectory line, without clamping its fraction.
  The volume getter uses old-to-current displacement and only normalizes the extension when the authored
  round length exceeds `0.001f`. These are compiled-code findings, not observed collision outcomes in a run.
- Collision double dispatch exchanges the two movement arguments along with the volume roles. The four
  stubs at `004098c0`, `004262e0`, `004059a0` and `00426320` prove that order. The provisional mesh wrapper
  passed the movements unchanged; its corrected full section now matches, and the old body is a failing
  negative control. All six CLine interface methods match, with four methods sharing one dispatch body.
- Map-grid entries contain next/previous links at `+0/+4`; the owner is recovered as entry minus `0xc`
  (`00492c90`). The inherited `Invalidate` label at `00492c60` is a constructor called from the two owning
  object constructors. `00491900` instead constructs eight-byte grid nodes, whose destructor conditionally
  frees their child-pointer array. Entry initialization/update and node/list/iterator/bounds operations now
  match; exhausted iteration retains null, and removal does not invalidate the entry's stored layer.
- Map-grid radius selection uses `radius * 2.01f`, falling back to layer zero with a diagnostic if no layer
  fits (`00491c50`). Coordinate conversion (`00492670`) uses the retail x87 integer-conversion path, then
  shifts and clamps X/Y against per-layer bounds. Its rounding must not be described as floor or truncation
  independently of the floating-point control word. Both complete bodies and their relocations match.
- Map-grid radius queries scan expanded XY rectangles from layer four down to zero, with X advancing before
  Y and each node's linked list visited in order. They perform no distance, Z or type filter. An invalid first
  sector preserves the previous shared iterator (`00491ea0`). The matched line-query entry, layer setup and
  next-entry functions retain a shared query flag, in-place endpoint clipping whose Boolean result is ignored,
  and a center-plus-two-neighbors scan with no deduplication. Sector advancement remains a near miss.
- Map-grid teardown and sorting now match (`00491930`, `004926e0`), as do the owned initialization and
  exit-registration bodies. Teardown frees layers four through zero, with each node releasing its child-pointer
  array. Sorting moves trees behind the original tail but excludes that tail from the walk; an original tree
  tail therefore precedes the moved trees. It is not a stable partition of the entire list.
- Polygon-bucket radius/line query entry and iteration, random-triangle selection and packed-vertex conversion
  now match (`004d4aa0` through `004d5930`, except line advancement). Queries retain shared global iterator/line
  state and compare a full 32-bit query stamp with a sign-extended 16-bit triangle stamp. The packed vertices
  are six-byte records, and triangles contain three short indices, a short stamp and a 32-slice Z mask.
- Polygon-bucket construction/destruction, XY segment/cell intersection and the complete 984-byte
  triangle/cell test now match (`004d39d0`, `004d3a00`, `004d3b10`, `004d3ce0`), including the latter's jump
  table. The build/load drafts preserve owned versus borrowed bulk buffers and newest-first vertex lookup.
  Their mesh inputs establish 12-byte triangles containing three vertex pointers and the position index at
  vertex offset `+0x20`; they do not contain the provisional extra three triangle indices. Build and load
  remain partial, so the matching query methods do not establish the entire constructed data pipeline.
- Collision reports hold six normal vectors at `+0x08` and a separate triangle normal at `+0xd4`, preserving
  all later offsets. The indexed stores at `004ad421..004ad442`, six-contact/pass limits and triangle-normal
  stores at `00478fe4..0047900e` establish these fields. The sphere caller of `004acf30` passes its current
  start and travel vectors by value (`004accbe..004acd1b`); the provisional contact-position/original-direction
  arguments were wrong. The corrected complete caller, resolver and mesh line test remain uncredited drafts.
- The swept-triangle helper's sixth argument is a float radius. The two actual callers dereference their radius
  pointer at `004ac440` and `004ac65c`; the draft incorrectly forwarded report field `+0`. The common geometry
  interface and both callers now preserve the observed argument. Their remaining byte differences stay open.
- The ray/sphere helper (`00479630`) matches: it treats the endpoints as an unbounded forward ray, and its inside-sphere path returns radial depth rather than distance along that ray. Box distance (`00479770`) has a retail quirk when all three axes are outside: `sqrt(x*x + y*y + z+z)`, where x/y/z are the positive excesses. `004798a4 DC C0` doubles Z. Twenty-seven authored cases ran against unchanged retail bodies in a guarded native i386 harness; three one-byte controls replace that FADD with FMUL and distinguish the corner results. This establishes those isolated results with x87 control word `037f`, not full game or device acceptance.
- Fourteen guarded executions of unchanged swept-sphere/triangle code (`00478510`) and three one-byte controls establish face/edge/vertex contact, the rejection of equal prior hits, the initial-overlap override and retention of the face normal for edge/vertex contacts. A separate cancellation witness exposed a candidate defect: A=(100000,100000,0), B=(100001,99999,0), C=(100000,100000,-1), position=A, movement=(-1,-1,0), radius=0. The original refuses it without changing the report. Retail rounds plane/numerator intermediates to float32 at `004787cb`, `004787ea`, `00478a77`, `00478a96`. A shared plane-distance calculation restores the real Dot calls and these stores without compiler directives or volatile variables. A separate check executed both compiled cores: the earlier draft accepts the witness and changes the report; the corrected candidate and original refuse it and leave the report untouched. Fourteen earlier cases and three corresponding controls agree on return values and all initialized report bytes; opaque fourth vector words are recorded separately. The integrated core equals the exercised candidate section. Dependencies remain original code, and the corrected core remains a byte mismatch; this is bounded candidate execution, not acceptance of the reconstructed geometry pipeline. The offset wrapper (`004780f0`, 110 bytes) now matches its entire section and relocations.
- The world line dispatcher (`0050b030`) is fully drafted but not byte matched. Fifteen executions of the unchanged dispatcher with explicitly mocked terrain, grid and volume dependencies, plus three one-byte controls, establish filtering, the dying-building exception, exact `meshCollision == 1`, strict broad-hit versus inclusive mesh-hit ties, report reuse after failed calls, and partial output writes. `firstOnly` sets the hit type without replacing the pointer, part or distance. This is original dispatch with instrumented dependencies, not actual collision integration, reconstructed-source execution or a game run.
- Map cell-height construction (`00490e30`, 218 bytes) now matches: each of 64x64 eight-unit cells scans
  an inclusive 9x9 set of signed height samples and stores scaled maximum then minimum. The terrain trace
  (`00490a40`) remains partial. It samples beyond the supplied endpoint, recursively narrows a crossing,
  and tests water only for flag value one. Its packed-coordinate conversion uses float bias `3afff2e5` and
  `49152.0f`, not ordinary integer truncation; those details must survive further reconstruction.
- The height-field lifecycle and all three height samplers (`0047e870`, `0047e8a0`, `0047ea20`, `0047eb00`, `0047eb80`) now match, as do Map's construction/destruction and global init/exit. `CHeightField` occupies `0x13dc` bytes at Map offset zero: the AYADATA size word at `006317e8`, base Load and constructor callers agree, as does the reconstructed ResourceAccumulator size word. Its owned signed-16 sample buffer is `64*64*9*9*2` bytes. At legal X=512, the integer sampler uses Y>>8 where the interior uses Y>>3; the branch actually tests masked bits, not full equality. These use authored samples, not a real map load. Scaled collision height uses bias `3afffeb0`, distinct from the map trace. Color/dimension setup and surface normals remain partial; base loading and later Map operations remain open. The October 1 loader recheck (`0047f750`) retains its 608-byte section against a 610-byte retail body. Packed-colour ownership, direct member reads, maximum expressions and a byte-offset height cursor do not close it; all 15 callable graphs and 12 exact controls are restored. A nested maximum reduces the byte difference count by moving later instructions into alignment, but introduces branches absent from retail. It is rejected. Six maximum spellings (declaration first, ternary, if/else, `max(max())`, starting from b, a declaration list) and all 30 orders of the colour block (`A`, `S`, the three ambient bytes) don't fix it: the best is shape 41/117 (`A ar ab ag S r b g`) or 43/91 (`A ar S ab ag`), against 48/106 now. Nothing committed. The separate landscape tile helper also remains an interface hypothesis: retail `UpdateArea` narrows twice (`005474cc`, `00547501`), while `AddDamage` sign-extends the cell at `0054774f` before narrowing at `0054779e`. Changing the shared helper from `UWORD` to `SINT` reproduces these conversions but fixes neither caller and also changes the unmatched `RenderShadowMap` code. The declaration is restored, preserving all 66 callable graphs and 51 exact controls.
- Persistent collision initialization, candidate admission, recursive node traversal, overlap checking,
  scheduling and event handling now match (`00480a30` through `004812d0`, excluding `MovedSector`). A separated
  pair schedules from surface distance divided by the sum of maximum velocities; zero summed speed returns
  without scheduling. The code preserves query order, immediate-check recursion protection, next-frame
  fallback and reuse of an incoming event. It refuses scheduling above 950 monitored references. These static
  findings do not establish observed event timing in a running game.
- Normal-squad member queries, centroid/all-dying tests, and member cleanup with optional rescheduling now
  match. Slot 75 takes an FVector by value and returns a unit pointer (`004e8d50`), rather than the former four-integer/BOOL
  declaration; both normal and relaxed squad interfaces now preserve that ABI. The controller's `+0x108`
  field and member-record `+4/+8` values are floats, while `+0x110` is a BOOL. The main controller remains a
  partial reconstruction, so these corrections are not complete squad-AI acceptance.
- Normal squads append themselves to the faction lists (`004e6c68`, `004e6c7f`) but insert admitted members
  at the front (`004e6efe`). The provisional source had those operations swapped. Checking both callers with
  the actual SPtrSet owner now proves the corrected relocation targets. Target refresh/pursuit classification,
  summed threat/importance, leader-threat query and unit-list creation also match; event 4000 reschedules at
  current time plus `FloatRandom()*2 + 2`. The one-byte selector allocations are real instructions at
  `0050b844` and `0050b86d`, while their original class identity remains open.
- Unit firing feasibility (`004fb5a0`) now matches. It first requires range classification zero; with a weapon,
  it uses zero height for an on-ground target or `min(terrain, water)-targetZ` otherwise, admits the inclusive
  mode-height bounds and forwards to weapon feasibility. The fallback checks the spawner reader. The larger
  squad selector retains faction-list order, strict score comparisons and squad-reader return, but is still a
  partial reconstruction; its supporting matches do not prove the complete selection body.
- Weapon feasibility, desired pitch and minimum/maximum ballistic range have complete candidate bodies
  (`005088b0`, `005094b0`, `005096a0`, `005099a0`). Desired pitch and both range bodies now match
  their complete sections and relocations; feasibility remains unmatched. The matching round predicate (`0040d0f0`, 45 bytes)
  requires nonzero gravity and excludes beams and torpedoes. Static branches preserve strict angle-scan ties,
  a default pitch of `-PI/4`, different same-side/crossing-height square-root paths, and no random draws.
  The feasibility trace accepts an obstructing unit of the target's allegiance, not necessarily the exact
  target pointer. That feasibility claim remains a static reading of an unmatched draft, not runtime acceptance.
- Weapon round spawning (`005069f0`) now has a complete, uncredited candidate connected to its actual
  callers. Admission calls BattleEngine `WeaponFired` before checking the mode; successful round allocation
  gates launch-sequence advancement and spread draws. Flak consumes an extra draw conditionally, and
  successful shell creation gates three further GAME draws using `&400`, not modulo. The matched burst
  handler ignores SpawnRound's result before advancing/rescheduling its event; the partial Fire body
  does not roll back cooldown on failed spawning. Muzzle effects retain permanent/temporary link lifetimes.
- All eleven reconstructed shell bodies and both shell vtables match. `CShell` derives through CActor,
  with a rotation matrix at `+0xe0`, a 256-byte resource name at `+0x110`, and factory allocation `0x210`.
  The old CThing-plus-padding declaration hid the actor methods. Its name setter copies nonzero bytes
  without adding a terminator. Init runs CActor initialization, consumes three CRT `rand()` draws for
  rotation, then schedules shutdown after four seconds. These follow the actor's GAME draw and precede
  the weapon's three shell-launch GAME draws; the streams are distinct. Move calls the actor first, damps
  velocity by 0.7 on ground or 0.9 otherwise, and postmultiplies orientation. These are compiled matches,
  not observations from a running game.
- Front-end drawing, the in-game end screen and the pause/message overlay share the same byte at `00679b40`.
  `game.cpp` and `DXEngine.cpp` now use FrontEnd's `gInFrontEnd` definition, removing a provisional second
  symbol without inventing a second global. The six checked stores include `0047185a` and `0053ee07`.
- `CSpawnerThing` shutdown and interrupted-group deactivation clear its squad's `+0x80` field before detaching
  the reader (`004e3330`, `004e3760`). `SetSpawnScript` (`004e37c0`) writes the embedded init's `mScript`, not
  `mSpawnScript`; event 3000 routes to `004e3370`. Init's final amount/squad-size arithmetic remains a near miss.
- `CIBuffer` now reconstructs all twelve functions from constructor `00488210` through `LockDynamic`
  `004885e0`, including the five-slot device-lifecycle vtable. Managed buffers retain a CPU copy; dynamic locks
  use discard only when `D3DUSAGE_DYNAMIC` is set. Device release nulls the buffer without resetting `mLocked`.

- **Mesh rubble spawning 00443a20 matches, October 2.** A separate check independently rebuilt the helper's reconstruction with the pinned stock VC6 compiler, then reproduced the full integrated score: all 1,152 section bytes and 42 relocation meanings match; the recorded body contributes 1,141 game bytes. Using the transform-output position as the translated centre removes two redundant vector lifetimes. A reconstructed 12-byte angular view names the mesh particle's reused sprite fields: yaw at +0xc8, roll at +0xcc, pitch at +0xd0. CPDMesh's existing update consumes these as yaw/pitch/roll; the view reproduces retail's 0x74 frame and spin/velocity store order without padding or artificial side effects. Its spelling is reconstructed, not evidence of the original source type. The helper independently resolved the cleanup/FuncInfo graph and its five references; the full score retains every earlier match, reports no relocation conflicts, and leaves the two ambiguous vtable identities unchanged. Specimen: BEA.exe, SHA-256 74154bfae14ddc8ecb87a0766f5bc381c7b7f1ab334ed7a753040eda1e1e7750.

- **Legacy occupancy decoding 004be050 matches, October 2.** A separate check independently compiled the reconstructed row decoder with pinned stock VC6 and confirmed the complete 288-byte section, padding included, and all three Read references. The retail function contributes 287 game bytes. Legacy y stays fixed across each packed row; computing gridY=y>>1 before the column loop gives the actual normalized row consumed by the per-bit writer. That writer preserves SetCell's x conversion, all bounds and set/clear masks, with no enabled-flag check added or removed. Version selection and stream read order stay intact. This is a faithful source reconstruction, not recovery of its original spelling. All 41 earlier object matches survive, and the complete integrated score preserves every previous match with no relocation conflicts. The earlier Load optimizer near-miss record below is superseded by this exact match. Specimen: BEA.exe, SHA-256 74154bfae14ddc8ecb87a0766f5bc381c7b7f1ab334ed7a753040eda1e1e7750.
