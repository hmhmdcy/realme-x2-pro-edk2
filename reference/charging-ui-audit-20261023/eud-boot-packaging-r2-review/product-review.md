# 本次两 FFS 实际候选：输入与结构绑定通过

已直接只读核对本次新候选，区别于同目录此前的 baseline/执行器准备审查。
执行器为最终 `f8e9a8ae…d141bf`，它在实际执行的150项输入 before/after 中
也绑定该 SHA。私有执行收据为 `6dafe9e1…87b44`，12条封装命令全部 rc0，
41份所列物理中间件/日志/产物 SHA 全匹配，父输入前后相等；mountinfo 不变
由实际执行收据报告。本审查没有运行任何封装工具、check-local、旧 baseline
或测试矩阵。

实际候选 `boot-two-ffs-private.img` 为100663296 bytes，完整 SHA：
`4126a2978bc79b5cb95b6e1b86bb432a6b16ece627776237c163b93b323bbfcf`。
原 a30 的完整 SHA 也已重新按文件核对。独立读取两者并解析数据，仅复用已
固定 SHA 的 kernel104 parser **定义**，没有导入或运行 package 执行入口。

| 实际字节检查 | 结果 |
| --- | --- |
| Android v1/page2048、ID | 新旧均有效；整头页除 kernel_size/ID 外相同 |
| 新几何 | kernel_size6679007；newused6684672，小于旧非零尾界6686720 |
| gzip | CRC/EOF/ISIZE通过；raw7340176 bytes；10-byte metadata头保持 |
| shim / compat / ramdisk | 原144-byte shim、原compat和完整ramdisk页逐字保持 |
| 绝对尾部 | newused之后及旧LIMIT之后均与原a30同绝对offset字节相等；原LIMIT尾非零 |
| main FV | 精确BDS/native-DTB两份FFS变化；其余99份完整FFS及顺序不变，所有type/attrs保持 |
| 两份新payload | BDS depex/UI原section不变；嵌入EFI精确匹配`a0e30c69…61768`，DTB精确匹配`9271d9cc…14358` |
| SEC / compact | 完整SEC与0xfe8位置保持，container位置及整个compact header逐字保持 |
| 文件一致性 | boot解出的raw/gzip/FD/main均等本次实际物理中间件 |

机器收据见 [product-review.json](product-review.json)，SHA
`d68604f4041d69f835d5caf7ac78ddb31a5a361872d2684d28481129484ed099`；
只读审查逻辑见 [review-product.py](review-product.py)。没有复制私有二进制或
原始日志到公共叶级目录。

在此有限源码/产物结构范围内未见新增阻项。该候选尚未部署；这份通过不证明
实际启动、panel、CSR/EUD-off、host拓扑、USB500授权或回退操作已经通过。
本轮没有设备、SSH、USB、SDK、Git、激活或重启操作。
