# Session 33：有效 EUD RX 抓包

2026-10-08 至 09，realme X2 Pro / SM8150。选取的短抓包来自
`E:\edk2-samurai-out\`；实验配置、镜像哈希及限制见
`../../sessions/33-rx-access-and-production-policy.md`。

`.raw` 为主机连续读取的 EUD TX 帧；同名 `.txt` 是现有
`linux-port/scripts/decode-eud-capture.py` 的重组输出。它们不是 USB 线上 OUT 抓包。
有些日志行开头丢失；0 stray 只证明帧重组没有需要跳过的字节，不保证无丢帧。
此处没有收录零捕获或误触发的 mode 12 样本。

复核一份记录：

```sh
python3 linux-port/scripts/decode-eud-capture.py reference/rx33/rx33-final-ABC.raw
```

最终版本的单字符回车后返回 `uid=0 gid=0`；ABC 仍为 `41 90 90`；
F1 的受理日志随后由主机 fastboot devices 确认，设备为 62bc28a1。
