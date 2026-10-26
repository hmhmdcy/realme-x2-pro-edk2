from pathlib import Path
import difflib,hashlib,json
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel223');previous=private.parent/'kernel222';kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel');parent='drivers/media/platform/qcom/camss/'
proof=json.loads((here.parent/'kernel222/sof-candidate-source-validation.json').read_text());original={};candidate={}
for name,digest in proof['original_sources_sha256'].items():
 original[name]=(kernel/name).read_text();assert hashlib.sha256(original[name].encode()).hexdigest()==digest
 candidate[name]=(previous/'sof-candidate-source'/name).read_text();assert hashlib.sha256(candidate[name].encode()).hexdigest()==proof['candidate_sources_sha256'][name]
name=parent+'camss-video.h';original[name]=(kernel/name).read_text();candidate[name]=original[name]
def replace(name,old,new):
 name=parent+name;assert candidate[name].count(old)==1,(name,old,candidate[name].count(old));candidate[name]=candidate[name].replace(old,new)
replace('camss-video.h','\tstruct list_head queue;\n','\tstruct list_head queue;\n\tbool sof_valid;\n')
name=parent+'camss-vfe.c';text=candidate[name];a=text.index('int vfe_queue_buffer_v2');b=text.index('\n/*',a);part=text[a:b];old='\tspin_lock_irqsave(&vfe->output_lock, flags);\n';assert part.count(old)==1
part=part.replace(old,old+'\tbuf->sof_valid = false;\n');candidate[name]=text[:a]+part+text[b:]
replace('camss-vfe.c','if (vfe->camss->res->version != CAMSS_8150 ||\n','if (vfe->camss->res->version != CAMSS_8150 ||\n\t    vfe->res->hw_ops != &vfe_ops_170 ||\n')
replace('camss-vfe.c','\t\tif (vfe->camss->res->version == CAMSS_8150)\n','\t\tif (vfe->camss->res->version == CAMSS_8150 &&\n\t\t    vfe->res->hw_ops == &vfe_ops_170)\n')
name=parent+'camss-vfe-17x.c';text=candidate[name];a=text.index('static void vfe_isr_sof(');b=text.index('\n/*',a);part=text[a:b]
part=part.replace('\tunsigned long flags;\n','\tunsigned long flags;\n\tunsigned int i;\n')
old='\tevent.u.frame_sync.frame_sequence = output->sof_sequence++;\n';assert part.count(old)==1
part=part.replace(old,old+'''	/* A previous buffer may await DONE when this SOF is handled. */
	for (i = 0; i < CAMSS_INIT_BUF_COUNT; i++) {
		struct camss_buffer *buf = output->buf[i];

		if (buf && !buf->sof_valid) {
			buf->vb.sequence = event.u.frame_sync.frame_sequence;
			buf->sof_valid = true;
			break;
		}
	}
''');candidate[name]=text[:a]+part+text[b:]
name=parent+'camss-vfe-17x.c';text=candidate[name];a=text.index('static void vfe_isr_wm_done(');b=text.index('\nstatic ',a);part=text[a:b]
part=part.replace('\tu64 ts = ktime_get_ns();\n','\tu64 ts = ktime_get_ns();\n\tbool sof_valid = true;\n')
old='\tready_buf->vb.sequence = output->sequence++;\n';assert part.count(old)==1
part=part.replace(old,'''	if (vfe->camss->res->version == CAMSS_8150) {
		sof_valid = ready_buf->sof_valid;
		if (!sof_valid)
			dev_err_ratelimited(vfe->camss->dev,
					    "Missing SOF tag for completed buffer\\n");
	} else {
		ready_buf->vb.sequence = output->sequence++;
	}
''')
old='\tvb2_buffer_done(&ready_buf->vb.vb2_buf, VB2_BUF_STATE_DONE);';assert part.count(old)==1
part=part.replace(old,'\tvb2_buffer_done(&ready_buf->vb.vb2_buf,\n\t\t\tsof_valid ? VB2_BUF_STATE_DONE : VB2_BUF_STATE_ERROR);');candidate[name]=text[:a]+part+text[b:]
target=private/'sof-candidate-source';assert not target.exists();target.mkdir(mode=0o700)
patch='Subject: [PATCH] media: camss: pair SM8150 captured buffers with SOF\n\nExpose FRAME_SYNC for the supported VFE170 path and tag the first active\nbuffer that has not already started. Reset the tag on requeue and report\na missing tag as a buffer error. Keep completion timestamps and all IRQ\nmasks, clocks and power policy unchanged.\n\n---\n'
for name in candidate:
 p=target/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(candidate[name]);patch+='diff --git a/'+name+' b/'+name+'\n'+''.join(difflib.unified_diff(original[name].splitlines(True),candidate[name].splitlines(True),fromfile='a/'+name,tofile='b/'+name))
(here/'camss-sm8150-paired-sof-candidate.patch').write_text(patch)
r=dict(stage=223,candidate_only=True,original_sources_sha256={n:hashlib.sha256(t.encode()).hexdigest() for n,t in original.items()},candidate_sources_sha256={n:hashlib.sha256(t.encode()).hexdigest() for n,t in candidate.items()},patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),buffer_tag_reset_on_requeue=True,only_supported_sm8150_vfe170_advertises_events=True,missing_tag_not_reported_as_success=True,physical_pairing_not_yet_verified=True)
(here/'sof-candidate-source-validation.json').write_text(json.dumps(r,indent=2)+'\n')
build=(here.parent/'kernel222/build-sof-candidate-r2.py').read_text().replace('kernel222','kernel223').replace('stage=222','stage=223').replace("kernel-before-sof-r2","kernel-before-paired-sof").replace('sof-build-r2-state','paired-sof-build-state').replace('sof-kernel-build-r2','paired-sof-kernel-build').replace('qcom-camss-sof222.ko','qcom-camss-sof223.ko').replace('camss-sm8150-sof-candidate.patch','camss-sm8150-paired-sof-candidate.patch')
build=build.replace(',initial_missing_dependency_modpost_failure_preserved=True','').replace(',only_commit_description_wrapped_after_build=True','')
compile(build,'build-paired-sof223','exec');(here/'build-paired-sof.py').write_text(build);print(json.dumps(r))
