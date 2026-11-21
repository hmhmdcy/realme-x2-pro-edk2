# 补丁上游化流水线

整理日期：2026-11-15。本文描述怎样把 RMX1931 的补丁集合自动分流到
各自的上游路径，以及哪些部分已经实现为脚本。

适用前提：内核源树 `~/standard-arm64-v7.3.1`，上游基线提交
`09455be5a baseline: Linux v7.3.1`，补丁目录 `linux-port/patches/`。

## 0. 结论

25 个补丁不能作为同一个序列提交上游。自动审计把它们分成五类，其中
只有 4 个能直接进入正常的内核评审流程，12 个必须先做 rebase，5 个应
直接删除。

| 类别 | 数量 | 上游去处 |
| --- | --- | --- |
| `lkm-submit` | 4 | 内核子系统邮件列表，无需板级上下文 |
| `split` | 3 | 先拆分：板级 DTS 走设备提交，通用代码走子系统提交 |
| `needs-rebase` | 12 | 先重定位到拆分后的 DTS 文件，再进入上面两类 |
| `drop` | 5 | 已在上游树中，从序列删除 |
| `mesa-upstream` | 1 | 走 Mesa merge request，不进内核序列 |

## 1. 为什么要分流

上游审核按「一个补丁只做一件事」判定。当前序列把三类改动混在一起：

- 板级硬件描述（`sm8150-samurai.dts` 及其 dtsi）必须作为设备提交，
  并由 DT 维护者按 `realme,samurai` 绑定审核；
- 通用驱动改动（`drivers/tty/serial/eud.c`、
  `drivers/remoteproc/qcom_q6v5_pas.c`）应与板级无关地单独评审；
- Mesa/Turnip 改动属于另一个项目，混入内核序列会被直接退回。

此外，序列里还有 5 个改动其实已经在上游树里（`0007` RMI4 reset
GPIO、`0027` GENI I2C 延迟探测等）。带着它们提交会让审核者先花时间
指出重复。

## 2. 已实现的工具

四个脚本放在 `linux-port/scripts/`，全部只读源码、不改 git 历史。

| 脚本 | 作用 |
| --- | --- |
| `upstream-patch-audit.py` | 判定每个补丁的类型与上游状态 |
| `upstream-split-series.py` | 把板级+通用混合补丁拆成两个独立补丁 |
| `upstream-relocate-patch.py` | 把板级 hunk 重定位到拆分后的目标文件 |
| `upstream-rebase-series.py` | 在基线 worktree 上顺序重放并验证 rebase 结果 |
| `upstream-route.py` | 汇总成按项目分目录的行动计划 |
| `upstream-format-submission.py` | 补齐邮件头（`From`/`Subject`/`Signed-off-by`） |

### 2.1 判定依据

审计不使用 commit subject 匹配，因为本仓库的历史是压缩导入，subject
在第 10 个提交之后就不再有意义。真正的判据是两条 git 事实：

```
git apply --reverse --check PATCH   # 成功 = 改动已在该树中
git apply --check         PATCH     # 成功 = 改动尚未进入该树
```

第二条对串联序列不可靠（后面的补丁依赖前面的），所以审计还会在
基线 worktree 上顺序重放整个序列，只有重放后仍失败的才标记
`needs-rebase`。

### 2.2 拆分与重定位

`upstream-split-series.py` 按文件路径判定归属：路径在
`arch/arm64/boot/dts/` 下、或文件名含板级标识（`samurai`、`s3706`、
`sofef03f` 等）即归入板级补丁，其余归入通用补丁。

`upstream-relocate-patch.py` 只做一件确定的事：拿 hunk 的上下文行到
候选文件中查找，唯一命中才改写目标文件；找不到或有歧义时原样保留并
报告 `unresolved`。它不猜内容，因此不会产生看似成功却错误的补丁。

## 3. 本轮实测结果

以 `09455be5a` 为基线顺序重放 25 个补丁：

```
applied-as-is      7   直接可用
already-in-tree    5   上游已有，应删除
needs-predecessor  6   依赖前序补丁创建的文件，序列内正常
needs-human        6   需人工重写
not-kernel         1   Mesa 补丁，另行处理
```

`needs-human` 的全部是 DTS 补丁。根因是本项目把原始的
`sm8150-samurai.dts`（293 行，由 `0002` 生成）在提交 `824dc0a56` 中
拆成了 76 行的 `.dts` 加 1082 行的 `sm8150-samurai-common.dtsi`，
而 `0006`/`0008`/`0013`/`0014`/`0026` 是按单体文件写的。

### 3.0 逐条结论

| 补丁 | 结论 | 依据 |
| --- | --- | --- |
| 0001 EUD early console | 直接可提交 | 基线 `git am` 通过 |
| 0002 samurai DTS | 直接可提交 | 先落地设备描述 |
| 0003 EUD 真 console | 直接可提交 | 依赖 0001/0002 的文件 |
| 0004 EUD AHB2PHY/RX | 依赖前序 | 需要 0003 生成的 `eud.c` |
| 0005 EUD CSR 映射 | 直接可提交 | `eud_earlycon.c` 已存在 |
| 0006 CPU7 OPP | 需重定位 | 目标节点在 `.dtsi` 中 |
| 0007 RMI4 reset GPIO | **删除** | 上游树已包含 |
| 0008 S3706 touch | 需重定位 | `rmi4` 节点在 `.dtsi`:436 |
| 0009 SOFEF03F 面板 | 拆分+重定位 | 面板节点在 `.dtsi`:506 |
| 0010 DPU 启动交接 | 直接可提交 | 纯 `dpu1` 代码 |
| 0011 stalled boot/A640 | 拆分 | 混有 `.dts` 与 `dpu1` |
| 0012 DSI clock/EOT | **删除** | 上游树已包含 |
| 0013 BQ28Z610 | 需重定位 | 电量计节点在 `.dtsi` |
| 0014 QUP1 I2C | 需重定位 | I2C 节点在 `.dtsi` |
| 0015 Turnip VM_BIND | Mesa | 走 mesa MR |
| 0016 90Hz | 依赖前序 | 需要 0009 生成的驱动 |
| 0017 双刷新率 | 依赖前序 | 同上 |
| 0018 sensor-power DT 数据 | 依赖前序 | 需要 0021 的驱动 |
| 0019 sensor-power genpd | 依赖前序 | 同上 |
| 0020 remoteproc PD 名称 | 直接可提交 | 纯 `qcom_q6v5_pas.c` |
| 0021 sensor-power subdev | 依赖前序 | 需要驱动本体 |
| 0022 legacy rproc 回退 | **删除** | 上游树已包含 |
| 0023 去掉 ready 日志刷屏 | **删除** | 上游树已包含 |
| 0026 EUD opt-in | 需重定位 | `.dts` 现为薄壳 |
| 0027 GENI I2C defer | **删除** | 上游树已包含 |

### 3.1 拆分的后果

这不是格式问题。拆分把板级内容分散到两个文件后：

- 只改 `.dts` 的补丁（`0026`）现在改的是薄壳，语义仍然正确；
- 改 `&cpu7_opp_table`、`&i2c1` 之类引用节点的补丁
  （`0006`/`0008`/`0013`/`0014`）必须落到 `.dtsi`；
- `0009` 在 `.dts` 里插入面板节点，但 `.dts` 已成为薄壳，插入点消失。

这三类不能用同一条规则自动处理，所以工具把无法唯一确定的部分留给
人工，而不是强行改写。

## 4. 实际执行顺序

```
1. 删除 5 个已在上游的补丁
2. 对 12 个 needs-rebase 做人工 rebase（优先 .dtsi 归属）
3. 拆分 3 个混合补丁
4. 4 个 lkm-submit 直接准备邮件提交
5. Mesa 补丁转投 mesa 的 merge request
```

建议先做第 1 步和第 5 步：这两步没有任何风险，并且立刻缩小序列。

## 4.1 邮件头规范化

25 个补丁里有 20 个不能直接 `git send-email`：有的是手写的裸 diff
（没有 `From`、没有 `Subject`），有的缺 `Signed-off-by`。
`upstream-format-submission.py` 只改元数据，并对无主题的裸 diff 合成
`<subsystem>: adjust <file>` 形式的主题。

已核对：格式化后 diff 行完全不变（`diff_changed=0`）。在基线
worktree 上按顺序 `git am`，`0001 0002 0003 0005 0007 0010 0020 0027`
全部成功；`0022 0023` 失败是因为它们本来就已在上游树中。

实测输出：

```
patches=25 normalised=20
git am: ok=8 bad=2 (0022/0023 = already-in-tree)
```

注意合成主题只是占位：提交前必须按补丁内容改成真实描述
（`drm/msm: abort matched stalled boot` 之类），否则审核者会要求重写。

## 5. 尚未实现

- 自动 rebase 只能处理「上下文在唯一文件中存在」的情形；需要在
  拆分后的 `.dtsi` 中新增节点的补丁仍需人工定位插入点。
- 没有生成 `git format-patch` 级别的系列（缺 cover letter、版本号、
  `Link:` 与 `Fixes:` 标记）。这些应在补丁内容定稿后再补，避免
  反复改写 Commit Message。
- 未做上游编译验证。rebase 只保证 `git apply` 成功，不保证
  `.dtsi` 合并后 dtc 能通过。
- DT 绑定文档（`realme,samurai` compatible）仍缺失，提交设备 DTS
  前必须补 `Documentation/devicetree/bindings/`。

## 6. 与既有文档的关系

- [22 内核侧进入 GitHub](22-kernel-upstream.md)：fork 工作流与
  `v7.3-rc6` 的对齐；
- [23 上 GitHub 的代理问题](23-upstream-push.md)：WSL 必须清空
  `http.proxy`/`https.proxy`；
- [适配分层](LINUX-ADAPTATION-LAYERS.md)：为什么板级描述与通用驱动
  必须分开评审，对应本文第 1 节。
