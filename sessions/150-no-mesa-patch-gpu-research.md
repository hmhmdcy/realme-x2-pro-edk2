# A640 GPU 无 Mesa 本地补丁研究

2026-10-13。用户要求查看文档并搜索、研究不修改Mesa的长期GPU修复方案。本次完成研究、原版驱动的独立进程验证与可编译的内核兼容候选，没有部署新内核或修改系统库。

关键发现：原版Mesa 26.2.4在VM_BIND失败后仍独立探测VA_START/VA_SIZE并使用SET_IOVA。因此只禁用VM_BIND不足以回到147的64 KiB内核分配器。针对本机同时拒绝EN_VM_BIND及VA_START、保留VA_SIZE，原版Turnip会使用GET_IOVA。

原版系统库在进程内模拟能力失败后完成36次像素验证、23,921,097个像素读回，零差异；首组183次GET_IOVA地址全部64 KiB对齐，VM_BIND/SET_IOVA调用为0。另覆盖4 KiB、8 KiB、60 KiB图像子分配，前方663,552字节哨兵数据保持。两组退出后各观察60秒，无新增GPU fault，累计仍3、taint0，启动与系统文件保持，收尾物理桌面存在、待取core和活动测试进程为0。

本地内核候选限定`realme,samurai`且A640，依赖147对齐修改，已在副本应用并以真实内核命令编译adreno_gpu.o，追加Werror后零诊断；checkpatch跳过DCO签名检查为0错误、0警告。主源码保持，尚未完整构建或部署。

兼容路径会失去稀疏绑定、地址捕获重放和lazy BO等能力；未来Mesa仍需检查GET_IOVA回退是否保留。完全保留功能且不维护本地Mesa补丁的路线是上游正式修复与发行版承接，不能承诺纯内核改动永久兼容所有Mesa版本。

详见[研究与路线比较](../reference/kernel150/README.md)、[候选补丁](../reference/kernel150/a640-kernel-iova-compat.patch)、[原版驱动验证](../reference/kernel150/compatibility-validation.json)、[子分配验证](../reference/kernel150/suballocation-validation.json)及[收尾](../reference/kernel150/closeout.json)。主验证的像素行数解析已从保存日志修正，未重复负载。

手机仍为147/software132加原有Mesa149库；不把研究候选写成已部署修复。原始证据归档保存在手机和主机私有目录，其他整机适配待办保持。
