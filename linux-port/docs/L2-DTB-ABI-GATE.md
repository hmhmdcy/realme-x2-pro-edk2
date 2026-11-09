# L2 DTB ABI 闸门：机器可读契约与离线验收

整理日期：2026-11-06。

本文记录 `samurai-dt-v1` 的第一个机器可读版本。它把“哪些节点/属性属于
稳定硬件契约、由哪个驱动消费、哪些变化允许作为加法”从叙述性文档变成
可执行检查，避免后续 DTB 候选在不知情的情况下改值、删节点或混入实验项。

## 1. 产物

| 产物 | 作用 |
| --- | --- |
| [`samurai-dt-v1-abi.json`](../dts/samurai-dt-v1-abi.json) | 机器可读的稳定字段、驱动消费者、UAPI、保留内存规则和允许加法 |
| [`check-dtb-contract.py`](../scripts/check-dtb-contract.py) | 用基线 DTB、候选 DTB 和 manifest 生成通过/失败报告 |
| [`test-dtb-contract.py`](../scripts/test-dtb-contract.py) | 用已知基线、加法候选、实验 profile、vendor DTB 和坏 UFS 样本自测闸门 |

manifest 当前声明 24 个资源组。2026-11-06 起基线改为 Linux v7.3.1
实机 DTB，增加标准 `mps,mp2650` 充电器，USB 控制器改用
`qcom,sm8150-dwc3`/`qcom,snps-dwc3` 的 `/soc@0/usb@a600000` 节点，
并加入 PM8150L 闪光灯：

- UFS host 和 UFS PHY；
- DSI 面板；
- MP2650 标准充电器；
- RMI4 触摸；
- GPIO 音量键；
- BQ28Z610 燃料计；
- AW8697 振动；
- ASoC 音频卡；
- SLPI sensor-power 电源；
- 主 DWC3 USB；
- 两个 CCI、CAMSS、四个 camera sensor、镜头和两个 PM8008；
- PM8150L 闪光灯控制器与 `led-0`。
- PM8150B Type-C。

它还固定了 `/reserved-memory` 的直接子节点集合、24 个装载/固件 carveout
的 `reg`/`size`/`no-map` 等字段，并声明 `/chosen`、`/memory` 属于动态
启动字段，不属于硬件 ABI。

## 2. 判定规则

检查器接受以下变化：

- 新增 manifest 明确列出的可选属性；
- phandle 重新编号后语义不变的引用；
- `/chosen` 和 `/memory` 的动态变化。

检查器拒绝以下变化：

- 删除或重命名契约节点；
- 改变稳定属性的值；
- 未登记的节点或属性新增；
- 改动 `reserved-memory` 的基址、大小、`no-map` 或记录布局；
- 在 OS-facing DTB 中出现 `qcom,msm-id`、`qcom,board-id`、
  `oppo,dtsi_no`；
- 混入 ICP、USB input、EUD route 等实验 compatible；
- 改变 Type-C 的当前 `disabled` 状态或加入实验 charging connector。

L3-02 的六个 sensor-power 属性被列为**允许加法**，并且检查值必须分别为
2,856,000/3,104,000/1,800,000/1,800,000/10,000/200,000；属性缺失时仍
保持当前驱动常量，因此旧 DTB/旧内核行为不变。

## 3. 运行方法

在 WSL 中从仓库根目录运行：

```bash
python3 linux-port/scripts/check-dtb-contract.py \
  --manifest linux-port/dts/samurai-dt-v1-abi.json \
  --baseline /path/to/os-dtb-baseline.dtb \
  --candidate /path/to/os-dtb-candidate.dtb \
  --output /path/to/contract-report.json
```

`baseline` 必须是**OS-facing** DTB，不能拿 vendor/compat DTB 当基线；后
者包含三个原厂匹配属性，按设计会被本闸门拒绝。

自测命令：

```bash
python3 linux-port/scripts/test-dtb-contract.py \
  --out /mnt/e/edk2-samurai-out/layer-adaptation-20261105 \
  --work-dir /mnt/e/edk2-samurai-out/layer-adaptation-20261105/l2-abi-contract/reports
```

## 4. 2026-11-05 结果

检查器完成 `required_any_properties` 修改后的完整自测 `passed: true`
（2026-11-05 复跑）：

| 案例 | DTB | 预期 | 实际 |
| --- | --- | --- | --- |
| baseline identity | `f7959f8a...` | 通过 | 通过 |
| L3-02 sensor additive | `89604b9c...` | 通过 | 通过；6 个新增属性全部在白名单 |
| experiment profile | `c582dd7c...` | 拒绝 | 拒绝；35 项失败，含实验 compatible、vendor 根属性、carveout 和 Type-C 变化 |
| vendor DTB as OS | `dcdd74ec...` | 拒绝 | 拒绝；6 项失败，三个 vendor 根属性被识别 |
| UFS stable-value mutation | 基线派生 `f407e1eb...` | 拒绝 | 拒绝；`lanes-per-direction` 从 2 改为 1 被抓到 |

收据：

- `E:\edk2-samurai-out\layer-adaptation-20261105\l2-abi-contract\test-summary.json`
  SHA-256 `74ed7afd7139f88dba0824a8f752f7486b6cfb41db18b067bf646b9a86c42628`；
- `E:\edk2-samurai-out\layer-adaptation-20261105\l2-abi-contract\test-run.log`
  与 summary 同哈希；
- 五个逐案例报告在
  `E:\edk2-samurai-out\layer-adaptation-20261105\l2-abi-contract\reports\`。

### 4.1 `remoteproc` → `qcom,rproc` 显式迁移

`sensor-power` 的标准生命周期改为 `qcom,rproc` 后，manifest 不再把
旧属性当成唯一必需项，而是声明二选一：

```text
required_any_properties: [[\"remoteproc\", \"qcom,rproc\"]]
```

同时用 `allowed_removed_properties` 和 `allowed_additive_properties`
只允许 `/sensor-power` 上的旧属性删除和新属性加入；其他属性删除仍按
原规则拒绝。canonical OS DTB `f7959f8a...` → 新 OS DTB
`b6faa45f7aabdf3d9a19e90bc566dd6da94fabd68c525e12072f8914030c1785`
的闸门结果 `passed=true`，语义差异只有这一对 phandle 属性。

这不是把契约改成“任意变更”：迁移白名单只匹配
`compatible = \"realme,samurai-sensor-power\"`，并保留
`vdd-supply`/`vddio-supply` 为必需属性。报告见
`E:\edk2-samurai-out\layer-adaptation-20261105\rproc-subdev-os-dtb\contract-report-r2.json`
（SHA-256 `ad2bc397...b64f`）。

manifest 当前 SHA-256 为
`52ef29204586c23498110111a0e2dacf59188dd80f828173c2b1a4e2f401e1b7`；
检查器 SHA-256 为
`2f1d217b2e79d3b8bba9f496ec6503dc3201db36fa7ee65b9b801742d8c630c8`。

## 5. 边界

这是一道**离线**闸门。通过它只证明：

- 候选 OS DTB 与基线相比没有未登记的稳定字段删除/改值；
- 已知加法属性存在且值符合契约；
- 实验项和 vendor 字段没有混入 OS-facing DTB；
- manifest 中的稳定节点仍能被解析并与驱动消费者对应。

它不证明：

- 候选 DTB 能在真机启动；
- k270/k363 两个内核都能绑定并恢复全部功能；
- 6/8/12 GiB、64/128/256 GB 等 SKU 都能启动；
- 任何桌面、发行版或硬件功能已经验收。

因此它只能作为 G1 的候选准入，不能替代 G3 的单变量启动窗口，也不能
替代 L2 双内核运行态矩阵和 SKU 矩阵。`samurai-dt-v1` 仍保持
`draft_offline_checked_not_runtime_verified`。

## 6. G3 真机补链（2026-11-05）

规范 OS DTB `b6faa45f7aabdf3d9a19e90bc566dd6da94fabd68c525e12072f8914030c1785`
已封装进 boot
`93ce2bfe5207e7cc63865a58fe637d13c345bfd14048ac7396936c6e23f30df7`
并真实启动。boot 只替换 DTB FFS，`metadata-review.json` 为
`passed=true`、`changed_ffs_guids` 只有 DTB GUID、
`non_dtb_ffs_body_changes=0`。启动后回读 boot 分区哈希与候选一致；
boot ID 为 `430ddbdc-f43d-4cfc-a2de-cfd8860e5f3f`。

将保存的 live FDT 与候选 DTB 做语义比较后，普通节点和属性没有增删；
唯一变化是 UEFI 动态替换的 `/chosen/bootargs`，另有 5 个预期的
`/chosen` 动态属性。报告
`g3-standard-os-dtb-runtime/candidate-vs-live-semantic.json`
SHA-256 为
`15ef1317d322b44b8b2b2f3f227df10f047d23e204ac5b2f4742934586992863`。

这一窗口同时证明 L3-02 的 `qcom,rproc` 绑定在规范 DTB 下仍生效：
SLPI、modem、adsp 三路 remoteproc 均为 `running`，`sensor-power` 为
`vdd=1 vddio=1`，SensorProxy 的加速度计和光线功能可 claim。

但 USB/EUD 未闭环：USB gadget 没有 attach，`usb0` 无载波；规范 DTB
虽然删除了私有 `eud-off-route`，仍保留 `serial@88e0000 = okay`，而
`qcom_eud_com` probe 会无条件启用 `CSR_EUD_EN`。因此这次只能证明
DTB 契约与 sensor 绑定进入运行态，不能证明完整 G3、冷/暖重启或
k270/k363 矩阵。manifest 的状态保持不变。
