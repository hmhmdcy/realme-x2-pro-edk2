# R2 短静态复审与私有增量链接缓存调查

本轮只读：未运行作者测试、生成器、编译器、链接器或固件工具；未访问设备、SSH、USB、SDK、Git，未修改共享树。仅在本目录生成审阅脚本和 JSON。

## R2 复审

`review.py` 独立核对冻结 R1/R2 全源与实际 CSR 收据。将 R2 的注释及精确 `Value == 0x01010101U` 谓词两行还原后，全源逐字等于已审 R1。因此 panel、event/Attempted/Cancelled 生命周期、unknown 零写、callback 全字写0及全字读回0、失败不能 veto EBS 等语义均保持。没有低字节 mask。原 DTB/R1 审阅及作者五个新案例只引用，没有重跑。

实际收据 SHA `a8f5a8c5664220ea86bd74c85c6eabafe655c325ac696ae312075b0afed411b0`：地址 `0x088e1014`、宽度32，两次完整字均 `0x01010101`，既有 polls `564370 → 564378 → 564387`，前后 fresh 健康、硬件写0。执行 CODE SHA 为 `810e220c03fab3f00fd88f2ddb742ee2c78ea5b7de09a84bf32997ef71bba6d8`。这足以支持限定 literal 接受，不证明 BeforeEBS 时写0成功、路由交还或 USB500。

结论：限定两行 R2 差异未见新增阻断。`review-result.json` SHA `bc04ce553e689629ed3c2a508c1aa46b65b25f149014429c83912b30234e750a`。

## 已定位的实际缓存

WSL repo：`/home/cy122/edk2-samurai/repo`。以下相对路径均在 `workspace/Build/samurai/RELEASE_GCC5/`：

- `AARCH64/MdeModulePkg/Universal/BdsDxe/BdsDxe/`：`GNUmakefile`、`DEBUG/BdsDxe.dll`（ELF）、`OUTPUT/BdsDxe.efi`、原 AutoGen.c/h、BdsDxe.lib、depex、map 和 `OUTPUT/static_library_files.lst` 全部保留。链接响应清单有41项，全部文件存在并已逐项记录 SHA。
- `AARCH64/Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBootManagerLib/`：原 `PlatformBm.obj`、`PlatformBootManagerLib.lib`、`DEBUG/AutoGen.h`、`OUTPUT/cc_resp.txt`、单对象清单、GNUmakefile 和编译依赖全部保留。当前实际源码/INF、所有编译依赖的现值 SHA 已记录；它们的现值不是旧编译输入逐字来源的额外独立证明。
- `FV/Ffs/6D33944A-EC75-4855-A54D-809C75241F6CBdsDxe/`：完整 FFS、PE32/depex/UI section 和工具命令 `.txt` 全部保留。

`cache-survey.py` 仅执行既有 parser 的函数定义，独立解开 SHA `a30fb444…ec280` 的实际 carrier 并比较：缓存 Bds EFI 与 a30 PE32 **逐字一致**（114688 bytes，SHA `8d72c4a69a64ab1f8e5f0b139daf34dfb0dbfe22113eb66ceac8ca839e71697e`）；缓存 FFS body 与实际模块 body 也逐字相同。旧 builder 保留的 `firmware/fvmain-candidate-private.Fv` 与 a30 解压出的 main FV 完全相同。这里未声称独立 FFS 文件 header/state 与 FV 内 header/state 完全相同。

`GNUmakefile:404` 已保留真正 gcc 链接参数及41库顺序；`407–414` 是 GenFw 转换链；`425–432` 是 GenFfs/GenSec 命令。平台库 `GNUmakefile:318–326` 是唯一 PlatformBm 编译、gcc-ar 归档操作。直接运行这些 makefile 会写共享目录，不能这样做。

实际工具存在：`/usr/bin/aarch64-linux-gnu-gcc[-15]`、gcc-ar、ld.bfd；`cc1/collect2/lto1/liblto_plugin.so`；`Common/edk2/BaseTools/Source/C/bin/{GenFw,GenSec,GenFfs}`；`BaseTools/Scripts/GccBase.lds` 及 `ArmPkg/Library/GccLto/liblto-aarch64.a`。已有 PlatformBm.obj 中编译器标识为 `GCC: (Ubuntu 15.2.0-16ubuntu1) 15.2.0`。当前工具均已记录 SHA，但尚未通过重链接证明它们能复现旧输出。BaseTools 不在当前 root 默认 PATH，应后续固定完整路径，不能借机重建工具。

完整输入/工具/依赖清单在 `cache-survey-result.json`，SHA `586ee1ee3d95da172f2f35bb1fb1ce3c350537a023089a01f878eb47fb140ea6`。

## 最短后续方案及尚缺的证明

1. 从已逐项哈希的41库建立私有只读输入快照；保持顺序、LTO选项、GccBase.lds 和工具字节。只复制必要的 Bds/平台模块缓存，不调用 build.sh、EDK2 AutoGen 或全平台 make。
2. **先用原 PlatformBootManagerLib.lib**，按 Bds GNUmakefile 的完整链接命令，仅把 ELF/map/TMPDIR 等输出指向私有目录。GenFw/GenSec/GenFfs 同样只写私有目录。必须得到与 a30 相同的 EFI/section/FFS body；不通过即停止，不进入 R2。
3. 精确复现有一个真实路径条件：a30 的 EFI 内嵌原完整 `/home/cy122/edk2-samurai/repo/workspace/Build/samurai/RELEASE_GCC5/AARCH64/MdeModulePkg/Universal/BdsDxe/BdsDxe/DEBUG/BdsDxe.dll`。实际 `GenFw/Elf64Convert.c:2203–2213` 使用输入文件名长度并直接复制 `mInImageName`。直接传入私有 ELF 路径会改变 PE 字节，不能忽略该差异后称逐字复现。可选最小处理是独立 private mount namespace 中只将该 DEBUG 路径映射到私有输出，绝不更改外部挂载/共享目录；或先证明私有链接 ELF 与缓存 DLL **整文件相同**，再以缓存 DLL 原路径只读输入 GenFw、私有输出做转换。后一办法只有 ELF 已整文件相同时才成立，否则仍缺基线。
4. 基线通过后，按现有 cc_resp、原 AutoGen 和头文件只编译 R2 的 `PlatformBm.c`，私有 gcc-ar 归档为单对象平台库。41库中仅该项替换为私有候选；其余40项不编译。然后以相同链接/封装链产出 Bds 候选。应再核 panel/其它模块及 Image/DTB 的边界；本轮不制作最终 firmware。

缓存未发现缺失项，足以尝试小范围私有增量；**尚缺实际原库 baseline relink 和 GenFw 路径处理的执行证据**，故不能写“已经可复现”或“R2 可部署”。私有 namespace 是否可用也未运行探测；这只是后续选择，不是本轮已有能力证明。没有建立新的完整固件构建流程。
