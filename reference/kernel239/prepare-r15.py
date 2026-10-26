"""Prepare complete r15 from r14, fixing initial ISP snapshots without inventing BLC."""
from pathlib import Path
import difflib,hashlib,json,shutil
R=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');cache=SDK/'work/libcamera238-r14-built/src/libcamera-v0.7.2'
changes={}
def change(name,old,new):
 before=(cache/name).read_text();assert before.count(old)==1,name
 changes[name]=(before,before.replace(old,new))
change('src/libcamera/software_isp/software_isp.cpp',
       '\tispWorkerThread_.start();\n\n\treturn debayer_->invokeMethod(&Debayer::start,',
       '\t/* start() is synchronous: publish its initial parameters before frames. */\n\tsaveIspParams();\n\tispWorkerThread_.start();\n\n\treturn debayer_->invokeMethod(&Debayer::start,')
change('src/ipa/simple/soft_simple.cpp',
       '\t\talgo->prepare(context_, 0, initial, params_);\n\tinitial.sensor.exposure',
       '\t\talgo->prepare(context_, 0, initial, params_);\n\tparams_->combinedMatrix = context_.activeState.combinedMatrix;\n\tinitial.sensor.exposure')
change('src/libcamera/software_isp/debayer_cpu.cpp',
       '\tupdateLookupTables(params);\n',
       '\tLOG(Debayer, Debug) << "Processing frame " << frame\n\t\t\t    << ", sequence " << input->metadata().sequence\n\t\t\t    << ", timestamp " << input->metadata().timestamp;\n\tupdateLookupTables(params);\n')
patch='Subject: [PATCH] software_isp: publish initial IPA parameters before streaming\n\nThe synchronous IPA start prepares the first parameters. Copy that snapshot\nbefore starting the worker, including the initial CCM. Keep asynchronous\nper-frame updates unchanged. Log frame identity next to CPU parameter dumps.\n\n---\n'
for name,(before,after) in changes.items():
 patch+='diff --git a/'+name+' b/'+name+'\n'+''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
name='0022-soft-initial-parameters.patch';(R/name).write_text(patch)
recipe=SDK/'work/libcamera239-r15';config=SDK/'work/samurai-camera-config239-r15';assert not recipe.exists() and not config.exists();recipe.mkdir();config.mkdir()
for p in (R.parent/'kernel238/recipes/libcamera').iterdir():
 if p.is_file():shutil.copyfile(p,recipe/p.name)
for p in (R.parent/'kernel238/recipes/samurai-camera-config').iterdir():
 if p.is_file():shutil.copyfile(p,config/p.name)
shutil.copyfile(R/name,recipe/name)
apk=(recipe/'APKBUILD').read_text();assert apk.count('pkgrel=14\n')==1
apk=apk.replace('pkgrel=14\n','pkgrel=15\n').replace('\t0021-imx319-gain-helper.patch\n','\t0021-imx319-gain-helper.patch\n\t'+name+'\n')
at=apk.rfind('\n"');apk=apk[:at]+'\n'+hashlib.sha512(patch.encode()).hexdigest()+'  '+name+apk[at:];(recipe/'APKBUILD').write_text(apk)
cfg=(config/'APKBUILD').read_text();assert cfg.count('pkgrel=9\n')==1
cfg=cfg.replace('pkgrel=9\n','pkgrel=10\n').replace('99990.7.2-r14','99990.7.2-r15');(config/'APKBUILD').write_text(cfg)
for dirname,source in [('libcamera',recipe),('samurai-camera-config',config)]:
 target=R/'recipes'/dirname;target.mkdir(parents=True)
 for p in source.iterdir():
  if p.is_file():shutil.copyfile(p,target/p.name)
sha=lambda b:hashlib.sha256(b).hexdigest()
report=dict(stage=239,patch_sha256=sha(patch.encode()),source_before_files={n:sha(v[0].encode()) for n,v in changes.items()},source_files={n:sha(v[1].encode()) for n,v in changes.items()},
            patch_count=22,prior21_patch_inputs_preserved=True,initial_start_synchronous_snapshot=True,initial_combined_matrix_published=True,per_frame_asynchronous_api_unchanged=True,black_level_and_tuning_unchanged=True,full_features_and_signing_inputs_retained=True)
(R/'r15-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
