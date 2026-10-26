# 490：r34/r29 七包候选与精确 r33/r28 回退包

已离线生成并签名，尚未安装。私有 `E:/edk2-samurai-out/kernel490/repository-r1/forward/` 为5个libcamera `99990.7.2-r34`＋config/stack `0.1.0-r29` 及索引；`rollback/` 逐字节复制475当前r33/r28七包及原签名索引。每包/索引hash见 [package-r1-validation.json](package-r1-validation.json)，当前候选清单见 [candidate-state.json](candidate-state.json)。

复用已核475载荷根，只替换 `usr/lib/libcamera.so.0.7.2` 为489原件（51,262,920B，SHA256 `b345af8b1430718b8fbcbbfde95916d66312bf0fc0e1b237edfb177332818bdd`）。新签名APK独立提取后57个文件/链接项一致，仅core变化，其他56项字节、mode和链接目标保持；IPA6/签名、proxy/base、通用profile及默认配置不变。没有重新strip或重签IPA，也未加入四KO、四私有profile或个体系数。core沿用489的Meson RUNPATH归一化，其他ELF保持现状，不声称紧凑release。

初始重包验证包含主机APK签名verify、实际签名包提取与ACL/内容核验、两个源文件零fuzz/offset重放及APKBUILD语法；其收据中solver=false是当时快照。随后追加的 [缓存依赖模拟r2](cached-solver-r2-validation.json) 使用481真实forward-final r33/r28 DB/world的独立副本、host APK3.0.8与原475公钥，私有仓库文件指向490签名索引，`--arch aarch64 --no-network --simulate add` 精确七pins通过。实际stdout仅7项升级、共961包；其余954包无计划变更，原缓存与副本DB/world均逐字节不变。未禁scripts/hooks，也未绕过签名/依赖或补造providers。

[首次CLI失败](cached-solver-r1-validation.json) 原样保留：误将repositories文件的 `ndx` 指令直接传入 `--repository`，未读到候选索引；r2只改用既有481/480成功的 `--repositories-file` 合同，在新root运行。它证明缓存r33到r34的依赖计划，不是实际安装、回退或当前手机状态证明。未访问SDK（公钥仅来自私有475既有集合），未做安装、ARM loader或设备执行；489先前的ARM/loader结果仅作为该精确core的既有证据。当前设备工作基线未由本轮改变。

源码配套为 [0067补丁](0067-camera-sensor-properties-v4l2-format.patch) 和两个APKBUILD overlay，只更新487属性与488格式映射及版本/依赖。基线输入引用见 [recipe-inputs.json](recipe-inputs.json)，重放证据见 [source-recipe-validation.json](source-recipe-validation.json)。保留原Meson安装步骤及生产 `isInstalled()`；未复制/构建整套recipe，完整recipe将按原流程处理其他ELF，与本次已测二进制重包的字节保证分开。

本地入口：`measure-inputs.py` 先guard/计量，`package-cohort.py --attempt rN --build-time TIMESTAMP` 在独立ext4 `camera490-package/rN` 重包，`prepare-source-recipe.py` 生成两文件补丁/overlay。r1已完成，工具拒绝覆盖已有尝试；其实际build-time、载荷根、全部原始日志和清单保存在私有 `package-state-r1-private.json`，不要重放旧r1。未改旧冻结载荷或Git/NAV。初始README/state已逐字节保留于私有 `repack-freeze-history-r1/`；当前manifest是追加缓存模拟后的revision2。`validate-cached-solver.py --attempt r2` 是已执行的有界入口，拒绝重放已有尝试。
