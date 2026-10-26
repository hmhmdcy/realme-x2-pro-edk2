# B候选的一致Image私有增量方案：输入已找到，尚未链接

现有缓存足以准备“原363基线复现→只换gauge对象”的私有增量，不需要先重建778个模块、相机软件包、DTB或SDK。**这里没有构建Image或重跑B的对象/函数测试。原363逐leaf对象哈希当时没有独立保存，故下列基线链接复现是必需门槛，尚未通过。** 本叶所有WSL、mount、payload操作已停止。root随后报告已以显式Ubuntu/root和原284 helper恢复原卷并二次检查通过，以有界anchor维持会话；本叶未另行重采，也不操作该anchor。root还在隔离/tmp复现protected_regular=2下的root open-a/UID1000 sticky-file EACCES，这支持一种机制，不解释全部历史ENOENT。本文仍须root单独review批准实际基线链接，不能据此立即启动构建。

## 实际输入和不能混用的边界

| 输入 | 已实核的固定值 |
|---|---|
| Image363源码 | `ba61a62293e0f6bc5838c06f2e85e033e3d702a8` |
| 当前source354 HEAD | `5b0e7a9ac5b311a4c4fe17cf48b7ed4fc9a7b91d`，tracked工作树clean；对ba61有39项camera/DT差异 |
| 原Image | 59243008B，`15746aab311eed32478cdee4e13c1677716ff48c8a04316c9c15cf606c9d6468` |
| 原vmlinux | 190302688B，`8e2bc2bd1de55eb53c58915ec03ae25dc77c9401e137d50fccbdcc173ff4dd96` |
| 原嵌入CONFIG | `23e088a90736bbbc442c672d82b35c11bf04f7dc489f1c6afb1b03dc0d8f30ed`，私有kernel457/config363-private相同 |
| 原Module.symvers | `0837fdc36f1bd6ab16109d4852883566b8fe42e5bb640771e30afb7822779223` |
| 原bq C / 当前缓存原bq.o | `b2cd415a…aec69e` / `5976585a…f7cb7c`，91448B |
| 冻结B C | `0aa3c533bab0ec9219364af5328d353334cbf5112f97c8529aa162f95fd88ffe` |

当前build的Image/vmlinux/Module.symvers仍精确匹配363，**不代表整个O和当前HEAD可直接链接采用**。`.config`已变为`e48f834d…34df3`，与原嵌入CONFIG有8项Rust探测差异（原rustc1.99/LLVM22.1.8，当前探测为0/未启用）。已编好的B对象`6809ee2b…69e125`来自该当前配置和另一个source/O路径，只复用其W=1收据；不可直接塞入363 archive。

`link-inputs.json`已经逐项固定当前`vmlinux.a`全部3247个对象的哈希/长度与对应`.cmd`哈希，全部现存，共366794920B；bq对象恰好一个。39项后续源码差异、8项Rust探测差异均未出现在这些对象保存的依赖中。这说明后续camera工作没有通过这些记录引入built-in源依赖，但不是原363逐对象二进制认证。`final-link-inputs.json`补齐libstub的32个实际成员以及**archive外**的`init/version-timestamp.o`、`.vmlinux.export.o`、原link script/lds、kallsyms/sorttable等实际输入。不能只复制vmlinux.a这个thin文件而漏掉成员。

实际GCC为Ubuntu15.2.0-16ubuntu1、binutils2.46，与保存的compile.h一致；已安装的nightly rustc为1.99.0/LLVM22.1.8，其路径和哈希已固定。原配置为LTO_NONE、RANDSTRUCT_NONE，MODVERSIONS/MODULE_SIG/TRIM_UNUSED_KSYMS关闭；BTF/Rust代码未启用，缺pahole不是此配置的构建缺项。需要Rust路径只为恢复原Kconfig探测值，不能把探测漂移当无条件可忽略的CONFIG变化。

## 后续具体执行顺序（本次未执行）

1. 实施时沿root已恢复的显式Ubuntu/root原guard再次串行确认32GiB backing与无SDK冲突；不使用fallback UID或改变锁权限。新建独占私有目录，例如由root分配的`/home/cy122/charging-management-20261023/<fresh-gauge-build>/`。不在只有约4.47GB余量的full282卷内再复制O；本次读取到home余量约835GB。原卷只作输入。
2. 把现O以保留文件属性的**独立副本**复制到私有`build/`，禁止hardlink或指向共享O的可写symlink。复制原396项`input-initramfs363/`和private tmp；396项kind/mode/uid/gid/content已经与363原manifest逐项相同。保留原三枚内嵌BT模块，不执行modules或modules_install。
3. 从固定ba61 Git对象只读导出到私有`source354/`，不是对共享HEAD checkout/reset。对导出文件校验Git内容；仅对与现source354字节相同的文件继承原mtime，避免archive统一时间导致无关重编。39项不同文件使用ba61原bytes。此步骤只写新私有源；没有.git时显式使用`LOCALVERSION=+`，保证原release。
4. 在**单独mount namespace且先设递归private propagation**后，仅在该namespace把私有source354/build/input-initramfs363/tmp映射到原四个canonical路径。这样保存的绝对include路径、DWARF comp_dir、thin archive和`.cmd`无需重写，写入落在私有副本，外部全局共享挂载不变。这不是SDK绑定；该namespace隔离本身也须先验证，当前未执行。若不能证明不传播，停止，不用全局bind代替。
5. 私有`.config`恢复精确23e088原bytes，保留原Module.symvers作为ABI参考。环境固定如下。先运行ba61自己的olddefconfig/prepare，要求CONFIG全文件仍精确23e088；只恢复8个Rust值，不能接受新symbol/comment/编译器探测等其它变化。

```sh
# 只供后续root审核的私有namespace内命令；此轮未运行。
export PATH=/home/cy122/.rustup/toolchains/nightly-x86_64-unknown-linux-gnu/bin:/home/cy122/.cargo/bin:$PATH
export RUSTUP_HOME=/home/cy122/.rustup
export KBUILD_BUILD_USER=builder KBUILD_BUILD_HOST=samurai KBUILD_BUILD_VERSION=363
export KBUILD_BUILD_TIMESTAMP='Tue Oct 20 03:03:47 UTC 2026'
export TMPDIR=/mnt/samurai-full282/tmp
unset KBUILD_EXTMOD KBUILD_OUTPUT KCONFIG_CONFIG SOURCE_DATE_EPOCH
make -C /mnt/samurai-full282/source354 O=/mnt/samurai-full282/build \
  ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- LOCALVERSION=+ W=1 -j4 olddefconfig prepare
```

6. **先不放B。** 在该私有副本中用原bq源和原`.cmd`做一次原bq对象再现，要求等于缓存`5976585a…`。这是后续采用时的定向构建门，本次未重跑。随后用正常Kbuild `Image`目标做私有基线链接，不加modules、dtbs或安装目标；要求3247个leaf及32个libstub成员全哈希不变、原initramfs完全不变，输出vmlinux/Image分别精确8e2b/15746。保存实际编译/链接命令与变更leaf清单。不能只因make返回0、当前vmlinux.o存在或vermagic相同而跳过这门。

```sh
make -C /mnt/samurai-full282/source354 O=/mnt/samurai-full282/build \
  ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- LOCALVERSION=+ W=1 -j4 Image
```

7. 只有基线门通过，复制冻结B这**一个C**到私有源并核0aa3哈希，编译`drivers/power/supply/bq27xxx_battery.o`后链接`Image`。同一3247-member集合/顺序中，只允许该对象改变；32个libstub、usr/initramfs对象和其它3246个leaf必须逐字节相同。正常导出表、kallsyms、relocations、System.map、build-id及最终链接容器会随地址改变，不能要求最终Image中其它绝对地址原封不动，也不能把这些链接产物差异算成新增功能。
8. 新Image应另给root审核的构建身份；若改变KBUILD_BUILD_VERSION/TIMESTAMP，额外允许的真实metadata对象是`init/version-timestamp.o`（在最终link script第78/189行直接加入，**不是**3247-member archive内的`init/version.o`）。保持CONFIG、UTS_RELEASE和现模块vermagic，不能伪称新字节仍为原Image363。新的uname version/hash要进入届时的新guard，当前guard不改。

## 相机ABI与真正剩余门槛

formal481 wrapper逐项映射到现存441 r4三KO和468 build2 sensor，哈希/现存ELF/vermagic/导入都实核于`abi-payload.json`。core84个、sensor70个导入全在原363符号表；CAMSS179个中10个由当前camera组提供；m2m95个中12个由当前组、25个由后续v4l2-mem2mem/vb2依赖提供。后两类本来就不全属于原363 Module.symvers，不能为“全等”而将新camera导出混入新Image。依赖KO已按441实际构建收据读缓存，但本次没有认证当前设备依赖文件bytes。

此方案保留原内核全部非gauge输入和公共headers、CONFIG、release、原built-in exports，并且不重建/安装任何camera、CCI、vb2或BT模块。未来还须核新Image的built-in export集合/namespace/签名语义不变，原模块导入仍可由原built-in与原已安装模块组满足；MODVERSIONS为off，零CRC不能另当类型ABI证明。新Image的模块文件保持与届时fresh设备清单相同，最终装载/开流仍属未来验收。

目前没有发现需补下载的构建输入；真正尚缺的是**未执行的基线再链接一致性证明**以及未来私有namespace映射确实不传播的执行前检查。如果基线不复现，停止在该门，不接受新B Image、不把失败解释成必须刷机。先定位哪个leaf/生成输入或工具发生漂移；若无法从原vmlinux/现缓存恢复对应性，最小可信重建范围才退到ba61的built-in集合+libstub+exports/kallsyms/version metadata，不涉及778个模块、DTB、SDK、rootfs或相机recipe。不能直接链接5b0当前O冒称单gauge变化。

B仍默认关闭；未来启用需独立审核`bq27xxx_battery.samurai_instant_current=1`，本方案没有改bootargs、DTB、当前4126 boot候选或FAT/分区。003净放电和后来SDP100轻负载正净流/UPower Charging是不同真实窗口；这里不重算时延、不承诺B改善图标或提高USB预算。
