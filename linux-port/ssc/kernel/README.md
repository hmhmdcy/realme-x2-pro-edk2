# FastRPC发布与模块生命周期修复

此目录提供完整GPL源码[fastrpc.c](fastrpc.c)、相对189已验收源码的[增量补丁](0001-fastrpc-publication-lifetime.patch)及[源码/产物锁](source-lock.json)。它针对本项目Image183同ABI内核树，不是单独的通用rootfs发布包。

修复在设备节点发布前完整初始化channel，全部节点成功后才允许open；session选择、引用获取与users挂链在同一channel锁内。初始owner引用由devres保留到RPMsg端点销毁、在途回调退出以后，失败清理包括部分子设备和DMA配置恢复。补齐文件操作表owner，模块退出按初始化逆序拆除。189 freezer等待保留。

227的11例原函数ASan/UBSan故障注入及原版负对照通过；228实际启动后验证模块refcount1→2→1、五路SSC测量和活动本地桌面Claim/Release。[228证据](../../../reference/kernel228/README.md)

外部M=构建用于快速候选验证，会产生O/4096。发布候选应使用匹配配置、headers和完整Module.symvers的真实树内目标；[受控构建器](../../../reference/kernel228/build-intree.py)在本项目树内构建，并保留完整全局符号/顺序。源码中没有插入intree声明。230已受控新启动，真正树内2abde加载与intree=Y/build-id核验通过，taint0；五流、保活1→2→1及实际活动桌面三项Claim/Release再验通过。source-lock当前运行与根文件系统默认均为2abde。[230证据](../../../reference/kernel230/README.md)

该修复没有实现SSR时的invoke/异步put_work/DMA排空，也没有证明解决共享池reclaim−22。原始189回退模块和228外建产物均私下保留，不应在有活动FD时强制卸载。
