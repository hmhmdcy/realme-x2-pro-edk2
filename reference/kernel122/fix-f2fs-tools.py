from pathlib import Path
import runpy,subprocess,difflib,hashlib,json
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel122/ensure-rootfs-volume.py')
stage=Path('/home/cy122/pmos-samurai-rootfs122');k=stage/'tools/f2fs-tools';out=Path('/mnt/e/edk2-samurai-out/kernel122');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel122')
status=subprocess.check_output(['git','status','--porcelain'],cwd=k,text=True)
if status==' M fsck/f2fs.h\n':
    clean=subprocess.check_output(['git','show','HEAD:fsck/f2fs.h'],cwd=k,text=True)
    assert (k/'fsck/f2fs.h').read_text()==clean.replace('\tu64 from_devino;\n};','\tu64 from_devino;\n\tu32 encoded_rdev;\n};')
    # Recover only the exact first edit of our failed include-anchor attempt.
    (k/'fsck/f2fs.h').write_text(clean)
assert subprocess.check_output(['git','status','--porcelain'],cwd=k,text=True)==''
names=['fsck/f2fs.h','fsck/sload.c','fsck/dir.c','fsck/dump.c'];before={n:(k/n).read_text() for n in names}
def replace(n,a,b):
    p=k/n;s=p.read_text();assert s.count(a)==1,(n,a);p.write_text(s.replace(a,b))
replace(names[0],'\tu64 from_devino;\n};','\tu64 from_devino;\n\tu32 encoded_rdev;\n};')
replace(names[1],'#include "fsck.h"','#include <sys/sysmacros.h>\n#include "fsck.h"')
replace(names[1],"\t\telse if (de[i].file_type == F2FS_FT_SYMLINK)\n\t\t\tret = f2fs_symlink(sbi, de + i);", "\t\telse if (de[i].file_type == F2FS_FT_SYMLINK)\n\t\t\tret = f2fs_symlink(sbi, de + i);\n\t\telse if (de[i].file_type == F2FS_FT_CHRDEV ||\n\t\t\t de[i].file_type == F2FS_FT_BLKDEV)\n\t\t\tret = f2fs_create(sbi, de + i);")
replace(names[1],'\tde->size = stat.st_size;','''	if (S_ISCHR(stat.st_mode) || S_ISBLK(stat.st_mode)) {
		u32 maj = major(stat.st_rdev), min = minor(stat.st_rdev);
		ASSERT(maj <= 0xfff && min <= 0xfffff);
		/* Linux new_encode_dev(), consumed by F2FS addr[1]. */
		de->encoded_rdev = (min & 0xff) | (maj << 8) |
				  ((min & ~0xffU) << 12);
	}
	de->size = stat.st_size;''')
replace(names[1],"\t\t} else {\n\t\t\tMSG(1, \"Error unknown file type\\n\");", "\t\t} else if (dentries[i].file_type == F2FS_FT_CHRDEV ||\n\t\t\t   dentries[i].file_type == F2FS_FT_BLKDEV) {\n\t\t\t/* Device inode was created without data blocks. */\n\t\t} else {\n\t\t\tMSG(1, \"Error unknown file type\\n\");")
replace(names[2],"\t\tsize = strlen(de->link);\n\t\tif (size + 1 > MAX_INLINE_DATA(node_blk))\n\t\t\tblocks++;\n\t} else {", "\t\tsize = strlen(de->link);\n\t\tif (size + 1 > MAX_INLINE_DATA(node_blk))\n\t\t\tblocks++;\n\t} else if (de->file_type == F2FS_FT_CHRDEV ||\n\t\t   de->file_type == F2FS_FT_BLKDEV) {\n\t\tsize = 0;\n\t} else {")
replace(names[2],'\tset_file_temperature(sbi, node_blk, de->name);','''	if (S_ISCHR(mode) || S_ISBLK(mode)) {
		unsigned int ofs = get_extra_isize(node_blk);
		node_blk->i.i_addr[ofs] = 0;
		node_blk->i.i_addr[ofs + 1] = cpu_to_le32(de->encoded_rdev);
	}

	set_file_temperature(sbi, node_blk, de->name);''')
replace(names[3],'#include <inttypes.h>','#include <inttypes.h>\n#include <sys/sysmacros.h>')
replace(names[3],'if ((!S_ISREG(imode) && !S_ISLNK(imode) && !(S_ISDIR(imode) && allow_folder))) {','if ((!S_ISREG(imode) && !S_ISLNK(imode) && !S_ISCHR(imode) &&\n\t     !S_ISBLK(imode) && !(S_ISDIR(imode) && allow_folder))) {')
replace(names[3],"\t\t} else {\n\t\t\tdump_link(sbi, ni, node_blk, name);\n\t\t}",'''\t\t} else if (S_ISCHR(imode) || S_ISBLK(imode)) {
			unsigned int ofs = get_extra_isize(node_blk);
			u32 old = le32_to_cpu(inode->i_addr[ofs]);
			u32 enc = le32_to_cpu(inode->i_addr[ofs + 1]);
			u32 maj = old ? (old >> 8) & 0xff : (enc >> 8) & 0xfff;
			u32 min = old ? old & 0xff : (enc & 0xff) | ((enc >> 12) & 0xfff00);
			ASSERT(mknod(name, imode, makedev(maj, min)) == 0);
		} else {
			dump_link(sbi, ni, node_blk, name);
		}''')
replace(names[3],"\t\t\tif (!S_ISLNK(imode))\n\t\t\t\tASSERT(chmod(name, imode) == 0);\n\t\t\tASSERT(lchown(name, inode->i_uid, inode->i_gid) == 0);", "\t\t\t/* chown clears setuid/setgid: restore the encoded mode last. */\n\t\t\tASSERT(lchown(name, inode->i_uid, inode->i_gid) == 0);\n\t\t\tif (!S_ISLNK(imode))\n\t\t\t\tASSERT(chmod(name, imode) == 0);")
patch=''.join(''.join(difflib.unified_diff(before[n].splitlines(True),(k/n).read_text().splitlines(True),fromfile='a/'+n,tofile='b/'+n)) for n in names)
(ref/'f2fs-tools-device-nodes-and-dump-mode.patch').write_text(patch)
subprocess.run(['git','diff','--check'],cwd=k,check=True)
original=stage/'tools/original-native-fsck.f2fs';assert not original.exists();original.write_bytes((stage/'tools/install-root/usr/local/sbin/fsck.f2fs').read_bytes())
with (out/'dump-tools-patched-build-private.txt').open('w') as log:
    subprocess.run(['make','-j4'],cwd=k,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=90)
    subprocess.run(['make','DESTDIR='+str(stage/'tools/install-root'),'install'],cwd=k,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
report=dict(original_commit='83fd39a184df96db5def895ddc55bf68e720ef76',local_linux_packaging_tool_fix=True,sload_char_block_inode_and_linux_device_number_supported=True,dump_char_block_supported=True,dump_encoded_special_mode_restored_after_chown=True,original_binary_preserved=True,patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),patched_binary_sha256=hashlib.sha256((stage/'tools/install-root/usr/local/sbin/fsck.f2fs').read_bytes()).hexdigest(),phone_not_used=True,fixtures_pending=True)
(ref/'f2fs-tools-fix-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
