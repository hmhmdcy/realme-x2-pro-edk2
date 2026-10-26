# Boot 封装 R2：两份实际 baseline 的只读薄审

本轮只读核对新 compact/gzip baseline 的公开和私有收据、实际执行器字节、
产物哈希与输入前后摘要。没有执行 baseline、封装工具、测试、SDK、Git 或
设备操作；不改原执行器、根导航或冻结输入。候选执行器尚待作者提供冻结路径，
本文件只记录 baseline 和下一候选的核对边界。

| 阶段 | 实际结果 | 与旧失败的区别 |
| --- | --- | --- |
| 旧 `eud-boot-packaging-review` | 第七层 compact 失败；FD 有 5 个 header 字节不同，gzip 未执行 | `-F FALSE` 跳过 ARM reset-vector 生成；失败原件与 false 收据保留 |
| `eud-boot-compact-baseline-r2` | 一次 GenFv rc0；完整 7MiB FD 逐字等 a30 | 正常默认 rebase 路径，不传 `-F FALSE`；使用私有 pre-rebase SEC 和原 PE sidecar，未手填 header |
| `eud-boot-gzip-baseline` | 一次 `gzip -c` rc0；整个 gzip 及追加 compat 的 payload 逐字等 a30 | regular fd0、原整数 MTIME；不改 gzip 头掩盖差异 |

compact 的公开收据 SHA `25e640ab…1873`、私有收据 `c81ae504…467b`，
执行器 `09b99fa6…04902`；gzip 对应 `bbc1c7e1…73c9f`、
`3de516c8…33632`、`86db76d8…726f` 均已核实际文件。
两个私有收据中 141/144 项 `inputs_before` 与 `inputs_after` 分别相等，
所列 evidence 产物 SHA 全匹配，mountinfo 不变由原执行收据报告。

原 GenFv 的绝对工具路径和 SHA 由 inspection 固定；compact 配置为 FS3、
base `0xce000000`、block `0x1000`、blocks `0x700`。SEC 输入为私有复制的
pre-rebase FFS `da8f6b97…5266c`，配原 PE `.efi` sidecar
`684fc7c8…1388a` 与 map。完整旧 SEC 出现在 `0xfe8`、55384 bytes，
SHA `825690b6…a37c0`；整个输出 FD 为7340032 bytes、
`a71478b4…bb02`。向量 `ce270014…` 和 checksum `a0f4` 是工具路径的结果，
不是执行器之后写入。

gzip 工具固定为 `/usr/bin/gzip`，argv 只有 `-c`，从 regular raw 文件 fd0
读取。只给私有 raw 设置原 MTIME1792719172；没有改压缩后头部。
raw 为7340176 bytes、`cefdcde9…fc14`；gzip 为6229964 bytes、
`b8deffe8…65d7`；gzip+原 compat 为6680790 bytes、`44625abd…e982`。
这只是原载体复现，不是 R2 firmware 或启动验收。

## 候选薄审的固定门

- inspection 以实际 a30 boot及其私有输出为准；共享 `FVMAIN.Fv` 与 a30 不同，
  不能拿它替代 baseline。main FV 有101份完整 FFS，仅 BDS 与 native-DTB
  可变，其余99份要比完整 FFS 字节，不能只比 body 或跳过 checksum。
- 冻结 BDS EFI 为 `a0e30c69…61768`，110592 bytes；native DTB 为
  `9271d9cc…14358`，115936 bytes。只允许按原 PE32/depex/UI/FFS 与
  RAW/FREEFORM 层重封装，不热改 PE、DTB 或其它模块。
- 完整 SEC 与 `0xfe8` 位置都保留；原144-byte shim、450826-byte compat、
  单字节 `0a` ramdisk 保留。
- Android v1/page2048；旧 ID 必须先按原公式核验。候选 header 只许改
  kernel_size 的 offset8..11 和 ID 的 offset576..607，其余整页保持。
- 旧 used 为6686720，原96MiB载体在这个绝对 offset 起已有非零尾部。
  `newused > 6686720` 必须失败；不得把尾部当 padding 或迁移尾部。
  新 header/payload/对齐/ramdisk 后接回原同一绝对 newused offset 以后的
  原字节，并核旧6686720以后的整尾与总长100663296保持。
- gzip 允许新内容引起压缩流、长度、CRC 改变；原 MTIME/FLG/FNAME/XFL/OS
  与固定 raw ISIZE 要核验，不能运行后热补 gzip/FV header。
- 任意工具失败、字节不符、大小越界都应留真实 stdout/stderr/中间件及失败
  收据，不能改标成功或自动换参数重跑。候选默认 `check-local` 与显式执行
  入口要分清；本薄审不会运行任何一个入口。
