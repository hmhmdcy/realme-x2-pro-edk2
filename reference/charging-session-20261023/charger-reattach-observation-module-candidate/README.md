# 接回短观察：实际 Image502 单充电模块构建

已将[六组定向检查通过的源码候选](../charger-reattach-observation-candidate/README.md)编译为单个私有充电模块。**未安装、未加载、未改当前manifest、手机或桌面，实际时延收益仍未验证。** 当前手机继续使用charger `10ec06fb…fa6297f`及已采用的IRQ/保护配套。

新模块只在已观察到真实断源后接回时，以250ms的after-work观察间隔运行原完整安全步骤；BOOTTIME三秒硬截止后恢复1000ms。同窗反复通知不续期，不跳过APSD/预算、保护采样、温区、Full/再充或净流判断。初始online不会触发加速。TI资料的电流每秒更新及约0.74秒的输入分类阶段不会因它消失；相对正常观察的潜在收益仅是剩余发现等待，尚未量化。详见[IRQ001相对时间线](../../charging-ui-audit-20261023/icon-irq001-timing/README.md)。

实际产物为156800字节AArch64 `samurai_mp2650`，SHA256 `97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd`；完整GNU note SHA256 `fe15a2fcb618dee0b161952cd66c32f2d5ecc9c8d50b0975242da5353c472016`。私有文件位于`E:/edk2-samurai-out/charging-management-20261023/charger-reattach-observation-module-private-01/samurai-mp2650-reattach-observation-private.ko`，不随公开文本导出。

`build-ko.py`默认拒绝执行；`--check-local`只检查已冻结源码/测试收据及实际R8八个未变头。显式构建复用原284存储检查与既有私有Image502配置、生成头和15097行builtin符号表；只新增source view与O目录，不改共享输入。没有使用PM/USB候选、SDK或新Image。源码delivery为`6aa4d49a…215138`，原R8九份源码均按原构建映射核对；只替换charger C并添加一个观察helper，八个旧头保持。

唯一原exec会话62616终态0；`modules_prepare`原child779等待0、15.978秒，单ko原child2585等待0、3.010秒。W=1、KCFLAGS=-Werror，零warning/error；intree=Y，vermagic与当前k363+精确一致，54个强导入均对应实际Image502 builtin导出，无模块provider fallback。生成配置及autoconf逐字匹配，所有追踪的共享输入、旧ko及冻结源码前后保持。详细输入/实际child/日志摘要和输出在[构建结果](ko-result.json)。这些静态检查不代替加载、运行ABI或实体时延验收。

下一步只需围绕这一只charger安排保留当前USB/保护的增量更新及精确回退，不能把本候选混进旧boot或三文件暂存事务。当前IRQ保护实例已消耗一次MAC采证；此模块不重载该provider或重武装查询。尚未生成或执行新的现场更新事务。
