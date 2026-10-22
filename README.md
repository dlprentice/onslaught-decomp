# onslaught-decomp

Status: active
Last updated: 2026-10-22
Summary: a byte-matching decompilation of *Battle Engine Aquila*'s PC game code, the tools that judge the match, and
the knowledge behind it; bring your own game and compiler.

A byte-matching decompilation of *Battle Engine Aquila* (Lost Toys, 2003) against the retail PC executable:
`BEA.exe`, SHA-256 `74154bfae14ddc8ecb87a0766f5bc381c7b7f1ab334ed7a753040eda1e1e7750`. The C++ in `src/` starts
from Stuart Gillam's GPL release of the game's source ([stuart73/Onslaught](https://github.com/stuart73/Onslaught))
and is completed, function by function, until Microsoft Visual C++ 6.0 SP5 compiles each game function to exactly the
bytes the retail executable holds at its address.

**From this tree, the check matches 5,449 of the retail game's 5,482 functions** (1,359,136 of 1,367,287 bytes), and
every function this tree annotates matches. The other 33 are defined in four files of Microsoft's DirectX SDK sample
code that this tree leaves out (see "What is left out"); [docs/SCORE.md](docs/SCORE.md) lists them under "Not in this
tree". The record of the check that measured this is in [docs/check/](docs/check/).

## Related projects

- [onslaught-ce](https://github.com/dlprentice/onslaught-ce): Onslaught CE, the native Linux and Windows port built
  from this decompilation; play the game here.
- [onslaught-godot](https://github.com/dlprentice/onslaught-godot): the Godot rebuild of the game.
- [onslaught-preservation](https://github.com/dlprentice/onslaught-preservation): documentation of the game's
  formats, saves, mechanics, levels and engine.
- [Onslaught-Career-Editor](https://github.com/dlprentice/Onslaught-Career-Editor): the companion app for careers,
  saves, settings and lore (to be renamed onslaught-companion).
- [stuart73/Onslaught](https://github.com/stuart73/Onslaught): Stuart Gillam's GPL release of the game's source,
  which `src/` starts from.

## What is here

| Path | What it holds |
| --- | --- |
| `src/` | the game's C++: Stuart's release, the PC build's changes, and the reconstructed rest. Each function carries a `// FUNCTION: 0xADDRESS` annotation naming its retail address. |
| `linklib/` | the link's provisional, link-only pieces, labelled as such; never part of the score |
| `config/` | the compiler flags, the SHA-256 pins of every input, the function table, the link order ([config/README.md](config/README.md)) |
| `tools/` | the matching check, the linker and link comparison, the whole-executable inventory and data tools ([tools/README.md](tools/README.md)) |
| `notes/` | the matching knowledge: the toolchain, compiler behaviour, techniques, divergences from Stuart's source and the link ([notes/README.md](notes/README.md)) |
| `docs/SCORE.md` | the score, the matched functions and the functions this tree leaves out, rewritten by `tools/decomp.py score` |
| `docs/check/` | the check this tree's score comes from: its log and its matched-symbol table ([docs/check/README.md](docs/check/README.md)) |
| `THIRD-PARTY.md` | the third-party material in `src/`, and what is left out |

## What it is, and what it is not

- It is source that compiles to the retail bytes. A function "matches" when its whole compiled section equals the
  retail bytes at its address, relocation fields aside, and every relocation lands where the rest of the evidence says
  (`tools/decomp.py`'s docstring gives the rules).
- It is not the original source text and not a clean-room implementation. Where the source takes a form only the
  compiler's output justifies, it says so in a `STAND-IN`, `RECONSTRUCTED` or `CONCESSION` comment with the evidence.
  One function matches through a build concession, bytes written into its compiled object after compiling
  (`config/object-patches.tsv`).
- It contains no part of the game: no executable, data, text dump or byte listing beyond short signatures. The tools
  read your own copy of the game at run time and check it by its hash first. The PC build's hard-coded strings
  (`src/PCText.cpp`, the credits and front-end text) are in the source because the match needs them.
- It contains no part of the toolchain: no Visual C++ binaries, headers or libraries and no DirectX SDK binaries,
  headers or libraries, only the SHA-256 pins that say which ones the match needs.
- Of Microsoft's DirectX sample code, it keeps exactly one part: `src/d3dapp.cpp` and `src/d3dapp.h`, the sample
  application framework as Stuart Gillam's GPL release of the game's source includes it (their header keeps
  Microsoft's 1998-2000 notice). They are here as released by Stuart Gillam under GPL-3.0, as
  [THIRD-PARTY.md](THIRD-PARTY.md) and [REUSE.toml](REUSE.toml) record. Every other sample file the game linked is
  left out (below), and so is the SDK's own sample framework, whose headers the build reads from your copy of the SDK.

## What is left out

- `src/wavread.cpp`, `src/dxutil.cpp`, `src/d3dutil.cpp` and `src/DXFont.cpp` are Microsoft's DirectX SDK sample code
  as the game changed it. Stuart's release does not include them, so they are not published. Their 33 functions are the
  difference between 5,449 and 5,482. `src/WavRead.h`, the sample's header, is replaced by a declaration of the same
  interface written for this project (GPL-3.0), so the sound code that includes it compiles unchanged.
- `src/splinebasis.c`, an unreferenced 872-byte data block typed out from the retail executable, has no functions and
  matters only to the link's data layout; it is left out.
- `config/link-objects.txt` lists all five of those files in retail's link order, each under a comment line that says
  it is not in this tree. `config/objects.tsv` has a row only for an object whose code names its own source file
  (a `__FILE__` string), so of the five it lists `wavread.cpp` and `DXFont.cpp`, each annotated in its `note` column.
  The check skips a source that is not present.
- The link (`tools/link.py`) needs further inputs that are not freely available, among them the prebuilt NvTriStrip
  library retail linked and import libraries made from the game's DLLs (`config/link-inputs.sha256` pins them all).
  Reproducing the linked executable is therefore not yet possible from this tree and public inputs alone; the
  function match is.
- Per-function notes (what each retail function does, its callers and data) are not in this first release. They will
  follow once they have been rewritten and reviewed one by one.

## Reproducing the match

You need, all from your own copies:

- **The retail executable**: `BEA.exe` with SHA-256 `74154bfa…` (above), and the game folder it came from (two
  mission-script files are compiled in; `config/game-data.sha256` pins them).
- **Visual C++ 6.0 SP5 Professional**: CL 12.00.8804 driving C1 12.00.8867, C1XX 12.00.8964 and C2 12.00.8966 (the
  `c2.dll` SP5 installs from `msvcep.dll`), LINK 6.00.8447. The binaries must match `config/toolchain.sha256`, and
  the `VC98/Include` tree the manifest `config/vc6-include.sha256` (993 files).
- **The DirectX 9.0 SDK** (`dx9sdk.exe`, SHA-256 `3825dec8…`): its `Include/` folder (`config/dx9sdk-include.sha256`)
  and its sample framework's `Samples/C++/Common/Include/` (`config/dx9samples-include.sha256`).
- **Wine** able to run 32-bit programs, **Python 3**, and GNU binutils' `objdump` (for `diff` and `dis`).

### The compiler's paths

The match depends on the Windows paths at which the compiler sees itself and the SDK: the precompiled header records
the paths of the headers it read, and code compiled with a header made under other paths differs
(`CHud::RenderWorldTargetSprites` by 672 bytes). The tools therefore never run the compiler from where your copies
are. Inside the Wine prefix they link

- `C:\Program Files\Microsoft Visual Studio` to your Visual C++ 6 install (`BEA_VC6`),
- `C:\DXSDK\Include` and `C:\DXSDK\Samples\C++\Common\Include` to your two SDK folders,
- `C:\dev\ONSLAUGHT2` to this checkout's `src/` (the retail build compiled from there: its `__FILE__` strings say so),

and run `C:\Program Files\Microsoft Visual Studio\VC98\Bin\CL.EXE`. These are VC6's and the SDK's own default install
folders. The score in [docs/SCORE.md](docs/SCORE.md) was measured at exactly these paths, with the compiler and SDK
folders anywhere on the Linux side. `BEA_VC6_AT` and `BEA_DXSDK_AT` change the first two; the match is measured only
at the defaults. The precompiled header (`build/pch/`, made from `src/common.h` on first use) is keyed on the paths, so
changing them makes a new one.

### Settings

The tools read every input location from an environment variable and have no built-in path for any of them: an unset
input stops a command with the variable's name. The only default location is the Wine prefix's (below). These are all
the variables the tools read:

| Variable | What it names |
| --- | --- |
| `BEA_PRISTINE` | required: your retail `BEA.exe` (read only) |
| `BEA_VC6` | required: the Visual C++ 6 install, the folder holding `VC98/`, `Common/MSDev98/` and `os/system/` |
| `BEA_DX9_INCLUDE` | required: the DirectX 9.0 SDK's `Include` folder |
| `BEA_DX9_SAMPLES_INCLUDE` | required: the SDK's `Samples/C++/Common/Include` folder |
| `BEA_GAME` | the game folder holding `data/MissionScripts/` (default: the folder holding `BEA_PRISTINE`) |
| `BEA_WINEPREFIX` | the Wine prefix the compiler runs in (recommended; create it once, below) |
| `BEA_WINE_BASE` | used only when `BEA_WINEPREFIX` is unset: a base prefix, default `$XDG_CACHE_HOME/onslaught-decomp/wine` (`~/.cache/onslaught-decomp/wine` without `XDG_CACHE_HOME`). A Git clone compiles in the base prefix itself; any other copy of the tree compiles in a copy of it named after the copy's folder, made on first use |
| `BEA_VC6_AT`, `BEA_DXSDK_AT` | optional: the Windows paths the compiler and the SDK are linked at (defaults above); `-` runs the compiler from your folders' own location through Wine's `Z:` drive, which makes the code depend on where they are |
| `BEA_LAB` | only for `tools/link.py`: the folder of the link's further inputs (the paths `config/link-inputs.sha256` marks `lab` are relative to it). The check does not read it |
| `BEA_TMP` | optional, for `tools/icfsim.py`: where it keeps its scratch files (default the system's temporary folder) |
| `BEA_MAIN` | optional, for `tools/equiv.py`: the checkout whose `build/matched.tsv` it reads for symbol evidence (default this one) |
| `BEA_NAME_TABLE` | optional, for `tools/equiv.py`: an address/name table for callees no source annotates (default `config/functions.tsv`) |

`tools/decomp.py` also imports an optional `site_paths.py` beside it, which this tree does not have and Git ignores: a
Python file you may add whose attributes stand in for unset variables (`PRISTINE`, `VC6`, `DX9_INCLUDE`,
`DX9_SAMPLES_INCLUDE`, `LAB`, `WINE_BASE`, `NAME_TABLE`, `VC6_AT`, `DXSDK_AT`). While that file exists, `VC6_AT` and
`DXSDK_AT` default to `-` unless it sets them, which moves the compile off the paths the match is measured at.

Then:

```sh
export BEA_PRISTINE=/path/to/BEA.exe BEA_VC6=/path/to/vc6 \
       BEA_DX9_INCLUDE=/path/to/DXSDK/Include BEA_DX9_SAMPLES_INCLUDE=/path/to/DXSDK/Samples/C++/Common/Include
export BEA_WINEPREFIX="$HOME/.cache/onslaught-decomp/wine"
WINEPREFIX="$BEA_WINEPREFIX" wineboot -i          # once: create the prefix (64-bit Wine with 32-bit support works)
python3 tools/decomp.py check                     # compile every source with VC6 and compare it with retail
python3 tools/decomp.py check src/Hud.cpp -v      # one file, every function's result
python3 tools/decomp.py diff 0x004a2a20           # side-by-side disassembly of one function against retail
python3 tools/decomp.py score                     # full check; rewrites docs/SCORE.md and build/matched.tsv
```

Every input is checked against its pin before anything compiles; a changed or missing file stops the tools with the
file's name. The tools write only under this checkout's ignored `build/`, `src/data/` and `local-data/` folders, in
the Wine prefix (including the links above) and in the temporary folder.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md): changes come in as issues and pull requests, are checked against the full
byte comparison in the working tree, and arrive here with the next export. `src/` files keep their line counts.

## Licence

Code (`src/`, `linklib/`, `config/`, `tools/`): GPL-3.0-only ([COPYING](COPYING)). Stuart Gillam's source release
ships the GPL version 3 text and never offers "any later version", so the source seeded from it, and this tree as a
whole, is GPL version 3 only. Notes and documentation: CC BY-SA 4.0; notes that quote Stuart's source keep its GPL
alongside. [REUSE.toml](REUSE.toml) maps every path, and [THIRD-PARTY.md](THIRD-PARTY.md) names the third-party
material. *Battle Engine Aquila* and its data belong to their owners; this repository contains none of the game's
files.
