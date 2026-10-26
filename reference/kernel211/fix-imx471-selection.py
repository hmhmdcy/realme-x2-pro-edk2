from pathlib import Path
import difflib,hashlib,json,re
here=Path(__file__).resolve().parent;k=Path('/home/cy122/pmos-samurai-kernel136/kernel');path=k/'drivers/media/i2c/imx471.c';private=Path('/mnt/e/edk2-samurai-out/kernel211')
original=path.read_text();sha=lambda s:hashlib.sha256(s.encode()).hexdigest()
assert sha(original)=='110977b81694bac72d9c87aec45367747b72526f9ea309863c0964c1af9f84d8'
table=original.split('mode_1928x1088_regs[] = {',1)[1].split('\n};',1)[0]
values={n:int(v,0) for n,v in re.findall(r'\{\s*(IMX471_REG_\w+),\s*(0x[0-9a-fA-F]+|\d+)\s*\}',table)}
crop=dict(left=values['IMX471_REG_X_ADD_STA'],top=values['IMX471_REG_Y_ADD_STA'],width=values['IMX471_REG_X_ADD_END']-values['IMX471_REG_X_ADD_STA']+1,height=values['IMX471_REG_Y_ADD_END']-values['IMX471_REG_Y_ADD_STA']+1)
assert crop==dict(left=8,top=408,width=4640,height=2644)
assert values['IMX471_REG_BINNING_TYPE']==0x22
assert values['IMX471_REG_DIG_CROP_X_OFFSET']+values['IMX471_REG_DIG_CROP_WIDTH']<=crop['width']//2
assert values['IMX471_REG_DIG_CROP_Y_OFFSET']+values['IMX471_REG_DIG_CROP_HEIGHT']<=crop['height']//2
text=original
old='struct imx471_mode {\n\tu32 width;\n\tu32 height;\n';new=old+'\n\t/* Analogue readout window in native pixel-array coordinates. */\n\tstruct v4l2_rect crop;\n'
assert text.count(old)==1;text=text.replace(old,new)
old='\t\t.height = 1088,\n\t\t.fll_def = 1308,'
new='\t\t.height = 1088,\n\t\t.crop = {\n\t\t\t.left = 8,\n\t\t\t.top = 408,\n\t\t\t.width = 4640,\n\t\t\t.height = 2644,\n\t\t},\n\t\t.fll_def = 1308,'
assert text.count(old)==1;text=text.replace(old,new)
old='\t*v4l2_subdev_state_get_format(sd_state, fmt->pad) = fmt->format;\n\n\tif (fmt->which == V4L2_SUBDEV_FORMAT_TRY)\n\t\treturn 0;\n\n\tif (media_entity_is_streaming(&sensor->sd.entity))\n\t\treturn -EBUSY;'
new='\tif (fmt->which == V4L2_SUBDEV_FORMAT_ACTIVE &&\n\t    media_entity_is_streaming(&sensor->sd.entity))\n\t\treturn -EBUSY;\n\n\t*v4l2_subdev_state_get_format(sd_state, fmt->pad) = fmt->format;\n\t*v4l2_subdev_state_get_crop(sd_state, fmt->pad) = mode->crop;\n\n\tif (fmt->which == V4L2_SUBDEV_FORMAT_TRY)\n\t\treturn 0;'
assert text.count(old)==1;text=text.replace(old,new)
old='\tcase V4L2_SEL_TGT_CROP:\n\t\tsel->r = *v4l2_subdev_state_get_crop(sd_state, sel->pad);\n\t\tbreak;'
new=old.rsplit('\t\tbreak;',1)[0]+'\t\treturn 0;';assert text.count(old)==1;text=text.replace(old,new)
assert text.split('mode_1928x1088_regs[] = {',1)[1].split('\n};',1)[0]==table
path.write_text(text)
patch=''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='a/drivers/media/i2c/imx471.c',tofile='b/drivers/media/i2c/imx471.c'))
(here/'imx471-selection.patch').write_text(patch)
report=dict(stage=211,source_before_sha256=sha(original),source_after_sha256=sha(text),crop_returns_success=True,try_and_active_crop_state_initialized=True,analogue_readout_crop_from_existing_register_window=crop,binning=[2,2],digital_crop_offsets_after_binning=[values['IMX471_REG_DIG_CROP_X_OFFSET'],values['IMX471_REG_DIG_CROP_Y_OFFSET']],digital_crop_not_misreported_as_analogue_window=True,register_programming_table_unchanged=True,active_busy_rejection_before_state_mutation=True,hardware_module_not_yet_replaced=True)
(here/'imx471-selection-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
plan=json.loads((private/'current-work-private.json').read_text());plan.update(state='211 heap integration and scoped permissions deployed/verified. IMX471 source now initializes per-mode analogue crop from actual register window and returns success; active busy check precedes state updates. Candidate module build pending, running old module.',next='Build compatible IMX471+CCI targets with metadata preserved, install only updated sensor module and verify after guarded warm boot; then native TRY/ACTIVE selection and actual ordinary-user libcamera capture.')
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(report))
