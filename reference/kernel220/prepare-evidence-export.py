from pathlib import Path
here=Path(__file__).resolve().parent
text=(here.parent/'kernel219/collect-final-evidence.py').read_text()
text=text.replace('k219-runtime/boot-id-private.txt','k220-baseline/boot-id-private.txt').replace("base=root/'k219-runtime'","base=root/'k220-baseline'")
text=text.replace('k219-','k220-').replace('stage=219','stage=220')
text=text.replace('current_module_backup_and_native_test_logs_preserved=True','native_test_logs_and_contexts_preserved=True,kernel_module_backup_retained_in_prior219_archive=True')
compile(text,'evidence-export220','exec');(here/'collect-final-evidence.py').write_text(text)
print('Private220 native evidence export prepared; no archive created yet')
