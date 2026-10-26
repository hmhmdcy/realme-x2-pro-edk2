from pathlib import Path
HERE=Path(__file__).resolve().parent
path=HERE/'auto-capture-body.py';source=path.read_text();assert " name='scene-native';case=root/name;case.mkdir()" in source
source=source.replace(" name='scene-native';case=root/name;case.mkdir()", " name='scene-isolated' if isolated else 'scene-native';case=root/name;case.mkdir()")
source=source.replace(" before=status()['completed']", " if isolated:env['LIBCAMERA_IPA_FORCE_ISOLATION']='1'\n before=status()['completed']")
source=source.replace(" idle();s=status();", " assert state['captures'][name]['final_locked_run']>=8,'AWB did not maintain convergence metadata'\n idle();s=status();")
lines=source.splitlines(keepends=True)
assert lines[-1].startswith(" state['candidate_final_status']")
body=''.join(lines[:2])+" for isolated in [False,True]:\n"+''.join(' '+line for line in lines[2:-1])+lines[-1]
path.write_text(body)
print('Fixed-state native and isolated AWB capture body prepared')
