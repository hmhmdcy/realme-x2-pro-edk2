# BNEP/UHID 独立固化候选

目标包 `samurai-bluetooth-host-k363-0.1.0-r0`，只补当前 k363 缺失的 BNEP 与 UHID。已完成两次独立签名构建和 [隔离 APK 载荷验证](package-validation.json)，两包均为15171字节、SHA256 `982e7aff09cb696e921b6058f5f0c6f74b06afe13ed767eda988b5ea469bec9f`。主交付见 [清单](artifact-manifest.json)；手机或原rootfs未安装，硬件功能未验收。

载荷固定为三个 `0644 root:root` 文件：

- `usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/kernel/net/bluetooth/bnep/bnep.ko`
- `usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/kernel/drivers/hid/uhid.ko`
- `usr/lib/modules-load.d/60-samurai-bluetooth-host.conf`，字节为 `bnep\nuhid\n`。

依赖仅 `bluez kmod openrc`。没有服务、安装脚本、trigger、`replaces` 或覆盖选项；不在安装中主动加载模块。BNEP 用于 PAN，UHID 用于用户态 HID 桥接；这两个模块不能作为普通 GATT 已验收的证据。

## 来源和构建条件

复用 [host-config 构建结果](../bluetooth-host-config-20261023/module-build-validation.json) 和 [原363记录](../kernel363/boot-candidate-build-validation.json)。固定源码提交 `ba61a62293e0f6bc5838c06f2e85e033e3d702a8`，原363配置仅将 `CONFIG_BT_BNEP`、`CONFIG_UHID` 从 `n` 改为 `m`。不重建 Image，也不加入额外内核改动。

`build-apk.py` 在创建输出前要求真实的 `passed` 构建报告、正确的原363记录和两份独立原件锁。它读取实际 ELF，逐项检查 AArch64 ET_REL、完整363 vermagic、`intree=Y`、build-id、模块名称、依赖、原件 hash/长度和导入符号；原363 `Module.symvers` 必须为 `0837fdc36f1bd6ab16109d4852883566b8fe42e5bb640771e30afb7822779223`，所有实际导入均须存在。旧k132模块不可作为输入。

只有这些检查通过，才在新的 Linux 文件系统目录执行配方 `package()`，核对恰好三个文件及模式，再复用203已有 `apk mkpkg` 和签名密钥路径。工具不生成或复制私钥。`APKBUILD.in` 的 SHA512 占位符只由已锁定的真实字节渲染；模板不是可直接提交的正式源包。

本次两构使用不同的空 build/output 目录，已独立核对两份签名、两包逐字一致、签名目录中的三个路径/模式和实际数据块。原363符号表在授权恢复既有284 backing挂载的同一WSL进程中只读复制；新私有副本1005354字节、SHA与固定值一致。BNEP的77项、UHID的38项实际导入均独立匹配原表，未仅采信构建报告的布尔值。两份原件的 hash、build-id与导入集合锁见 [module-inputs-lock.json](module-inputs-lock.json)。

原生 `apk extract` 复现此前265已有的共享祖先 `parent is not a directory` 失败，私有日志保留于 `bluetooth-host-modules20261023-validation2/isolated-extract.log`，没有算成提取成功。改用真正 APK3 installer 在全新隔离数据库安装本包后，三个载荷字节、0644模式、root所有权、APK owner和版本均通过，正常标志为 `f:S`，无 `f/s/x` 失败标志。安装使用 `--no-scripts --no-network --no-commit-hooks`，solver依赖仅以三条明确的 metadata-only fixture记录提供，未生成假依赖APK，也不代表依赖载荷、服务或系统trigger功能验证。

新包的 APK 路径与 JSON 路径使用不同变量，写报告后再次读回 APK hash。私有生成 manifest 中的 `independent_readback_and_isolated_install_validation_pending` 是构建阶段历史状态，已由本目录规范 `package-validation.json` 完成；设备前置检查继续待办。构建工具不覆盖已有 build/output 目录，重复构建必须改用新的目录。

## 部署边界

候选签名通过不等于现场可无条件安装。现场外部安装入口必须在调用 APK 前核对设备身份、当前内核 release、输入 manifest/签名/hash，以及三个真实目标路径、规范化路径、文件所有者和内容；有冲突就停止，不使用 `replaces` 或任意覆盖。外部检查还必须确认当前内核目录的 `modules.order` 存在。旧 APK 安装 hook 的拒绝不保证阻断事务，不能把它当作部署闸门。

父线已只读核对115的 OpenRC `modules` 服务会读取 `/usr/lib/modules-load.d`，且 boot/modules 链接存在。现有 kmod trigger 作用于 `/lib/modules/*`，只有存在 `modules.order` 才执行 depmod；缺少时可能清除 aliases，不能省略上述前置检查。BusyBox 在已有 kmod 时不重复 depmod。这里沿用既有系统机制，不附加自定义 trigger，也不复制或替换现有 `modules.order`。这些是缓存的系统行为依据，仍需现场确认当前实际路径布局和 owner。

当前窗口由父线协调，本目录工具不连接手机，不更改原有蓝牙平台包、蓝牙 helper、USB、充电或相机文件。真正模块加载、PAN/UHID 功能和卸载/恢复尚需设备窗口；普通 GATT 另行验收。
