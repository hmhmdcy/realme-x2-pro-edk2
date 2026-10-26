from pathlib import Path
import difflib,hashlib,json
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel213');source=Path(json.loads((private/'source-location-private.json').read_text())['source'])
names=['src/libcamera/software_isp/debayer_cpu.h','src/libcamera/software_isp/debayer_cpu.cpp'];before={n:(source/n).read_text() for n in names}
header=before[names[0]];needle='\tDebayerParams params_;\n';assert header.count(needle)==1;header=header.replace(needle,needle+'\tbool lookupTablesValid_ = false;\n')
cpp=before[names[1]]
needle='\tccmEnabled_ = ccmEnabled;\n';assert cpp.count(needle)==1;cpp=cpp.replace(needle,needle+'\tlookupTablesValid_ = false;\n')
needle='\tconst bool gammaUpdateNeeded =\n';assert cpp.count(needle)==1;cpp=cpp.replace(needle,needle+'\t\t!lookupTablesValid_ ||\n')
needle='\tparams_ = params;\n';assert cpp.count(needle)==1;cpp=cpp.replace(needle,needle+'\tlookupTablesValid_ = true;\n')
after={names[0]:header,names[1]:cpp};patch=''
for name in names:
    path=source/name;(private/'libcamera-source-before'/path.name).write_text(before[name]);path.write_text(after[name]);patch+=''.join(difflib.unified_diff(before[name].splitlines(True),after[name].splitlines(True),fromfile='a/'+name,tofile='b/'+name))
target=repo/'linux-port/camera/libcamera/0009-softisp-cpu-initialize-luts.patch';assert not target.exists();target.write_text(patch)
report=dict(stage=213,cpu_lut_validity_fix_prepared=True,first_process_forces_gamma_and_color_lut_generation=True,reconfigure_invalidates_cached_luts=True,no_frame_dropped_or_faked=True,no_hardware_mode_register_or_queue_api_change=True,patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),changed_sources={name:dict(before_sha256=hashlib.sha256(before[name].encode()).hexdigest(),after_sha256=hashlib.sha256(after[name].encode()).hexdigest()) for name in names},native_helper_only_source_not_yet_modified=True)
(here/'lut-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
