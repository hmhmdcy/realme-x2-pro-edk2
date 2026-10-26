# Image502：采用真实新 boot 的候选

仅从`image502-notify-live-001`的真实passed postboot原件采用新boot，生成：

`/var/lib/samurai/image502-notify-live-001-adopted/boot-id-private.txt`

实际执行前默认`python3 -B adopt.py`只核本地冻结输入，已真实rc0。未执行SSH/adoption，没有创建该guard，也未访问或修改现用global pointer。

## 真实执行顺序

root完成502 logdump-only激活与新boot只读采集后，在当前独占窗口执行：

```text
python3 -B adopt.py --context <本次502事务/host-context-private.json> --postboot-directory <同事务内实际passed采集目录> --execute-adopt --window-confirmed
```

常规修复/重启的一般授权沿用；window仅绑定root持有的实际当前窗口，不增加审批流程。源码固定原key、IPv6原peer29和HostKeyAlias；不做fallback。

`review`先调用冻结502 operator重核七份原件及合同，再核实际执行的collector源码/request、接收器真实退出码和完整report；重新执行同一collector audit。要求精确#502、新boot不同于当前context旧boot、完整boot97811不变、新logdump ace2、R8/相机/服务/保护、SDP/CDP、Full/FC、flagY/NOW/AVG全部合格。旧501 report或只有passed标签均不能通过。没有双分区写完成假设。

采用前必须确认现pointer仍指向实际已验501 guard，带Image501/original-key标记、boot97811及旧logdump7e5；这是本轮boot不变时必须增加的区分门。旧4126/ACA、已指新502、其它guard或混合载体拒绝。保留旧guard和所有原件。

远端单次payload在创建新guard前，重用实际502 collector进行fresh只读采集/audit并核同一新boot；随后只创建新0700 guard目录及fsync证据。不会改充电/USB/桌面或写CSR。主机保存`adoption-01-private/boot-adoption-before-image502-private.json`完整备份；待同一Popen真实终态rc0与严格回复后，再要求global pointer字节仍等于备份，最后原子切换pointer并fsync。新endpoint原件含本次真实newboot/newguard及`postboot_Image502_passed`，pointer含Image502/newlogdump身份。

同child communicate/wait尾与已验501逐字相同。缺回复、断线、非零退出或中断均保留新事务原件；该一次目录仍存在，不自动重放、不删unknown、不重建guard，也不把SSH断开当adoption成功。需要root观察原child/现有原件后决定收敛，不能从旧501 guard推造成功。

10个本轮实际函数fixture覆盖新502review、旧501/sameboot/旧logdump/改boot拒绝、旧pointer四种混淆拒绝，以及实际temp pointer并发变化拒绝、备份保留和原子发布。测试只在临时目录写合成guard/pointer原件；未访问现pointer或设备。旧501优化解释器、CDP和其它未变矩阵复用，不重跑；不是实际502采用或充电时延验收。
