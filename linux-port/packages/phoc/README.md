# phoc 0.57.0-r2

This local package carries one output-management fix for runtime refresh
rate switching.

Upstream `phoc_output_config_head_to_output_config()` only reads
`head->state.mode` when the selected fixed mode is marked preferred.
Selecting the non-preferred 60 Hz mode therefore produced a zero-sized
custom mode and Phoc fell back to the preferred 90 Hz timing. The patch
uses `head->state.mode` whenever it is present and keeps
`head->state.custom_mode` only for actual custom timings.

The package source and build options otherwise match Alpine edge
`community/phoc` 0.57.0. The APK should be installed together with its
`phoc-schemas` subpackage.

Upstream `main` at `1ef2711f87f74f7493249ff9209c3831783722f4`
(2026-10-31) and the 0.58.0 tag
`d50d76a4add49add71b259df9cf67d58b3cbddfb` still contain the original
condition. KDE/KWin does not use `wlr-output-management`; its KScreen/DBus
path is a different implementation.
