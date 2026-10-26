# Image501 图标采集profile模板：尚无真实identity pins

默认 `launcher.py check-local` 仅核本地源码/收据。原worker、audit及历史32例收据逐字保持；capture-entry只改新guard常量，原90秒稳定观察、实时source/硬件输入/UDC/MaxPower/current_avg读取保持。原launch-once、ready门、status/fetch及未知不重发流程保持，使用新的host/remote输出目录。

新profile必须来自实际501 postboot及adoption：完整boot97811/logdump7e5d、#501、param Y+唯一cmdline、startup/native/硬件500、R8、相机481、EUD producer检查全部通过；采用 `/var/lib/samurai/image501-gauge-live-001-adopted/boot-id-private.txt`。新endpoint要求 `postboot_Image501_passed=true`，原strict kernel184密钥与IPv6参数保持，不沿旧R3 endpoint隐式取身份。

`bind-identity.py` 默认不生成任何输入。只有实际adoption成功后，显式传其 `adoption-01-private/` 和对应passed postboot目录及 `--execute-bind`，才写入独立私有runtime pins：先临时文件，用实际reviewed_identity/adopt_local复核，再原子rename至 `.../image501-activation/image501-gauge-live-001/adoption-01-private/icon-identity-pins-private.json`。全套实际原件、transport/key源码均按SHA绑定；不生成假的新boot/endpoint。缺pins时可做源码check，launch必拒。

新2组定向检查使用临时合成profile，验证新完整pair/guard/flag/endpoint拒绝门及保留代码范围；未跑旧32/12套，未访问设备或网络，没有发用户ready或启动采集。baseline receipt仅证明旧generic worker/audit范围，不能代替新501实际采集。当前没有更改或安装Phosh。
