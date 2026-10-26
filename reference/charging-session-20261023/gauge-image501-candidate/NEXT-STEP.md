# B501 被拒后的最小修正设计（未执行）

当前 `gauge-image501-B-01` 必须保留为失败原件。两个Kbuild目标返回0，但一致性门拒绝了三项 archive leaf 差异；它不是已认证候选。根只授权本轮只读归因，没有再次构建或封装。

实际固定源解释了差异：`init/version.c` include `version-timestamp.c`，先在 `init/version.o` 中编入 weak `init_uts_ns`/`linux_banner`。`init/Makefile` 的 `utsversion-tmp.h` 同样消费显式 `KBUILD_BUILD_VERSION/TIMESTAMP`，所以改变身份会同时改变该archive叶和最终强定义的 `init/version-timestamp.o`。实际 version.o 只有 `.data`/`.rodata` 的身份字符串变化，可执行section完全相同。

`usr/Makefile` 把 `KBUILD_BUILD_TIMESTAMP` 作为 `gen_initramfs.sh -d` 参数，参数变化本身便触发归档更新。脚本将日期转成epoch，传给 `gen_init_cpio -t`；C程序用它替换条目mtime。实际397条中396条只有mtime从1792465427变为1792775788，全部文件数据、其它header字段、顺序和剩余原始bytes不变。gzip使用原 `-n -f -9`，两份头都没有时间字段变化；增加18B来自CPIO内容变化后的重新压缩，不能只把它称为gzip header差异。

优先下一方案是在另一个唯一私有目录从已通过基线重新复制，保留原失败与基线不变。仍仅换冻结B C，版本号为501；把 **reproducible timestamp** 显式固定为原 `Tue Oct 20 03:03:47 UTC 2026`，实际执行UTC另写构建收据。内核身份的日期将明确是复现时间戳，不能称为本次实际编译时间。这样保持gen_initramfs实际 `-d` 参数和所有原归档mtime，不需要修改、补丁或手工回填CPIO/ELF，也不需要新make规则。

相关实际调用链没有读取 `SOURCE_DATE_EPOCH`。内核文档将它用于编译器日期宏等可复现场景；它不能替代这里显式传给 `gen_initramfs.sh -d` 的 `KBUILD_BUILD_TIMESTAMP`。下一阶段继续清除此变量，避免隐含输入；原CONFIG和工具链不变。

下一次必须由根明确批准的门是：允许 bq.o 加 **已经证明只含身份字符串变化的 init/version.o** 两个archive叶，以及archive外 `init/version-timestamp.o` 身份元数据；其余3245叶和32个libstub逐字不变。version.o仍须逐section证明只替换 `#363/原日期` 为 `#501/相同复现日期`，可执行section不变。`usr/initramfs_data.cpio`、压缩数据、`usr/initramfs_data.o` 三者均须精确原哈希；396项输入属性/数据也保持。任何新的差异继续拒绝。

随后才运行已准备的只读ABI检查：实际ELF导出与symvers名字/类别/namespace行保持、release/CONFIG/public headers保持，核原778缓存模块和481相机组/其缓存依赖的导入。MODVERSIONS关闭时零CRC不是额外类型ABI证明。此处未运行该检查，未宣称新Image兼容通过，未部署、改bootargs/DTB或启用参数。

以上只是最小修正设计；当前没有第二次构建，也没有放宽既有执行器硬门。仍需根后续安排。
