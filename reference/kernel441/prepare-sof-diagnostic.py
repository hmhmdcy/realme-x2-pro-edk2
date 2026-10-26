"""Add bounded software queue identity to the existing missing-SOF error."""
from pathlib import Path
import hashlib,json,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;v=storage.mount.mounted_build().parent;k=v/'source354'
p=k/'drivers/media/platform/qcom/camss/camss-vfe.c'
before=p.read_text();a='"Missing SOF tag for completed PIX buffer\\n");'
b='"Missing SOF tag for completed PIX buffer pad=%u active=%u sof=%u next-tag=%u\\n",\n\t\t\t\t\t    output->pad, output->gen2.active_num,\n\t\t\t\t\t    line->output[0].sof_sequence,\n\t\t\t\t\t    output->buf[1] ? output->buf[1]->sof_valid : 0);'
assert before.count(a)==1
assert not subprocess.check_output(['git','-C',str(k),'status','--porcelain'],text=True)
p.write_text(before.replace(a,b));subprocess.run(['git','-C',str(k),'diff','--check'],check=True)
diff=subprocess.check_output(['git','-C',str(k),'diff'],text=True);(HERE/'sof-queue-diagnostic.patch').write_text(diff)
subprocess.run(['git','-C',str(k),'add','--',str(p.relative_to(k))],check=True)
subprocess.run(['git','-C',str(k),'commit','-m','media: camss: identify the output that completes without a SOF'],check=True,capture_output=True)
state=json.loads((HERE/'kernel-source-state.json').read_text())
state['source_hashes'].append(dict(path=str(p.relative_to(k)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
state.update(commit=subprocess.check_output(['git','-C',str(k),'rev-parse','HEAD'],text=True).strip(),software_queue_diagnostic_only=True,no_new_mmio=True)
(HERE/'kernel-source-state.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(dict(stage=441,existing_error_extended_with_output_pad_and_queue_state=True,no_behavior_change=True,no_mmio_added=True,phone_changed=False,passed=True)))
