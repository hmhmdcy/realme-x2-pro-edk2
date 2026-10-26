# Image502：新 boot 只读采集候选

从实际已验的501 collector `be1b56a1…18eea` 派生，只迁移502身份与本次logdump-only上下文。boot完整SHA仍为`97811cc4…67f695`；新logdump为`ace2e261…763ed1`，其冻结FAT收据将Image绑定到`085d0306…b25955`。精确内核版本为`#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026`，release、R8、481/468、startup500、flagY和独立NOW/AVG条件保持。

`payload.py`调用已冻结502 operator的七原件context验证；只接受`image502-notify-live-001`及其新schema、当前501旧boot/guard/板型/rootfs和真实终态原件。没有旧`pair_complete`或双分区写门，也没有把boot尺寸当内容验证：设备仍以O_RDONLY分块读取完整boot与logdump，分别核97811和ace2。新boot必须不同于该502 context里的旧boot；不能拿旧501 context或guard冒认502启动。

23个device函数与当前501源码逐字相同，包含实际SDP/CDP预算、保护/温控/精确Full、相机四PM/m2m空闲、四个新PID身份、服务/故障、EUD producer缺席与Gauge检查。SDP按native500/source500/hardware500核验；CDP按source1.5A、native500及hardware不超过900mA核验。正常Full/FC、净电流符号均不强行变成Charging；未知或ENODATA保留原错误/等待。没有CSR/MMIO、裸I2C、充电控制、guard或pointer写入。

## 使用顺序

默认本地检查已真实rc0，不连接设备：

```text
python3 -B payload.py
python3 -B device.py --check-local
```

将来由root核实际新endpoint与同一独占窗口后，导入`payload.py`：

1. `make_request(context_path, camera481_path, endpoint, True, True)`；context固定为本次502事务的`host-context-private.json`，camera为原481 expected。endpoint必须是原key下已观察的`fe80::62:bcff:fe28:a101%29`；不自动回退IPv4或换key。
2. `make_payload(request)`生成实际源码；root通过既有严格原key传输单次执行`python3 - --execute --window-confirmed --new-endpoint <endpoint>`。本叶没有自行建立传输的入口。
3. 对同一传输的真实stdout/stderr/退出码调用`save_response`，保存于本事务目录内一个全新`postboot-…-private`目录；失败原件同样保留。`receiver-result`只是本地接收结果，后续adopt会重新执行实际audit。
4. 只有实际passed的新boot原件才交下一叶adoption；本采集器不创建新guard。

下面是root在已完成实际新endpoint/内核小探测后使用的WSL Python片段；本轮没有执行它。它不导入旧`run-image501-postboot`，也不调用旧R3远端guard。`observed`必须尚不存在：

```python
from pathlib import Path
import hashlib, importlib.util, subprocess
ref = Path('/mnt/e/RealmeX2Pro edk2/reference')
leaf = ref / 'charging-oem-audit-20261023/image502-postboot-readonly'
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
p = load('postboot502_payload', leaf / 'payload.py')
transport = ref / 'kernel184/host.py'
assert hashlib.sha256(transport.read_bytes()).hexdigest() == '7f49a922e0babf167c77ad6e9bd7edf63e437418d5134e3d081fb8a0082a4f4c'
h = load('original_strict_key', transport)
txn = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/image502-notify-activation/image502-notify-live-001')
endpoint = 'fe80::62:bcff:fe28:a101%29'  # root已在本窗口真实确认的endpoint
request = p.make_request(txn / 'host-context-private.json',
    '/mnt/e/edk2-samurai-out/kernel481/formal-expected-private.json', endpoint, True, True)
code = p.make_payload(request)
argv = [h.SSH, '-6', '-T', *h.OPTIONS, '-o', 'HostKeyAlias=169.254.42.1',
    'root@' + endpoint, 'python3 - --execute --window-confirmed --new-endpoint ' + endpoint]
child = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
try:
    stdout, stderr = child.communicate(input=code)
finally:
    child.wait()
observed = txn / 'postboot-r1-01-private'
result = p.save_response(observed, stdout, stderr, child.returncode, code)
print(result)
```

若传输结果未知，保留同child/输出后观察，不创建第二次采集或adoption来冒认原动作成功。纯只读失败不触发自动控制或回退。

`test-delta.py`执行8个受影响实际函数边界：合成502的新boot/七原件context、旧501或同boot拒绝、boot变更/旧logdump拒绝、旧schema及未观察peer拒绝，并核原SDP/CDP/Full分支。fixture由已验501 postboot04原件复制后明确改变身份与logdump，不能当真实502实测。其余旧矩阵与收据复用，不重跑。默认检查/fixture均未执行SSH、USB、prepare、构建、Git或adoption；新内核的实机启动和延迟收益尚待root收集。

`prepare.py`是本轮离线派生记录，已经完成；冻结后不要再运行以覆写源。原501及502 activation叶均未修改。
