# 私有封装方案：先逐字复现 a30 基线

根审核后仅执行了一次旧 a30 baseline，**第7层 compact FD 字节不一致后停止，未通过**。没有生成 R2 候选或 boot.img；gzip未运行。未运行旧 generated builder、build.sh、make/AutoGen，未重编 R2，未访问设备/SDK/Git、挂载或写共享输出。唯一目录已有失败原件，不得重放。

实际 host exec session `90615`、WSL宿主PID579，终态exit1。执行器 SHA `255e73c69eee98da87dea022e2347ccddff743d471a2b9fce2dc30c301a4e708`。mainFV/FV_IMAGE/align8/LZMA/GUIDED/containerFFS前6层全部工具rc0且逐字等a30；第7层GenFv本身rc0，但compact仅5个header字节不同，断言即停。133个父输入/共享缓存前后SHA相同。真实私有 `result.json` SHA `b6bdaa042815759447c2d36d2fdd204644d7db73efdfb3830e9481b260e23637`；简明公开收据在 `baseline-result.json`，完整原件仍只在私有目录。

差异全部是 FV ZeroVector 的 offset0..3：原 `ce270014`、新 `00000000`（3个非零字节缺失），以及 FV header checksum offset50..51：`a0f4→6e30`；其它7340027字节相同，包含所有完整SEC/container FFS。`compact-difference.json` 保存精确区间。原 B 指令为 `0x140027ce`，相对目标 `0x9f38`。

源码原因已定位而非推测数据损坏：`GenFvInternalLib.c:3651–3652` 的 `ForceRebase==0` 提前返回发生在 ARM machine 检测之前（TE路径4002设置mArm）；GenerateFvImage3071仅在mArm时调用 UpdateArmResetVectorIfNeeded并于3081–3082重新计算header checksum；2290–2298生成真实AArch64 B。故下述原计划的 `-F FALSE` 虽保存SEC字节，也跳过必要reset-vector生成，不能封存为可用FD。没有手填向量或校验值。

最短后续仅是另获批准、新唯一目录的 compact-only baseline：让原默认SEC rebase/mArm路径运行，优先使用已存在的原pre-rebase SEC及其必要私有PE/TE sidecar，保持原base/位置并要求最终SEC及整FD逐字等a30。源码路径、sidecar和具体命令须先限定核对，不能把本次失败改标通过。当前停止，不执行此建议。

`inspection.json` 是实际输入 manifest，SHA `2caa68c513fd7503e0357aa4eb392594c906c82133c6e8d5d1fd3c3e703a3b87`。它包含101个 main-FV 完整 FFS 的位置/大小/原字节 SHA、standalone 极性 SHA、工具与配置/来源 SHA、容器/SEC、gzip 和 Android 几何。`inspect-inputs.py` 只读生成此调查；名称已避免遮蔽 Python 标准库。

## 固定原件

- 精确回退为 `E:/edk2-samurai-out/charging-management-20261023/usb-boot/boot-charging-usb-dt.img`，100663296 bytes，SHA `a30fb4440726e1c3ab80ad65277db4e57fec9a0924380cc07830a5c6e69ec280`。更早389不是本轮回退。
- a30 对应私有 `usb-boot/firmware/fvmain-candidate-private.Fv`：32461056 bytes，SHA `899e0c84c7003941e3b900039445272ad7eebefc07a7706135e0051ca7b7bc01`；私有 `firmware-candidate-private.fd`：7MiB，SHA `a71478b42db56f46aeda543031b95743f851d175e5771a3f133991beecdfbb02`。两者均逐字匹配直接从 a30 解开的实际内容。
- 冻结 R2 EFI：110592 bytes，SHA `a0e30c69b91f5605c07136f3f0c6900434f99d72159c5c61ac01db47fc061768`。候选 native DTB：115936 bytes，SHA `9271d9cc33b3701ad0675c6345d43e9a5c404aa6c192126edc3eb715b0914358`。它们只做来源核对，下面 baseline 不使用它们替换任何 FFS。

共享 `FVMAIN.Fv` 已被旧 builder 恢复为32455680-byte旧输出，不能当基线；其 `.txt` 报告和 FFS中间件仍是 a30 的版本。方案只从实际 a30/其已核私有输出提取输入。

## State、SEC 和完整 flags

main FV 是 FS2 `8c8ce578-8a3d-4f1c-9935-896185c32dd3`，原 `FVMAIN.inf` 的 block size `0x40`、NumBlocks `0`（自动大小）、attributes/文件顺序保留，只替换 `EFI_FILE_NAME` 为私有输入路径。实际101个 FFS 均 State `0xf8`；GenFvInternalLib.c:441–442 对 erase=1 的输入会反相 State。因此提取完整 FFS 后，仅将 byte23 `f8→07` 转回 standalone 极性，原 header/data checksum 不改。header checksum 按定义先将 byte17（data checksum）和 byte23（State）置0再验算；转换前后都满足。101份转换后的**完整字节**全部与原 standalone 缓存一致，未以忽略 checksum/代码差异放行。

compact FV 是 **FS3** `5473c07a-3dcb-4dca-bd6f-1e9689e7349a`，`FVMAIN_COMPACT.inf` 固定 base `0xCE000000`、block `0x1000`、blocks `0x700`。a30 SEC GUID `8af09f13-44c5-96ec-1437-dd899cb5ee5d` 位于 `0xfe8`，已经 rebased；其 body 确与 pre-rebase 缓存不同。必须提取实际 a30 SEC，保留其 body/attributes/位置，并对本次 compact GenFv 使用 **`-g FS3 -F FALSE`**：原 base 不变，源码 FfsRebase:3651–3652 明确跳过重定位，避免对已重定位 SEC 再改写。不能重做 SEC 或复用 pre-rebase 缓存冒认完整字节保持。

## 待根审核的最小 baseline 执行器

`baseline-draft.py` 默认或 `--check-local` 只核输入和旧 Android ID，打印完整 argv；在实际执行前，该分支已通过，输出当时的 `packing_executed=false`、`private_directory_exists=false`。根随后批准的唯一一次 `--execute-baseline` 已终止，目录 `E:/edk2-samurai-out/charging-management-20261023/eud-boot-pack-baseline-private-01/` 现在存在并拒绝重放。它没有候选路径开关，不生成 boot.img。

计划仅执行以下8条命令，所有输入/输出/配置副本均在该私有目录（工具使用 manifest 中的绝对路径和 SHA）：

1. `GenFv -g 8c8ce578-8a3d-4f1c-9935-896185c32dd3 -i FVMAIN.inf -o main.Fv`
2. `GenSec -s EFI_SECTION_FIRMWARE_VOLUME_IMAGE -o main.fv.sec main.Fv`
3. `GenSec --sectionalign 8 -o main.aligned main.fv.sec`
4. `LzmaCompress -e -o main.lzma main.aligned`
5. `GenSec -s EFI_SECTION_GUID_DEFINED -g ee4e5898-3914-4259-9d6e-dc7bd79403cf -r PROCESSING_REQUIRED -o main.guided main.lzma`
6. `GenFfs -t EFI_FV_FILETYPE_FIRMWARE_VOLUME_IMAGE -g 9E21FD93-9C72-4C15-8C4B-E77F1DB2D792 -o container.ffs -i main.guided`
7. `GenFv -g 5473c07a-3dcb-4dca-bd6f-1e9689e7349a -F FALSE -i FVMAIN_COMPACT.inf -o compact.fd`
8. `gzip -c`，**没有文件名 argv**；fd0 重定向到打开的私有 `raw.bin` regular file，fd1 为 `raw.gz`。这与 `Silicon/platform.sh.inc:7–9` 的真实 argv/重定向相同，既不是 pipeline 输入，也不是 `gzip -c raw.bin`。

baseline 采用原101个 FFS、原 BDS、原 DTB；每一步立即与 a30 的相应字节比较。原 FV_IMAGE section 为扩展8-byte header；aligned input32461064 bytes；LZMA前13字节 `5d000000010851ef0100000000`（16MiB字典、明确原输入长度）；guided data offset24、attributes1。重建 container 必须整文件等于 state-normalized 原 container。compact FD 必须完整7MiB相同，随后原144-byte shim+FD 的7340176字节 raw 必须相同，最后 gzip 和 gzip+原compat 的 payload 必须整文件相同。任一步不一致均保存结果并停止，没有白名单、裁剪、补 padding 或“只语义一致”放行。

gzip 头逐项固定：`1f 8b 08 00 44 b9 da 6a 00 03`，DEFLATE，FLG0/FNAME缺省，**MTIME1792719172**，XFL0，OS3。源 hook 从 regular raw 文件重定向；现存原 raw 文件与 a30 整文件相同且 mtime 的整数秒恰为1792719172。执行器只对私有 raw 显式设置这个旧 mtime，并记录 fd0 的 fstat；它**不把这个设置当作压缩复现证明**，仍要求工具输出的整个 gzip（包括10-byte头、DEFLATE流、CRC32和ISIZE）与 a30 完全相同。若 GNU gzip/输入行为产生0时间戳或任何其它差异就停止，不改写头掩盖。现有工具固定 `/usr/bin/gzip` SHA `2ba6fd35db5f0b5561e56b97124a08b067464b795e8e08278367f23dc539d549`。baseline 未执行，是否逐字复现仍待实际结果。

## baseline 通过后的候选范围与不可突破的边界

候选阶段另行批准、另建唯一目录。只按原 BDS `GenSec PE32` +原 depex/UI+原 `GenFfs -oi` 参数封装新 EFI，不修改 PE 或填充假造旧 EFI SHA；native DTB仅按原 RAW+FREEFORM 命令包入已冻结 DTB。main FV 的101模块中只允许 BDS GUID `6d33944a-ec75-4855-a54d-809c75241f6c` 和 native-DTB GUID `25462cda-221f-47df-ac1d-259cfaa4e326` 的完整 FFS 内容变化，其余99份完整字节均需保持。FV长度/block count/header checksum、对齐PAD，以及压缩容器的size/checksum/压缩字节随内容变化属于结构性重建，须逐层验证；不能将外层容器变化冒认第三个独立模块改动。SEC完整字节/位置保持；compact总长、原shim/compat/ramdisk保持。panel沿用冻结 R2 的源审阅，实际启动行为仍未验收。

Android v1/page2048：旧 kernel payload6680790 bytes，used结束6686720；ramdisk仅 `0a`。旧 ID 已在**任何封装工具之前**核实：SHA1(kernel payload+LE32 length+ramdisk+LE32 length+LE32 second0+LE32 recovery_dtbo0)，20-byte digest后补12个0，位于576..607。候选只允许更改 header offset8..11 的 kernel_size 与576..607的 ID；其余整个原 header page保留。compat是原450826字节，SHA `05ea54c5…2e58`，仍作为 gzip 后的原字节追加。

原96MiB载体的尾部**从6686720起立即存在非零字节**。候选新used若超过6686720，必须停止；不能假定旧尾部空白或搬移它。新used不大于旧边界时，构造新header/payload/合法页对齐/原ramdisk页后，从同一个**绝对新used offset**接回实际 a30 的剩余全部字节，并核旧6686720之后每个字节不变及总长100663296。gzip候选允许DEFLATE字节/压缩长度和CRC32随新 raw变化；raw固定7340176故ISIZE保持；原MTIME/FLG/FNAME/XFL/OS保持。不能简单重用旧CRC或旧Android ID。

Linux Image363 是外部 `/Image`，现有已绑定 SHA `15746aab311eed32478cdee4e13c1677716ff48c8a04316c9c15cf606c9d6468`，不在本封装中重编/替换；kernel104仅复用其解析器函数定义，不运行旧实验。当前没有新固件、boot验收或USB500结论。
