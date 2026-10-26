# kernel70：资源缺失影响范围与原生硬件前提

主记录：[session70](../../sessions/70-pm8009-resource-and-touch-prerequisites.md)。
本轮只读，无内核/DTS变更、刷机、USB gadget绑定或EUD控制实验。

四份副本先在手机保存，再压缩导出：command DB5427字节、provider state907字节、
完整dmesg85404字节、runtime facts333字节；设备SHA256、gzip CRC及长度均通过。
`verify.py` 核对九份raw/text、单次数据帧、已观察关闭、起止标记/哈希/CRC、
源码快照、当前实际源码保留、最终owner状态及SHA256SUMS，不访问手机。
在保留实际WSL源码路径的工作区运行 `python3 verify.py`。

`source-audit.json`/`*.source.gz` 固定实际驱动、已激活固件DTB和Realme原厂19781树；
旧Android live DT只保存选定节点/引用和原件哈希，原件留在旧项目。
cmd-db有139条/135个唯一资源，没有F类资源；整个实际DTB及旧Android树没有这些
节点的 -supply 消费者。不能由此证明物理PM8009不存在或所有硬件供电已正确。
触摸的GENI/RMI4/总线前提尚未启用，原厂原始flags须按驱动解释。

`filesystem-capacity.json`/`logdump-offline-mdir.txt` 是原有离线镜像的只读容量核对，
空闲36737024字节，不是当前手机分区重扫或可刷完整pmOS的证明。
`source-preservation.json`/`finish-state.json` 核对实际源码、原驱动、终端和回退保留。
`windows-close-observations.json` 的关闭信息来自工具stdout/stderr；事件文件无关闭行。
部分tool-result观察输出被工具截短，完整接收保存在.raw/.txt，校验只使用完整文件。
手机/tmp原件保留到重启；残缺实时前缀不补字，未进行新的EUD实验。
