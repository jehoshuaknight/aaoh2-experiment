"""CPU emulation of mesh.slang's peoplesAt (0.1.11): exact provinces, one noise field per people."""
import re, sys, numpy as np
from PIL import Image
S=sys.argv[1]; A=S+'/out/AstraNovum/bin/game/'
t=open('shaders/ethnicity_tables.slang').read()
def table(fn):
    body=t[t.index(fn+'(uint i)'):]; body=body[:body.index('default')]
    return re.findall(r'case (\d+)u: return (.*?);', body)
mix=np.array([tuple(int(x) for x in re.findall(r'(\d+)u', v)) for _,v in table('provinceMix')])
cols=np.array([[(c>>16)&255,(c>>8)&255,c&255] for c in [int(v.rstrip('u')) for _,v in table('ethColourHex')]],np.float32)/255
M32=np.uint64(0xFFFFFFFF)
def eh3(c):
    q=[(ci.astype(np.int64)+(1<<20)).astype(np.uint64) for ci in c]
    h=((q[0]*np.uint64(1597334677))&M32)^((q[1]*np.uint64(3812015801))&M32)^((q[2]*np.uint64(2654435769))&M32)
    h=((h^(h>>np.uint64(16)))*np.uint64(2246822519))&M32; h=((h^(h>>np.uint64(13)))*np.uint64(3266489917))&M32; h^=h>>np.uint64(16)
    return (h&np.uint64(0xFFFFFF)).astype(np.float64)/16777216.0
def n3(p):
    i=np.floor(p); f=p-i; f=f*f*(3-2*f); x,y,z=i[...,0],i[...,1],i[...,2]
    L=lambda a,b,t:a+(b-a)*t
    x00=L(eh3((x,y,z)),eh3((x+1,y,z)),f[...,0]); x10=L(eh3((x,y+1,z)),eh3((x+1,y+1,z)),f[...,0])
    x01=L(eh3((x,y,z+1)),eh3((x+1,y,z+1)),f[...,0]); x11=L(eh3((x,y+1,z+1)),eh3((x+1,y+1,z+1)),f[...,0])
    return L(L(x00,x10,f[...,1]),L(x01,x11,f[...,1]),f[...,2])
def aao(up,f,fw,seed):
    seed=np.asarray(seed,float); off=np.stack([np.mod(seed*0.618,1),np.mod(seed*0.377,1),np.mod(seed*0.271,1)],-1)*97.0
    k=np.clip(1-(fw*f-0.2)/0.3,0,1); return 0.5+(n3(up*(57.29578*f)+off)-0.5)*k
def field(up,fw,seed):
    seed=np.asarray(seed,float)
    w=np.stack([aao(up,0.12,fw,seed+21),aao(up,0.12,fw,seed+34),aao(up,0.12,fw,seed+55)],-1)-0.5
    q=up+w*0.16; q/=np.linalg.norm(q,axis=-1,keepdims=True)
    return 0.46*aao(q,0.22,fw,seed)+0.27*aao(q,0.6,fw,seed+3.1)+0.17*aao(q,1.7,fw,seed+7.3)+0.10*aao(q,4.6,fw,seed+9.9)
def tsv(p):
    for l in open(p,encoding='utf-8'):
        if l.startswith('#') or not l.strip(): continue
        yield l.rstrip('\n').split('\t')
reg={int(f[0]):int(f[1]) for f in tsv(A+'data/earth/provinces.tsv')}
order=sorted(reg,key=lambda p:(reg[p],p)); idx={p:i for i,p in enumerate(order)}
ids=np.array(Image.open(A+'textures/bodies/Earth_provinces.png').convert('RGB')).astype(np.int64); ids=ids[...,0]+ids[...,1]*256+ids[...,2]*65536
wat=np.array(Image.open(A+'textures/bodies/Earth_water.png').convert('L'))>127
sat=np.array(Image.open(A+'textures/bodies/Earth.jpg').convert('L').resize((ids.shape[1],ids.shape[0])),np.float32)/255
def render(lon0,lon1,lat1,lat0,fw,name):
    lons=np.arange(lon0,lon1,fw); lats=np.arange(lat1,lat0,-fw); LON,LAT=np.meshgrid(lons,lats)
    H,W=ids.shape; py=((90-LAT)/180*H).astype(int).clip(0,H-1); px=((LON+180)/360*W).astype(int).clip(0,W-1)
    pid=ids[py,px]; water=wat[py,px]|(pid==0)
    lr,ln=np.radians(LAT),np.radians(LON); up=np.stack([np.cos(lr)*np.cos(ln),np.sin(lr),-np.cos(lr)*np.sin(ln)],-1)
    pi=np.array([idx.get(int(p),0) for p in pid.ravel()]).reshape(pid.shape)
    M=mix[pi]
    sh=[((M[...,1]>>16)&127)/100,((M[...,0]>>18)&127)/100,((M[...,1]>>9)&127)/100,((M[...,2]>>9)&127)/100,((M[...,2]>>25)&127)/100]
    gg=[M[...,0]&511,(M[...,0]>>9)&511,M[...,1]&511,M[...,2]&511,(M[...,2]>>16)&511]
    best=np.full(LAT.shape,-1e9); second=np.full(LAT.shape,-1e9); gb=gg[0].copy(); gs=gg[0].copy()
    for g,s in zip(gg,sh):
        sc=np.where(s>0.005, 0.33*np.log(np.maximum(s,1e-6))+4.5*(field(up,fw,g*1.37)-0.5), -1e9)
        m1=sc>best; m2=(~m1)&(sc>second)
        second=np.where(m1,best,np.where(m2,sc,second)); gs=np.where(m1,gb,np.where(m2,g,gs))
        best=np.where(m1,sc,best); gb=np.where(m1,g,gb)
    k=np.where(second>-1e8,0.5*(1-np.clip((best-second)/0.22,0,1)**2*(3-2*np.clip((best-second)/0.22,0,1))),0)
    col=cols[gb]*(1-k[...,None])+cols[gs]*k[...,None]
    gap=best-second; ink=np.where(second>-1e8,(1-np.clip(gap/0.05,0,1))*(1-np.clip((fw-0.03)/0.09,0,1)),0); col=col*(1-0.28*ink)[...,None]
    l=(col*[0.299,0.587,0.114]).sum(-1,keepdims=True); col=l+(col-l)*0.86
    shade=np.clip(0.80+sat[py,px]*0.9,0.82,1.12)[...,None]; out=col*shade
    R_=np.where(water,-1,np.array([reg.get(int(p),-1) for p in pid.ravel()]).reshape(pid.shape))
    def edge(a): return (a!=np.roll(a,1,1))|(a!=np.roll(a,1,0))
    pe=edge(np.where(water,-1,pid))&~water; out[pe]*=0.6; out[edge(R_)&~water]=0.04; out[water]=[0.02,0.04,0.07]
    Image.fromarray((np.clip(out,0,1)*255).astype(np.uint8)).resize((900,int(900*LAT.shape[0]/LAT.shape[1]))).save(S+f'/work/{name}.png')
render(50,150,75,30,0.15,'siberia_new'); render(-12,45,62,33,0.07,'europe_close'); render(-125,-65,52,24,0.08,'usa_close'); render(-5,20,55,42,0.02,'europe_zoom')
