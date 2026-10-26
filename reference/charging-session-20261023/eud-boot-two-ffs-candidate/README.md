# 两 FFS 私有 boot 候选：私有构建通过，未部署

冻结执行器 SHA `f8e9a8aeb7b92c87be4cf66f8a99d950b6247146cf913b5971734bf496d141bf` 经 root 与独立薄审后，唯一一次 `--execute-two-ffs` 已通过；真实宿主 exec session2380 / Linux PID473，exit0。私有 `boot-two-ffs-private.img` 为100663296B，SHA `4126a2978bc79b5cb95b6e1b86bb432a6b16ece627776237c163b93b323bbfcf`；kernel_size6679007、newused6684672，小于原绝对尾边界6686720。默认 `--check-local` 仍只读；程序没有部署、传输、重启、SDK、Git、NAV、make/AutoGen或源码编译路径。

冻结输入为实际96MiB a30 boot SHA `a30fb4440726e1c3ab80ad65277db4e57fec9a0924380cc07830a5c6e69ec280`，R2 EFI SHA `a0e30c69b91f5605c07136f3f0c6900434f99d72159c5c61ac01db47fc061768`，native DTB SHA `9271d9cc33b3701ad0675c6345d43e9a5c404aa6c192126edc3eb715b0914358`。复用冻结 `baseline-draft.py` 的原kernel104解析器和实际FFS极性/配置函数（按SHA导入，主入口不运行）。输入/工具/原件检查仍绑定原 `inspection.json` SHA `2caa68c5…a3b87`。

原 mainFV/section/LZMA/guided/container六层已逐字复现；原compact基线实际通过见同级 `eud-boot-compact-baseline-r2/result.json`（私有收据 `c81ae504…1467b`），gzip/fullpayload基线见 `eud-boot-gzip-baseline/result.json`（私有收据 `3de516c8…33632`）。这些既有层本轮没有重跑。最早 `-F FALSE` 失败原件及报告仍原样保留，不作为可用输入。

## 唯一候选路径及步骤

唯一输出目录为 `E:/edk2-samurai-out/charging-management-20261023/eud-boot-two-ffs-candidate-private-01/`；存在即拒绝重放，失败/中断留全部原件。先保存输入快照和初始result，再执行12条具体工具命令：新EFI的PE32 section和原depex/UI按原 `-oi` 规则组成BDS FFS；冻结DTB按RAW+FREEFORM原规则组成native-DTB FFS；随后原mainFV、FV_IMAGE、align8、LzmaCompress、GUIDED、container、默认GenFv compact和原gzip。没有PE尾部填充、重新链接或DTC重建。

mainFV仍是原101模块/原顺序。比较完整FFS（含头/State/校验）时，精确变化集合必须为BDS `6d33944a-ec75-4855-a54d-809c75241f6c` 和native-DTB `25462cda-221f-47df-ac1d-259cfaa4e326`，其余99份完整FFS逐字不变。所有模块type/attrs保持；BDS depex/UI原section逐字保持，新PE32 payload必须完全等于冻结EFI；DTB RAW payload必须完全等于冻结DTB。

compact使用已证明的原pre-rebase SEC+同名PE relocation sidecar+map输入，并省略 `-F FALSE`，由原GenFv正常设置mArm、重定位、生成ARM vector和checksum。最终SEC完整FFS及0xfe8位置保持，容器位置保持，整个compact header与原件相同，总长固定7MiB。不能手填resetvector/checksum。

原144-byte shim和原compat保持。gzip原argv仅 `gzip -c`，private regular fd0、7340176-byte raw、mtime_ns1792719172000000000，记录fstat；gzip10-byte头必须等原件。新DEFLATE/CRC正常随新raw计算，不借旧头修补绕过检查。

## Android与写后验证

工具运行前核旧Android v1 ID，页2048、ramdisk字节0a。新payload为新gzip+原compat。newused必须不大于 **6686720**，否则立即停，不写boot；因为原a30尾部在该绝对位置起即有非零数据。

Android header复制原完整页，只更新offset8..11的kernel_size及576..607的ID。ID用LE32长度按v1定义重新计算；使用原ramdisk完整页。新有效prefix后，从实际a30的同一个绝对newused位置接回剩余全部字节，总长必须100663296。原6686720之后及newused之后均逐字保持。

写入仅私有 `boot-two-ffs-private.img`，`xb`/flush/fsync后整文件读回，再重新解析Android/gzip CRC和EOF/compat、FD/FV/FFS/section与ID。再次验证精确两FFS集合、99完整FFS、SEC/位置、shim/ramdisk、Android头两区之外及绝对tail。父输入/源码/缓存和mountinfo前后若变，结果不得通过；所有命令、错误和hash留私有，公开只输出简明result。

外部Linux Image363（原SHA `15746aab…d6468`）不在这条构建路径中读取、编译或替换。本次实际构建与写后完整重解析均通过：只有两份FFS变化，其余99份完整FFS、SEC全字节及位置、shim/compat/ramdisk/绝对tail保持，Android头只size/ID改变；父输入与mountinfo前后保持。私有result SHA `6dafe9e10877973d62b4348fdded0236ef47944e121d10ae2da96a9e84787b44`，实际commands SHA `49ddb8dc32ebb8f404b9fce76d23a3786def49840f5adf2eaeb2a9dc62731bae`。这仅是未部署的可审候选，不代表真实boot、panel、CSR/EUD、拓扑或USB500验收通过。
