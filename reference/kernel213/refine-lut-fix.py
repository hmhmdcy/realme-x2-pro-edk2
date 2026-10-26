from pathlib import Path
import difflib,hashlib,json
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel213');source=Path(json.loads((private/'source-location-private.json').read_text())['source'])
product=repo/'linux-port/camera/libcamera/0009-softisp-cpu-initialize-luts.patch'
(private/'initial-bool-lut-proposal-not-built.patch').write_bytes(product.read_bytes())
(private/'initial-bool-lut-proposal-validation-private.json').write_bytes((here/'lut-source-validation.json').read_bytes())
header='src/libcamera/software_isp/debayer_cpu.h';cpp='src/libcamera/software_isp/debayer_cpu.cpp'
for name in [header,cpp]:(source/name).write_bytes((private/'libcamera-source-before'/Path(name).name).read_bytes())
path=source/cpp;before=path.read_text();needle='\tparams_.gamma = 1.0;\n';assert before.count(needle)==1
assert 'stored last used gamma to an out-of-range value' in before
after=before.replace(needle,'\tparams_.gamma = -1.0;\n');path.write_text(after)
patch=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+cpp,tofile='b/'+cpp));product.write_text(patch)
report=dict(stage=213,cpu_first_lut_fix_prepared=True,existing_configure_comment_intends_out_of_range_gamma=True,old_gamma_sentinel=1.0,new_gamma_sentinel=-1.0,first_frame_and_reconfigure_force_existing_gamma_and_color_lut_generation=True,no_frame_discard_or_queue_api_change=True,no_added_member_or_header_change=True,earlier_bool_proposal_not_built_or_deployed=True,patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),changed_sources={cpp:dict(before_sha256=hashlib.sha256(before.encode()).hexdigest(),after_sha256=hashlib.sha256(after.encode()).hexdigest())},native_helper_only_source_not_yet_modified=True)
(here/'lut-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
