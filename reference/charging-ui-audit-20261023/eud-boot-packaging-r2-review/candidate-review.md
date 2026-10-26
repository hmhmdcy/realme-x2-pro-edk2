# 两 FFS 候选执行器：冻结字节薄审

已只读审查最终 `package.py` SHA
`f8e9a8aeb7b92c87be4cf66f8a99d950b6247146cf913b5971734bf496d141bf`，
在本次静态代码和已有 baseline 收据范围内，未见新增阻项。原 f0 完整原件保留；
新旧实际字节仅增加 `sys.dont_write_bytecode=True` 一行，阻止非 `-B` 导入
旧 helper 时产生源目录 pycache。没有重新执行 check-local、baseline、测试或
封装工具。根已独立授权作者的一次私有封装；本审查不执行该授权。

已核对的实际代码门包括：

- 默认只读分支与显式 `--execute-two-ffs` 分开；唯一私有输出目录存在即拒绝。
  所有封装输出均指向该目录；没有部署、设备、传输、SDK、Git、make/AutoGen
  或 Image 编译路径。
- 原 Android ID 在工具前验证；EFI、DTB、工具、原 parser/helper 和两份成功
  baseline 的精确摘要被绑定。原 source/cache/父输入及 mountinfo 前后不符
  不能通过。
- 只重封装 BDS 的 PE32/原 depex/UI 和冻结 native DTB 的 RAW/FREEFORM。
  main FV 校验精确两份完整 FFS 改变、其余99份完整字节和顺序不变，并校验
  所有 type/attrs、原 BDS depex/UI、EFI/DTB 精确 payload。没有忽略 checksum
  或只比较 body。
- 使用已通过的正常 GenFv SEC/PE sidecar 路径，未传 `-F FALSE`，未热补
  reset-vector/FV header。完整 SEC、0xfe8、容器位置、整个 compact header
  与固定 7MiB FD 长度均有比较门。
- 原 shim、compat、ramdisk 整页保持；gzip 仍是 regular fd0、仅 `-c`、原
  MTIME，工具输出头须等原件。新流由工具正常计算 CRC/ISIZE，随后解压复核。
- `newused<=6686720` 在写 boot 前检查。header 只更新 kernel_size/ID；
  新有效 prefix 后接回原同一绝对 offset 的剩余字节，且分别比较 newused 后
  全尾及原 LIMIT 后全尾，总长100663296。原尾部非零，因此不能迁移或当空白
  覆盖。
- 私有 boot 以 `xb`、flush/fsync 写入后整文件读回，再解析 Android/gzip
  EOF/CRC/compat、FD/FV/FFS/section/ID，并再次执行 main 精确两变/99不变、
  SEC、shim、ramdisk、允许 header 区与绝对 tail 的比较。
- 工具与验证失败保留日志、中间件和失败状态，不自动重试或换参数。没有把
  旧 compact 失败改成成功；正常最终输入快照若无法完成，也不能将运行判为
  通过，须按不完整私有收据处理。

原 kernel104 parser 的定义及其 SHA 已只读核对，导入限于原 definitions-only
切片，没有运行其旧实验；它会核 FV 和完整 FFS header/data checksum、section
边界及 GUID 唯一性。两份新 baseline 的单独薄审保留在同目录。

这是**执行器准备**的代码审查，不是候选已经生成的收据。实际产物须在执行
终态后再绑定输入和结构；任何启动、panel、CSR/EUD-off、拓扑、USB500或
回退实效均未由此证明。本轮没有设备、SSH、SDK、Git 或任何封装执行。
