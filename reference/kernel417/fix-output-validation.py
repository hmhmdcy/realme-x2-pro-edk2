"""Add the vb2 output-field callback required before Request QBUF."""
from pathlib import Path
import importlib.util,subprocess
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354'
path=source/'drivers/media/platform/qcom/camss/camss-icp-a5-m2m.c';text=path.read_text()
marker='static void buffer_queue(struct vb2_buffer *vb)'
assert text.count(marker)==1 and 'buffer_output_validate' not in text
text=text.replace(marker,(HERE/'output-validation-tail.c').read_text()+'\n'+marker)
text=text.replace('\t.buf_prepare = buffer_prepare,','\t.buf_prepare = buffer_prepare,\n\t.buf_out_validate = buffer_output_validate,')
path.write_text(text);subprocess.run(['git','-C',str(source),'diff','--check'],check=True)
print('Added explicit ANY/NONE progressive output validation; failed runtime r2 retained.')
