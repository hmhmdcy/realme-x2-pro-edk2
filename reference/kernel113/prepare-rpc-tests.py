from pathlib import Path
ref=Path('/mnt/e/RealmeX2Pro edk2/reference')
text=(ref/'kernel112/test_rpcd_ram.c').read_text()
text=text.replace('#include "apps_std.c"','#include "apps_std.c"\n#include "listener.c"')
anchor='\tputs("PASS:'
start=text.index(anchor)
text=text[:start]+'''
	fixture("sensors/registry/temp.json", "RENAMED");
	char oldpath[]="/mnt/vendor/persist/sensors/registry/temp.json";
	char newpath[]="/persist/sensors/registry/registry/sample";
	uint32_t rename_nums[]={33,sizeof(oldpath),sizeof(newpath)};
	struct fastrpc_io_buffer rename_in[]={{.p=rename_nums,.s=sizeof(rename_nums)},
		{.p=oldpath,.s=sizeof(oldpath)},{.p=newpath,.s=sizeof(newpath)}};
	struct fastrpc_interface iface=apps_std_interface;
	iface.data=&ctx; struct fastrpc_interface *ifaces[]={&iface};
	struct fastrpc_io_buffer *returned=NULL; uint32_t reply=999;
	assert(!invoke_requested_procedure(1,ifaces,0,REMOTE_SCALARS_MAKE(31,3,0),&reply,rename_in,&returned));
	assert(reply==0 && returned==NULL);
	readable(&ctx,newpath,"RENAMED");
	assert(hexagonfs_ram_rename(oldpath,newpath)==-ENOENT);
	assert(hexagonfs_ram_rename(newpath,"/proc/oppoVersion/modemType")==-EROFS);
	assert(hexagonfs_ram_rename(newpath,"/persist/sensors/registry/../../escape")<0);
	assert(hexagonfs_ram_rename(newpath,"/persist/sensors/registry/link")<0);
	assert(hexagonfs_ram_rename("/persist/sensors/registry/link",newpath)<0);
	assert(hexagonfs_ram_rename("/persist/sensors/registry/registry",newpath)<0);
	assert(hexagonfs_ram_rename(newpath,"/persist/sensors/registry/registry")<0);
	assert(hexagonfs_ram_rename(newpath,"/persist/sensors/registry/../")<0);
	assert(hexagonfs_ram_rename(NULL,newpath)<0);
	readable(&ctx,newpath,"RENAMED");
	readable(&ctx,"/proc/oppoVersion/modemType","4");
	uint32_t stat_nums[]={31,sizeof(newpath)};
	struct fastrpc_io_buffer stat_in[]={{.p=stat_nums,.s=sizeof(stat_nums)},
		{.p=newpath,.s=sizeof(newpath)}};
	assert(!invoke_requested_procedure(1,ifaces,0,REMOTE_SCALARS_MAKE(31,2,1),&reply,stat_in,&returned));
	assert(reply==0 && returned && returned[0].s==96);
	iobuf_free(1,returned); returned=NULL;
	rename_nums[0]=32;
	assert(invoke_requested_procedure(1,ifaces,0,REMOTE_SCALARS_MAKE(31,3,0),&reply,rename_in,&returned)==1);
	assert(reply==AEE_EUNSUPPORTED && returned==NULL);
	rename_nums[0]=33; rename_in[0].s=4;
	assert(invoke_requested_procedure(1,ifaces,0,REMOTE_SCALARS_MAKE(31,3,0),&reply,rename_in,&returned)==1);
	assert(reply==AEE_EBADPARM && returned==NULL);
	rename_in[0].s=sizeof(rename_nums); rename_in[0].p=NULL;
	assert(invoke_requested_procedure(1,ifaces,0,REMOTE_SCALARS_MAKE(31,3,0),&reply,rename_in,&returned)==1);
	assert(reply==AEE_EBADPARM && returned==NULL);
	puts("PASS: actual extended MID dispatch/stat/RAM rename/readback; overwrite/aliases, missing sources, traversal/symlink/directory/RO/malformed-buffer rejection");
	return 0;
}
'''
(ref/'kernel113/test_rpcd_rename.c').write_text(text)
text=(ref/'kernel112/test-rpcd-ram.sh').read_text().replace('kernel112','kernel113').replace('test_rpcd_ram','test_rpcd_rename').replace('test-rpcd-ram','test-rpcd-rename')
text=text.replace('iobuffer,listener,localctl','iobuffer,localctl')
(ref/'kernel113/test-rpcd-rename.sh').write_text(text)
text=(ref/'kernel113/build-rpcd-v4.sh').read_text().replace('v4','v5')
(ref/'kernel113/build-rpcd-v5.sh').write_text(text)
print('EXTENDED_MID_ACTUAL_HANDLER_RENAME_ASAN_UBSAN_TESTS_PREPARED')
