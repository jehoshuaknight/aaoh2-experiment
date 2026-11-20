"""CPU preview of the 0.1.13 clean ethnicity map: flat province fills, stripes for big minorities."""
import re, sys, numpy as np
from PIL import Image
S=sys.argv[1]; A=S+'/out/AstraNovum/bin/game/'
t=open('shaders/ethnicity_tables.slang').read()
def table(fn):
    body=t[t.index(fn+'(uint i)'):]; body=body[:body.index('default')]
    return re.findall(r'case (\d+)u: return (.*?);', body)
mix=np.array([tuple(int(x) for x in re.findall(r'(\d+)u', v)) for _,v in table('provinceMix')])
rmix=np.array([tuple(int(x) for x in re.findall(r'(\d+)u', v)) for _,v in table('regionMix')])
cols=np.array([[(c>>16)&255,(c>>8)&255,c&255] for c in [int(v.rstrip('u')) for _,v in table('ethColourHex')]],np.float32)/255
def tsv(p):
    for l in open(p,encoding='utf-8'):
        if l.startswith('#') or not l.strip(): continue
        yield l.rstrip('\n').split('\t')
reg={int(f[0]):int(f[1]) for f in tsv(A+'data/earth/provinces.tsv')}
order=sorted(reg,key=lambda p:(reg[p],p)); idx={p:i for i,p in enumerate(order)}
ids=np.array(Image.open(A+'textures/bodies/Earth_provinces.png').convert('RGB')).astype(np.int64); ids=ids[...,0]+ids[...,1]*256+ids[...,2]*65536
wat=np.array(Image.open(A+'textures/bodies/Earth_water.png').convert('L'))>127
sat=np.array(Image.open(A+'textures/bodies/Earth.jpg').convert('L').resize((ids.shape[1],ids.shape[0])),np.float32)/255
def ss(e0,e1,x): t=np.clip((x-e0)/(e1-e0),0,1); return t*t*(3-2*t)
def render(lon0,lon1,lat1,lat0,fw,name,exact=True):
    lons=np.arange(lon0,lon1,fw); lats=np.arange(lat1,lat0,-fw); LON,LAT=np.meshgrid(lons,lats)
    H,W=ids.shape; py=((90-LAT)/180*H).astype(int).clip(0,H-1); px=((LON+180)/360*W).astype(int).clip(0,W-1)
    pid=ids[py,px]; water=wat[py,px]|(pid==0)
    R_=np.array([reg.get(int(p),-1) for p in pid.ravel()]).reshape(pid.shape)
    if exact:
        M=mix[np.array([idx.get(int(p),0) for p in pid.ravel()]).reshape(pid.shape)]
        g1=M[...,0]&511; g2=(M[...,0]>>9)&511; s1=((M[...,1]>>16)&127)/100; s2=((M[...,0]>>18)&127)/100
    else:
        M=rmix[np.clip(R_,0,None)]
        g1=M[...,0]&511; g2=(M[...,0]>>9)&511; s1=(M[...,1]&127)/100; s2=((M[...,0]>>18)&127)/100
    st=((LON+180) - LAT)/1.5; stW=min(fw/1.5*1.4,1.0); fr=st-np.floor(st)
    f=np.clip(s2/np.maximum(s1+s2,1e-3),0.25,0.5)
    band=ss(f-stW,f+stW,fr)*(1-ss(1-stW,1,fr))
    c1=cols[g1]; c2=cols[g2]
    striped=c2*(1-band[...,None])+c1*band[...,None]
    blend=c1*(1-f[...,None])+c2*f[...,None]
    k=ss(0.18,0.35,stW)
    col=np.where(((s2>=0.25)&(g2!=g1))[...,None], striped*(1-k)+blend*k, c1)
    l=(col*[0.299,0.587,0.114]).sum(-1,keepdims=True); col=l+(col-l)*0.86
    out=col*np.clip(0.80+sat[py,px]*0.9,0.82,1.12)[...,None]
    def edge(a): return (a!=np.roll(a,1,1))|(a!=np.roll(a,1,0))
    out[edge(np.where(water,-1,pid))&~water]*=0.55; out[edge(np.where(water,-1,R_))&~water]=0.04; out[water]=[0.02,0.04,0.07]
    Image.fromarray((np.clip(out,0,1)*255).astype(np.uint8)).resize((900,int(900*LAT.shape[0]/LAT.shape[1]))).save(S+f'/work/{name}.png')
render(50,150,75,30,0.12,'clean_siberia'); render(-125,-65,52,24,0.07,'clean_usa'); render(-12,45,62,33,0.06,'clean_europe')
render(-12,45,62,33,0.06,'clean_europe_fallback',exact=False)
