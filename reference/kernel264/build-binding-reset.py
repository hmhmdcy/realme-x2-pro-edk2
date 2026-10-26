"""Discard descriptors from retired camera links when their IO is rebound."""
from pathlib import Path
import difflib,hashlib,json,shutil,subprocess
R=Path(__file__).parent;P=Path('/mnt/e/edk2-samurai-out/kernel264');SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire263-broadcast';p=W/'pipewire-1.6.9/src/pipewire/impl-port.c'
s=p.read_text();assert hashlib.sha256(s.encode()).hexdigest()==json.loads((R/'proxy-only-build-validation.json').read_text())['source_sha256']
(P/'core-proxy-only-before-binding-private.c').write_text(s)
needle='''	if (!mix->rt.active) {
		spa_list_append(&impl->rt.mix_list, &mix->rt.link);''';assert s.count(needle)==1
s=s.replace(needle,'''\tif (!mix->rt.active) {
		/* A re-bound camera link must not announce a buffer from the retired
		 * pool. The data loop is locked here, before this mix can be driven. */
		if (this->direction == PW_DIRECTION_OUTPUT && impl->reliable_broadcast) {
			for (uint32_t i = 0; i < 2; i++) {
				if (!mix->io[i])
					continue;
				pw_log_info("%p: reset camera mix IO status:%d id:%u", this,
					mix->io[i]->status, mix->io[i]->buffer_id);
				*mix->io[i] = SPA_IO_BUFFERS_INIT;
			}
		}
		spa_list_append(&impl->rt.mix_list, &mix->rt.link);''')
p.write_text(s);original=(SDK/'work/pipewire262/pipewire-1.6.9/src/pipewire/impl-port.c').read_text()
(R/'core-binding-reset-candidate.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='a/src/pipewire/impl-port.c',tofile='b/src/pipewire/impl-port.c')))
q=subprocess.run(['chroot',str(SDK),'ninja','-C','/work/pipewire263-broadcast/build','-j2','src/pipewire/libpipewire-0.3.so.0.1609.0'],capture_output=True)
(P/'binding-reset-build-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr).decode(errors='replace')[-2500:]
shutil.copyfile(W/'build/src/pipewire/libpipewire-0.3.so.0.1609.0',P/'libpipewire-binding-reset.so')
report=dict(stage=264,compiled=True,source_sha256=hashlib.sha256(s.encode()).hexdigest(),core_sha256=hashlib.sha256((P/'libpipewire-binding-reset.so').read_bytes()).hexdigest(),spa_sha256=json.loads((R/'reset-output-build-validation.json').read_text())['spa_sha256'],busy_counters_never_reset=True,no_system_deployment=True)
(R/'binding-reset-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
