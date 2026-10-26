from pathlib import Path
import difflib,hashlib,json,os,shutil,subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel198');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();base=k/'drivers/media/platform/qcom/camss';names=['camss.c','camss-vfe.c','camss.h'];original={n:(base/n).read_bytes() for n in names};assert sha(base/'camss.c')=='cc212a4c8674e15fe93a8fba3801fb6850596b7960e1a1df9ab4984ef1633ca2'
for n,b in original.items():p=out/(n+'.before198-private');assert not p.exists();p.write_bytes(b)
state={n:(k/n).read_bytes() for n in ['.config','Module.symvers','modules.order']};image={n:sha(k/n) for n in ['arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb']};env=dict(os.environ,KBUILD_BUILD_VERSION='183',PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup');modified={};patch=''
try:
 s=original['camss.h'].decode().replace('void camss_add_clock_margin(u64 *rate);','void camss_trace_clocks(struct device *dev, struct camss_clock *clock,\n\t\t\tint nclocks, const char *reason);\nvoid camss_add_clock_margin(u64 *rate);');modified['camss.h']=s
 s=original['camss.c'].decode().replace('#include <linux/clk.h>','#include <linux/clk.h>\n#include <linux/clk-provider.h>')
 marker='int camss_enable_clocks(int nclocks, struct camss_clock *clock,'
 diagnostic='''static bool clock_trace;
module_param(clock_trace, bool, 0444);
MODULE_PARM_DESC(clock_trace, "Read clock state around camera power/reset");

void camss_trace_clocks(struct device *dev, struct camss_clock *clock,
			int nclocks, const char *reason)
{
	int i;

	if (!clock_trace)
		return;
	for (i = 0; i < nclocks; i++)
		dev_info(dev, "clock-trace %s name=%s rate=%lu hw=%d\\n",
			 reason, clock[i].name, clk_get_rate(clock[i].clk),
			 __clk_is_enabled(clock[i].clk));
}

'''
 assert s.count(marker)==1;s=s.replace(marker,diagnostic+marker);start=s.index(marker);end=s.index('\n/*\n * camss_disable_clocks',start);block=s[start:end];needle='''			goto error;
		}
	}
''';assert block.count(needle)==1;block=block.replace(needle,'''			goto error;
		}
		camss_trace_clocks(dev, &clock[i], 1, "enabled");
	}
''');s=s[:start]+block+s[end:];modified['camss.c']=s
 s=original['camss-vfe.c'].decode();needle='''		ret = vfe_reset(vfe);
		if (ret < 0)''';assert s.count(needle)==1;s=s.replace(needle,'''		camss_trace_clocks(vfe->camss->dev, vfe->clock, vfe->nclocks,
				   "before-vfe-reset");
		ret = vfe_reset(vfe);
		camss_trace_clocks(vfe->camss->dev, vfe->clock, vfe->nclocks,
				   "after-vfe-reset");
		if (ret < 0)''');modified['camss-vfe.c']=s
 for n,s in modified.items():
  (base/n).write_text(s);path='drivers/media/platform/qcom/camss/'+n;patch+='diff --git a/'+path+' b/'+path+'\n'+''.join(difflib.unified_diff(original[n].decode().splitlines(True),s.splitlines(True),fromfile='a/'+path,tofile='b/'+path))
 (ref/'temporary-clock-diagnostic.patch').write_text(patch)
 with (out/'diagnostic-olddefconfig-private.log').open('xb') as log:subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','olddefconfig'],cwd=k,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 targets=['drivers/media/common/videobuf2/videobuf2-'+n+'.ko' for n in ['common','memops','v4l2','dma-sg']]+['drivers/media/platform/qcom/camss/qcom-camss.ko']
 with (out/'diagnostic-build-private.log').open('xb') as log:subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory','W=1','-j3',*targets],cwd=k,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 dest=out/'qcom-camss-clock-trace.ko';assert not dest.exists();shutil.copyfile(k/targets[-1],dest);subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(dest)],check=True)
finally:
 for n,b in original.items():(base/n).write_bytes(b)
 for n,b in state.items():(k/n).write_bytes(b)
assert all(sha(k/n)==h for n,h in image.items());diag=[s for s in (out/'diagnostic-build-private.log').read_text().splitlines() if 'warning:' in s or 'error:' in s];assert not diag,diag
vm=subprocess.check_output(['modinfo','-F','vermagic',str(dest)],text=True).strip();assert vm==json.loads((ref.parent/'kernel197/camss-module-build-validation.json').read_text())['vermagic'];check=subprocess.run(['perl',str(k/'scripts/checkpatch.pl'),'--no-tree','--strict','-'],input=patch,capture_output=True,text=True);(out/'diagnostic-checkpatch-private.log').write_text(check.stdout+check.stderr)
r=dict(stage=198,module_sha256=sha(dest),module_bytes=dest.stat().st_size,vermagic=vm,original_source_sha256={n:hashlib.sha256(b).hexdigest() for n,b in original.items()},diagnostic_source_sha256={n:hashlib.sha256(s.encode()).hexdigest() for n,s in modified.items()},original_source_restored_after_build=all((base/n).read_bytes()==b for n,b in original.items()),image_dtb_config_symbols_order_restored=True,w1_diagnostics=0,checkpatch_exit=check.returncode,diagnostic_default_disabled=True,normal_clock_and_reset_actions_unchanged=True);(ref/'clock-diagnostic-module-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
