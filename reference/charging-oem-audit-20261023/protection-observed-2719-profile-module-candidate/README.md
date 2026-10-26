# observed-2719 诊断 profile：独立保护模块

只编译冻结 `protection-observed-2719-profile-candidate`（delivery `45467c…a509`）的三个实际源码。复用原 observer 的 Image502 in-tree 单 ko 方法、原 kernel284 Ubuntu/root storage guard；新唯一 source-view/kbuild/output，未链接 Image、未使用 SDK、未访问手机或更改包、manifest、guard。

实际新模块为 `f6bef8a239d5101dbb710f1dd5da9642bdc7ac5e4e568e2e1193de6233a31d7e`，93,912 bytes；note SHA `bf148be50cb3a4c30bf3ab194f90163fbd47ce5dcbcaf1adb7d84392d242ecdd`。私有导出路径和完整身份见 `module-identity.json`。AArch64、intree=Y，原 k363 vermagic；actual Image502 config/autoconf 完全相同，31 个强导入全部由 Image502 builtin 导出满足，零缺失、零 W=1/Werror 诊断。源级类型 ABI、加载和实机协议验收不由这些检查证明。

唯一执行 session15608 已 exit0；原 make PID811（modules_prepare，16.318s）和2617（protection.ko，2.685s）均由原 Popen wait 到终态0，受跟踪 shared/502/旧源码和冻结三源前后不变。没有新 anchor、卸卷或存活构建进程。`ko-result.json` 保存实际命令、日志摘要和 before/after；原始构建日志留私有 `/home/cy122/charging-management-20261023/protection-observed-2719-profile-module-01/`。`method-delta.patch` 仅源 pins、唯一目录、参数身份核验和默认 source check 的差异。

`observed_2719_diagnostic` 仍默认 false，0444 只读加载参数；默认普通六命令/Health/TCA/Full 控制不变。未来只有明确加载该诊断 profile 且 fresh 完整0001=2719门通过时，0056 才选三字节；0050/52仍四字节，物理读取36字节和 checksum/length位置不变。实际旧7848的 `-90`、缺少 after0A、一次 attempt 已耗事实不改，未产生新查询。profile选择不说明2719的新位或TCA含义、稳定性或安全正常。

当前7848保护实例及97c单charger包完全保持。此模块不是可部署事务，未生成新cohort/host/request；不可为换 profile 热重载或重arm当前已消耗实例。将来如需采用，必须独立审核同一 boot/cohort/manifest与新的可查询实例窗口；回退的已存7848模块仍为 `7848cf…3044`、note `fc0d25…33ec`，本轮未操作回退。

冻结源已有11组实际C函数和18个保存报文parser案例，本轮直接引用其收据，没有重跑旧21/149/11/18矩阵；只执行新ko构建和真实配置/导入/note检查。`build-ko.py` 默认只读小源码检查，显式 `--execute` 会因唯一输出已存在而拒绝，禁止重放本次构建。
