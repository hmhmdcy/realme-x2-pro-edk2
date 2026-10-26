# IRQ postboot / adoption：固定压缩传输入口

当前502大JSON曾两次在1703936B处传输中断，原key的native `-C`完整通过。原IRQ host R2严格比较发送argv与保存收据，不能临时加`-C`后冒称原profile通过。本叶固定组合原源码，只在原SSH executable后插入一个`-C`；key、选项、peer、命令、请求、device payload与十门audit保持。此profile尚未用于实际IRQ启动，不表示USB传输或PM故障已修复。

`host_module()`装载已钉住的原R2模块，仅替换其`transport_argv`，原`probe_payload/make_request/saved_transport/evaluate_response`函数体不改。`adoption_module()`装载原IRQ adoption，仅让其`host_module`返回同一固定profile；原review、fresh device payload、guard/pointer发布和原owned Popen/EOF/finally-wait保持。原叶没有被修改。后续icon和保护采证审核必须使用本profile，不得用无压缩原CLI审核本profile产生的收据。

默认只核来源：

```text
python3 -B profile.py
```

实际使用须先完成独立stage/activation。只有真实完成材料通过原审核后，才可在该activation目录内生成新的probe/capture输出；不能复用已存在目录或未知传输。root持当前设备窗口时：

```text
python3 -B profile.py probe --context <actual/context> --output <actual/probe-new> --execute --window-confirmed
python3 -B profile.py collect --context <actual/context> --camera <original/camera-proof> --probe-directory <actual/probe-new> --output <actual/capture-new> --execute --window-confirmed
python3 -B profile.py adopt --context <actual/context> --camera <original/camera-proof> --probe-directory <actual/probe-new> --capture-directory <actual/capture-new> --execute --window-confirmed
```

probe/collect直接复用原adoption的`transfer()`持同一Popen到真实wait终态。原文件`adopt-stdout/stderr/child/terminal`逐字保存，再建立postboot契约名的精确字节副本；失败或畸形响应也在finally保留已有原件，不补造缺失receipt。每个输出目录另存本profile SHA。collect使用原collection专用命令，不会误走默认source-only入口。原设备payload没有增加采证查询、控制、桌面或模块操作；adopt才会沿原条件新建guard/pointer。

新定向检查覆盖两个命令只有`-C`差异、原saved_transport接受正确profile并拒绝旧argv/错input、原R2拒绝压缩收据、实际本地子进程在fake SSH边界上的同child wait/非零原包保留、原adoption函数/设备payload相同、缺材料零输出及默认零设备访问。没有重跑原18/20等矩阵，没有手机、SDK或构建卷操作；测试中的身份和JSON始终是明确合成fixture。

首轮6个方法中5个通过；缺材料case错误预期FileNotFoundError，实际原validator先以ValueError拒绝，未创建输出。原失败保留于`history/initial-test-result.json`，生产源码没有为此放宽。只修fixture的文件名/异常预期并重跑该1个方法，含默认入口检查；其余5个方法经AST主体逐字核对复用原通过结果，汇总在`test-result.json`。
