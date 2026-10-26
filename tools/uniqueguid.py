import io
q = 'Platform/Realme/sm8150/samurai.fdf.inc'
t = io.open(q, encoding='utf-8', errors='replace').read()
# give our added TLMMDxe a unique FFS file GUID to avoid clash with the shared DALTLMM slot (8681cc5a)
if '8681CC5B' in t:
    print('already renamed')
else:
    t = t.replace('FILE DRIVER = 8681CC5A-0DF6-441E-B4B8-E915C538F067 {',
                  'FILE DRIVER = 8681CC5B-0DF6-441E-B4B8-E915C538F067 {')
    io.open(q, 'w', encoding='utf-8', newline='\n').write(t)
    print('TLMMDxe FFS GUID -> 8681CC5B-... (unique)')
