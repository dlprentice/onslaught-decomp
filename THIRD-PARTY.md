# Third-party material

Status: active
Last updated: 2026-10-22
Summary: the third-party material in this repository's source, and the third-party files the game linked that this
repository leaves out.

This repository's own code is GPL-3.0-only (`COPYING`); [REUSE.toml](REUSE.toml) maps every path. It contains no
part of the game, of Visual C++ 6 or of the DirectX SDK beyond the files listed here: the tools read those from your
own copies, checked by SHA-256 (README, "Reproducing the match").

## In this repository's source

| File | From | Licence |
| --- | --- | --- |
| `src/d3dapp.cpp`, `src/d3dapp.h` | Microsoft's DirectX sample application framework, as Stuart Gillam's GPL release of the game's source includes it | as released by Stuart Gillam under GPL-3.0 |
| `src/oggvorbis.h` | declarations from the Xiph.Org libogg and libvorbis 1.0 headers | BSD-3-Clause (Xiph.Org Foundation; `LICENSES/BSD-3-Clause.txt`), with this project's GPL-3.0-only |
| `src/OggFileRead.cpp` | its decode loop follows Xiph.Org's `decoder_example.c` (libvorbis 1.0), turned into a class | BSD-3-Clause (Xiph.Org Foundation), with this project's GPL-3.0-only |
| `src/adpcm.c` | the IMA ADPCM step tables (Jack Jansen's public reference implementation) | public reference tables |

## Left out

| File the game linked | From | Why |
| --- | --- | --- |
| `src/wavread.cpp`, `src/WavRead.h` | the DirectX SDK's wave-file sample | Microsoft sample code that Stuart's release does not include. `src/WavRead.h` here is this project's own declaration of the same interface (GPL-3.0-only). |
| `src/dxutil.cpp`, `src/d3dutil.cpp` | the DirectX SDK sample framework's utility code | Microsoft sample code that Stuart's release does not include |
| `src/DXFont.cpp` | the DirectX SDK sample framework's font class (`CD3DFont`), reworked by the game | Microsoft sample code that Stuart's release does not include |
| the SDK sample framework's headers (`D3DUtil.h`, `DXUtil.h` and others) | the DirectX 9.0 SDK | read at build time from your copy of the SDK (`BEA_DX9_SAMPLES_INCLUDE`) |
| NVIDIA's NvTriStrip library | NVIDIA | no stated licence; the link reads the prebuilt library from `BEA_LAB`. `src/NvTriStrip.h` here declares only what the game's callers use. |

The 33 functions the four left-out sample files define are listed in [docs/SCORE.md](docs/SCORE.md) under "Not in
this tree".
