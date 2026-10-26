from pathlib import Path
import difflib,hashlib,json,re,subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel156');out.mkdir(mode=0o700,exist_ok=True)
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel156')
names=['include/drm/drm_panel.h','include/drm/drm_bridge.h','drivers/gpu/drm/drm_panel.c',
    'drivers/gpu/drm/bridge/panel.c','drivers/gpu/drm/msm/disp/dpu1/dpu_kms.c',
    'drivers/gpu/drm/panel/panel-samsung-sofef03f.c','include/trace/events/drm_panel.h','MAINTAINERS']
assert hashlib.sha256((k/'drivers/gpu/drm/msm/dsi/dsi_host.c').read_bytes()).hexdigest()=='f6eaf35bc05aeb913ea65954b0a4787ac6fbe26c0aedf74477f27076897e2adf'
assert not (out/'source-before-private.json').exists()
before={n:(k/n).read_text() if (k/n).exists() else None for n in names}
(out/'source-before-private.json').write_text(json.dumps(before))
(out/'config-before-private').write_bytes((k/'.config').read_bytes())
other_args=['git','diff','--binary','--','.']+[':(exclude)'+n for n in names]
other=subprocess.check_output(other_args,cwd=k)
(out/'other-diff-before-private.patch').write_bytes(other)
after={n:v for n,v in before.items()}
def replace(n,old,new):
    assert after[n].count(old)==1,(n,old)
    after[n]=after[n].replace(old,new,1)
def function(s,name):
    m=re.search(r'^(?:static )?(?:int|void|bool) '+name+r'\([^;]+?\n\{',s,re.M)
    assert m,name
    end=m.end();depth=1
    while depth:
        if s[end]=='{':depth+=1
        elif s[end]=='}':depth-=1
        end+=1
    return s[m.start():end]

header=names[0]
replace(header,'\tbool enabled;','''\tbool enabled;

	/**
	 * @delay_backlight_until_first_frame:
	 * Command panels requiring a complete frame in GRAM before illumination.
	 * The display driver must call drm_panel_first_frame_done() after TX done.
	 */
	bool delay_backlight_until_first_frame;

	/**
	 * @backlight_ready: Whether positive brightness updates may reach the panel.
	 * Updated by the panel helpers; drivers read it with READ_ONCE().
	 */
	bool backlight_ready;''')
replace(header,'void drm_panel_enable(struct drm_panel *panel);',
    'void drm_panel_enable(struct drm_panel *panel);\nvoid drm_panel_first_frame_done(struct drm_panel *panel);')

core=names[2]
replace(core,'\tpanel->connector_type = connector_type;',
    '\tpanel->connector_type = connector_type;\n\tpanel->delay_backlight_until_first_frame = false;\n\tpanel->backlight_ready = false;')
replace(core,'#include <drm/drm_print.h>', '''#include <drm/drm_print.h>

#define CREATE_TRACE_POINTS
#include <trace/events/drm_panel.h>
#undef CREATE_TRACE_POINTS''')
old=function(after[core],'drm_panel_enable')
notify=old[old.index('\tret = backlight_enable'):old.index('\nexit:')]
helpers='''static void drm_panel_enable_backlight(struct drm_panel *panel)
{
	struct drm_panel_follower *follower;
	int ret;

	trace_drm_panel_backlight(dev_name(panel->dev), 1,
				  panel->backlight ? panel->backlight->props.brightness : -1);
'''+notify.rstrip()+'''
}

/**
 * drm_panel_first_frame_done - illuminate a panel after a complete frame
 * @panel: panel whose display controller has completed pixel transmission
 *
 * Call in sleepable commit context after a successful TX-complete wait.
 * A CTL start, TE pulse or page-flip event alone is not sufficient.
 */
void drm_panel_first_frame_done(struct drm_panel *panel)
{
	if (!panel || !panel->delay_backlight_until_first_frame)
		return;

	mutex_lock(&panel->follower_lock);
	if (panel->prepared && panel->enabled && !panel->backlight_ready) {
		WRITE_ONCE(panel->backlight_ready, true);
		drm_panel_enable_backlight(panel);
	}
	mutex_unlock(&panel->follower_lock);
}
EXPORT_SYMBOL_GPL(drm_panel_first_frame_done);

'''
new=old.replace('\tstruct drm_panel_follower *follower;\n','',1)
new=new.replace(notify,'''\tWRITE_ONCE(panel->backlight_ready,
		   !panel->delay_backlight_until_first_frame);
	if (panel->backlight_ready) {
		drm_panel_enable_backlight(panel);
	} else {
		int brightness = panel->backlight ? panel->backlight->props.brightness : -1;

		trace_drm_panel_backlight(dev_name(panel->dev), 0, brightness);
	}
''')
after[core]=after[core].replace(old,new,1)
replace(core,'/**\n * drm_panel_enable - enable a panel',helpers+'/**\n * drm_panel_enable - enable a panel')
old=function(after[core],'drm_panel_disable')
start=old.index('\tlist_for_each_entry(follower, &panel->followers, list)')
end=old.index('\n\tret = backlight_disable',start)
followers=old[start:end]
new=old[:start]+'''\tif (!panel->delay_backlight_until_first_frame || panel->backlight_ready) {
'''+''.join('\t'+line if line.strip() else line for line in followers.rstrip().splitlines(True))+'''
	}
	WRITE_ONCE(panel->backlight_ready, false);
	trace_drm_panel_backlight(dev_name(panel->dev), 2, 0);
'''+old[end:]
after[core]=after[core].replace(old,new,1)

bridge_header=names[1]
replace(bridge_header,'bool drm_bridge_is_panel(const struct drm_bridge *bridge);',
    'bool drm_bridge_is_panel(const struct drm_bridge *bridge);\nbool drm_panel_bridge_needs_first_frame(struct drm_bridge *bridge);\nvoid drm_panel_bridge_first_frame_done(struct drm_bridge *bridge);')
needle='static inline int drm_panel_bridge_set_orientation'
stubs='''static inline bool drm_panel_bridge_needs_first_frame(struct drm_bridge *bridge)
{
	return false;
}

static inline void drm_panel_bridge_first_frame_done(struct drm_bridge *bridge)
{
}

'''
replace(bridge_header,needle,stubs+needle)
bridge=names[3]
needle='EXPORT_SYMBOL(drm_bridge_is_panel);'
replace(bridge,needle,needle+'''

/**
 * drm_panel_bridge_needs_first_frame - check for deferred panel illumination
 * @bridge: bridge to examine, which may be a non-panel bridge
 */
bool drm_panel_bridge_needs_first_frame(struct drm_bridge *bridge)
{
	struct drm_panel *panel;

	if (!bridge || !drm_bridge_is_panel(bridge))
		return false;
	panel = drm_bridge_to_panel_bridge(bridge)->panel;
	return panel->delay_backlight_until_first_frame &&
		READ_ONCE(panel->enabled) && !READ_ONCE(panel->backlight_ready);
}
EXPORT_SYMBOL_GPL(drm_panel_bridge_needs_first_frame);

/**
 * drm_panel_bridge_first_frame_done - notify a panel after pixel TX completion
 * @bridge: panel bridge, or a non-panel bridge to ignore
 */
void drm_panel_bridge_first_frame_done(struct drm_bridge *bridge)
{
	if (bridge && drm_bridge_is_panel(bridge))
		drm_panel_first_frame_done(drm_bridge_to_panel_bridge(bridge)->panel);
}
EXPORT_SYMBOL_GPL(drm_panel_bridge_first_frame_done);''')

dpu=names[4]
replace(dpu,'#include "dpu_kms.h"','#include "dpu_kms.h"\n#include <drm/drm_bridge.h>')
helper='''static void dpu_kms_first_frame_backlight(struct drm_crtc *crtc)
{
	struct drm_encoder *encoder;
	bool needs_first_frame;
	int ret;

	if (!crtc->state->enable || !drm_atomic_crtc_effectively_active(crtc->state))
		return;

	drm_for_each_encoder_mask(encoder, crtc->dev, crtc->state->encoder_mask) {
		needs_first_frame = false;
		drm_for_each_bridge_in_chain(encoder, bridge) {
			if (drm_panel_bridge_needs_first_frame(bridge))
				needs_first_frame = true;
		}
		if (!needs_first_frame)
			continue;

		/* CTL start can precede pp_done: wait until all pixels reach GRAM. */
		ret = dpu_encoder_wait_for_tx_complete(encoder);
		if (ret && ret != -EWOULDBLOCK) {
			DPU_ERROR("first frame TX failed: %d; backlight stays blank\\n", ret);
			continue;
		}
		drm_for_each_bridge_in_chain(encoder, bridge)
			drm_panel_bridge_first_frame_done(bridge);
	}
}

'''
needle='static void dpu_kms_complete_commit(struct msm_kms *kms, unsigned crtc_mask)'
replace(dpu,needle,helper+needle)
replace(dpu,'\tfor_each_crtc_mask(dpu_kms->dev, crtc, crtc_mask)\n\t\tdpu_crtc_complete_commit(crtc);',
    '\tfor_each_crtc_mask(dpu_kms->dev, crtc, crtc_mask) {\n\t\tdpu_kms_first_frame_backlight(crtc);\n\t\tdpu_crtc_complete_commit(crtc);\n\t}')

panel=names[5]
replace(panel,'\tif (!ctx->panel.prepared)\n\t\treturn 0;\n\treturn mipi_dsi_dcs_set_display_brightness_large',
    '\tif (!ctx->panel.prepared)\n\t\treturn 0;\n\tif (backlight_get_brightness(bl) && !READ_ONCE(ctx->panel.backlight_ready))\n\t\treturn 0;\n\treturn mipi_dsi_dcs_set_display_brightness_large')
replace(panel,'\tctx->panel.prepare_prev_first = true;',
    '\tctx->panel.prepare_prev_first = true;\n\tctx->panel.delay_backlight_until_first_frame = true;')
replace(panel,'\t\t.type = BACKLIGHT_RAW, .brightness = 400, .max_brightness = 2047,',
    '\t\t.type = BACKLIGHT_RAW, .brightness = 400, .max_brightness = 2047,\n\t\t.power = FB_BLANK_POWERDOWN,')

after[names[6]]='''/* SPDX-License-Identifier: GPL-2.0-only */
#undef TRACE_SYSTEM
#define TRACE_SYSTEM drm_panel

#if !defined(_TRACE_DRM_PANEL_H) || defined(TRACE_HEADER_MULTI_READ)
#define _TRACE_DRM_PANEL_H

#include <linux/tracepoint.h>

TRACE_EVENT(drm_panel_backlight,
	    TP_PROTO(const char *panel, int phase, int brightness),
	    TP_ARGS(panel, phase, brightness),
	    TP_STRUCT__entry(
		    __string(panel, panel)
		    __field(int, phase)
		    __field(int, brightness)
	    ),
	    TP_fast_assign(
		    __assign_str(panel);
		    __entry->phase = phase;
		    __entry->brightness = brightness;
	    ),
	    TP_printk("panel=%s phase=%d brightness=%d", __get_str(panel),
		      __entry->phase, __entry->brightness)
);

#endif

#include <trace/define_trace.h>
'''
maint=after['MAINTAINERS']
start=maint.index('\nDRM DRIVERS\n')
end=maint.index('\nDRM DRIVERS AND MISC GPU PATCHES\n',start)
block=maint[start:end]
assert block.count('F:\tinclude/linux/vga*\n')==1
updated=block.replace('F:\tinclude/linux/vga*\n','F:\tinclude/linux/vga*\nF:\tinclude/trace/events/drm_panel.h\n')
after['MAINTAINERS']=maint[:start]+updated+maint[end:]
for n,s in after.items():(k/n).write_text(s)
assert subprocess.check_output(other_args,cwd=k)==other
patch='''Subject: [PATCH] drm/panel: delay SOFEF03F illumination until pixel TX completes

The stock panel needs a complete frame in GRAM before illumination.
Keep it blank through prepare/enable and defer positive backlight updates.
Have DPU commit completion wait for TX done only for opted-in panels, then
enable their backlight and followers. Reset readiness on disable and retain
normal behavior for other panels. CTL start or flip events are insufficient.

---

'''
for n in names:
    patch+='diff --git a/'+n+' b/'+n+'\n'
    if before[n] is None:patch+='new file mode 100644\n'
    patch+=''.join(difflib.unified_diff((before[n] or '').splitlines(True),after[n].splitlines(True),
        fromfile='/dev/null' if before[n] is None else 'a/'+n,tofile='b/'+n))
(ref/'first-frame-backlight.patch').write_text(patch)
report=dict(stage=156,baseline_kernel=154,modified_files=names,
    before_sha256={n:hashlib.sha256(v.encode()).hexdigest() if v is not None else None for n,v in before.items()},
    after_sha256={n:hashlib.sha256(v.encode()).hexdigest() for n,v in after.items()},
    source_dsi154_retained=True,panel_gpio153_retained=True,fixed_sleep_not_used=True,
    opt_in_only=True,hardware_tx_wait_required=True,hardware_bug_fixed=False,deployed=False)
(ref/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
