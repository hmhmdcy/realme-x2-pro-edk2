from pathlib import Path
import json
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel211')
assert json.loads((here/'flash-validation.json').read_text())['boot_flash_success']
assert (private/'reboot-request-private.json').exists() and (private/'fastboot-reboot-request-private.json').exists()
plan=json.loads((private/'current-work-private.json').read_text());plan.update(state='211 sensor-domain boot c3bf043f flashed once after fresh fastboot identity and preserved WARN2 recovery archive. Single fastboot reboot sent. Await new USB/boot/readback; do not replay markers.',transition_pending=True,next='Fresh USB discovery, strict key, collect-newboot211 and verify loaded sensor genpd, TRY/ACTIVE crop, heap autoload/scoped access. Then isolated sensor runtime wake to verify the MCLK fix, followed by user capture.')
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n')
text=(repo/'NEXT-SESSION.md').read_text();start=text.index('2026-10-15，');end=text.index('\n\n',start)
text=text[:start]+'2026-10-15，阶段211进行中。已完整停用/归档并核对当前fastboot身份，只刷boot211 c3bf043f…（DTB6f9f5b0f…，仅新增sensor供电域属性），发送一次reboot。正在等新USB/boot读回，不能重放三个请求marker。旧boot的两次MCLK WARN及taint512恢复证据已保留；新boot尚未验收。[211进展](reference/kernel211/README.md)。'+text[end:]
start=text.index('- 211当前现场：');end=text.index('\n',start)
text=text[:start]+'- 211当前现场：boot刷写及fastboot reboot均已提交一次，正在等新身份。私人211下reboot-request/boot-flash-request/fastboot-reboot-request均存在；k211-baseline/k211-before-reboot属于旧boot，不能授权新的切换。旧USB端点已另存，待重新发现。'+text[end:]
(repo/'NEXT-SESSION.md').write_text(text);print('211 flash/reboot markers recorded; new boot proof pending.')
