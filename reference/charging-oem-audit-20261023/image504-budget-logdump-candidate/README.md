# Image504 private FAT carrier plan

This frozen source plan will replace only `/Image` in a private copy of the
saved, passed **candidate502** logdump `ace2e261…763ed1`. That saved artifact is
also the exact rollback material for this step. It is not evidence the current
phone has adopted502: the first physical transaction remains prepared502, and
the current501/7e5 state is not promoted into a future live identity here.

Actual Image504 is already built:
`f6477d01d029cec888cafa739db0336e570274e9a3c38d4d5233959dd218a3f4`,
59243008 bytes. The build gate verifies frozen completed delivery88aa, actual
parent/namespace/make terminal facts, three-tree preservation, eight Kbuild
consumers,3241 unchanged archive members,32stub, exports/config/metadata and
unchanged gauge. New Image bytes are read only after that gate. There is no
new Image build, runtime identity, guard or activation request.

The original method is frozen
`gauge-image502-logdump-candidate/package-logdump.py`, SHA
`1a262316bc43536dcbc0c4305114deff31b9bcb13850e3674829f74ad6ac01e6`.
`prepare.py` reads and text-derives it; it does **not** import or execute the old
generator. Source derivation authenticates the old full delivery first.

Precise method delta:

- Input becomes saved502/ace2; its internal old Image must be085d,59243008B.
  The new input is actual504/f647. OUT is the unique
  `E:/edk2-samurai-out/charging-management-20261023/image504-budget-logdump-private-01`,
  target `logdump-image504-private.img`. Existing OUT refuses execution/replay.
- Proof gate and result labels bind the actual504 receipt shape and completed
  original processes, not old502 build fields. Saved502 carrier proof separately
  checks its passed FAT/readback/fsck receipt and boot97811/DTB metadata.
- Tool calls use original `Popen` plus `finally wait`, no timeout kill/replay.
  PID/terminal/returncode are recorded. Request stdin is DEVNULL; logs are
  ordinary private files and are flushed/fsynced before completion.
- Any caught error forces `passed=false`, including an output-receipt write
  failure after validation fields had been set. Successful result exposes exact
  `candidate`, `rollback`, `Image504` path/hash/size fields for later artifact
  binding. Those fields are not future hardware/adoption proof.

The 1MiB bounded read helper, exact FAT16 parser, content checks, permitted-range
calculation and `fsck.fat -n`/post-fsck byte comparison remain identical LF source
text. Full raw source hashes are separately pinned; no normalized source hash is
misrepresented as a raw-file hash. The FAT remains64MiB with the existing exact
geometry. SAMURAI.DTB A823, its entry/chain and all non-Image bytes must stay
exact. Only old/new Image clusters, their FAT entries and Image directory slots
are permitted to differ. No boot/BDS/native-DTB/ramfs/cmdline change is made;
the Image504 build already proved the inherited initramfs and gauge unchanged.
No full boot file is copied/read here; only its saved receipt identity is checked.

Actual default `package-logdump.py` check passed in child785/wait0. It read and
hashed saved502 FAT, actual504 Image and pinned tools, verified their provenance
and parsed the FAT, but executed no mcopy/fsck and created no private OUT. The
existing parser/bounded-read checks are reused rather than rerunning an old
matrix. Source/delta/default-check are ready for root review; no packaging
execution has happened at this source stage.

After that review the sole explicit `--execute-logdump` would copy ace2 once,
normal mcopy-overwrite Image, read it back, validate allowed ranges and every
unchanged byte, run pinned readonly fsck, then verify inputs/mountinfo unchanged.
Failure retains the unique OUT/raw logs and cannot be replayed. Final packaging
must use that same original process/handle through its real terminal state.

The already-built provider2691 may be paired later; this carrier does not install
or bind it. Runtime-on/active native DEVICE and provider-first scope remain as
documented by the504 source. No auto/direct-complete, full PM recovery, physical
latency, SDP500, r5 cause or icon benefit is newly accepted by this packaging.
No phone, SSH, USB, SDK, storage helper/volume, Git, existing carrier, old frozen
leaf or prepared502 transaction is changed.
