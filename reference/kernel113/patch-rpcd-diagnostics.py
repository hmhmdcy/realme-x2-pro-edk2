from pathlib import Path
root=Path('/home/cy122/hexagonrpc-v04-k112/hexagonrpcd')
path=root/'listener.c'; text=path.read_text()
assert 'listener-next ret=' not in text
assert text.count('\tuint32_t handle;')==1
text=text.replace('\tuint32_t handle;', '\tuint32_t handle = 0;')
anchor='''		if (ret)
			break;

		if (returned != NULL)'''
replacement='''#ifdef HEXAGONRPC_FLYWHEEL_TRACE
		fprintf(stderr, "listener-next ret=%d handle=%u method=%u scalar=%08x\\n",
			ret, handle, REMOTE_SCALARS_METHOD(sc), sc);
#endif
		if (ret)
			break;

		if (returned != NULL)'''
assert text.count(anchor)==1; text=text.replace(anchor,replacement)
anchor='''		if (ret)
			break;

		if (decoded != NULL)'''
replacement='''#ifdef HEXAGONRPC_FLYWHEEL_TRACE
		fprintf(stderr, "listener-dispatch ret=%d result=%u handle=%u method=%u\\n",
			ret, result, handle, REMOTE_SCALARS_METHOD(sc));
#endif
		if (ret)
			break;

		if (decoded != NULL)'''
assert text.count(anchor)==1; text=text.replace(anchor,replacement)
path.write_text(text)
path=root/'rpcd.c'; text=path.read_text()
anchor='\trun_fastrpc_listener(fd, n_ifaces, ifaces);'
assert text.count(anchor)==1
text=text.replace(anchor, '''	ret = run_fastrpc_listener(fd, n_ifaces, ifaces);
#ifdef HEXAGONRPC_FLYWHEEL_TRACE
	fprintf(stderr, "listener-exit ret=%d errno=%d\\n", ret, errno);
#endif''')
path.write_text(text)
print('FAST_RPC_NUMERIC_LISTENER_DIAGNOSTICS_PREPARED')
