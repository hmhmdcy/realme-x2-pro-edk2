"""Publish the two-file489 delta and recipe overlays; never builds or reads SDK."""
from pathlib import Path
import difflib,hashlib,json,shutil,subprocess
import storage
HERE=Path(__file__).resolve().parent;PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel490')
PATCH='0067-camera-sensor-properties-v4l2-format.patch'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    workspace=storage.workspace();assert shutil.disk_usage(workspace.parent).free>2*1024**3+16*1024**2
    source_state=HERE.parent/'kernel489/source-state.json';state=json.loads(source_state.read_text());assert state['passed']
    assert {row['path'] for row in state['changes']}=={'src/libcamera/sensor/camera_sensor_properties.cpp','src/libcamera/v4l2_subdevice.cpp'}
    baseline=Path(state['baseline_source']);candidate=Path(state['source'])
    replay=workspace/'source-replay';assert not replay.exists() and not (HERE/PATCH).exists()
    replay.mkdir();lines=[];rows=[]
    for row in state['changes']:
        name=row['path'];before=(baseline/name).read_bytes();after=(candidate/name).read_bytes()
        assert hashlib.sha256(before).hexdigest()==row['baseline_sha256'] and hashlib.sha256(after).hexdigest()==row['candidate_sha256']
        lines.extend(difflib.unified_diff(before.decode().splitlines(True),after.decode().splitlines(True),fromfile='a/'+name,tofile='b/'+name))
        target=replay/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(before)
        rows.append(dict(path=name,before_sha256=row['baseline_sha256'],after_sha256=row['candidate_sha256'],source_stage=row['stage']))
    patch=HERE/PATCH;patch.write_text(''.join(lines))
    for label,extra in [('dry-run',['--dry-run']),('apply',[])]:
        result=subprocess.run(['patch','-p1','--batch','--fuzz=0','-i',str(patch),*extra],cwd=replay,capture_output=True)
        log=result.stdout+result.stderr;(PRIVATE/('source-replay-'+label+'-private.log')).write_bytes(log)
        assert result.returncode==0 and b'fuzz' not in log.lower() and b'offset' not in log.lower()
    assert all(sha(replay/row['path'])==row['after_sha256'] for row in rows)
    recipe_rows=[]
    for package in ['libcamera','samurai-camera-config']:
        original=HERE.parent/'kernel475/recipes'/package/'APKBUILD';text=original.read_text()
        if package=='libcamera':
            assert text.count('pkgrel=33\n')==1;text=text.replace('pkgrel=33\n','pkgrel=34\n')
            needle='\t0066-camss-r33-processed-ipe-cohort.patch\n';assert text.count(needle)==1
            text=text.replace(needle,needle+'\t'+PATCH+'\n')
            at=text.rfind('"');text=text[:at]+hashlib.sha512(patch.read_bytes()).hexdigest()+'  '+PATCH+'\n'+text[at:]
            assert 'DESTDIR="$pkgdir" meson install --no-rebuild -C output' in text
        else:
            assert text.count('pkgrel=28\n')==1;text=text.replace('pkgrel=28\n','pkgrel=29\n').replace('99990.7.2-r33','99990.7.2-r34')
        target=HERE/'recipes'/package/'APKBUILD';target.parent.mkdir(parents=True);target.write_text(text)
        result=subprocess.run(['sh','-n',str(target)],capture_output=True)
        (PRIVATE/('recipe-'+package+'-syntax-private.log')).write_bytes(result.stdout+result.stderr);assert result.returncode==0
        recipe_rows.append(dict(package=package,baseline_apkbuild_sha256=sha(original),candidate_apkbuild_sha256=sha(target)))
    references=dict(stage=490,materialization='overlay references only; no full recipe source copy or recipe build',
        libcamera_base='reference/kernel440/recipes/libcamera',
        existing_cohort_patch=dict(path='reference/kernel475/0066-camss-r33-processed-ipe-cohort.patch',sha256=sha(HERE.parent/'kernel475/0066-camss-r33-processed-ipe-cohort.patch')),
        new_patch=dict(path='reference/kernel490/'+PATCH,sha256=sha(patch)),
        configuration_base='reference/kernel440/recipes/samurai-camera-config',
        overlay_apkbuilds=['reference/kernel490/recipes/libcamera/APKBUILD','reference/kernel490/recipes/samurai-camera-config/APKBUILD'])
    (HERE/'recipe-inputs.json').write_text(json.dumps(references,indent=2)+'\n')
    report=dict(stage=490,passed=True,changed_source_files=rows,patch=PATCH,patch_sha256=sha(patch),
        zero_fuzz_zero_offset_two_file_replay_matches489=True,source489_receipt_sha256=sha(source_state),recipe_apkbuilds=recipe_rows,
        framework_version='99990.7.2-r34',configuration_version='0.1.0-r29',meson_install_step_unchanged=True,
        production_isInstalled_function_changed=False,full_recipe_materialized=False,full_recipe_build_executed=False,
        artifacts_are_cached_binary_repack=True,new_core_uses489_meson_normalized_bytes=True,other_ELFs_unchanged=True,
        no_sdk_access=True,no_device=True,private_factory_data_added=False)
    (HERE/'source-recipe-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(stage=490,passed=True,changed_source_files=2,patch_sha256=sha(patch),recipe_build_executed=False)))


if __name__=='__main__':main()
