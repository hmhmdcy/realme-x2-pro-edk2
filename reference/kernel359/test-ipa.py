"""Run real AArch64 module with private factory profiles and native references."""
from pathlib import Path
from contextlib import contextmanager
import json, shutil, subprocess, sys
import host, storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;TREE='/work/libcamera/src/libcamera-v0.7.2'
assert json.loads((HERE/'build-validation.json').read_text())['exit_code']==0
cases=json.loads((P/'cases-private.json').read_text());results=[]
relative=Path('/private/camss359-contract');stage=storage.SDK/str(relative).lstrip('/')
backing=storage.candidate().parent/'camss359-contract';backing.mkdir(exist_ok=True);stage.mkdir(exist_ok=True)
assert subprocess.run(['mountpoint','-q',str(stage)],capture_output=True).returncode
subprocess.run(['mount','--bind',str(backing),str(stage)],check=True,capture_output=True)
try:
    with storage.sdk_candidate():
        reuse='--reuse-built-contract' in sys.argv
        if reuse:assert (HERE/'exposure-contract.cpp').read_bytes()==(stage/'contract.cpp').read_bytes() and (stage/'contract').is_file()
        else:shutil.copyfile(HERE/'exposure-contract.cpp',stage/'contract.cpp')
        flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror','-DLIBCAMERA_BASE_PRIVATE','-I'+TREE+'/include','-I'+TREE+'/output/include','-I'+TREE+'/src/ipa/camss-vfe']
        links=[TREE+'/output/src/ipa/libipa/libipa.a','-L'+TREE+'/output/src/libcamera','-L'+TREE+'/output/src/libcamera/base','-Wl,-rpath-link,'+TREE+'/output/src/libcamera/base','-lcamera','-lcamera-base','-ldl']
        if not reuse:
            q=subprocess.run(['chroot',str(storage.SDK),'g++',*flags,str(relative/'contract.cpp'),TREE+'/src/ipa/camss-vfe/exposure_program.cpp',*links,'-o',str(relative/'contract')],capture_output=True)
            (P/'contract-build.log').write_bytes(q.stdout+q.stderr)
            assert not q.returncode,q.stderr.decode()[-7000:]
        base=['chroot',str(storage.SDK),'env','LD_LIBRARY_PATH='+TREE+'/output/src/libcamera:'+TREE+'/output/src/libcamera/base',
              'LIBCAMERA_IPA_PROXY_PATH='+TREE+'/output/src/libcamera/proxy/worker','LIBCAMERA_LOG_LEVELS=*:ERROR',str(relative/'contract'),TREE+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so']
        variant=dict(s5kgw1='sunny_s5kgw1',imx471='sunny_imx471',imx319='sunny_imx319',s5k3m5='qtech_s5k3m5sx')
        for row in cases:
            profile=Path(row['profile']);native=Path(row['native_reference']);usecase=row['name'].rsplit('-',1)[-1]
            complete=P/'profiles'/(variant[row['model']]+'-'+usecase+'.yaml')
            for source in [profile,native,complete,Path(row['legacy_profile'])]:shutil.copyfile(source,stage/source.name)
            m=row['match'];args=[str(relative/profile.name),row['model'],*[str(m[k]) for k in ['width','height','pixel_rate','line_length','frame_length']],str(row['minimum_lines']),str(row['maximum_lines']),str(row['minimum_code']),str(row['maximum_code']),str(relative/native.name),str(relative/complete.name)]
            # A fresh isolated attempt confirmed clone3 ENOSYS; retain it as
            # an environment-limited failure instead of retrying or calling
            # threaded execution proof of isolated IPC.
            transports=['direct','threaded'] if row is cases[0] else ['direct']
            for transport in transports:
                if reuse:
                    previous=sorted(P.glob(row['name']+'-'+transport+'-r*.log'),key=lambda p:p.stat().st_mtime)
                    if previous:
                        latest=previous[-1]
                        newest=max((stage/'contract').stat().st_mtime,(storage.SDK/TREE.lstrip('/')/'output/src/ipa/camss-vfe/ipa_camss_vfe.so').stat().st_mtime)
                        if latest.stat().st_mtime>=newest and b'EXPOSURE_CONTRACT_PASS' in latest.read_bytes():
                            results.append(dict(case=row['name'],transport=transport,native_allocations=row['native_cases'],reused_unchanged_evidence=True,passed=True));print(row['name']+' '+transport+' unchanged successful evidence reused',flush=True);continue
                q=subprocess.run([*base,transport,*args],capture_output=True,timeout=90)
                number=1
                while (P/f'{row["name"]}-{transport}-r{number}.log').exists():number+=1
                (P/f'{row["name"]}-{transport}-r{number}.log').write_bytes(q.stdout+q.stderr)
                if q.returncode:raise RuntimeError((row['name'],transport,q.returncode,q.stderr.decode()[-5000:]))
                assert b'EXPOSURE_CONTRACT_PASS' in q.stdout
                result=dict(case=row['name'],transport=transport,native_allocations=row['native_cases'],passed=True);results.append(result);print(json.dumps(result),flush=True)
finally:subprocess.run(['umount',str(stage)],check=True,capture_output=True)
report=dict(stage=359,actual_aarch64_ipa=True,execution='ARM64 SDK under QEMU user emulation',synthetic_v4l2_controls=True,sensor_ranges_based_on_current_driver_source=True,hardware_exercised=False,
    cases=results,complete_calibration_profiles_parse=True,isolated_ipc_verified=False,threaded_proxy_verified=True,
    native_allocations_bit_exact=True,real_sensor_range_quantization=True,delayed_statistics_use_sof_policy=True,
    historical_ev_and_flicker_metadata=True,convert_controls_does_not_commit=True,invalid_controls_atomic=True,
    ae_only_controls_do_not_create_isp_revisions=True,coalesced_wb_acknowledgement=True,restart_resets_policy=True,
    ipc_pipeline_version=1,sdk_bind_unmounted=True,installed=False,passed=True)
(HERE/'ipa-contract-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(stage=359,transports_and_contexts=len(results),passed=True)))
