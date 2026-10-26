"""Connect typed GTM, serialized PIX RUP acknowledgements and SOF snapshots."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage433prepare',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);kernel=m.mounted_build().parent/'source354';camss=Path('drivers/media/platform/qcom/camss');uapi=Path('include/uapi/linux/qcom-camss-config.h')
git=lambda *a:subprocess.check_output(['git','-C',str(kernel),*a],text=True).strip();base='52127e558704de6a640d076ef605182fe6fff0d7'
assert git('rev-parse','HEAD')==base and not git('status','--porcelain')
for p in [kernel,*kernel.parents,*(kernel/camss).parents,*(kernel/uapi).parents]:assert not (p/'AGENTS.md').exists(),str(p/'AGENTS.md')
names=['camss-vfe-175-gtm.c','camss-vfe-175-gtm.h','camss-vfe-175-pixel.c','camss-vfe-175-pixel.h','camss-vfe-17x.c','camss-vfe.c','camss-vfe.h','camss-video.h','Makefile'];texts={str(camss/n):(kernel/camss/n).read_text() if (kernel/camss/n).exists() else '' for n in names};texts[str(uapi)]=(kernel/uapi).read_text()
def change(path,old,new):
 assert texts[str(path)].count(old)==1,(str(path),old);texts[str(path)]=texts[str(path)].replace(old,new)
for name in names[:2]:texts[str(camss/name)]=(HERE/name).read_text()
change(uapi,'\tCAMSS_PARAMS_IFE_DS4 = 8,','\tCAMSS_PARAMS_IFE_DS4 = 8,\n\tCAMSS_PARAMS_IFE_GTM = 9,')
change(uapi,'/* Local experimental identifier, not reserved upstream.', '''/* Local experimental GTM parameter/statistics types, not reserved upstream.
 * Flags must be zero; disabling also requires the full payload and cookie.
 * cookie is a caller token, not proof of application. Statistics acknowledge
 * it only after PIX REG_UPDATE ACK and snapshot it at the buffer's SOF.
 * base is unsigned Q12 (18 bits), slope is signed Q20 (26 bits).
 * CPU DMI uses canonical low/high words, without the HW-CDM word swap.
 */
#define CAMSS_IFE_GTM_ENTRIES 64
struct camss_ife_gtm_segment {
	__u32 base;
	__s32 slope;
};
struct camss_params_ife_gtm {
	struct v4l2_isp_block_header header;
	__u64 cookie;
	__u32 enabled;
	__u32 reserved;
	struct camss_ife_gtm_segment segments[CAMSS_IFE_GTM_ENTRIES];
} __attribute__((aligned(8)));

#define CAMSS_IFE_GTM_STATUS_ACKED (1U << 0)
#define CAMSS_IFE_GTM_STATUS_ENABLED (1U << 1)
struct camss_stats_ife_gtm {
	struct v4l2_isp_block_header header;
	__u64 cookie;
	__u64 generation;
	__u32 status;
	__u32 bank;
} __attribute__((aligned(8)));

/* Local experimental identifier, not reserved upstream.''')
change(uapi,'\tCAMSS_STATS_AWB_BG = 2,','\tCAMSS_STATS_AWB_BG = 2,\n\tCAMSS_STATS_IFE_GTM = 3,')
change(uapi,'\tCAMSS_STATS_BG_MAX_PAYLOAD)\n','\tCAMSS_STATS_BG_MAX_PAYLOAD + sizeof(struct camss_stats_ife_gtm))\n')
change(camss/'Makefile','camss-vfe-175-ds4.o','camss-vfe-175-ds4.o \\\n\t\tcamss-vfe-175-gtm.o')
change(camss/'camss-vfe-175-pixel.h','#include "camss-vfe-175-stats.h"','#include "camss-vfe-175-stats.h"\n#include "camss-vfe-175-gtm.h"')
change(camss/'camss-vfe-175-pixel.h','\tstruct vfe_175_stats_state stats;','\tstruct vfe_175_stats_state stats;\n\tstruct vfe_175_gtm_state gtm;')
change(camss/'camss-vfe-175-pixel.h','vfe_175_params_info[9]','vfe_175_params_info[10]')
change(camss/'camss-vfe-175-pixel.c','vfe_175_params_info[9]','vfe_175_params_info[10]')
change(camss/'camss-vfe-175-pixel.c','\t[CAMSS_PARAMS_IFE_DS4] = {','\t[CAMSS_PARAMS_IFE_GTM] = {\n\t\t.size = sizeof(struct camss_params_ife_gtm),\n\t\t.block_validate = vfe_175_gtm_validate,\n\t},\n\t[CAMSS_PARAMS_IFE_DS4] = {')
change(camss/'camss-vfe-175-pixel.c','\tvfe_175_wb_write(vfe);\n\tvfe_175_lsc_init(vfe);','\tvfe_175_wb_write(vfe);\n\tvfe_175_gtm_stop(vfe);\n\tvfe_175_lsc_init(vfe);')
change(camss/'camss-vfe-175-pixel.c','void vfe_175_pixel_stop(struct vfe_device *vfe)\n{','void vfe_175_pixel_stop(struct vfe_device *vfe)\n{\n\tvfe_175_gtm_stop(vfe);')
change(camss/'camss-vfe-175-pixel.c','\t\tif (block->type == CAMSS_PARAMS_IFE_DS4) {','\t\tif (block->type == CAMSS_PARAMS_IFE_GTM) {\n\t\t\tvfe_175_gtm_params(vfe, block);\n\t\t\toffset += block->size;\n\t\t\tcontinue;\n\t\t}\n\t\tif (block->type == CAMSS_PARAMS_IFE_DS4) {')
change(camss/'camss-video.h','\tbool sof_valid;','\tbool sof_valid;\n\t/* IFE175 processing state captured with this buffer\'s input SOF. */\n\tu64 gtm_cookie, gtm_generation;\n\tu32 gtm_status, gtm_bank;')
change(camss/'camss-vfe.c','\t\tvfe->res->hw_ops->vfe_stats_fill(vfe, output, stats);\n\t\tgoto done;','\t\tvfe->res->hw_ops->vfe_stats_fill(vfe, output, stats);\n\t\tif (vfe->camss->res->version == CAMSS_8150 && output->line->is_pix)\n\t\t\tvfe_175_gtm_fill(vfe, output, buf, stats);\n\t\tgoto done;')
change(camss/'camss-vfe.c','static struct camss_buffer *vfe_params_apply_next','struct camss_buffer *vfe_params_apply_next')
change(camss/'camss-vfe.c','\tbuf = vfe_buf_get_pending(params);','''	buf = list_first_entry_or_null(&params->pending_bufs, struct camss_buffer, queue);
	if (buf && line->is_pix && vfe->camss->res->version == CAMSS_8150 &&
	    vfe_175_gtm_defer(vfe, buf->meta))
		return NULL;
	buf = vfe_buf_get_pending(params);''')
change(camss/'camss-vfe.h','void vfe_params_apply_queued(struct vfe_device *vfe, struct vfe_line *line);','''/* output_lock held; caller completes the returned buffer after unlocking. */
struct camss_buffer *vfe_params_apply_next(struct vfe_device *vfe,
					 struct vfe_line *line, u32 sequence);
void vfe_params_apply_queued(struct vfe_device *vfe, struct vfe_line *line);''')
change(camss/'camss-vfe-17x.c','\tvfe->reg_update |= vfe_reg_update_mask(vfe, line_id);','\tvfe->reg_update |= vfe_reg_update_mask(vfe, line_id);\n\tif (vfe->camss->res->version == CAMSS_8150 && vfe->line[line_id].is_pix)\n\t\tvfe_175_gtm_arm(vfe);')
change(camss/'camss-vfe-17x.c','\t\t\t\tbuf->sof_valid = true;','\t\t\t\tbuf->sof_valid = true;\n\t\t\t\tif (line->is_pix)\n\t\t\t\t\tvfe_175_gtm_tag(vfe, buf);')
old='''static void vfe_isr_reg_update(struct vfe_device *vfe, enum vfe_line_id line_id)
{
	struct vfe_output *output;
	unsigned long flags;'''
new='''static void vfe_isr_reg_update(struct vfe_device *vfe, enum vfe_line_id line_id)
{
	struct vfe_line *line = &vfe->line[line_id];
	struct camss_buffer *params = NULL;
	struct vfe_output *output;
	unsigned long flags;'''
change(camss/'camss-vfe-17x.c',old,new)
change(camss/'camss-vfe-17x.c','''	output = &vfe->line[line_id].output[0];

	if (output->wait_reg_update)''','''	output = &line->output[0];
	if (vfe->camss->res->version == CAMSS_8150 && line->is_pix) {
		struct vfe_175_gtm_state *gtm = &vfe->pixel175.gtm;

		vfe_175_gtm_ack(vfe);
		/* A deferred GTM starts only after the previous PIX RUP is retired. */
		if (output->state == VFE_OUTPUT_ON && (gtm->tracking || gtm->deferred)) {
			params = vfe_params_apply_next(vfe, line, output->sof_sequence);
			if (params)
				vfe->res->hw_ops->reg_update(vfe, line_id);
		}
	}

	if (output->wait_reg_update)''')
change(camss/'camss-vfe-17x.c','''	spin_unlock_irqrestore(&vfe->output_lock, flags);
}

/*
 * vfe_isr_wm_done''','''	spin_unlock_irqrestore(&vfe->output_lock, flags);
	if (params)
		vb2_buffer_done(&params->vb.vb2_buf, VB2_BUF_STATE_DONE);
}

/*
 * vfe_isr_wm_done''')
change(camss/'camss-vfe-17x.c','\t\t\t      sizeof(struct camss_params_ife_ds4),','\t\t\t      sizeof(struct camss_params_ife_ds4) +\n\t\t\t      sizeof(struct camss_params_ife_gtm),')
subprocess.run(['git','-C',str(kernel),'switch','-c','samurai-vfe175-gtm-ack433'],capture_output=True,check=True)
for rel,text in texts.items():(kernel/rel).write_text(text)
subprocess.run(['git','-C',str(kernel),'diff','--check'],check=True)
subprocess.run(['git','-C',str(kernel),'add','--',*texts],check=True)
(HERE/'gtm-driver.patch').write_text(subprocess.check_output(['git','-C',str(kernel),'diff','--cached','--binary'],text=True))
subprocess.run(['git','-C',str(kernel),'commit','-m','media: camss: add IFE175 GTM and SOF-bound PIX update receipts'],check=True)
r=dict(stage=433,parent_commit=base,commit=git('rev-parse','HEAD'),branch=git('branch','--show-current'),source_hashes=[dict(path=rel,sha256=hashlib.sha256((kernel/rel).read_bytes()).hexdigest()) for rel in texts],typed_gtm_bytes=536,gtm_stats_bytes=32,gtm_param_type=9,gtm_stats_type=3,real_pix_reg_update_ack_hook_connected=True,sof_snapshot_connected=True,hardware_verified=False,production_ipa_integrated=False,installed=False,passed=True)
(HERE/'source-state.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
