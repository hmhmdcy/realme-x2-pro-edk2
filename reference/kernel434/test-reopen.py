from pathlib import Path
import importlib.util,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage434test',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);K=m.mounted_build().parent/'source354'
raw=(K/'drivers/media/platform/qcom/camss/camss-vfe-17x.c').read_text();start=raw.index('static int vfe_enable(');brace=raw.index('{',start);end=brace+1;depth=1
while depth:depth+=(raw[end]=='{')-(raw[end]=='}');end+=1
work=P/'reopen-test';work.mkdir(exist_ok=True);(work/'enable-body-private.c').write_text(raw[start:end]+'\n');shutil.copyfile(HERE/'reopen-test.c',work/'test.c')
q=subprocess.run(['gcc','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-no-pie','-I'+str(work),str(work/'test.c'),'-o',str(work/'test')],capture_output=True);assert not q.returncode,q.stderr.decode()
q=subprocess.run([str(work/'test')],capture_output=True);assert not q.returncode,q.stderr.decode();assert b'REOPEN_PASS' in q.stdout
r=dict(stage=434,actual_vfe_enable_body=True,stopped_pix_rup_cleared_before_initial_packet=True,rdi_bits_preserved=True,repeat_open_without_module_reload=True,prepare_and_enable_errors_checked=True,non_pix_path_unchanged=True,host_asan_ubsan=True,passed=True)
(HERE/'reopen-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
