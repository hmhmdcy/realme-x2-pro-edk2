# USB IRQ 板级配套独立薄审

限定离线范围未发现新增阻断。绑定作者 delivery `6a6a727d…effc51` 与 pair `1d1e65c1…cafb16`；未执行作者工具、旧16例、编译或设备入口。

独立解析实际新旧 DTB：965个旧节点、3965个旧属性的原始字节、保留表和版本均保持，只多 PMIC2 下一个 USB input 节点及五个精确属性。两 IRQ 四元组与原同机资料一致，按原父链继承 SPMI 四单元控制器；EUD／Type-C disabled 不变。实际 PMIC probe→OF populate→platform child 的源链能提供驱动要求的直接 PMIC parent；原新驱动的单节点去重逻辑复用既有独审。

新模块原件为 AArch64 ELF64LE relocatable，独立数到44个强导入、0个弱导入，intree／OF alias／vermagic符合记录。44导入的实际 Image502 builtin 满足性复用冻结导出映射收据；核命令来源、session59826及PID1022/2880终态0、W=1无诊断、跟踪输入前后不变。未再次运行构建或扫描其它模块。

这是未安装的 DTB＋模块配套候选。不能以加载成功代替真实 probe／双命名 IRQ 注册和物理边沿计数；两 IRQ 都缺失时原1秒poll仍可回退。没有新 boot／R9 cohort、APSD许可或物理时延通过结论。

`review-result.json` SHA256：`84e331194922b6967c78d7bb1cd0531fd2b23bef2b69cc70e48ca9c2212a8799`。本叶 `review.py` 只读取/hash/解析格式，不导入作者模块。
