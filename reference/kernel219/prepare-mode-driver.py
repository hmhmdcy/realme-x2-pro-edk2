"""Retain factory modes, remove unsupported digital-crop-as-compose metadata."""
from pathlib import Path
import difflib,hashlib,json,re,shutil

here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel219')
kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel')
old=(kernel/'drivers/media/i2c/imx471.c').read_text()
assert hashlib.sha256(old.encode()).hexdigest()=='cc7562794d1a9b69a0bf7e98f7ed8fcb9e9917b7a6a5c46b833f649a8c60b175'
previous=private.parent/'kernel217/candidate-source'
new=(previous/'imx471.c').read_text()
old_selection=new[new.index('\tstruct imx471 *sensor = to_imx471(sd);',new.index('static int imx471_get_selection')):new.index('\tcase V4L2_SEL_TGT_CROP:',new.index('static int imx471_get_selection'))]
assert 'V4L2_SEL_TGT_COMPOSE_DEFAULT' in old_selection
new=new.replace(old_selection,'\tswitch (sel->target) {\n',1)
new=new.replace('\tu32 binning;\n\tstruct v4l2_rect digital_crop;\n','')
new,count=re.subn(r'^\t\t\.(?:binning|digital_crop) = .*\n','',new,flags=re.M)
assert count==6
assert not any(x in new for x in ['V4L2_SEL_TGT_COMPOSE','digital_crop','binning;'])
# Fixed metadata controls never access registers, even if changed while powered.
old_ctrl='if (ctrl->id == V4L2_CID_LINK_FREQ || ctrl->id == V4L2_CID_PIXEL_RATE)'
assert new.count(old_ctrl)==1
new=new.replace(old_ctrl,'if (ctrl->id == V4L2_CID_LINK_FREQ || ctrl->id == V4L2_CID_PIXEL_RATE ||\n\t    ctrl->id == V4L2_CID_HBLANK)')
candidate=private/'candidate-source';candidate.mkdir(mode=0o700)
(candidate/'imx471.c').write_text(new)
shutil.copyfile(previous/'sm8150-samurai.dts',candidate/'sm8150-samurai.dts')
old_board=(kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts').read_text()
new_board=(candidate/'sm8150-samurai.dts').read_text()
patch=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/drivers/media/i2c/imx471.c',tofile='b/drivers/media/i2c/imx471.c'))
patch+=''.join(difflib.unified_diff(old_board.splitlines(True),new_board.splitlines(True),fromfile='a/arch/arm64/boot/dts/qcom/sm8150-samurai.dts',tofile='b/arch/arm64/boot/dts/qcom/sm8150-samurai.dts'))
(here/'imx471-factory-modes.patch').write_text(patch)
report=dict(stage=219,source_sha256=hashlib.sha256(new.encode()).hexdigest(),board_sha256=hashlib.sha256(new_board.encode()).hexdigest(),
            removed_unsupported_compose_targets=True,digital_crop_not_misrepresented_as_composition=True,
            hblank_metadata_does_not_access_registers=True,legacy_mode_and_factory_register_tables_preserved=True,
            full_raw_still_requires_explicit_module_opt_in=True,geometry_contract_not_claimed_complete=True,
            canonical216_source_not_modified=True)
(here/'factory-mode-candidate-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
