from pathlib import Path
import hashlib,json,subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel156')
out=Path('/mnt/e/edk2-samurai-out/kernel156')
report=json.loads((ref/'source-validation.json').read_text())
before=json.loads((out/'source-before-private.json').read_text())
for n,sha in report['after_sha256'].items():assert hashlib.sha256((k/n).read_bytes()).hexdigest()==sha,n
args=['git','diff','--binary','--','.']+[':(exclude)'+n for n in report['modified_files']]
assert subprocess.check_output(args,cwd=k)==(out/'other-diff-before-private.patch').read_bytes()
name='drivers/gpu/drm/msm/disp/dpu1/dpu_trace.h'
assert name not in before
before[name]=(k/name).read_text()
report['modified_files'].append(name)
report['before_sha256'][name]=hashlib.sha256(before[name].encode()).hexdigest()
(out/'source-before-private.json').rename(out/'source-before-eight-files-private.json')
(out/'source-before-private.json').write_text(json.dumps(before))
(out/'other-diff-before-private.patch').rename(out/'other-diff-before-eight-files-private.patch')
args=['git','diff','--binary','--','.']+[':(exclude)'+n for n in report['modified_files']]
(out/'other-diff-before-private.patch').write_bytes(subprocess.check_output(args,cwd=k))
p=k/'drivers/gpu/drm/panel/panel-samsung-sofef03f.c'
s=p.read_text();assert s.count('.power = FB_BLANK_POWERDOWN,')==1
p.write_text(s.replace('.power = FB_BLANK_POWERDOWN,','.power = BACKLIGHT_POWER_OFF,',1))
p=k/'drivers/gpu/drm/msm/disp/dpu1/dpu_kms.c'
s=p.read_text();old='\t\tret = dpu_encoder_wait_for_tx_complete(encoder);\n\t\tif (ret'
assert s.count(old)==1
p.write_text(s.replace(old,'\t\tret = dpu_encoder_wait_for_tx_complete(encoder);\n\t\ttrace_dpu_first_frame_backlight(DRMID(crtc), DRMID(encoder), ret);\n\t\tif (ret',1))
point='''TRACE_EVENT(dpu_first_frame_backlight,
	    TP_PROTO(u32 crtc, u32 encoder, int ret),
	    TP_ARGS(crtc, encoder, ret),
	    TP_STRUCT__entry(
		    __field(u32, crtc)
		    __field(u32, encoder)
		    __field(int, ret)
	    ),
	    TP_fast_assign(
		    __entry->crtc = crtc;
		    __entry->encoder = encoder;
		    __entry->ret = ret;
	    ),
	    TP_printk("crtc=%u encoder=%u ret=%d", __entry->crtc,
		      __entry->encoder, __entry->ret)
);

'''
p=k/name;s=p.read_text();mark='#define DPU_ATRACE_END(name)'
assert s.count(mark)==1;p.write_text(s.replace(mark,point+mark,1))
import difflib,textwrap
code=(ref/'finalize-style.py').read_text()
exec(compile(code[code.index("patch=ref/'first-frame-backlight.patch'"):],str(ref/'finalize-style.py'),'exec'))
print('K156_NEW_BACKLIGHT_API_AND_EARLY_DPU_TRACE_READY')
