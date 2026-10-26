# 地址 helper 的平台配方增量

这里提供下一次平台源集整合时可用的 helper-only 接入器，没有构建、签名或安装 APK。现有 canonical recipe 是历史 `samurai-platform 5-r2`；充电已确认现场 R8 的模块/service，但没有提供完整、获批的当前平台源集及所有权基线。因此本目录的 `5-r3` 只演示历史 `5-r2` 的增量，不能据此回灌旧 USB、音频或充电配置，也不代表现场下一必然版本。

[配方差异](APKBUILD.patch)仅增加 pkgrel 并更新 `usr_sbin_samurai-radio-address` 的 SHA512；载荷仍属于同一个 `samurai-platform`，没有第二个 owner、新依赖、服务或安装钩子。[来源锁](source-lock.json)固定旧 helper、已通过修复 `33749acb…ffd0a7` 和已审 recipe 结构。helper 本体及原有8类错误传播验证直接复用上级目录，未重跑。

在 WSL/Linux 中直接使用实际入口（输出必须是新的、仓库外目录；无需手动复制19个源）：

```sh
python3 '/mnt/e/RealmeX2Pro edk2/reference/bluetooth-static-fixes-20261023/radio/integration/integrate-radio.py' \
  --baseline '/mnt/e/RealmeX2Pro edk2/linux-port/packages/samurai-platform' \
  --baseline-sha256 420304d2dfb56771ce917ccc14a8ee3bce6ca5daa7e8f07c2a316ea5bf6dc71a \
  --output /home/cy122/x2pro-linux/radio-platform-integration20261023-review
```

入口先核对显式 recipe 摘要、19个源的 SHA512、旧 helper 精确字节及固定 package()/依赖结构。checksum 区只允许19行字面校验和。然后在新目录生成 `source-overlay/APKBUILD`、唯一 helper 副本及其余18个源的只读引用，运行旧/新真实 `package()`，核对完整载荷字节和 mode，并确认 baseline 原件前后不变。输出保留 payload、日志、patch 和验证 JSON；recipe 在执行副本中仅规范化 CRLF，源载荷字节不变。失败保留私有证据，没有签包入口。

[实际 staging 报告](staging-validation.json)通过：前后各19项，只有 `/usr/sbin/samurai-radio-address` 字节变化，0755保留，其余18项完全一致；recipe 只有 pkgrel/该源校验和变化。错误 recipe pin、结构/钩子漂移、源校验和错误及 checksum shell 展开均在创建输出或执行 package() 前拒绝。私有最终 staging 为 `/home/cy122/x2pro-linux/radio-platform-integration20261023-final`；配方另存 `E:/edk2-samurai-out/bluetooth-static-fixes-20261023/radio/integration/APKBUILD.historical-5-r3`。

取得完整获批 baseline 后，将 `--baseline` 和显式 recipe 摘要指向它。若仍是已审19源/相同 package()/依赖结构且 helper 尚为原版，入口保持该 baseline 其它源与 checksum，仅把其实际 pkgrel 增加1；已有其它 helper 修订、版本/结构/依赖变化会立即拒绝，需重新审查合并。SHA256 pin 只证明输入对应，不能代替现场 owner/内容与当前性确认。签包时应复用现有 `apk mkpkg/sign` 工具和私钥路径，但必须先使来源锁、版本、载荷及安装前态对应完整获批 baseline；旧硬编码5-r2构建器不能直接用于此增量。

本轮未改旧 helper/recipe/source 锁、旧签名包、共享 SDK/O，也没有访问手机、SSH、WinRT、执行设备服务或构建新 rootfs。原生 BusyBox/DMS/真实地址应用仍沿用上级候选的待验边界。
