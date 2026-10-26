from pathlib import Path
import hashlib,importlib.util,json,struct,sys

out=Path('/mnt/e/edk2-samurai-out/kernel113')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
image=(out/'original-slpi-analysis-private.elf').read_bytes()
maps=json.loads((out/'original-slpi-analysis-segments-private.json').read_text())
parser=out/'ulog-reference/slpi-ulog-coredump.py'
assert hashlib.sha256(parser.read_bytes()).hexdigest()==json.loads((ref/'ulog-parser-reference.json').read_text())['sha256']
core=out/'slpi-coredump-v17-private.elf'
assert hashlib.sha256(core.read_bytes()).hexdigest()==json.loads((ref/'ulog-v17-validation.json').read_text())['coredump_sha256']
spec=importlib.util.spec_from_file_location('samurai_npa_dump',parser)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
dump=mod.Dump(core,0)
def read(address,size,live=True):
    matching=[s for s in maps if s['va']<=address and address+size<=s['va']+(s['memsz'] if live else s['filesz'])]
    assert len(matching)==1
    s=matching[0];relative=address-s['va']
    return dump.read(s['pa']+relative,size) if live else image[s['fileoff']+relative:s['fileoff']+relative+size]
def classify(value):
    matching=[s for s in maps if s['va']<=value<s['va']+s['memsz']]
    if len(matching)==1:
        s=matching[0]
        return 'segment '+str(s['index'])+' relative '+hex(value-s['va'])+(' code/rodata' if s['flags']&1 else ' data')
    return value if value<0x100000 else 'other pointer/value'
sites=next(x for x in json.loads((out/'npa-string-xrefs-private.json').read_text()) if x['name']=='/icb/arbiter' and x['segment']==4)['pointer_sites']
results=[]
for site in sites[:2]:
    address=site['address']-24
    static=list(struct.unpack('<24I',read(address,96,False)))
    live=list(struct.unpack('<24I',read(address,96,True)))
    results.append(dict(address=address,static=static,live=live))
    if '--verbose' in sys.argv:
        print(json.dumps(dict(resource_name_reference_relative=site['relative_offset'],
            fields=[dict(byte_offset=i*4-24,static=classify(a),live=classify(b)) for i,(a,b) in enumerate(zip(static,live))])))
(out/'npa-resource-tables-private.json').write_text(json.dumps(results,indent=2)+'\n')
definition=results[1]
plugin=definition['live'][9] # name-relative +12; matched npa_resource_definition field.
plugin_words=list(struct.unpack('<8I',read(plugin,32,True)))
print('RUNTIME_RESOURCE_PLUGIN '+json.dumps([classify(x) for x in plugin_words]))
callback=plugin_words[4]
matches=[s for s in maps if s['va']<=callback<s['va']+s['filesz'] and s['flags']&1]
if len(matches)==1:
    s=matches[0];relative=callback-s['va']
    (out/'npa-runtime-plugin-private.json').write_text(json.dumps(dict(plugin=plugin,
        words=plugin_words,callback=callback,segment=s['index'],relative=relative),indent=2)+'\n')
    print(json.dumps(dict(create_callback_in_matching_firmware=True,callback_segment=s['index'],
        callback_relative=relative,supported_clients=plugin_words[1])))
    block=read(callback,1024,False)
    assert block==read(callback,1024,True)
    print(json.dumps(dict(runtime_callback_1024_bytes_match_original=True,
        matching_block_sha256=hashlib.sha256(block).hexdigest())))
    listing=(out/'original-slpi-disassembly-private.txt').read_text().splitlines()
    instructions=[]
    import re
    for line in listing:
        m=re.match(r'\s*([0-9a-f]+):',line)
        if m and callback<=int(m.group(1),16)<callback+1024: instructions.append(line)
    assert instructions
    (out/'icb-create-client-callback-private.txt').write_text('\n'.join(instructions)+'\n')
    if '--verbose' in sys.argv:
        for line in instructions[:120]:
            line=re.sub(r'^\s*[0-9a-f]+:', 'CODE:',line)
            line=re.sub(r'-?0x[0-9a-f]{7,8}', '<firmware-pointer>',line)
            print(line)
    resource_handle=definition['live'][14] # name-relative +32
    resource_words=list(struct.unpack('<16I',read(resource_handle,64,True)))
    print('RUNTIME_RESOURCE_WORDS '+json.dumps([classify(x) for x in resource_words]))
    route_index=resource_words[2] # +8 is npa_resource.index, corroborated by the header.
    print('RUNTIME_RESOURCE_ROUTE_INDEX '+json.dumps(route_index))
    text='\n'.join(instructions)
    route_match=re.search(r'call (0x[0-9a-f]+)[^\n]*\n[^\n]*memw\(r24\+#0x4\) = r2',text)
    assert route_match
    route_address=int(route_match.group(1),16)
    route_lines=[]
    for line in listing:
        m=re.match(r'\s*([0-9a-f]+):',line)
        if m and route_address<=int(m.group(1),16)<route_address+384: route_lines.append(line)
    assert route_lines
    assert read(route_address,384,False)==read(route_address,384,True)
    (out/'icb-route-lookup-private.txt').write_text('\n'.join(route_lines)+'\n')
    (out/'icb-runtime-route-data-private.json').write_text(json.dumps(dict(resource_handle=resource_handle,
        resource_words=resource_words,route_index=route_index,route_address=route_address),indent=2)+'\n')
    if '--verbose' in sys.argv:
        for line in route_lines:
            line=re.sub(r'^\s*[0-9a-f]+:', 'CODE:',line)
            line=re.sub(r'-?0x[0-9a-f]{7,8}', '<firmware-pointer>',line)
            print(line)
    route_text='\n'.join(route_lines)
    global_match=re.search(r'r5 = memw\(##(-?0x[0-9a-f]+)\)',route_text)
    assert global_match
    global_address=int(global_match.group(1),0)&0xffffffff
    config=struct.unpack('<I',read(global_address,4,True))[0]
    config_words=list(struct.unpack('<12I',read(config,48,True)))
    assert 0<config_words[1]<=32 and route_index<config_words[1]
    context=struct.unpack('<I',read(config_words[2]+4*route_index,4,True))[0]
    context_words=list(struct.unpack('<12I',read(context,48,True)))
    print('RUNTIME_ICB_CONFIG '+json.dumps([classify(x) for x in config_words]))
    print('RUNTIME_ICB_CONTEXT '+json.dumps([classify(x) for x in context_words]))
    tree=context_words[2]
    print('ROUTE_TREE_ROOT '+json.dumps([classify(x) for x in struct.unpack('<8I',read(tree,32,True))]))
    target_match=re.search(r'call (0x[0-9a-f]+)[^\n]*\n[^\n]*r0 = memw\(r4\+#0x8\)',route_text)
    assert target_match
    tree_function=int(target_match.group(1),0)
    tree_lines=[]
    for line in listing:
        m=re.match(r'\s*([0-9a-f]+):',line)
        if m and tree_function<=int(m.group(1),16)<tree_function+160: tree_lines.append(line)
    assert tree_lines and read(tree_function,160,False)==read(tree_function,160,True)
    if '--verbose' in sys.argv:
        print('TREE_LOOKUP_FUNCTION')
        for line in tree_lines:
            line=re.sub(r'^\s*[0-9a-f]+:', 'CODE:',line)
            line=re.sub(r'-?0x[0-9a-f]{7,8}', '<firmware-pointer>',line)
            print(line)
    (out/'icb-runtime-route-tree-private.json').write_text(json.dumps(dict(global_address=global_address,
        config=config,config_words=config_words,context=context,context_words=context_words,
        tree=tree,tree_function=tree_function,tree_lines=tree_lines),indent=2)+'\n')
    def walk(node,minimum=None,maximum=None,seen=None):
        if not node: return []
        if seen is None: seen=set()
        assert node not in seen and len(seen)<512
        seen.add(node)
        low,high,value,left,right=struct.unpack('<5I',read(node,20,True))
        key=(high<<32)|low
        assert (minimum is None or key>minimum) and (maximum is None or key<maximum)
        return walk(left,minimum,key,seen)+[dict(master=high,slave=low,route_nonnull=bool(value),
            node=node,route=value)]+walk(right,key,maximum,seen)
    routes=walk(tree)
    print(json.dumps(dict(runtime_route_tree_nodes=len(routes),
        master_ids=sorted(set(x['master'] for x in routes)),
        slave_zero_route_master_ids=[x['master'] for x in routes if x['slave']==0])))
    clients=[]
    for item in json.loads((out/'npa-string-xrefs-private.json').read_text()):
        if item['name'] not in ['SPI_QUP_DDR','I2C_QUP_DDR']: continue
        address=item['vector_address']
        actual=list(struct.unpack('<4I',read(address,16,True)))
        pairs=[(actual[i],actual[i+1]) for i in range(0,4,2)]
        island_listing=(out/'original-slpi-text7-disassembly-private.txt').read_text().splitlines()
        address_forms=[hex(next(x['address'] for x in json.loads((out/'npa-string-xrefs-private.json').read_text()) if x['name']==item['name']))]
        address_forms.extend(hex((int(x,0)-2**32)) for x in list(address_forms))
        xref=next(i for i,line in enumerate(island_listing) if any(x in line for x in address_forms))
        after='\n'.join(island_listing[xref:xref+30])
        handle_match=re.search(r'memw\(##(-?0x[0-9a-f]+)\) = r0',after)
        assert handle_match
        handle_address=int(handle_match.group(1),0)&0xffffffff
        handle=struct.unpack('<I',read(handle_address,4,True))[0]
        assert handle==0
        if item['name']=='SPI_QUP_DDR':
            success_match=re.search(r'if \(!p0.new\) jump:t (0x[0-9a-f]+)',after)
            error_match=re.search(r'jump (0x[0-9a-f]+)[^\n]*\n[^\n]*r0 = #0x0',after)
            # The error log path branches back to the same normal epilogue.
            if not error_match:
                error_match=re.search(r'r1:0 = combine\([^\n]+\n[^\n]*jump (0x[0-9a-f]+)',after)
            assert success_match and error_match
            success=int(success_match.group(1),0);error=int(error_match.group(1),0)
            success_line=next(i for i,line in enumerate(island_listing) if re.match(r'\s*'+format(success,'x')+':',line))
            error_line=next(i for i,line in enumerate(island_listing) if re.match(r'\s*'+format(error,'x')+':',line))
            assert 'dealloc_return' in '\n'.join(island_listing[success_line:success_line+2])
            assert 'call ' in island_listing[error_line] and success==error+4
            start=int(re.match(r'\s*([0-9a-f]+):',island_listing[xref]).group(1),16)-128
            assert read(start,384,False)==read(start,384,True)
            (out/'spi-npa-return-proof-private.json').write_text(json.dumps(dict(
                normal_return=success,error_log=error,code_start=start,matched_bytes=384,
                source_lines=island_listing[error_line:success_line+2]),indent=2)+'\n')
        clients.append(dict(client=item['name'],client_type=1024,client_value_bytes=16,
            runtime_npa_handle_is_null=True,
            runtime_vector_matches_original=actual==item['vector_words'],
            vector_pairs=[dict(master=a,slave=b,route_exists=any(x['master']==a and x['slave']==b and x['route_nonnull'] for x in routes)) for a,b in pairs]))
    print(json.dumps(dict(runtime_clients=clients)))
    (out/'icb-runtime-route-inventory-private.json').write_text(json.dumps(dict(routes=routes,clients=clients),indent=2)+'\n')
    inventories={}
    for category,count_index,list_index in [('master',5,6),('slave',7,8)]:
        count=context_words[count_index]
        assert 0<count<128
        nodes=struct.unpack('<'+'I'*count,read(context_words[list_index],4*count,True))
        inventory=[]
        for node in nodes:
            words=struct.unpack('<12I',read(node,48,True))
            name=None
            try:
                raw=read(words[0],64,True).split(bytes([0]),1)[0]
                if raw and len(raw)<64 and re.fullmatch(rb'[A-Za-z0-9_/ .-]+',raw):name=raw.decode()
            except (AssertionError,KeyError): pass
            inventory.append(dict(id=words[1],name=name))
        print(json.dumps(dict(category=category,node_count=count,nodes=inventory)))
        inventories[category]=inventory
    assert 'r22 = lsr(r1,#0x3)' in text
    assert 'r19 = #0x4' in text
    assert plugin_words[1]&1024 and route_index==0
    assert len(routes)==68
    assert all(x['runtime_vector_matches_original'] for x in clients)
    assert all(not pair['route_exists'] for x in clients for pair in x['vector_pairs'])
    report=dict(firmware_reference='own original 00121',
        coredump_reference='RAM v17',coredump_sha256=hashlib.sha256(core.read_bytes()).hexdigest(),
        original_firmware_files_verified=24,
        callback_bytes_matched=1024,callback_sha256=hashlib.sha256(block).hexdigest(),
        route_lookup_bytes_matched=384,tree_lookup_bytes_matched=160,
        active_plugin_supported_clients=plugin_words[1],vector_client_type_supported=True,
        npa_client_value_unit='bytes',npa_client_value_bytes=16,master_slave_pairs=2,
        route_context_count=config_words[1],selected_route_context_index=route_index,
        runtime_route_tree_nodes=len(routes),
        runtime_master_nodes=len(inventories['master']),runtime_slave_nodes=len(inventories['slave']),
        runtime_route_master_ids=sorted(set(x['master'] for x in routes)),
        clients=clients,error_4_is_route_lookup_null_branch=True,
        callback_error_is_not_unsupported_client_type=True,
        error_4_is_not_memory_allocation_error=True,
        spi_npa_failure_uses_normal_function_epilogue=True,
        spi_normal_epilogue_bytes_match_original=384,
        successful_stk3331_queries_despite_i2c_npa_failure=['RAM v9 physical cover/uncover','RAM v17'],
        npa_error_alone_does_not_prove_spi_transport_unavailable=True,
        npa_error_as_sensor_root_cause_proven=False,
        alternate_device_addresses_used=False,firmware_patched=False,phone_changed=False,
        raw_code_memory_and_addresses_private=True,
        next_investigation='Own SSC sensor registration/instantiation and unfiltered SUID/event path',
        sensor_function_accepted=False,goal_complete=False)
    (ref/'npa-own-firmware-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('OWN_FIRMWARE_NPA_FORENSICS_VALIDATED')
else:
    print(json.dumps(dict(create_callback_in_matching_firmware=False,supported_clients=plugin_words[1])))
