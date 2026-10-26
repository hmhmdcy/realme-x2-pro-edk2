# Session 34 的临时终端记录

对应 `../../sessions/34-temporary-eud-terminal.md` 的成功实测。
`.raw` 是手机 TX 的 EUD 帧，`.txt` 是未经显示过滤的设备输出，
`.events.txt` 是主机逐字发送/受理记录。这些不是 USB OUT 抓包。

最终键盘测试 interactive2 应仅有以下 ACK 字节：
`15,69,78,7f,64,0a,03`，且没有发送光标查询生成的额外 ESC。
日志中的 `ESC[6n` 保留原文，最终终端只在显示时过滤它。
