# B501 首次私有构建：一致性门拒绝，原件保留

原363基线已经在相邻 `gauge-image363-baseline` 全字节通过并冻结。本叶随后依根授权，用另一个独立私有副本，仅替换冻结B C（`0aa3c533…fd88ffe`），显式 #501 和实际执行UTC，执行 bq.o 与 Image 两个目标。未改配置、bootargs、DTB、模块或设备。

真实宿主 exec session30191、父worker479、子namespace1324：bq目标0（5.87秒）、Image目标0（48.21秒），但叶一致性门最终拒绝，整个worker退出1。私有原件 `/home/cy122/charging-management-20261023/gauge-image501-B-01` 保留且拒绝重放。原基线build/source/initramfs三树内容/属性、父mountinfo及共享关键输入均保持。

实际archive叶差异为 bq.o、init/version.o 和 usr/initramfs_data.o。后两项超出本次硬门，故没有将产生的Image标为可采用候选，也没有运行后续ABI检查、封装或部署。`audit-abi.py` 仅为通过构建门后的检查准备，本轮未运行，不代表ABI通过。

只读ELF/CPIO归因已终态0，详见 `failure-attribution.json`。version.o仅 `.data`/`.rodata` 身份字符串变化，可执行section不变；实际源会把同一身份先编入weak定义，再编入最终timestamp对象。CPIO397条中396条仅header mtime变化，全部文件内容/其它字段/顺序相同；重新压缩后增加18B，导致ramfs对象变化。`timestamp-evidence.json` 绑定实际来源行、原/新命令及被拒产物的真实SHA，不把它们当验收通过。

最小下一方案只落设计于 `NEXT-STEP.md`：保留当前失败与原基线，未来新私有阶段采用#501及明确的原复现时间戳，以冻结原initramfs bytes；实际UTC另存收据，并仅在根批准后允许已证明的version.o身份元数据变化。相关调用链不消费SOURCE_DATE_EPOCH，不能用它替代实际 `-d` 参数。本轮没有第二次构建、放宽门或修改任何产物字节。
