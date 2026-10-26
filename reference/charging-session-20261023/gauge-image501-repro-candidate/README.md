# B501 原复现时间戳阶段

根在审读上一阶段差异证据后，明确批准另一个唯一私有阶段：固定B C（0aa3c533…fd88ffe），版本501配合原 `Tue Oct 20 03:03:47 UTC 2026` **reproducible timestamp**。本次实际执行UTC独立写入identity收据，不能将内核显示的日期称为实际编译日期。

唯一执行 `run-B.py --execute-B` 已通过：宿主 exec session23510、WSL父worker657、子namespace1231均终态0；bq目标5.64秒、Image目标47.70秒。输出 `/home/cy122/charging-management-20261023/gauge-image501-B-repro-01` 保留，拒绝重放。从已逐字复现的363基线独立复制，原基线三树、上一失败关键原件、共享关键输入及父挂载均前后保持。

只运行bq.o→Image。实际archive叶仅bq.o与身份字符串元数据init/version.o改变；其余3245叶及32个libstub保持，成员顺序精确原值。两个version对象已逐section并按整个ELF字节证明只有原#363→#501字符串变化，可执行section及其它section保持。CPIO `fc1d2772…14c9669`、gzip `319b665d…4b81678`、usr对象 `25244378…07484de` 精确原SHA，396项输入属性/数据也保持。没有手工回填产物字节。

只读ABI检查 session55948 终态0：实际ELF的15097个导出名字与symvers相符，导出类别/namespace/CRC等整行精确原值；CONFIG、release、公共header保持。原778个缓存模块均核原SHA和导入；正式481四件及七件缓存依赖共11件核SHA/vermagic/导入，未解析强导入为零。这里只认证缓存构建与符号/provider兼容；MODVERSIONS关闭时零CRC不是额外类型ABI证明，也没有新增实机装载认证。

新 Image 为59243008B，SHA `3a656c75d3b714153d77b637654c894a0418fd688cc906d59a37a41401e8cc02`；vmlinux为190304432B，SHA `d994bffab610c10288646c67b620395773397b8b801911324d173c73a92d276b`。真实路径为私有输出下 `build/arch/arm64/boot/Image` 和 `build/vmlinux`。全部.o变化另列于ABI收据：两个kallsyms与vmlinux.o是链接派生产物，只有前述bq与版本元数据涉及叶/身份变化。

编译诊断为零，B参数实际零初始化BSS、权限0444，仍默认关闭。没有模块/DTB目标、bootargs参数变更、封装、设备或部署操作，不重跑旧函数套。是否启用参数、生成启动载体和部署由根后续另行安排。

第一次只读ABI检查 session72238 因两次exec之间WSL空闲回收、原缓存卷不再挂载而终态1；并非模块内容不匹配。已保留 `abi-preflight-failure-01.json`，入口改用原284 guard在同一读取进程中挂回/核对原32GiB卷后完成上述55948。没有重建内核、修改锁权限或使用SDK。
