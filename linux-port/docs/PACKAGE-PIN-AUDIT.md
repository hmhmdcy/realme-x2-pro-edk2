# 包版本固定审计（2026-11-15）

审计对象：`/home/cy122/samurai-dist-repo`（pmaports 稳定基线 `0a02ba2`），
共 1679 个 APKBUILD。工具：`linux-port/scripts/pkg-pin-audit.py`。

## 0. 结论

真正需要处理的硬性依赖约束只有 7 条，全部集中在 `samurai-camera-config`。
其余“看起来像固定版本”的写法都是 `provides=` 自引用或子包依赖父包
版本，属于上游约定，不能改。

| 位置 | 约束 | 判定 | 处置 |
| --- | --- | --- | --- |
| `samurai-camera-config:depends` | `libcamera=99990.7.2-r33` | 不能改成 `>=`，但能用 `~` 表达同版本 | 改 `libcamera~99990.7.2` |
| `samurai-camera-config:depends` | `libcamera-ipa=99990.7.2-r33` | 同上 | 改 `libcamera-ipa~99990.7.2` |
| `samurai-camera-config:stack()` | `libcamera-*==99990.7.2-r33`（5 个） | 同上，且 stack 是元包 | 同上改用 `~` |
| `samurai-platform:depends` | `usb-signaller>=0.4.3-r9` | 下限已足够松，本地 r11 满足 | 保留 |
| `samurai-platform:depends` | `unudhcpd>=0.5.0-r2` | 上游无 0.5.0-r2，实际绑定本地仓库 | 保留，见 §3 |

## 1. 哪些“固定版本”不是依赖

以下写法出现在 `provides=` 行或子包自引用中，必须原样保留：

- `alsaucm-conf=0.$pkgver-r$pkgrel` 等 6 处：`provides=`，行内注释写明
  *versioned provides need to be below default version*，是 provider
  优先级约定。
- `udev=176`、`alpine-base=1000-r0`、`*-openrc=9999`：同为 `provides=`
  自引用。
- `pipewire-libs=$pkgver-r$pkgrel`、`unl0kr=$pkgver-r$pkgrel`、
  `libgomp=$_gccrel`：子包对本配方的精确同版本依赖，不是外部固定。

工具第一版把这些误判成 `exact`，原因是把 `makedepends=` 并进了前一个
`depends=` 的多行值。修正引号/续行处理并识别 `subpackages` 后，误报
从 65 条降到 41→最终只剩 samurai 的 7 条真实约束。

### 其余 `exact` 条目的归因

全仓库仍有 41 条 `=` 记录，逐项核对后都不是“上游包被钉死”：

- `gcc=15.2.0-r9`（`cross/*` 8 个架构 × 4 个子包）：`_gccrel=$pkgver-r$pkgrel`，
  子包对同一编译器版本的精确配套依赖，必须同步。
- `libgomp=$_gccrel`（`main/gcc4`、`main/gcc6`、`cross/gcc4-*`）：同上，
  且 `gcc4`/`gcc6` 的 `pkgver=9999` 是刻意的假版本。
- `pipewire-libs=$pkgver-r$pkgrel`（`temp/pipewire` 2 处）、
  `unl0kr=$pkgver-r$pkgrel`（`main/buffybox`）：子包依赖父包，必须精确。
- `dbus-libs=99991.16.2-r1`、`libnm=99991.58.0-r1`、`polkit-libs=9999127-r2`
  （`extra-repos/systemd/*`）：systemd 仓库与主仓库同名包的版本隔离，
  是有意的，不能放松。
- `libcamera-ipa=99990.7.2-r33`（`temp/libcamera` 自身）：子包依赖父包。
- `libmm-glib=1.25.95_git20261005-r4`（`temp/modemmanager`）：子包自引用。

这些条目若改成 `>=`，会允许同包不同 revision 混用，属于破坏一致性，
不属于“解固定”的范围。

## 2. libcamera 为什么不能简单改成 `>=`

`samurai-camera-config` 把 YAML 装进 libcamera 的 IPA 数据目录：

```
/usr/share/libcamera/ipa/camss-vfe/{s5kgw1,imx471,imx319,s5k3m5}.yaml
/usr/share/libcamera/ipa/simple/s5kgw1.yaml
/etc/libcamera/configuration.yaml
```

这些路径由 libcamera 的 IPA 模块名决定，而模块名在 0.8.0 变了：

| 项 | 0.7.2 | 0.8.0 |
| --- | --- | --- |
| 软 ISP 目录 | `src/ipa/simple` | `src/ipa/softisp` |
| `IPAModuleInfo.name` | `"simple"` | `"softisp"` |
| 安装目录 | `ipa/simple/` | `ipa/softisp/` |
| 构建选项名 | `simple` | `softisp` |
| CAMSS 管线 | 下游补丁新增 `camss-vfe` | 上游仍无 `camss-vfe` |

也就是说，一旦依赖被解析到 `99990.8.0-r1`：

1. `s5kgw1.yaml` 会被装到 `ipa/simple/`，而 0.8.0 只从 `ipa/softisp/`
   读取，软 ISP 直接回退到 `uncalibrated.yaml`，我们的调优失效；
2. `camss-vfe` 管线与 IPA 在 0.8.0 里不存在，31 个 CAMSS 补丁没有落点；
3. `configuration.yaml` 的 `software_isp` 段在 0.8.0 仍被识别，但这不能
   补偿前两项。

实测证据（本机，2026-11-15）：

- 官方 aarch64 索引：`libcamera` 及其子包均为 `99990.8.0-r1`。
- 52 个补丁在 `v0.7.2` 基线上按序累积应用：`applied=52 failed=0`。
- 同一序列对 `v0.8.0`：只有 8 个能单独 `--check`，其余因
  `ipa/simple`→`softisp` 改名、管线删除而失败。
- 反向检查：`0001`（debayer_egl 日志）与 `0007`（imx471 helper）
  已在 0.8.0 中落地，可删除；其余 50 个没有上游对应实现。

结论：**只要还要 CAMSS 硬件管线和自定义 IPA 调优，libcamera 就不能
跨 0.7.2 的主版本**。但 `-r33` 这个 revision 是本地构建序号，没有
兼容意义——把 `=` 换成 apk 的模糊等号 `~`，允许同版本任意 revision，
是目前唯一安全的放松。

## 3. `~` 的语义与验证

apk-tools `src/version.c`：

```c
case '~':
        r |= APK_VERSION_FUZZY|APK_VERSION_EQUAL;
```

`apk_version_compare_blob_fuzzy` 在 fuzzy 置位且前缀相同时返回相等。
用 apk-tools 2.14.13（Alpine 3.22 / pmOS 实际使用的版本）的
`version.c` 编译实测：

| `pkg` | `dep` | fuzzy | 结果 |
| --- | --- | --- | --- |
| `99990.7.2-r33` | `99990.7.2` | 1 | `=` MATCH |
| `99990.7.2-r40` | `99990.7.2` | 1 | `=` MATCH |
| `99990.8.0-r1` | `99990.7.2` | 1 | `>` no-match |
| `99990.7.2-r33` | `99990.7.2-r33` | 0 | `=` MATCH |
| `99990.7.2-r40` | `99990.7.2-r33` | 1 | `>` no-match |

结论：写 `libcamera~99990.7.2`（不带 `-rN`）接受同版本任意 revision，
拒绝 0.8.0；写成 `~99990.7.2-r33` 反而只认 r33，失去放松意义。

abuild 侧同样允许 `~`：`check_depver()` 的合法分隔符列表是
`"<" ">" "=" "~" ">=" "<=" ">~" "<~"`。`linux-port/scripts/check-pkg-constraints.sh`
复现了这段逻辑，已对改动后的 7 条约束返回 `rc=0`。

仓库内此前 0 个 APKBUILD 使用 `~`，所以这是新写法；仍需在构建机用 abuild
真正 `build` 一次，静态解析通过不等于能产出包。

## 4. `unudhcpd>=0.5.0-r2`

- 上游 tag 最新为 `0.5.0`（2026-06-20），源码里 `dhcp_create_response`
  仍然 `memset(&response->flags, 0, ...)`，**没有**广播标志修复。
- 我们的 `0012-unudhcpd-honor-dhcp-broadcast-flag.patch` 反向应用失败，
  确认上游未合入。
- 官方 aarch64 索引里没有 `unudhcpd` 独立条目，它只作为依赖出现；
  因此 `>=0.5.0-r2` 实际只能由本地仓库满足。

处置：保留下限。若将来上游合入广播修复并发 0.5.1，该下限会自动接受
新版本；若上游只发 `0.5.0-r2` 而不含修复，则本地补丁仍会重复应用，
那时应先反向检查再决定是否删补丁。

## 5. `usb-signaller>=0.4.3-r9`

- 上游最新 tag `v0.4.3`（2026-10-22），CHANGELOG 只修了 systemd 下的
  UDC 等待，没有我们的板级描述符/网络所有权/host 角色生命周期补丁。
- 本地配方已是 `pkgrel=11`，`>=0.4.3-r9` 已满足；未来上游若发
  `0.4.4`，`>=` 会接受，但我们的 7 个补丁需要重新 rebase。

处置：保留。若要把风险收紧，可改成 `usb-signaller~0.4.3`，避免自动
跨到未验收的新 minor；但这会阻止上游安全修复，需先做补丁 rebase 再
决定。

## 6. 落地改动

只改 `samurai-camera-config`，一次一包，便于回退：

- 顶层 `depends` 与 `stack()` 的 7 个 `=99990.7.2-r33` 改为
  `~99990.7.2`，`pkgrel` 28 → 29。
- 路径与内容不动；等真正升级 libcamera 时再改 `ipa/softisp/` 和
  `camss-vfe` 管线。

## 7. 未验证项

- `~` 约束语法已实测通过；尚未用 abuild 实际产出 `samurai-camera-config-0.1.0-r29.apk`。
- 0.8.0 的 IPA 是否能完整加载我们的 `autofocus` 段未实测；源码显示
  0.8.0 的 `softisp` 已无 `configureAutofocus`，该段会被忽略。
- 以上均为源码/索引层面证据，不能替代实机相机验收。
