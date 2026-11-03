import re,html,sys
def text(path):
    t=open(path,encoding='utf-8',errors='replace').read()
    t=re.sub(r'(?is)<script.*?</script>|<style.*?</style>','',t)
    t=re.sub(r'(?i)</(td|th)>',' | ',t); t=re.sub(r'(?i)</tr>','\n',t)
    s=html.unescape(re.sub(r'<[^>]+>',' ',t)).replace('​','')
    s=re.sub(r'[ \t\r]+',' ',s); s=re.sub(r'\n\s*\n+','\n',s)
    return s
if __name__=='__main__':
    print(text(sys.argv[1]))
