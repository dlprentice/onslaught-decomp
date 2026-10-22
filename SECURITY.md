# Security

Status: active
Last updated: 2026-10-22
Summary: how to report a security problem in the tools, and what they read and write.

## Reporting a problem

Please report security problems privately through GitHub's **Report a vulnerability** form on this repository's
Security tab, not in a public issue. Describe what you found, how to reproduce it, and which commit and system you
used.

## What the tools touch

The tools run on your machine only and send nothing anywhere. They read your own copy of the game executable and the
toolchain from the locations you give them (read only: each file is checked against its SHA-256 pin first), run the
compiler and linker under Wine in the prefix you name, and write only under this checkout's ignored `build/`,
`src/data/` and `local-data/` folders, in that prefix (including the links it makes on the prefix's drive C to your
copies of the compiler and SDK), and in the system's temporary folder (or `BEA_TMP`). Problems that matter most here: a tool writing outside those places, or modifying an input
it was only meant to read.
