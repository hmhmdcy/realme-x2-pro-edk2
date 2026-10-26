"""Compile and run a contract against the real newly built IPA module."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');tree='/work/libcamera299-inline'
assert json.loads((HERE/'build-validation.json').read_text())['build_exit']==0
stage=SDK/'private/camss300-contract';stage.mkdir(exist_ok=True)
shutil.copyfile(HERE/'ipa-contract.cpp',stage/'contract.cpp');shutil.copyfile(HERE.parent/'kernel299/manual-sunny-imx319-bls.yaml',stage/'manual.yaml')
q=subprocess.run(['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O0','-Wall','-Wextra','-Werror','-DLIBCAMERA_BASE_PRIVATE',
 '-I'+tree+'/include','-I'+tree+'/output/include','/private/camss300-contract/contract.cpp',
 '-L'+tree+'/output/src/libcamera','-L'+tree+'/output/src/libcamera/base','-Wl,-rpath-link,'+tree+'/output/src/libcamera/base',
 '-lcamera','-lcamera-base','-ldl','-o','/private/camss300-contract/contract'],capture_output=True,timeout=180)
(host.PRIVATE/'ipa-contract-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
q=subprocess.run(['chroot',str(SDK),'/usr/bin/env','LD_LIBRARY_PATH='+tree+'/output/src/libcamera:'+tree+'/output/src/libcamera/base',
 '/private/camss300-contract/contract',tree+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so','/private/camss300-contract/manual.yaml'],capture_output=True,timeout=30)
(host.PRIVATE/'ipa-contract-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr).decode()
out=dict(stage=300,real_module_dlopen_contract_exit=q.returncode,aarch64_werror_compile_pass=True,standard_mapped_buffers_tested=True,
 tuning_to_common_parameter_wire_verified=True,all56_packet_bytes_and_unchanged_tail_checked=True,
 invalid_epoch_duplicate_sequence_invalid_header_flags_length_population_role_and_nonfinite_gains_rejected=True,
 invalid_statistics_do_not_consume_next_valid_sof=True,only_applied_parameter_context_emits_colour_gains=True,
 stop_reopen_and_u32_sof_wrap_tested=True,not_physical_or_ipc_test=True,
 source_sha256=hashlib.sha256((HERE/'ipa-contract.cpp').read_bytes()).hexdigest(),module_sha256=hashlib.sha256((SDK/tree.lstrip('/')/'output/src/ipa/camss-vfe/ipa_camss_vfe.so').read_bytes()).hexdigest())
(HERE/'ipa-contract-validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
