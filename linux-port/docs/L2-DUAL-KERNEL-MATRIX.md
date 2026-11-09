# L2 双内核与 DTB 兼容矩阵（离线）

整理日期：2026-11-05。

本文只记录**离线 DTB 语义矩阵**，不把“旧内核能解析/接受这棵树”写成
“旧内核已经成功启动”。运行态双内核仍需 G3 窗口和回滚镜像。

## 1. 输入身份

| 角色 | 内核 release / 来源 | 内核 Image SHA-256 | DTB | DTB SHA-256 |
| --- | --- | --- | --- | --- |
| k270 实机基线 | `7.3.0-rc6-rmx1931-samurai-k132+`，build 183 | `bfa72dd920c8376ceefc458fe7202a73ddb364b6727556471d70c8d0e7ade469` | 从 `boot-partition-k270-telephoto.img` 提取，113133 B | `429db1faee1eef25abc64d8ca58e3b5db82b834de926d401343f8e05752e36e6` |
| k363 规范基线 | `7.3.0-rc6-rmx1931-samurai-k363+`，`ba61a62...` | `15746aab311eed32478cdee4e13c1677716ff48c8a04316c9c15cf606c9d6468` | canonical `dcdd74ec...`，114556 B | `dcdd74ec903520c7023fa28badcb293b2e4e26ee5bac639497c63d53536b2c8d` |
| 候选 OS DTB | k363 源拆分，去掉 vendor 根属性 | 不适用 | `f7959f8a...`，114461 B | `f7959f8a0f8bd3b89dcd67db2f1362b746cc3c4b43f403edbf6fa5347143a3f0` |
| 旧 bring-up 树（参考） | `e42788eaf...`，`7.3.0-rc6-rmx1931-samurai+` | 本次矩阵不把它当目标运行镜像 | 旧树构建 DTB，103035 B | `2a9e3cac62e7f6b8eb767230b630ddbeee546535acf9eec225bf3591dd623cbb` |

k270 的 DTB 身份与
`E:\edk2-samurai-out\kernel270\build-package-validation.json` 中的
`dtb_sha256` 一致；k270 boot image SHA-256 为
`0904b3b6616652e08709891cfdee34f1f733ff1e7022b7749bedea758108e4e8`。

## 2. 语义矩阵

| 迁移 | 值变化属性 | 新增节点 | 新增属性 | 删除属性 | 结论 |
| --- | ---: | ---: | ---: | ---: | --- |
| k270 DTB → 候选 | **0** | 12 | 3 | 3（vendor 根属性） | **加法兼容候选**；运行态未验证 |
| k363 canonical → 候选 | **0** | 0 | 0 | 3（vendor 根属性） | 只拆 vendor 身份，硬件契约不变 |
| 旧 bring-up DTB → 候选 | 8 | 74 | 4 | 4 | 不是严格加法；不能作为冻结基线 |

k270 → 候选新增的 12 个节点全部是主摄/镜头/供电/引脚资源：

- `/soc@0/camss@acb3000/ports/port@0` 及其 endpoint；
- `/soc@0/cci@ac4a000/i2c-bus@0/camera@10`、port、endpoint；
- `/soc@0/cci@ac4a000/i2c-bus@0/lens@72`；
- PM8150 的 `ldo1`、`ldo3`、`ldo7`；
- 主摄 MCLK active/sleep 与 reset pinctrl。

新增的 3 个属性是 CCI 的 `vddio-supply`（两个 CCI）和
`/soc@0/cci@ac4a000/i2c-bus@0` 的 `status`。它们没有改写 k270 已有的
属性值。删除的 3 个属性只位于根节点：
`oppo,dtsi_no`、`qcom,board-id`、`qcom,msm-id`。

## 3. 这证明了什么

- 候选 DTB 相对 k270 实际 boot DTB 是**纯加法**，没有覆盖旧内核已消费的
  属性值；
- 候选 DTB 相对 k363 canonical 只少了三个 vendor 根属性；
- 旧内核的 FDT 解析器可以把候选 DTB 解成文本树（格式层面通过）；
- k270 的 IMX319/CCI/CAMSS 代码已经存在，新增节点具备被旧内核识别的基础。

它**没有证明**：

- k270 内核用候选 DTB 能启动；
- 新增 CCI 属性不会改变旧驱动的电源时序；
- 主摄、充电、EUD、USB 和显示在 k270 + 候选 DTB 下都恢复；
- 6/8/12 GiB、64/128/256 GB SKU 都已验证。

## 4. 运行时矩阵闸门

双内核运行态至少需要以下四组，每组保留旧 boot 和旧 logdump：

| 组合 | 目的 | 状态 |
| --- | --- | --- |
| k270 Image + k270 DTB | 已知回退基线 | 已有历史实机证据 |
| k270 Image + 候选 DTB | 旧内核接受新硬件契约 | **待 G3** |
| k363 Image + 候选 DTB | 新内核对规范 DTB | **待 G3** |
| k363 Image + k270 DTB | 反向兼容性对照，预期不完整 | 可选，不能作为生产组合 |

每组至少检查：PE/EFI 启动、USB NCM/SSH、EUD/pstore、显示、输入、
UFS/模块 release 匹配、充电状态和一次冷启动回退。不得把 L2 DTB 切换
与 L3 删除启动保险、L4 删除旧 UAPI 放在同一个启动周期。

SKU 矩阵独立于内核矩阵：DTB 不写死 RAM 大小；UFS 容量由运行时发现；
安装器不能用固定 `userdata` 镜像冒充所有容量。当前只能给出静态约束，
不能把 6/8/12 GiB 或 64/128/256 GB 写成已实机通过。

静态审计已经确认候选 DTB 的 `/memory@80000000` 是
`reg = <0 0x80000000 0 0>` 的零大小占位，RAM 由 EFI memory map 提供；
没有 `userdata`、`storage-size` 或类似容量属性。审计脚本为
[`audit-dtb-sku.py`](../../scripts/audit-dtb-sku.py)（在 WSL 的
`python3` + `libfdt` 下运行），结果 `passed: true`。这只排除 DTB
写死容量，不替代不同 SKU 的实际启动。

## 5. 当前结论

`samurai-dt-v1` **仍未冻结**。离线双 DTB 矩阵已经把 k270 到候选的差异
收敛为纯加法，下一步是在确认充电长测结束或取得维护窗口后，用候选
boot `3e83798e...` 做一次 k270 运行态启动和一次 k363 运行态启动；
两者都通过后，才讨论冻结和发布每内核/固件组合的 DTB 哈希。

## 6. 收据

- `E:\edk2-samurai-out\layer-adaptation-20261105\dual-kernel-matrix\k270-embedded-trimmed.dtb`
  （SHA-256 `429db1fa...e36e6`）；
- `E:\edk2-samurai-out\layer-adaptation-20261105\dual-kernel-matrix\k270-vs-candidate-semantic.json`
  （SHA-256 `fac14db3...d410`）；
- `E:\edk2-samurai-out\layer-adaptation-20261105\dual-kernel-matrix\legacy-vs-candidate-semantic.json`
  （SHA-256 `7e237665...6db7`）。
- `E:\edk2-samurai-out\layer-adaptation-20261105\dual-kernel-matrix\sku-static-audit.json`
  （SHA-256 `7c9ea11c...3a7d`）。
