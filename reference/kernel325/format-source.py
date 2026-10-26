from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;TREE=Path('/home/cy122/x2pro-linux/camera325-gw1-tpg-kernel');p=TREE/'drivers/media/i2c/s5kgw1.c'
before=p.read_text();old='\t\tV4L2_CID_TEST_PATTERN, ARRAY_SIZE(s5kgw1_test_pattern_menu) - 1,\n\t\t0, 0, s5kgw1_test_pattern_menu);'
new='\t\t\t\t     V4L2_CID_TEST_PATTERN,\n\t\t\t\t     ARRAY_SIZE(s5kgw1_test_pattern_menu) - 1,\n\t\t\t\t     0, 0, s5kgw1_test_pattern_menu);'
assert before.count(old)==1;p.write_text(before.replace(old,new))
(HERE/'s5kgw1-test-pattern.patch').write_bytes(subprocess.check_output(['git','-C',str(TREE),'diff','--','drivers/media/i2c/s5kgw1.c']))
receipt=HERE/'kernel-source-validation.json';d=json.loads(receipt.read_text());d['source_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();receipt.write_text(json.dumps(d,indent=2)+'\n')
q=subprocess.run(['perl',str(TREE/'scripts/checkpatch.pl'),'--strict','--no-tree',str(HERE/'s5kgw1-test-pattern.patch')],capture_output=True)
(HERE/'style-validation.json').write_text(json.dumps(dict(stage=325,exit_code=q.returncode,output=q.stdout.decode(),passed=q.returncode==0),indent=2)+'\n');print(q.stdout.decode());assert not q.returncode
