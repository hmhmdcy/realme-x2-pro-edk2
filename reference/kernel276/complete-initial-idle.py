from pathlib import Path
import hashlib,json,shutil
R=Path(__file__).resolve().parent;W=Path('/home/cy122/x2pro-linux/camera270-kernel');name='drivers/i2c/busses/i2c-qcom-cci.c';p=W/name;text=p.read_text()
a='''\t\tret = i2c_add_adapter(&cci->master[i].adap);
\t\tif (ret < 0)
\t\t\tgoto error_i2c;
\t}

\treturn 0;''';b=a.replace('\n\treturn 0;','\n\tpm_runtime_mark_last_busy(dev);\n\tpm_runtime_idle(dev);\n\treturn 0;');assert text.count(a)==1;text=text.replace(a,b);p.write_text(text);shutil.copyfile(p,R/'i2c-qcom-cci.c')
lock=R/'source-candidate-validation.json';d=json.loads(lock.read_text());d['source_files_sha256'][name]=hashlib.sha256(text.encode()).hexdigest();d['initial_idle_requested_after_adapter_registration']=True;lock.write_text(json.dumps(d,indent=2)+'\n')
print('Initial runtime idle added after adapter registration; rebuild required')
