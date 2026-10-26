from pathlib import Path
import importlib.util,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;parent=Path('/home/cy122/x2pro-linux/camera334-ccm-kernel')
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();tree=build.parent/'source338'
base='6c762eae4a4af55d8d9111d3c9fd8c2880f5dad1';relative=Path('drivers/media/platform/qcom/camss/camss-vfe-175-stats.c')
assert subprocess.check_output(['git','-C',str(parent),'rev-parse','HEAD'],text=True).strip()==base
assert not subprocess.check_output(['git','-C',str(parent),'diff','HEAD']) and not tree.exists()
branch='samurai-lux-grid338'
exists=subprocess.run(['git','-C',str(parent),'show-ref','--verify','--quiet','refs/heads/'+branch]).returncode==0
if exists:
 assert subprocess.check_output(['git','-C',str(parent),'rev-parse',branch],text=True).strip()==base
 command=['git','-C',str(parent),'worktree','add',str(tree),branch]
else:command=['git','-C',str(parent),'worktree','add','-b',branch,str(tree),base]
subprocess.run(command,check=True)
p=tree/relative;s=p.read_text();needle='#define VFE_175_BG_THRESHOLD             16383'
assert needle in s;s=s.replace(needle,needle+'''\n/* Keep both axes divisible by 16 for the common 16x16 metering aggregation.
 * The allocation/ABI maximum remains unchanged; metadata reports actual rows.
 */
#define VFE_175_BG_DEFAULT_ROWS          16''')
needle='bg->rows = min_t(u32, CAMSS_STATS_BG_ROWS, height / 2);';assert needle in s;s=s.replace(needle,'bg->rows = min_t(u32, VFE_175_BG_DEFAULT_ROWS, height / 2);');p.write_text(s)
(HERE/'kernel').mkdir(exist_ok=True);shutil.copyfile(p,HERE/'kernel'/p.name)
(HERE/'bg-grid.patch').write_bytes(subprocess.check_output(['git','-C',str(tree),'diff','HEAD']))
(HERE/'source-state.json').write_text(json.dumps(dict(stage=338,source=str(tree),base_commit=base,branch='samurai-lux-grid338',changed_sources=[str(relative)],installed=False,
 board_sensor_uapi_changes=False,bg_default_grid=[32,16],maximum_regions_unchanged=768),indent=2)+'\n')
print('Prepared32x16 default BG grid in VFE175 statistics backend only.')
