# Protection observer：实际Image502匹配模块

本叶只把已独审的observer源码增量链接为真实`samurai_gauge_protection`模块，不改变已冻结普通运行逻辑。源delivery `907fc124…2a304`、21实际函数/并发检查及旧codec149收据全部复用，没有重跑。原observer叶保持冻结；本叶没有安装、加载、发查询、更新manifest或操作手机。

## 实际产物

私有ko：`E:/edk2-samurai-out/charging-management-20261023/protection-query-observer-module-private-01/samurai-gauge-protection-observer-private.ko`

- SHA256：`7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044`
- 88856字节，ELF64 little-endian AArch64，模块名`samurai_gauge_protection`，`intree=Y`。
- vermagic：`7.3.0-rc6-rmx1931-samurai-k363+ SMP preempt mod_unload aarch64`。
- 完整36字节`.note.gnu.build-id` SHA256：`fc0d253d556b6ba656db263aaa50c37e3af2c7fe115b67e6b02641ae8b5733ec`；GNU build-id：`0ecb5ed3d416bedd0654fdb7e44ad5841386e8e5`。相同目录保留该note原字节。

这些是新身份，不能冒用原R8的ko `75b97e0d…783c7`、loaded note `930e0e1f…6fe76`或旧manifest。root未来的一致cohort至少需要准确替换保护ko及对应manifest，USB IRQ/其它组件由其独立交付绑定；本叶不生成或安装cohort。

## 精确构建输入与终态

复用已实际通过的USB IRQ board builder的同一intree方法，使用真实Image502私有`source354/build`，不是当前共享Image363的符号表替代：

- Image502：`085d0306…b25955`；build receipt `feb6fd2e…940e6`。
- 实际`.config`：`23e088a9…f30ed`；生成autoconf逐字匹配。
- 实际`vmlinux.symvers`：`84f5fc33…f4d47`，15097条builtin导出。
- 三份源严格绑定：provider `3e1e81a3…b8f6d`、gauge-i2c `8846d206…7c8b2`、gauge-protocol `98148c07…9c28df`。

原284 storage helper先核固定32GiB backing和helper SHA，再沿Ubuntu/root原guard。仅创建唯一私有source view与O=目录，将三份源原样复制，只在私有Makefile添加`obj-m += samurai-gauge-protection.o`。普通Kbuild生成module metadata和intree标记，没有伪造MODULE_INFO。

原唯一exec handle38225已真实rc0退出：`modules_prepare`的owned PID836 wait rc0、19.297秒；单ko的owned PID2656 wait rc0、3.344秒。两阶段均W=1、KCFLAGS=-Werror，零warning/error/undefined诊断。没有新Image、全模块矩阵、SDK、Git、设备、安装、重启、桌面变更或长期anchor；没有卸卷。出错/未知时该唯一输出必须保留并观察原handle，不能重放builder。

新对象`442f6567…b82b6`是在实际502配置下本次编译的对象，不冒用之前仅W1检查的旧配置对象`939aee63…a1965`。普通Health/TCA/Full/charger策略、六命令入口和旧fault不因链接改变；新三条仍只在root-only显式一次capture中可达，默认无新增查询，complete不是兼容/稳定或TCA分类证明。

## 符号与保持范围

实际ko的31个强未定义符号全部逐项映射到Image502 builtin export rows，没有弱符号、未解析强符号、模块provider fallback或depends项。完整映射保存在私有构建目录`Image502-import-map.json`，摘要由`ko-result.json`绑定。此核验是实际名称/导出来源与相同生成配置证据，不能代替全部类型ABI证明、内核加载或物理协议验收。

前后逐项核shared source/build配置、Image/符号表/生成头、实际502对应输入、旧保护ko/命令/源码及冻结observer源码，全部不变。构建目录为`/home/cy122/charging-management-20261023/protection-query-observer-module-01/`，原始两个日志、命令、真实child终态、对象及链接记录都保留。`ko-result.json`是链接收据；`module-identity.json`供root/UI后续一致cohort仅读绑定，没有当前运行boot或已加载成功声明。
