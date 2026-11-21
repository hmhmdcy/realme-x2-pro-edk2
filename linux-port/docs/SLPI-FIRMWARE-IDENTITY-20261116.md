# SLPI 固件路径身份核对（2026-11-16）

## 结论

`samurai-ssc` 把 SLPI 固件路径写死为
`qcom/sm8150/realme/samurai-a11-r187/slpi.mdt`，而 pmaports 分支写的是
`qcom/sm8150/realme/samurai-slpi-a11/slpi.mdt`。两者看起来是不同固件，
但在实机上**字节完全相同**：

```text
1f475cab01b2c62645cc249fe775ef7e365132537e186e9bd97a399da89b98a5 \
  /lib/firmware/qcom/sm8150/realme/samurai-a11-r187/slpi.mdt
1f475cab01b2c62645cc249fe775ef7e365132537e186e9bd97a399da89b98a5 \
  /lib/firmware/qcom/sm8150/realme/samurai-slpi-a11/slpi.mdt
```

因此路径差异不构成行为差异，也不需要在两个分支之间「统一」固件；
真正决定能否启动的是 `config['firmware_manifest']` 的校验，两个目录都
必须在清单内。

## 为什么仍然保留两个目录名

- `samurai-a11-r187` 是本机实际抽取并验证过的路径，设备当前
  `/usr/bin/samurai-ssc` 与 EDK2 侧源码都用它；
- `samurai-slpi-a11` 是 pmaports 的对外发布命名，来自
  `provision-firmware.py` 的规范化目标；
- 二者同源，保留双名可避免重命名已发布包或让用户重灌固件。

## 与本次同步相关的另一处修正

EDK2 侧 `linux-port/ssc/samurai-ssc.py` 曾硬编码
`DAEMON_HASH`/`LIBRARY_HASH`（`1902f1b6…`、`45570ea4…`）。实际安装的
`/usr/libexec/samurai-hexagonrpcd` 与 `/usr/lib/samurai/ssc/libssc.so.2`
是 `9e9def53…`、`ec84351b…`，硬编码值已过时，会让每次 `start` 在
`check_hash()` 处直接失败。

现改为校验包内已随二进制生成的清单：

```text
/usr/share/samurai/ssc-daemon.sha256
/usr/share/samurai/ssc-library.sha256
```

清单由打包过程从实际二进制生成，不会与交付内容脱节。

## 未在实机验证

本次只做了路径与哈希比对（只读），没有重启 SLPI 或复测传感器。
