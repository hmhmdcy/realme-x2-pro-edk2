from pathlib import Path
import shutil
root=Path('/home/cy122/hexagonrpc-v04-k112/hexagonrpcd')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
def edit(name,old,new):
    p=root/name; text=p.read_text(); assert text.count(old)==1,(name,old)
    p.write_text(text.replace(old,new))
edit('listener.c','\tif (method >= ifaces[handle]->n_procs) {', '''	/* Public QAIC extended methods use wire method 31 plus a leading MID. */
	if (method == 31) {
		if (REMOTE_SCALARS_INBUFS(sc) < 1 || !decoded ||
		    decoded[0].s < sizeof(uint32_t) || !decoded[0].p) {
			*result = AEE_EBADPARM;
			return 1;
		}
		memcpy(&method, decoded[0].p, sizeof(method));
		if (method < 31) {
			*result = AEE_EBADPARM;
			return 1;
		}
#ifdef HEXAGONRPC_FLYWHEEL_TRACE
		fprintf(stderr, "listener-mid=%u\\n", method);
#endif
	}

	if (method >= ifaces[handle]->n_procs) {''')
edit('hexagonfs.h','#endif', '''int hexagonfs_ram_rename(const char *oldpath, const char *newpath);

#endif''')
shutil.copyfile(ref/'hexagonfs_ram_registry.c',root/'hexagonfs_ram_registry.c')
edit('interfaces/apps_std.def','#endif /* INTERFACE_APPS_STD_DEF */', '''HEXAGONRPC_DEFINE_REMOTE_METHOD(33, apps_std_frename, 1, 2, 0, 0)

#endif /* INTERFACE_APPS_STD_DEF */''')
edit('apps_std.c','static uint32_t apps_std_stat(', '''static uint32_t apps_std_frename(void *data,
                                const struct fastrpc_io_buffer *inbufs,
                                struct fastrpc_io_buffer *outbufs)
{
	int ret;
	if (!inbufs[1].s || !inbufs[2].s || !inbufs[1].p || !inbufs[2].p ||
	    memchr(inbufs[1].p, 0, inbufs[1].s) != (char *)inbufs[1].p + inbufs[1].s - 1 ||
	    memchr(inbufs[2].p, 0, inbufs[2].s) != (char *)inbufs[2].p + inbufs[2].s - 1)
		return AEE_EBADPARM;
	ret = hexagonfs_ram_rename(inbufs[1].p, inbufs[2].p);
	if (ret) {
		fprintf(stderr, "RAM registry rename failed: %s\\n", strerror(-ret));
		return AEE_EFAILED;
	}
	printf("ram-rename(%s, %s) completed\\n", (char *)inbufs[1].p, (char *)inbufs[2].p);
	return 0;
}

static uint32_t apps_std_stat(''')
anchor='''		.impl = apps_std_stat,
	},
};'''
edit('apps_std.c',anchor, '''		.impl = apps_std_stat,
	},
	{ .def = NULL, .impl = NULL, },
	{ .def = &apps_std_frename_def, .impl = apps_std_frename, },
};''')
edit('apps_std.c','.n_procs = 32,','.n_procs = 34,')
print('EXTENDED_MID_AND_REAL_RAM_RENAME_PREPARED')
