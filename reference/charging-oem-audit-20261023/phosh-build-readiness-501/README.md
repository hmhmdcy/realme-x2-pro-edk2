# Phosh 0.57.0-r3 私有构建前提：已求解，缺11份固定载荷

**尚未安装构建依赖或编译 Phosh。** 唯一私有 root 已创建；已取得并严格验证304个包，原315包闭包仍不完整。没有改手机、原 seed、SDK、原 DB/world、原仓库配置、Image、rootfs发行产物或 Git。

## 已完成的最短路径

1. 复用了现有 Ubuntu `/usr/bin/qemu-aarch64`、已启用的 `qemu-aarch64` binfmt `POF`，以及原 aarch64-musl seed 的 GCC15.2.0-r9、musl1.2.6-r5、abuild3.18、Meson1.12。无需先下载交叉工具链/QEMU；历史 kernel214 已有相同 seed 的真实模拟编译器运行收据。本轮未运行 seed 内工具。
2. 在 `/home/cy122/charging-management-20261023/phosh-external-power-build-501-r1/root` 建立唯一0700独立副本，复制21830个普通文件、2713374932字节；每个普通文件都核了不同 inode，未用 hardlink。原 work/private/candidate/packages、家目录和签名材料没有复制；只有必要的 bin/sbin/lib/usr/etc/var，排除了 var/cache/log/tmp 内容。此前空间约822GB，复制前再次检查了充足余量；没有挂载原 seed。
3. 只用冻结 aarch64 main索引 `8408c99f…c3b119`、community索引 `86a0b6cc…dc60cd` 的新私有 file://副本，由原 x86_64 `apk.static` 默认信任验证并离线 `add --simulate`。结果315新增、0升降级/删除，总708包；压缩载荷合计165242520字节。没有 `--allow-untrusted`，没有更新 edge 索引。
4. 读取真实#501 postboot04留存的完整 APK DB，只比较实装 Phosh 的42条直接 ELF SONAME provider；私有 seed+固定闭包所选 provider 的包名及 `V/A/C/c/D/p` 与实机全部一致。只证明这42个直接 provider 的固定包元数据匹配，不代替编译后 ELF/ABI 验证。原 Phosh/UPower 两包的 `V/A/C/c/D/p` 也与缓存索引完全相等。

`private-copy-and-solver-result.json`、`closure-abi-result.json` 保留实际路径/命令/输入 SHA。原 seed 和新副本 DB/world 在 copy/solver/download各阶段均未改变。新副本此刻仍未安装任何新增包。

## 304份载荷与 noarch 边界

第一轮只按315份固定文件名下载，终态为279份取得、11份官方精确地址404、25份 `.PKGINFO arch=noarch` 与索引 `A=aarch64` 字面校验不符。最初失败源码和收据保存在 `history-download01/`；未重跑整315。

本机 apk 帮助编译关闭，因此定向读取了[官方 v3.0.8 index 文档](https://raw.githubusercontent.com/alpinelinux/apk-tools/v3.0.8/doc/apk-index.8.scd)45–46及[实际实现](https://raw.githubusercontent.com/alpinelinux/apk-tools/v3.0.8/src/app_index.c)142–144：`--rewrite-arch` 只将生成索引的 `pkg->arch` 改为指定值。原件固定在 `apk-index-source/`，未执行下载源码。

随后仅重取这25份 exact noarch文件；以真实 `apk verify` 验证全部304份签名，再以真实 `apk index --rewrite-arch aarch64` 计算索引。全部304份 `P/V/A/C/c/D/p` 与原冻结索引严格相同；版本、控制摘要和依赖没有放宽。`partial304-result.json` SHA `685990bdb580f071442c8562fea5cb1659e4e38c0fd6a1afe1a59119d4e39633`。先前一次验证索引命令漏传公钥目录造成 rc99，原日志保留；带原公钥后 rc0，不是包签名失效，也没有绕过信任。

304份已核文件和索引位于同一私有 base；它们不是一个可安装的完整315闭包，未强制装包或忽略未满足依赖。

## 11项真正缺口

| 缺失固定包 | 分类/固定包元数据中的路径 |
| --- | --- |
| gobject-introspection、gobject-introspection-dev 1.86.0-r1 | 实际 GIR工具/运行库；`src/meson.build:608/620` 在 `bindings-lib=true` 时生成 GIR/typelib，不能因 introspection 默认false而省略 |
| feedbackd-dev 0.8.9-r4 | 原 APKBUILD 直接makedepend；顶层 Meson 的 libfeedback-0.0 依赖需要它 |
| xkeyboard-config-dev 2.48-r0 | gnome-desktop-dev 的开发依赖 |
| nss-dev 3.130-r0 | evince-dev→poppler-dev 开发依赖 |
| libhwy 1.4.0-r0 | appstream-dev→appstream→vips |
| blake3-libs 1.8.7-r0 | appstream-dev→appstream-compose |
| bubblewrap 0.13.0-r0 | gnome-desktop-dev→libgnome-desktop-3 |
| ghostscript 10.07.1-r0 | evince-dev→libspectre-dev→libspectre |
| libde265 1.1.2-r0 | evolution-data-server-dev→evolution-data-server→GTK4→gst-plugins-bad |
| libjxl 0.11.2-r2 | evolution-data-server-dev→evolution-data-server→webkit2gtk-6.0 |

11项都不是42个直接runtime provider，也没有仅由 check/docs 引入的项；前三份（GIR两包+feedbackd-dev）直接挡编译/绑定生成。其余项属于正常发行开发包的依赖闭包；不能只关测试就假称完整。路径来自固定索引/已装元数据的依赖图，不是新的315项实机测试。

其它缓存进行了有限深度文件名盘点，另见739个 APK名，未发现11份精确版本。官方 v3.24 同版本池也窄查了这11个文件：GIR两份1.86.0-r1可取且签名有效，但真实控制摘要分别 `Q1Oa1X…`、`Q1q348…`，与冻结 edge 期望 `Q1OT2e…`、`Q1I3aB…` 不同，因此隔离拒绝；其余9项404。不能把“同版本”当“同原件”。当前 edge 的 GIR已为r2，未采用它。[当前官方包页](https://pkgs.alpinelinux.org/package/edge/main/aarch64/gobject-introspection-dev)

## 最小下一动作

优先找原控制摘要的三份实际编译/GIR输入，不再重放315下载或改版本。只有在原固定载荷可获得，或 root 明确另行批准一个可复审的构建输入变更后，才继续私有安装与构建。普通包配方下，强制安装304份、跳过依赖或偷偷禁用 bindings-lib 都不能形成合格替代路径。

若该前提闭合，保留原配方完整四项 `b_lto=true / phoc_tests=disabled / man=true / bindings-lib=true`。原 abuild-meson 的 prefix/libdir、plain/PIE/staticpic、`wrap-mode=nodownload` 也须保留。release 已捆绑 gvc/libcall-ui；gmobile/feedback/handy由已核包提供，不从wrap拉Git。原 check仍需xvfb-run/xmlstarlet。只构建原0.57.0-r3加已冻结五文件补丁的 Phosh/正常split产物，再核生成的动态依赖、ABI、资源/UI和回退包；不重建Image/rootfs，也不在手机安装。

最终UI目标仍是显示真实 LINE_POWER Online 的独立接电标记；原电池闪电、Battery State、UPower和充电预算/策略保持。
