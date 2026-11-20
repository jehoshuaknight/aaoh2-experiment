"""CPU preview of the 0.1.14 ethnographic map (seed model in the shader)."""
import re, sys, numpy as np
from PIL import Image
S=sys.argv[1]; A=S+'/out/AstraNovum/bin/game/'
def table(t,fn):
    body=t[t.index(fn+'(uint i)'):]; body=body[:body.index('default')]
    return re.findall(r'case (\d+)u: return (.*?);', body)
t1=open('shaders/ethnicity_tables.slang').read(); t2=open('shaders/ethnicity_seeds.slang').read()
cols=np.array([[(c>>16)&255,(c>>8)&255,c&255] for c in [int(v.rstrip('u')) for _,v in table(t1,'ethColourHex')]],np.float32)/255
rng=[tuple(int(x) for x in re.findall(r'(\d+)u', v)) for _,v in table(t2,'seedRange')]
ent=np.array([tuple(int(x) for x in re.findall(r'(\d+)u', v)) for _,v in table(t2,'seedEntry')])
M32=np.uint64(0xFFFFFFFF)
def eh3(c):
    q=[(ci.astype(np.int64)+(1<<20)).astype(np.uint64) for ci in c]
    h=((q[0]*np.uint64(1597334677))&M32)^((q[1]*np.uint64(3812015801))&M32)^((q[2]*np.uint64(2654435769))&M32)
    h=((h^(h>>np.uint64(16)))*np.uint64(2246822519))&M32; h=((h^(h>>np.uint64(13)))*np.uint64(3266489917))&M32; h^=h>>np.uint64(16)
    return (h&np.uint64(0xFFFFFF)).astype(np.float64)/16777216.0
def n3(p):
    i=np.floor(p); f=p-i; f=f*f*(3-2*f); x,y,z=i[...,0],i[...,1],i[...,2]; L=lambda a,b,t:a+(b-a)*t
    x00=L(eh3((x,y,z)),eh3((x+1,y,z)),f[...,0]); x10=L(eh3((x,y+1,z)),eh3((x+1,y+1,z)),f[...,0])
    x01=L(eh3((x,y,z+1)),eh3((x+1,y,z+1)),f[...,0]); x11=L(eh3((x,y+1,z+1)),eh3((x+1,y+1,z+1)),f[...,0])
    return L(L(x00,x10,f[...,1]),L(x01,x11,f[...,1]),f[...,2])
def aao(up,f,fw,seed):
    off=np.array([np.mod(seed*0.618,1),np.mod(seed*0.377,1),np.mod(seed*0.271,1)])*97.0
    k=np.clip(1-(fw*f-0.2)/0.3,0,1); return 0.5+(n3(up*(57.29578*f)+off)-0.5)*k
def tsv(p):
    for l in open(p,encoding='utf-8'):
        if l.startswith('#') or not l.strip(): continue
        yield l.rstrip('\n').split('\t')
reg={int(f[0]):int(f[1]) for f in tsv(A+'data/earth/provinces.tsv')}
ids=np.array(Image.open(A+'textures/bodies/Earth_provinces.png').convert('RGB')).astype(np.int64); ids=ids[...,0]+ids[...,1]*256+ids[...,2]*65536
wat=np.array(Image.open(A+'textures/bodies/Earth_water.png').convert('L'))>127
sat=np.array(Image.open(A+'textures/bodies/Earth.jpg').convert('L').resize((ids.shape[1],ids.shape[0])),np.float32)/255
lights=np.array(Image.open(A+'textures/bodies/Earth_lights.jpg').convert('L').resize((ids.shape[1],ids.shape[0])),np.float32)/255
def ss(e0,e1,x): t=np.clip((x-e0)/(e1-e0),0,1); return t*t*(3-2*t)
def render(lon0,lon1,lat1,lat0,fw,name):
    lons=np.arange(lon0,lon1,fw); lats=np.arange(lat1,lat0,-fw); LON,LAT=np.meshgrid(lons,lats)
    H,W=ids.shape; py=((90-LAT)/180*H).astype(int).clip(0,H-1); px=((LON+180)/360*W).astype(int).clip(0,W-1)
    pid=ids[py,px]; water=wat[py,px]|(pid==0)
    R_=np.array([reg.get(int(p),-1) for p in pid.ravel()]).reshape(pid.shape)
    lr,ln=np.radians(LAT),np.radians(LON); up=np.stack([np.cos(lr)*np.cos(ln),np.sin(lr),-np.cos(lr)*np.sin(ln)],-1)
    east=np.cross(np.array([0,1,0.]),up); east/=np.linalg.norm(east,axis=-1,keepdims=True); north=np.cross(up,east)
    wq=np.stack([aao(up,0.05,fw,11)+0.5*aao(up,0.14,fw,5), aao(up,0.05,fw,23)+0.5*aao(up,0.14,fw,9)],-1)-0.75
    wf=np.stack([aao(up,0.45,fw,31)+0.5*aao(up,1.2,fw,41), aao(up,0.45,fw,37)+0.5*aao(up,1.2,fw,43)],-1)-0.75
    p=up+(east*wq[...,0:1]+north*wq[...,1:2])*0.085+(east*wf[...,0:1]+north*wf[...,1:2])*0.016; p/=np.linalg.norm(p,axis=-1,keepdims=True)
    city=ss(0.05,0.6,np.clip((lights[py,px]-0.0)*1.0,0,1))
    out=np.zeros(LAT.shape+(3,),np.float32)
    for r in np.unique(R_):
        if r<0: continue
        m=(R_==r)&~water; s,e=rng[r]; E=ent[s:e]; P=p[m]; C=city[m]
        g=E[:,0]>>22; la=np.radians((E[:,0]&1023)/1023*180-90); lo=np.radians(((E[:,0]>>10)&2047)/2047*360-180)
        cvec=np.stack([np.cos(la)*np.cos(lo),np.sin(la),-np.cos(la)*np.sin(lo)],-1)
        d=np.degrees(np.arccos(np.clip(P@cvec.T,-1,1)))
        w=(E[:,1]&255)/32; rad=((E[:,1]>>8)&255)/8; urb=((E[:,0]>>21)&1)==1
        W_=np.where(urb[None,:], w[None,:]*(0.45+2.2*C[:,None]), w[None,:])
        contrib=W_*np.exp(-(d/rad)**2)
        ug=np.unique(g); sc=np.stack([contrib[:,g==k].sum(1) for k in ug],1)
        o=np.argsort(-sc,1); best=np.take_along_axis(sc,o[:,:1],1)[:,0]; second=np.take_along_axis(sc,o[:,1:2],1)[:,0] if sc.shape[1]>1 else np.zeros_like(best)
        gb=ug[o[:,0]]; gs=ug[o[:,1]] if sc.shape[1]>1 else gb
        gap=np.log(np.maximum(best,1e-9)/np.maximum(second,1e-5)); aa=0.012+fw*0.25
        k=np.where(second>0,0.5*(1-ss(0,aa,gap)),0)
        col=cols[gb]*(1-k[:,None])+cols[gs]*k[:,None]
        ink=np.where(second>0,(1-ss(0,aa*0.6,gap))*(1-ss(0.03,0.15,fw)),0); col*= (1-0.22*ink)[:,None]
        empty=np.array([0.46,0.44,0.40]); t_=ss(0.02,0.15,best)[:,None]; col=empty+(col-empty)*t_
        out[m]=col
    l=(out*[0.299,0.587,0.114]).sum(-1,keepdims=True); out=l+(out-l)*0.86
    out=out*np.clip(0.80+sat[py,px]*0.9,0.82,1.12)[...,None]
    def edge(a): return (a!=np.roll(a,1,1))|(a!=np.roll(a,1,0))
    out[edge(np.where(water,-1,pid))&~water]*=0.75; out[edge(np.where(water,-1,R_))&~water]=0.04; out[water]=[0.02,0.04,0.07]
    Image.fromarray((np.clip(out,0,1)*255).astype(np.uint8)).resize((900,int(900*LAT.shape[0]/LAT.shape[1]))).save(S+f'/work/{name}.png')
render(50,150,75,30,0.12,'ethno_siberia'); render(-125,-65,52,24,0.07,'ethno_usa'); render(-12,45,62,33,0.06,'ethno_europe'); render(-180,180,80,-60,0.4,'ethno_world')
