from pathlib import Path
import difflib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE.parent/'kernel377/queue-overlap-validation.json').read_text())['passed']
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354';relative=Path('drivers/media/platform/qcom/camss')
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
parent=json.loads((HERE.parent/'kernel377/source-state.json').read_text())['commit'];assert git('rev-parse','HEAD')==parent and not git('status','--porcelain')
names=['camss-icp-a5-boot.c','camss-icp-a5-boot.h','camss-icp-a5-boot-test.c'];before={}
for name in names:before[name]=(source/relative/name).read_text();(P/(name+'.before')).write_text(before[name])
after=dict(before);s=before[names[0]]
anchor='#define CONFIG_IOVA (SHARED_IOVA + 0x20000U)';assert s.count(anchor)==1
s=s.replace(anchor,'/* The 100-KiB debug queue is mapped by firmware as a full 1-MiB\n * region starting at SHARED_IOVA + DBG_OFFSET. Keep commands beyond it.\n */\n#define CONFIG_IOVA (SHARED_IOVA + 0x200000U)')
anchor='\t\terror = get_unaligned_le32(a5->message + 28);\n\t\tif (!error)\n\t\t\terror = get_unaligned_le32(a5->message + 32);';assert s.count(anchor)==1
s=s.replace(anchor,'\t\ta5->session_header_error = get_unaligned_le32(a5->message + 28);\n\t\ta5->session_payload_status = get_unaligned_le32(a5->message + 32);\n\t\terror = a5->session_header_error ?: a5->session_payload_status;')
anchor='\ta5->session_scratch_bytes = 0;';assert s.count(anchor)==1;s=s.replace(anchor,anchor+'\n\ta5->session_header_error = a5->session_payload_status = 0;')
anchor='\t\tif (map && a5->command_queued)\n\t\t\ta5->session_uncertain = true;\n\t\treturn ret;';assert s.count(anchor)==1
s=s.replace(anchor,anchor.replace('\n\t\treturn ret;','\n\t\tdev_info(a5->dev, "A5 IPE region opcode=%u failed ret=%d hfi=%u status=%u queued=%u reply=%u uncertain=%u\\n",\n\t\t\t a5->session_opcode, ret, a5->session_header_error,\n\t\t\t a5->session_payload_status, a5->command_queued,\n\t\t\t a5->session_reply, a5->session_uncertain);\n\t\treturn ret;'))
anchor='\tif (ret) {\n\t\tsession_command_failed(a5, ret);\n\t} else {\n\t\tsession->scratch_bytes';assert s.count(anchor)==1
s=s.replace(anchor,'\tif (ret) {\n\t\tsession_command_failed(a5, ret);\n\t\tdev_info(a5->dev, "A5 IPE CONFIG_IO failed ret=%d hfi=%u status=%u\\n",\n\t\t\t ret, a5->session_header_error, a5->session_payload_status);\n\t} else {\n\t\tsession->scratch_bytes')
after[names[0]]=s
after[names[1]]=before[names[1]].replace('\tu32 session_scratch_bytes, io_configs, config_maps, config_unmaps;', '\tu32 session_scratch_bytes, io_configs, config_maps, config_unmaps;\n\tu32 session_header_error, session_payload_status;')
patch=''
for name in names:
 (P/(name+'.proposed')).write_text(after[name]);patch+=''.join(difflib.unified_diff(before[name].splitlines(True),after[name].splitlines(True),fromfile='a/'+str(relative/name),tofile='b/'+str(relative/name)))
(HERE/'command-window.patch').write_text(patch);(HERE/names[2]).write_text(after[names[2]])
(HERE/'proposal-state.json').write_text(json.dumps(dict(stage=378,parent=parent,changed=names[:2],command_iova='0x07600000',existing_reserved_shared_window_reused=True,installed=False),indent=2)+'\n')
print('Separated command alias from the firmware debug mapping; retained actual error status diagnostics.')
