from pathlib import Path
import difflib,hashlib,json,shutil

here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel225');sdk=Path('/home/cy122/x2pro-linux/libcamera214-root')
state=json.loads((private/'r12-build-state-private.json').read_text())
assert state['exit']==1 and state['original214_files_links_modes_restored']
assert not Path('/proc',str(state['pid'])).exists()
assert not (sdk/'private/libcamera214-before225').exists()
state.update(terminal=True,observed_session_exit=1);(private/'r12-build-state-private.json').write_text(json.dumps(state,indent=2)+'\n')
log=(private/'full-r12-build-private.log').read_text(errors='replace')
assert "no matching function for call to" in log and 'IPASoftInterface::start' in log
r=dict(stage=225,first_build_exit=1,framework_candidate='99990.7.2-r12',
 failure='Generated threaded start forwarding omitted additional output parameters for non-void start.',
 original214_restored=True,no_phone_mutation=True,no_apks_deployed=True,
 correction='Forward output parameters in the non-void ThreadProxy start branch just as for the void branch.')
(here/'first-build-generator-failure-validation.json').write_text(json.dumps(r,indent=2)+'\n')
name='utils/codegen/ipc/generators/libcamera_templates/module_ipa_proxy.h.tmpl'
base=sdk/'work/libcamera225-built/src/libcamera-v0.7.2';original=(base/name).read_text()
old='\t\t\treturn ipa_->{{method.mojom_name}}({{method.parameters|params_comma_sep}});'
new='''			return ipa_->{{method.mojom_name}}({{method.parameters|params_comma_sep}}
	{{- ", " if method|method_param_outputs|params_comma_sep -}}
	{{- method|method_param_outputs|params_comma_sep}});'''
assert original.count(old)==1;text=original.replace(old,new)
patch='''Subject: [PATCH] ipc: forward start output arguments with a return value

The threaded proxy accepts customizable start signatures but drops output
arguments when start also returns a value. Forward them consistently with
the existing void-returning branch. Software IPA start uses these outputs
to apply initial sensor controls before streaming begins.

---
diff --git a/'''+name+' b/'+name+'\n'+''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
(here/'libcamera-threaded-start-outputs.patch').write_text(patch)
p=private/'manual-source'/name;assert not p.exists();p.parent.mkdir(parents=True);p.write_text(text)
recipe=sdk/'work/libcamera225';patchname='0019-ipc-threaded-start-outputs.patch';assert not (recipe/patchname).exists();(recipe/patchname).write_text(patch)
apk=(recipe/'APKBUILD').read_text();marker='\t0018-simple-manual-exposure-controls.patch\n';assert apk.count(marker)==1;apk=apk.replace(marker,marker+'\t'+patchname+'\n')
marker=next(l for l in apk.splitlines(True) if l.rstrip().endswith('  0018-simple-manual-exposure-controls.patch'));apk=apk.replace(marker,marker+hashlib.sha512(patch.encode()).hexdigest()+'  '+patchname+'\n');(recipe/'APKBUILD').write_text(apk)
proof=dict(stage=225,patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),
 original_sources_sha256={name:hashlib.sha256(original.encode()).hexdigest()},
 source_files={name:hashlib.sha256(text.encode()).hexdigest()},
 all_existing_ipa_start_signatures_preserved=True,only_additional_start_output_forwarding_changed=True,
 first_build_failure_preserved=True,not_built_or_deployed=True)
(here/'generator-source-validation.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps(r))
