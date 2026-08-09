import xml.etree.ElementTree as ET, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import icons as IC

NS='{http://www.topografix.com/GPX/1/1}'; U='gpx/'
def load(p):
    r=ET.parse(U+p).getroot()
    return np.array([(float(t.get('lat')),float(t.get('lon'))) for t in r.iter(NS+'trkpt')])
def cum(a):
    R=6371000.0; la=np.radians(a[:,0]); lo=np.radians(a[:,1])
    h=np.sin(np.diff(la)/2)**2+np.cos(la[:-1])*np.cos(la[1:])*np.sin(np.diff(lo)/2)**2
    return np.concatenate([[0],np.cumsum(2*R*np.arcsin(np.clip(np.sqrt(h),0,1)))])
def seg(a,k0,k1):
    c=cum(a); i0=np.searchsorted(c,k0*1000); i1=np.searchsorted(c,k1*1000); return a[i0:i1]
def at(a,km):
    c=cum(a); i=min(np.searchsorted(c,km*1000),len(a)-1); return float(a[i,0]),float(a[i,1])

FU=load('_____Fuchskaute___Ulmtalradweg.gpx'); KN=load('______ber_den_Knoten.gpx')
DI=load('_____Dilltalradweg.gpx'); GR=load('______ber_Greifenstein.gpx')
ROUTES=[FU,KN,DI,GR]

S=2                      # Supersampling
W,H=1600*S,1200*S
PAPER=(243,232,208); INK=(59,52,42); MUTED=(126,112,88)
GF="/usr/share/fonts/truetype/google-fonts/%s.ttf"
F=lambda n,s: ImageFont.truetype(GF%n,int(s*S))

img=Image.new('RGB',(W,H),PAPER); d=ImageDraw.Draw(img)

# Papierkorn
rnd=random.Random(7)
grain=Image.new('L',(W//4,H//4))
grain.putdata([rnd.randint(0,255) for _ in range(grain.size[0]*grain.size[1])])
grain=grain.resize((W,H),Image.BILINEAR).filter(ImageFilter.GaussianBlur(1))
img=Image.composite(Image.new('RGB',(W,H),(233,221,196)),img,grain.point(lambda v:20 if v>150 else 0))
d=ImageDraw.Draw(img)

# Projektion
def merc(a): return np.radians(a[:,1]), np.log(np.tan(np.pi/4+np.radians(a[:,0])/2))
AX=np.concatenate([merc(r)[0] for r in ROUTES]); AY=np.concatenate([merc(r)[1] for r in ROUTES])
pad=0.10
box=(300*S,70*S,1300*S,1130*S)
sc=min((box[2]-box[0])/((AX.max()-AX.min())*(1+pad)),(box[3]-box[1])/((AY.max()-AY.min())*(1+pad)))
cx,cy=(AX.min()+AX.max())/2,(AY.min()+AY.max())/2
MX,MY=(box[0]+box[2])/2,(box[1]+box[3])/2
def P(lat,lon):
    x=math.radians(lon); y=math.log(math.tan(math.pi/4+math.radians(lat)/2))
    return (MX+(x-cx)*sc, MY-(y-cy)*sc)
def PA(a):
    X,Y=merc(a); return list(zip(MX+(X-cx)*sc, MY-(Y-cy)*sc))

# Waldflächen (weiche Blobs entlang der Routen)
forest=Image.new('L',(W,H),0); fd=ImageDraw.Draw(forest)
rnd=random.Random(11)
for r in ROUTES:
    pts=PA(r)
    for i in range(0,len(pts),9):
        x,y=pts[i]
        rr=rnd.randint(34,88)*S
        if rnd.random()<0.55:
            fd.ellipse([x-rr,y-rr*0.8,x+rr,y+rr*0.8],fill=255)
rnd2=random.Random(41)
for _ in range(26):
    x=rnd2.randint(0,W); y=rnd2.randint(0,H)
    rr=rnd2.randint(90,210)*S
    fd.ellipse([x-rr,y-rr*0.75,x+rr,y+rr*0.75],fill=88)
forest=forest.filter(ImageFilter.GaussianBlur(26*S))
forest=forest.point(lambda v: 255 if v>110 else int(v*0.9))
img=Image.composite(Image.new('RGB',(W,H),(214,222,190)),img,forest.point(lambda v:int(v*0.38)))
d=ImageDraw.Draw(img)
fmask=forest.load()
rmask=Image.new('L',(W,H),0); rmd=ImageDraw.Draw(rmask)
for r in ROUTES: rmd.line(PA(r),fill=255,width=int(30*S),joint='curve')
rmask=rmask.load()
rnd=random.Random(23)
for _ in range(1700):
    x=rnd.randint(0,W-1); y=rnd.randint(0,H-1)
    if 0<=x<W and 0<=y<H and fmask[x,y]>170 and rmask[x,y]==0 and rnd.random()<0.34:
        IC.tree(d,x,y,rnd.uniform(4.5,7.5)*S,(164,184,138))
for _ in range(420):
    x=rnd.randint(0,W-1); y=rnd.randint(0,H-1)
    if 60<fmask[x,y]<=170 and rmask[x,y]==0 and rnd.random()<0.34:
        IC.tree(d,x,y,rnd.uniform(3.5,5.5)*S,(202,210,180))

# Flüsse (aus Streckenabschnitten abgeleitet)
def water(pts,w):
    d.line(pts,fill=(150,190,206),width=int(w*S*1.9),joint='curve')
    d.line(pts,fill=(112,164,188),width=int(w*S),joint='curve')
water(PA(seg(KN,28.5,36.5)),7)      # Lahn Weilburg–Löhnberg
water(PA(seg(DI,44.0,56.0)),6)      # Dill Richtung Dillenburg
water(PA(seg(FU,20.5,23.5)),5)      # Krombachtalsperre-Zulauf

# Routen: gestrichelte Wanderkarten-Linie
def dashed(pts,col,dash=14,gap=10,w=4):
    acc=0; on=True; cur=[pts[0]]
    for i in range(1,len(pts)):
        x0,y0=pts[i-1]; x1,y1=pts[i]
        seglen=math.hypot(x1-x0,y1-y0); t=0
        while t<seglen:
            step=min((dash if on else gap)*S-acc, seglen-t)
            nx=x0+(x1-x0)*(t+step)/seglen; ny=y0+(y1-y0)*(t+step)/seglen
            if on: cur.append((nx,ny))
            t+=step; acc+=step
            if acc>=(dash if on else gap)*S-0.01:
                if on and len(cur)>1: d.line(cur,fill=col,width=int(w*S),joint='curve')
                on=not on; acc=0; cur=[(nx,ny)]
    if on and len(cur)>1: d.line(cur,fill=col,width=int(w*S),joint='curve')

for r in ROUTES:
    dashed(PA(r),(255,255,255),w=7,dash=14,gap=10)
for r in ROUTES:
    dashed(PA(r),(176,96,58),w=4,dash=14,gap=10)

# Highlights
HL=[
 ("Fuchskaute",        at(FU,17.0), IC.fox,       'l', (-6,-56)),
 ("Krombachtalsperre", at(FU,22.4), IC.lake,      'l', (-30,10)),
 ("Ulmtalradweg",      at(FU,34.4), IC.fastpath,  'r', (18,34)),
 ("Der Knoten",        at(KN,52.1), IC.windmount, 'r', (12,46)),
 ("Grube Fortuna",     at(DI,23.1), IC.mine,      'r', (14,44)),
 ("Dilltal",           at(DI,47.0), IC.dillherb,  'r', (14,42)),
 ("Lahn bei Löhnberg", at(KN,32.5), IC.river,     'l', (-14,46)),
 ("Weiltalradweg",     at(KN,19.2), IC.idyllic,   'l', (-26,6)),
]
f_lab=F("Lora-Italic-Variable",26); f_place=F("Poppins-Medium",30)

def label(x,y,txt,font,side):
    tw=d.textlength(txt,font=font); th=font.size
    tx=x-tw/2 if side=='c' else (x if side=='r' else x-tw)
    ty=y
    d.rectangle([tx-9*S,ty-5*S,tx+tw+9*S,ty+th+7*S],fill=(246,237,216))
    d.text((tx,ty),txt,font=font,fill=INK)

for name,(la,lo),fn,side,(ox,oy) in HL:
    x,y=P(la,lo)
    fn(d,x,y,34*S)
    label(x+ox*S,y+oy*S,name,f_lab,side)

# Endpunkte
for name,(la,lo),fn in [("HAIGER",(50.7402,8.2223),IC.shark),("BRANDOBERNDORF",(50.4332,8.4970),IC.home)]:
    x,y=P(la,lo)
    fn(d,x,y,44*S)
    tw=d.textlength(name,font=f_place)
    yy=y+62*S
    d.rectangle([x-tw/2-14*S,yy,x+tw/2+14*S,yy+f_place.size+12*S],fill=(59,52,42))
    d.text((x-tw/2,yy+5*S),name,font=f_place,fill=(243,232,208))

# Kompass
ccx,ccy,cr=1478*S,1086*S,54*S
d.ellipse([ccx-cr,ccy-cr,ccx+cr,ccy+cr],outline=(176,96,58),width=3*S)
d.polygon([(ccx,ccy-cr*.82),(ccx-cr*.24,ccy+cr*.10),(ccx+cr*.24,ccy+cr*.10)],fill=(176,96,58))
d.polygon([(ccx,ccy+cr*.72),(ccx-cr*.24,ccy+cr*.10),(ccx+cr*.24,ccy+cr*.10)],fill=(214,200,172))
f_n=F("Poppins-Medium",22)
d.text((ccx-d.textlength("N",font=f_n)/2,ccy-cr-32*S),"N",font=f_n,fill=INK)

# Titel-Kartusche unten links
f_t=F("Poppins-Bold",60); f_s=F("Lora-Italic-Variable",27)
cx0,cy0,cx1,cy1=64*S,676*S,478*S,1042*S
d.rectangle([cx0,cy0,cx1,cy1],fill=(246,238,218),outline=(176,96,58),width=3*S)
d.rectangle([cx0+9*S,cy0+9*S,cx1-9*S,cy1-9*S],outline=(206,186,152),width=1*S)
tx=cx0+34*S
d.text((tx,cy0+42*S),"BRANDY",font=f_t,fill=INK)
ay=cy0+132*S; a0,a1=tx+2*S,tx+134*S
d.line([(a0,ay),(a1,ay)],fill=(176,96,58),width=5*S)
for xx,dx in ((a0,1),(a1,-1)):
    d.line([(xx,ay),(xx+13*S*dx,ay-9*S)],fill=(176,96,58),width=5*S)
    d.line([(xx,ay),(xx+13*S*dx,ay+9*S)],fill=(176,96,58),width=5*S)
d.text((tx,cy0+160*S),"HAIGER",font=f_t,fill=INK)
d.line([(tx,cy0+252*S),(cx1-34*S,cy0+252*S)],fill=(206,186,152),width=2*S)
d.text((tx,cy0+272*S),"Wege durch das",font=f_s,fill=MUTED)
d.text((tx,cy0+312*S),"Lahn-Dill-Bergland",font=f_s,fill=MUTED)

img=img.resize((1600,1200),Image.LANCZOS)
img.save('/home/claude/cover/brandy-haiger-karte.png')
print("ok")
