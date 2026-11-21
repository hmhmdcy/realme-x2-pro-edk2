# samurai-refresh 1-r1（Phoc 历史工具）

Plasma Mobile/KWin 不使用 `wlr-output-management-v1`，当前设备也已卸载
Phoc。Plasma 下应使用 `kscreen-doctor` 或 Plasma 显示设置；本包只保留给
重新安装 Phosh/Phoc 的场景，不加入 Plasma 桌面依赖。

Small owner package for `/usr/sbin/samurai-refresh`. The tool uses the
existing `wlr-output-management-v1` protocol through `wlr-randr` to select
either stock 1080x2400 mode exposed by the DRM panel driver.

It is intentionally separate from `samurai-platform` so installation never
overwrites the live USB, charging, modem, or audio scripts.

```sh
samurai-refresh status
samurai-refresh 90
samurai-refresh 60
```

The helper discovers the active Wayland socket when run from root SSH. A
non-root caller may also inherit `XDG_RUNTIME_DIR` and `WAYLAND_DISPLAY`
from the desktop session.
