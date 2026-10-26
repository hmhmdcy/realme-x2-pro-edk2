# kernel69：USB 功能前提和 EUD 共存边界

主记录：[session69](../../sessions/69-usb-gadget-state-and-eud-coordination-audit.md)。
设备只读，未绑定 gadget、切换 EUD、刷机或改内核；普通 USB 共存尚未验证。

`verify.py` 离线核对十份 raw 解帧/text、单次数据帧、观察到的关闭结果、五份导出
起止标记/设备 SHA256/gzip CRC/长度、source snapshots 与 SHA256SUMS。
它不访问手机，不把0 stray/成功短命令当传输无损证明。

`latest-dmesg.validated.txt` 是69499字节设备保存的完整快照；其 gzip15676字节，
SHA256为28ad635dfebf39904397cff93a588aaa70eac1de3f18ed68dacb428f8d7d2dda。
`usb-baseline`/`udc-before`/`driver-facts`/`driver-binding` 分别记录 configfs、UDC、
boot_id/taint/DT 和实际 legacy glue 绑定；首次 readlink usage 原样保留。

`source-audit.json` 固定原厂源码、QUIC官方库和实际主线文件哈希/行号；
`*.source.gz` 是原始源码快照。`source-audit.py` 只审查源码，不是 EUD 工具。
`extract-export.py` 沿用已有离线校验逻辑，仅调整输出目录。
`capture-state.ps1` 只核对枚举/owner/已有哈希和驱动配置，不开 COM/USB。
`finish-state.json` 记录 Windows Shared/未Attached/无已知 owner、零刷机与零控制切换。
`windows-close-observations.json` 明确关闭信息来自 exec stdout/stderr，事件文件本身没有关闭行。

可在本目录运行 `python3 verify.py`。来源审查不能代替实际 gadget 枚举、流量或共存验收。
