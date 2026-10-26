"""Add the manufacturer-backed color-bar mode through standard V4L2 control."""
from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent;BASE=Path('/home/cy122/x2pro-linux/camera318-lsc-kernel');TREE=Path('/home/cy122/x2pro-linux/camera325-gw1-tpg-kernel')
commit='7f2de88ea5576457cd332b2383ad887e72c6698c'
assert subprocess.check_output(['git','-C',str(BASE),'rev-parse','HEAD'],text=True).strip()==commit
assert not subprocess.check_output(['git','-C',str(BASE),'status','--porcelain','--untracked-files=no'])
assert not TREE.exists()
q=subprocess.run(['git','-C',str(BASE),'worktree','add','-b','samurai-gw1-tpg325',str(TREE),commit],capture_output=True,timeout=180)
(host.PRIVATE/'worktree.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
p=TREE/'drivers/media/i2c/s5kgw1.c';old=p.read_text();s=old
def replace(a,b):
 global s
 assert s.count(a)==1,a
 s=s.replace(a,b)
replace('#define S5KGW1_EXPOSURE_MARGIN\t6','#define S5KGW1_EXPOSURE_MARGIN\t6\n#define S5KGW1_REG_TEST_PATTERN\tCCI_REG16(0x0600)')
replace('static const s64 s5kgw1_link_freqs[] = { 499200000 };','''static const s64 s5kgw1_link_freqs[] = { 499200000 };

static const char * const s5kgw1_test_pattern_menu[] = {
\t"Disabled",
\t"Color Bars",
\t"Shade Color Bars",
};

static const u8 s5kgw1_test_pattern_values[] = { 0, 2, 3 };''')
replace('\tcase V4L2_CID_EXPOSURE:\n', '''\tcase V4L2_CID_TEST_PATTERN:
\t\tcci_write(sensor->regmap, S5KGW1_REG_TEST_PATTERN,
\t\t\t  s5kgw1_test_pattern_values[ctrl->val], &ret);
\t\tbreak;
\tcase V4L2_CID_EXPOSURE:
''')
replace('v4l2_ctrl_handler_init(h, 9);','v4l2_ctrl_handler_init(h, 10);')
replace('\tret = h->error;\n', '''\tv4l2_ctrl_new_std_menu_items(h, &s5kgw1_ctrl_ops,
\t\t\t\t     V4L2_CID_TEST_PATTERN,
\t\t\t\t     ARRAY_SIZE(s5kgw1_test_pattern_menu) - 1,
\t\t\t\t     0, 0, s5kgw1_test_pattern_menu);
\tret = h->error;
''')
p.write_text(s);q=subprocess.run(['git','-C',str(TREE),'diff','--check'],capture_output=True);assert not q.returncode,q.stdout.decode()
patch=subprocess.check_output(['git','-C',str(TREE),'diff','--','drivers/media/i2c/s5kgw1.c'])
(HERE/'s5kgw1-test-pattern.patch').write_bytes(patch)
report=dict(stage=325,base_commit=commit,source_tree=str(TREE),branch='samurai-gw1-tpg325',source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
 standard_control='V4L2_CID_TEST_PATTERN',menu={'0':'Disabled','1':'Color Bars','2':'Shade Color Bars'},register='0x0600',register_bits=16,register_values=[0,2,3],
 manufacturer_evidence='../kernel324/gw1-pattern-primary-source.json',existing_pm_cache_group_hold_and_stream_setup_reused=True,
 only_sensor_driver_changed=True,board_dt_changed=False,soc_driver_changed=False,tuning_tables_changed=False,built=False,installed=False)
(HERE/'kernel-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
