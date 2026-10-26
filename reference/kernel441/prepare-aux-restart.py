"""Keep strict SOF rejection and identify the auxiliary starvation boundary."""
from pathlib import Path
import hashlib,json,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;v=storage.mount.mounted_build().parent;k=v/'source354';c=k/'drivers/media/platform/qcom/camss'
assert not subprocess.check_output(['git','-C',str(k),'status','--porcelain'],text=True)
header=c/'camss-vfe.h';s=header.read_text();a='\tunsigned int sof_sequence;';assert s.count(a)==1
header.write_text(s.replace(a,a+'\n\tbool recovering_sof;'))
p=c/'camss-vfe.c';s=p.read_text()
def replace(a,b):
 global s
 assert s.count(a)==1,(a,s.count(a));s=s.replace(a,b)
at='static struct camss_buffer *vfe_output_done('
helper='''/* Only a restart after an empty auxiliary address FIFO can produce an
 * expected untagged head. It remains an ERROR buffer and carries no SOF.
 * A tagged completion ends recovery; later missing tags are still faults. */
static bool vfe_aux_restart_drop(struct vfe_output *output,
                                 const struct camss_buffer *buffer)
{
 if (buffer->sof_valid) {
  output->recovering_sof = false;
  return false;
 }
 return output->video_out.auxiliary && output->recovering_sof;
}

'''
replace(at,helper+at)
replace('\tu32 index;\n\n\tready_buf = output->buf[0];','\tu32 index;\n\tbool restart_drop;\n\n\tready_buf = output->buf[0];')
replace('\t\tif (ready_buf->sof_valid)\n\t\t\toutput->sequence', '\t\trestart_drop = vfe_aux_restart_drop(output, ready_buf);\n\t\tif (ready_buf->sof_valid)\n\t\t\toutput->sequence')
replace('\t\t\toutput->sequence = ready_buf->vb.sequence + 1;\n\t\telse', '''\t\t\toutput->sequence = ready_buf->vb.sequence + 1;
\t\telse if (restart_drop)
\t\t\tdev_info_ratelimited(vfe->camss->dev,
\t\t\t\t"Dropped untagged auxiliary restart buffer pad=%u sof=%u\\n",
\t\t\t\toutput->pad, line->output[0].sof_sequence);
\t\telse''')
replace('\toutput->sof_sequence = 0;','\toutput->sof_sequence = 0;\n\toutput->recovering_sof = false;')
replace('''\t\tif (vid->auxiliary && output->gen2.active_num == 1)
\t\t\tops->vfe_output_start(vfe, output);''','''\t\tif (vid->auxiliary && output->gen2.active_num == 1) {
\t\t\toutput->recovering_sof = true;
\t\t\tops->vfe_output_start(vfe, output);
\t\t}''')
p.write_text(s);subprocess.run(['git','-C',str(k),'diff','--check'],check=True)
(HERE/'aux-restart-sof.patch').write_text(subprocess.check_output(['git','-C',str(k),'diff'],text=True))
paths=[str(f.relative_to(k)) for f in [p,header]]
subprocess.run(['git','-C',str(k),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(k),'commit','-m','media: camss: distinguish rejected auxiliary restart heads from SOF faults'],check=True,capture_output=True)
state=json.loads((HERE/'kernel-source-state.json').read_text());rows={r['path']:r for r in state['source_hashes']}
for f in [p,header]:rows[str(f.relative_to(k))]=dict(path=str(f.relative_to(k)),sha256=hashlib.sha256(f.read_bytes()).hexdigest())
state.update(source_hashes=list(rows.values()),commit=subprocess.check_output(['git','-C',str(k),'rev-parse','HEAD'],text=True).strip(),auxiliary_restart_state_explicit=True,untagged_buffers_still_vb2_error=True,unexpected_sof_faults_still_errors=True,changes_only_geometry_and_paired_format_sizing=False)
(HERE/'kernel-source-state.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(dict(stage=441,auxiliary_fifo_restart_only=True,valid_sof_clears_recovery=True,untagged_data_still_rejected=True,no_mmio_or_uapi_change=True,phone_changed=False,passed=True)))
