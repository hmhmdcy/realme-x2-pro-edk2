#!/usr/bin/env python3
"""Point linux-port/README.md at the LoadOptions image and the new scripts."""
P = "/mnt/e/RealmeX2Pro edk2/linux-port/README.md"
s = open(P, encoding="utf-8", newline="").read()
before = s

s = s.replace("boot-samurai-linux.img", "boot-samurai-linux-cmdline.img")
assert s != before, "boot-samurai-linux.img not found in README.md"

anchor = "| `collect-artifacts.sh` | 整理补丁编号、把补丁/DTB/核对表复制回本目录 |\n"
assert s.count(anchor) == 1, "scripts table anchor not found"
rows = (
    "| `patch-bootmanager-cmdline.py` | 把内核命令行做成 boot option 的 LoadOptions（HANDOVER-NEXT.md §19） |\n"
    "| `build-cmdline-firmware.sh` | WSL 里重编 samurai 固件 |\n"
    "| `verify-cmdline-firmware.py` | 离线核对 LoadOptions / 启动项 / FD / boot.img |\n"
    "| `archive-cmdline-firmware.sh` | 归档产物到 `E:\\edk2-samurai-out\\` 并提交 |\n"
)
s = s.replace(anchor, anchor + rows, 1)

tail = """
## 2026-10-07（下午）：内核命令行进了 LoadOptions

`boot-samurai-linux.img` 之后多了一个超集 **`boot-samurai-linux-cmdline.img`**
（sha256 `b9fb2064…`）：启动项 "Linux (mainline samurai)" 现在把与设备树逐字相同的
内核命令行作为 LoadOptions 一起传进去，设备树万一没带 bootargs 也不会黑屏静默。
改动、证据与真机步骤见 `HANDOVER-NEXT.md` §19（EDK2 提交 `c2a3697`）。

**第 3 步真机验证仍未做**：本轮手机没有连接（`adb devices` 为空、Windows 上没有
`VID_05C6`），所以只做了离线加固与验证。手机接上后刷的是
`boot-samurai-linux-cmdline.img`，步骤同上面第 3 步。
"""
if "## 2026-10-07（下午）" not in s:
    s = s.rstrip("\n") + "\n" + tail

open(P, "w", encoding="utf-8", newline="").write(s)
print("README.md updated: %d -> %d bytes" % (len(before), len(s)))