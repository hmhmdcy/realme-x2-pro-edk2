# EUD boot-only 新 boot：只读采集器候选

本叶只为候选 boot `4126a297…bbfcf`、保留 Image363 准备一次新 boot 取证。尚未运行设备采集，不建立或采用新 guard，不做 SSH/USB/SDK/Git、CSR MMIO、配置/限额写入、服务启停、重启或自动恢复。默认入口为 `python3 -B payload.py --check-local`，只做本地 AST/hash 检查。

## 与 root 的最小接口

`contract.json` 给出完整字段/argv。`payload.py` 不实现网络或 endpoint 发现。root 先独立验证实际独占窗口、**原 pinned key/严格 host-key 的新 endpoint**，再用显式 `--emit-payload --execute --window-confirmed --original-key-verified --new-endpoint … --context-private … --camera-private …` 准备私有 Python 源；这一步只输出源，不发送或执行。

输入为 session 的 `samurai-eud-fastboot-context-v1`。准备器从 context 同目录 `files.guard.path=guard-private.json` 取精确 raw guard，核其 hash 等于 files.guard.sha256 与顶层 guard_sha256，guard transaction/token/boot_id 对应 context transaction/token/old_boot_id。身份 pin 来自这份原 fresh guard 的 SoC/raw-compatible hash、rootfs hash和精确k363 version，**不重新使用旧R7 guard的boot值**。相机481正式wrapper raw必须为 `1c458491…f4705`。两者及context hash嵌入私有payload。

root将精确payload沿自行核准的传输送到：`python3 -B - --execute --window-confirmed --new-endpoint <同一实际endpoint>`。该endpoint字符串是外部传输核准的关联证据，采集器不能自行认证它或原key。normal未优化Python为必需；若 optimize 非零，入口直接拒绝。

## 实际读取与检查

1. 先核实际新boot UUID≠context oldboot、aarch64、精确release/version#363、rootfs hash、SoC serial raw hash、compatible raw hash含realme,samurai、taint0。不符合则不会读分区或映射RAM。
2. boot96MiB完整hash必须4126，logdump64MiB完整hash必须aca0；均 O_RDONLY 并核实际BLKGETSIZE64。Image363 `15746aab…d6468` 的关联来自既有kernel365完整FAT/logdump及mcopy `::/Image` 收据，不拿uname冒充Image hash，也不新增FAT解析器。
3. 固定R8 manifest `320316c3…c10a1f`、全部installed_files、三module磁盘/实际live note相等、native retained、helper absent；取前后fresh telemetry、保护状态、真实source/native、charger限额和UDC只读状态。未知/ENODATA/零预算明确为not-ready，不填100。SDP按实际native≤500mA；CDP/DCP的合法1.5A、现observer Type-C1.5/3A不被旧100压低。输入≤min(900mA,实际budget)，CC≤250mA，CV≤8.725V及现温区帽；保留Full精确hold语义、PF_EN继承0和完整error/fault/timeout门。启动MaxPower仍100，不发500申报。UDC configured不据此认证物理供电或host拓扑。
4. 相机481 wrapper全部files/packages、三模块磁盘/loaded note及468 sensor note/live、四PM suspended、m2m/core idle。m2m允许已完成的jobs及注册provider的owner_refs=57，不把该引用误判为活动任务。四UID10000服务读取本次实际PID/startticks/state/exe/cmdline，完全不硬锁旧PID。附OpenRC/remoteproc/蓝牙存在与当前boot相关faults；启动未就绪只记真实失配，不自动等待/重启服务。
5. 查DT COM节点status disabled、实际cmdline/DT bootargs无EUD console及任何earlycon、无bound qcom_eud_com/ttyEUD/active EUD console producer。缺字段不会捏造为clean；host拓扑由root另取。

## reserved RAM 与收据边界

唯一 `/dev/mem` 映射是已证 reserved RAM `0x9ffe3000+0x14000`，O_RDONLY/PROT_READ；不会读0x088e1014或任何EUD CSR。只在新身份和两完整分区通过后读取。`prepare.py` 从冻结 `read-eud-ram-r8.py`（SHA `c6f42e51…80443`）静态AST取出实际READ_CODE的只读capture前段，未import旧main、旧device-window或旧boot guard；保留reserved leaf、magic/version/size和head-tail距离检查。其地址/格式来源与原实际RAM收据一致。来源和抽取段hash在source-result。

header不稳定时仍保留读到的raw；decoder不将它判通过。retained history复用原 `count=min(Head,Size)` 环形decode，不把Tail当删除位置；未证明32bit Head从未wrap或marker时效。只公布严格白名单 `[SAMURAI-EUD-OFF] attempted/write/arm/before/after/status` 行及其字段。缺失、多个、失败、非完整after0或不一致write均not-ready，**缺marker也不等于callback失败**。

一条格式/值一致的报告只表示固件报告“attempted、before/after/status”；`callback_success_independently_proven=false` 始终保留。它不是本工具制造的callback成功事实，不单独证明当前物理EUD-off、USB直连、SDP500或图标收益。真正后续拓扑和USB行为仍由root根据独立现场证据判断。

## 私有保存、失败与验证

root传输返回后调用 `payload.save_response(new_absolute_private_out, stdout_bytes, stderr_bytes, exit_code, emitted_payload_bytes)`；它只建新0700本地私有目录，保存精确源/stdout/stderr，存在时解码保存exact ring bin，并返回白名单summary。失败、非零、partial JSON也先原样留存；不清旧目录、不恢复设备、不建guard。整个raw含板身份、package db、进程和dmesg，只能私有保存；不得把完整stdout作为公开报告。

`test-result.json` 的10组使用实际候选函数，OS/MMIO边界fake：新boot/错误SoC、SDP100/500与CDP1.5A分支、输入预算/Full、ENODATA和旧timeout、实际481缓存的owner_refs57及新服务UID、producer/implicit earlycon、白名单marker缺失/失败/重复、实际只读RAM capture、实际context raw绑定、普通读取失败partial原件、私有receiver白名单。500仅为软件fixture，不是新实体试验。未重跑旧充电/保护/guard/transport大套，没有执行整个collect或设备syscall。

九个通用文件/属性/ELF-note helper来自冻结r7-postboot实际源，source-result保留hash；它们的复用不继承旧R7/440身份。候选只交代码/contract/定向测试，实际使用和新boot验收窗口由root安排。
