#!/usr/bin/env python3
"""Give the command block in HANDOVER-NEXT.md section 19.6 a sane order.

The first version listed comlog before the flash, which reads as if the capture
had to start before the phone was even rebooted.
"""
import sys

OLD = (
    "```powershell\n"
    "E:\\eud-host\\eudtool.exe com-up\n"
    "E:\\eud-host\\comlog.exe COM14 600 E:\\eud-host\\samurai-linux.log\n"
    "# 重启后 9501 出现时执行上面两行，再：\n"
    "fastboot flash boot E:\\edk2-samurai-out\\boot-samurai-linux-cmdline.img\n"
    "fastboot reboot\n"
    '# 菜单里音量键选 "Linux (mainline samurai)"，电源键确认\n'
    "```\n"
)
NEW = (
    "```powershell\n"
    "# 1) 刷入并重启，手机会先起 UEFI\n"
    "fastboot flash boot E:\\edk2-samurai-out\\boot-samurai-linux-cmdline.img\n"
    "fastboot reboot\n"
    "\n"
    "# 2) 重启后约 3.5 s 出现 9501 控制设备；这步必须赶在内核打第一行之前\n"
    "E:\\eud-host\\eudtool.exe com-up\n"
    "E:\\eud-host\\comlog.exe COM14 600 E:\\eud-host\\samurai-linux.log\n"
    "\n"
    "# 3) 屏幕出现 UEFI 菜单后：音量键选 \"Linux (mainline samurai)\"，电源键确认\n"
    "#    或者用 §19.8 的 flash-and-capture-linux.ps1，它自己处理这个时隙\n"
    "```\n"
)

p = "/mnt/e/RealmeX2Pro edk2/HANDOVER-NEXT.md"
s = open(p, encoding="utf-8", newline="").read()
n = s.count(OLD)
if n != 1:
    print("block found %d times (expected 1)" % n)
    sys.exit(1)
open(p, "w", encoding="utf-8", newline="").write(s.replace(OLD, NEW, 1))
print("patched", p)