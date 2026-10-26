from pathlib import Path
import json
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel210')
assert json.loads((here/'flash-validation.json').read_text())['boot_flash_success']
assert (private/'reboot-request-private.json').exists() and (private/'fastboot-reboot-request-private.json').exists()
plan=json.loads((private/'current-work-private.json').read_text());plan.update(state='Boot210 flashed successfully once after fresh fastboot identity. Fastboot reboot sent once. Await fresh USB discovery/new boot/readback. Do not replay restart/flash/reboot markers.',transition_pending=True,next='Discover new USB peer, authenticate strict host key, run collect-newboot; sourceboot guard k210-baseline is OLD and must not authorize any new transition.')
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n')
text=(repo/'NEXT-SESSION.md').read_text();start=text.index('2026-10-15，');end=text.index('\n\n',start)
text=text[:start]+'2026-10-15，阶段210，完整外设goal active。已安装三个相机模块，完成外设停用/归档；核对当前fastboot身份后只刷boot210（89242ade…），并已发送一次fastboot reboot。正在等待新USB与启动读回，禁止重放已有切换marker。[210进展](reference/kernel210/README.md)、[完整209快照](archive/NEXT-SESSION-through209-2026-10-15.md)、[边界](WORKING-BOUNDARIES.md)。'+text[end:]
start=text.index('- 当前运输');end=text.index('\n',start)
text=text[:start]+'- 当前运输 `reference/kernel210/host.py`；旧USB端点已另存，待发现新端点。`k210-baseline/boot-id-private.txt`是切换前旧boot身份，不能授权新的切换。私人kernel210下reboot-request、boot-flash-request、fastboot-reboot-request均已存在；先读新状态，不重复发送。'+text[end:]
text=text.replace('此刻尚无重启或刷写请求。','现已完成一次boot刷写及fastboot reboot，待新boot读回；Image183/logdump仍应保持。')
text=text.replace('内核 `/home/cy122/pmos-samurai-kernel136/kernel` 仍204源码','209结束时内核 `/home/cy122/pmos-samurai-kernel136/kernel` 仍204源码')
(repo/'NEXT-SESSION.md').write_text(text)
p=here/'README.md';text=p.read_text().replace('尚未发出切换。手机此刻仍为207第二boot、Image183及boot204。','已在核对当前fastboot身份后只刷boot210并发送一次reboot，正在等待新boot读回。旧boot身份不得授权新切换。')
p.write_text(text);print('210 transition state recorded; all three request markers must not be replayed.')
