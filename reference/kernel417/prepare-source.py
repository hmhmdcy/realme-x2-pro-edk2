"""Add typed Media Request IQ controls to the maintained candidate adapter."""
from pathlib import Path
import difflib,hashlib,importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel417');P.mkdir(mode=0o700,exist_ok=True)
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';base='b4f382affa9a8be089ccec6170c34d74005103ce'
git=lambda *args:subprocess.check_output(['git','-C',str(source),*args])
assert git('rev-parse','HEAD').decode().strip()==base and not git('status','--porcelain')
git('checkout','-b','samurai-ipe-request-iq417')
directory=source/'drivers/media/platform/qcom/camss';path=directory/'camss-icp-a5-m2m.c';original=path.read_text();text=original
def replace(old,new):
    global text
    assert text.count(old)==1,old[:120];text=text.replace(old,new)
replace('#include <linux/slab.h>','#include <linux/slab.h>\n#include <linux/sched.h>\n#include <linux/qcom-ipe-a5.h>\n#include <media/v4l2-ctrls.h>')
replace('struct work_struct work;','struct work_struct work;\n\tstruct v4l2_ctrl_handler controls;\n\tstruct task_struct *control_task;\n\tstruct qcom_ipe_a5_frame_params *pending_params;\n\tbool params_written;')
marker='/* Export the original SG buffer';assert text.count(marker)==1;text=text.replace(marker,(HERE/'adapter-control-tail.c').read_text()+'\n'+marker)
replace('enum camss_a5_ipe_result result = CAMSS_A5_IPE_RESET_REQUIRED;','enum camss_a5_ipe_result result = CAMSS_A5_IPE_RESET_REQUIRED;\n\tstruct media_request *request = src ? src->vb2_buf.req_obj.req : NULL;\n\tstruct qcom_ipe_a5_frame_params *params = NULL;')
replace('if (src)\n\t\t\tv4l2_m2m_buf_done','if (src) {\n\t\t\tv4l2_ctrl_request_complete(request, &ctx->controls);\n\t\t\tv4l2_m2m_buf_done')
replace(' VB2_BUF_STATE_ERROR);\n\t\tif (dst)',' VB2_BUF_STATE_ERROR);\n\t\t}\n\t\tif (dst)')
replace('\tinput = image_buffer(&src->vb2_buf);','''	if (request) {
		params = kzalloc(sizeof(*params), GFP_KERNEL);
		if (!params) { ret = -ENOMEM; goto finish; }
		ctx->pending_params = params;
		ctx->params_written = false;
		WRITE_ONCE(ctx->control_task, current);
		ret = v4l2_ctrl_request_setup(request, &ctx->controls);
		WRITE_ONCE(ctx->control_task, NULL);
		ctx->pending_params = NULL;
		if (!ret && !ctx->params_written) ret = -ENOENT;
		if (!ret) ret = camss_a5_ipe_frame_params_check(params);
		if (ret) goto finish;
	}
	input = image_buffer(&src->vb2_buf);''')
replace('ret = camss_a5_ipe_run_status(dev->a5, &ctx->session, &job, &result);','ret = frame_params_run(ctx, &job, params, &result);')
replace('finish:\n\tif (output)','finish:\n\tkfree(params);\n\tif (output)')
replace('\tv4l2_m2m_buf_copy_metadata(src, dst);','\tv4l2_ctrl_request_complete(request, &ctx->controls);\n\tv4l2_m2m_buf_copy_metadata(src, dst);')
replace('\t\tv4l2_m2m_buf_done(buffer, VB2_BUF_STATE_ERROR);','\t{\n\t\tv4l2_ctrl_request_complete(buffer->vb2_buf.req_obj.req, &ctx->controls);\n\t\tv4l2_m2m_buf_done(buffer, VB2_BUF_STATE_ERROR);\n\t}')
marker='static const struct vb2_ops queue_ops = {'
replace(marker,'static void buffer_request_complete(struct vb2_buffer *vb);\n\n'+marker)
replace('\t.buf_prepare = buffer_prepare,','\t.buf_prepare = buffer_prepare,\n\t.buf_request_complete = buffer_request_complete,')
marker='static void buffer_queue(struct vb2_buffer *vb)';assert text.count(marker)==1
text=text.replace(marker,(HERE/'output-validation-tail.c').read_text()+'\n'+marker)
replace('\t.buf_prepare = buffer_prepare,','\t.buf_prepare = buffer_prepare,\n\t.buf_out_validate = buffer_output_validate,')
marker='static int queue_init(void *private,';assert text.count(marker)==1;text=text.replace(marker,(HERE/'adapter-request-tail.c').read_text()+'\n'+marker)
replace('\t\tq->drv_priv = ctx;','\t\tq->drv_priv = ctx;\n\t\tq->supports_requests = !i;')
replace('\tv4l2_fh_init(&ctx->fh, &dev->video);','''	v4l2_fh_init(&ctx->fh, &dev->video);
	v4l2_ctrl_handler_init(&ctx->controls, 1);
	v4l2_ctrl_new_custom(&ctx->controls, &frame_params_config, NULL);
	ret = ctx->controls.error;
	if (ret) {
		v4l2_ctrl_handler_free(&ctx->controls);
		v4l2_fh_exit(&ctx->fh);
		kfree(ctx);
		goto put_owner;
	}
	ctx->fh.ctrl_handler = &ctx->controls;''')
replace('\t\tret = PTR_ERR(ctx->fh.m2m_ctx);','\t\tret = PTR_ERR(ctx->fh.m2m_ctx);\n\t\tv4l2_ctrl_handler_free(&ctx->controls);')
replace('\tv4l2_fh_del(&ctx->fh, file);','\tv4l2_ctrl_handler_free(&ctx->controls);\n\tv4l2_fh_del(&ctx->fh, file);')
replace('\tmedia_device_init(&dev->media);','\tmedia_device_init(&dev->media);\n\tdev->media.ops = &request_ops;')
path.write_text(text)
colour=directory/'camss-icp-a5-colour.c';data=colour.read_text();assert '#include <linux/export.h>' not in data
colour.write_text('#include <linux/export.h>\n'+data+'\n'+(HERE/'frame-check-tail.c').read_text())
header=directory/'camss-icp-a5-colour.h';data=header.read_text();data=data.replace('#include <linux/types.h>','#include <linux/types.h>\n#include <linux/qcom-ipe-a5.h>')
data=data.replace('\n#endif','\nint camss_a5_ipe_frame_params_check(const struct qcom_ipe_a5_frame_params *params);\n\n#endif');header.write_text(data)
(source/'include/uapi/linux/qcom-ipe-a5.h').write_bytes((HERE/'qcom-ipe-a5.h').read_bytes())
subprocess.run(['git','-C',str(source),'diff','--check'],check=True)
files=['drivers/media/platform/qcom/camss/'+n for n in ['camss-icp-a5-m2m.c','camss-icp-a5-colour.c','camss-icp-a5-colour.h']]+['include/uapi/linux/qcom-ipe-a5.h']
(HERE/'request-iq.patch').write_bytes(git('diff','--',*files[:3])+subprocess.run(['git','diff','--no-index','--','/dev/null',str(source/files[3])],capture_output=True).stdout.replace(str(source).encode()+b'/',b''))
for rel in files:
    dest=P/Path(rel).name;dest.write_bytes((source/rel).read_bytes())
state=dict(stage=417,source=str(source),branch='samurai-ipe-request-iq417',parent=base,commit=base,changed=files,
    prepared=True,committed=False,installed=False,phone_accessed=False,last_device_evidence_stage=406,
    candidate_request_iq_interface=True,legacy_direct_bypass_preserved=True,full_goal_kept_active=True)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(state,indent=2))
