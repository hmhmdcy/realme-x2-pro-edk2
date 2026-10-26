# 472 控制时序工具候选：实际构建

两个 AArch64 可执行候选已生成，只编译本阶段私有工具源码；没有重编 libcamera／IPA、上传、运行客户端或访问手机。原 [PREPARATION.md](PREPARATION.md) 和 [preparation-validation.json](preparation-validation.json) 保留其生成时“未编译”的事实；本次实际结果由 [tools-build-validation.json](tools-build-validation.json) 单独记录。

| 私有产物 | 字节数 | SHA256 |
|---|---:|---|
| `E:/edk2-samurai-out/kernel472/control-stepper-mode2-aarch64` | 520528 | `d8b73c3b88f47716d4bc92e4e587f103d48c9d57bc317293f74befdd8455ce98` |
| `E:/edk2-samurai-out/kernel472/delay-capture-mode2-aarch64` | 85480 | `efaed465acb59ef653f28e7d2a2286dd511830759223f72acde5f686f751ef52` |

最终源码与准备差异候选完全相同：

| 输入 | SHA256 |
|---|---|
| `candidate-control-stepper.c` | `cb167ab1d1df16e3682f44d44fecff8a362e321320bfde94e2f5298179d94679` |
| `candidate-delay-capture.cpp` | `8a038dedbf60dbed8da94fe7d514c443af0e30dc4ab7b50ef01f65afdd79a037` |
| `306-mode2-tools.patch` | `2c7e92808c1a57e3c7df9ca7ff9d32409e5cb04bdeda5f21df8dd9a385793097` |

该补丁只描述306副本到472候选的变化，未应用到冻结306或共享源码；构建没有产生额外源码差异。

[build-tools.py](build-tools.py) 沿用441/442 capture的 SDK chroot 编译方式，输入为既有461的 **0.7.2公开及生成 headers、core与base库**。SDK gcc／g++均为 Alpine15.2.0。C++使用 `-std=c++20 -O2 -Wall -Wextra -Werror`；C使用 `-std=gnu11 -static -O2 -Wall -Wextra -Werror`，保留原306紧凑代码已有的 `-Wno-misleading-indentation`。两个候选源码与准备时哈希一致，没有新增源修复。最初脚本在编译前因version.h按三个宏定义版本而非字符串而拒绝；改为核MAJOR/MINOR/PATCH后，两个实际编译均一次通过。

构建前实际确认 SDK `/work/libcamera` 无绑定且无编译占用。随后将461目录临时绑定到该槽并设为**只读**，结束已卸载。124个 headers、core/base/IPA/sign/proxy及 Ninja状态文件哈希前后相同，冻结306源也未改变。SDK工作副本仅位于 `/private/camss472-tools`；SDK现已交还。

stepper为静态ELF，无解释器和DT_NEEDED；capture的解释器为 `/lib/ld-musl-aarch64.so.1`，依赖 `libcamera.so.0.7`、`libcamera-base.so.0.7`、libstdc++、libgcc和musl，后续须配套既有461 runtime及通常的SONAME文件名。链接使用的core SHA为 `9b352a12…af3af`、base SHA为 `f8c3039b…5f3c4`；完整路径及SHA在收据。未运行loader或客户端，不将链接通过写成目标手机动态加载或IPC验证。

源码顺序已核：`camera.configure()`成功、buffer分配及回调连接后，capture才调用 `stepper.start()`；子进程首次mode2守卫因此处于configure之后、camera.start之前，另在SOF0复核。守卫查询的是active format/crop与controls；它不代替传感器寄存器锁存或物理帧时序测量。后续仍须由冻结前置收据提供精确 `MEASURE_KERNEL_RELEASE`／`MEASURE_KERNEL_VERSION`，并按准备说明使用独立测量profile和恢复包装器。

本次确认的范围是当前0.7.2 C++ API、标准V4L2 UAPI的编译／链接和ELF架构。**mode2曝光／增益生效延迟仍未测量，未预设为2帧。**
