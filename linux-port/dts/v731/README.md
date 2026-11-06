# Linux v7.3.1 Samurai DTB inputs

This directory holds the production OS-facing wrapper for the standardized
Linux v7.3.1 build. It is applied inside the v7.3.1 source tree; the shared
SoC and board fragments are owned by
`linux-port/patches/v7.3.1/0001-arm64-add-standard-samurai-platform-glue.patch`.

The wrapper deliberately:

- removes the source-tree debug `bootargs` and `stdout-path`;
- disables the EUD serial controller on the production USB port;
- switches the primary USB controller to the standard `snps,dwc3` binding with
  USB 2.0 peripheral mode;
- keeps the SuperSpeed/DisplayPort PHY disabled because this phone exposes only
  USB 2.0 on its Type-C connector.

The compiled artifact and all source/build/runtime hashes are recorded in
[`source-lock.json`](source-lock.json).
