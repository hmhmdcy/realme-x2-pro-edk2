# Session 75 GPU/GMU research

Own-device evidence takes precedence over another handset's configuration.

- [Mesa Freedreno/Turnip documentation](https://docs.mesa3d.org/drivers/freedreno.html): Turnip supports A6xx. The local test selects only its ICD, checks the physical A640 and driver ID, submits vertex/fragment draws, and verifies all readback pixels and signaled fences. No DRM shim or CPU ICD is used.
- [Mesa EGL documentation](https://docs.mesa3d.org/egl.html): confirms available graphics paths. Vulkan was selected for the temporary RAM-only test to avoid window-system setup.
- [OnePlus hotdog owner's GPU bring-up evidence](https://github.com/Sr-0w/hotdog-linux-bringup/blob/main/docs/evidence/2026-08-04-mainline616-gpu.md): same SM8150/A640 requires GPU/GMU enablement and a board-specific signed ZAP path. Its success does not prove this handset works; none of its proprietary firmware was copied.
- [DRM mailing-list review of error unwinding](https://www.mail-archive.com/dri-devel@lists.freedesktop.org/msg635274.html): reports the pre-existing double destruction of the DPU global private object when hardware initialization fails. Session 75 independently reproduced that exact poisoned-list fault after boot-frame drain timeout. The local cleanup guard tracks successful private-object initialization and makes finalization happen once.
- Actual v7.3-rc6 kernel sources were checked for A640 firmware names, non-split MDT loading, PAS authentication, clocks, OPPs, interconnects and IOMMU. Stock ELF hash metadata and LOAD segment match this handset's split stock blobs; the relocatable 4 KiB image fits its 8 KiB reserved carveout.
- Ubuntu 26.04 arm64 Mesa 26.0.3 and Vulkan loader 1.4.341 packages were fetched through an isolated APT source using the Ubuntu archive keyring. The temporary userspace bundle includes only the recursively required ELF libraries, not other GPU ICDs. Package identities, versions and SHA256 values are in `userspace-manifest.json`.

Runtime results, failures and acceptance limits are recorded separately after real-device testing.
