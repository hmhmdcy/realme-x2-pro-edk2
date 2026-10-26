from pathlib import Path
import difflib
import re
import subprocess

root = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/kernel180')
path = root / 'drivers/soc/qcom/pdr_interface.c'
before = (out / 'pdr_interface.c.before-private').read_text()
source = path.read_text()
for name in ('pdr_locator_new_server', 'pdr_locator_del_server', 'pdr_notifier_new_server', 'pdr_notifier_del_server'):
    pattern = r'^static (?:int|void) ' + name + r'\([^{}]+\n'
    old = re.search(pattern, before, re.M).group()
    source = re.sub(pattern, lambda _: old, source, count=1, flags=re.M)
source = source.replace('\t\t\t\tind_msg->service_path, ind_msg->curr_state, ind_msg->transaction_id);',
                        '\t\t\t\tind_msg->service_path, ind_msg->curr_state,\n\t\t\t\tind_msg->transaction_id);')
path.write_text(source)
patch = 'Subject: [PATCH] soc: qcom: pdr: fence peers and release locks during transactions\n\n'
patch += 'Retain services until callbacks and workers stop. Order old DOWN before\nnew states, and stop the WCD parent interrupt before removing children.\n\n---\n'
for name in ('drivers/soc/qcom/pdr_interface.c', 'drivers/mfd/wcd934x.c'):
    original = (out / (Path(name).name + '.before-private')).read_text()
    current = (root / name).read_text()
    patch += ''.join(difflib.unified_diff(original.splitlines(True), current.splitlines(True),
                                        fromfile='a/' + name, tofile='b/' + name))
(ref / 'pdr-and-parent-irq.patch').write_text(patch)
check = subprocess.run(['scripts/checkpatch.pl', '--no-tree', '--strict', '--no-signoff',
                        str(ref / 'pdr-and-parent-irq.patch')], cwd=root, capture_output=True, text=True)
(out / 'checkpatch-current-private.log').write_text(check.stdout + check.stderr)
print(check.stdout + check.stderr)
assert check.returncode == 0
subprocess.run(['git', 'diff', '--check'], cwd=root, check=True)
