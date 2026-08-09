from PIL import ImageDraw
import math

INK=(59,52,42)
def poly(d,pts,fill=None,outline=INK,w=3):
    d.polygon(pts,fill=fill,outline=outline)
    if w>1:
        d.line(list(pts)+[pts[0]],fill=outline,width=w,joint='curve')
def circ(d,x,y,r,fill=None,outline=INK,w=3):
    d.ellipse([x-r,y-r,x+r,y+r],fill=fill,outline=outline,width=w)

# --- Fuchs (Fuchskaute) ---
def fox(d,x,y,s):
    o=(200,110,50); lt=(240,222,196)
    # Ohren
    poly(d,[(x-s*.62,y-s*.30),(x-s*.52,y-s*.95),(x-s*.14,y-s*.50)],o)
    poly(d,[(x+s*.62,y-s*.30),(x+s*.52,y-s*.95),(x+s*.14,y-s*.50)],o)
    poly(d,[(x-s*.55,y-s*.36),(x-s*.50,y-s*.78),(x-s*.26,y-s*.50)],(224,150,120),None,0)
    poly(d,[(x+s*.55,y-s*.36),(x+s*.50,y-s*.78),(x+s*.26,y-s*.50)],(224,150,120),None,0)
    # Kopf
    poly(d,[(x-s*.70,y-s*.36),(x+s*.70,y-s*.36),(x+s*.30,y+s*.42),(x,y+s*.78),(x-s*.30,y+s*.42)],o)
    # Wangen hell
    poly(d,[(x-s*.30,y+s*.05),(x,y+s*.30),(x+s*.30,y+s*.05),(x,y+s*.74)],lt,None,0)
    # Augen + Nase
    circ(d,x-s*.28,y-s*.02,s*.075,INK,INK,1)
    circ(d,x+s*.28,y-s*.02,s*.075,INK,INK,1)
    circ(d,x,y+s*.60,s*.085,INK,INK,1)

# --- See (Krombachtalsperre) ---
def lake(d,x,y,s):
    w=(126,176,198)
    pts=[(x-s*.85,y-s*.05),(x-s*.55,y-s*.42),(x+s*.05,y-s*.50),(x+s*.62,y-s*.28),
         (x+s*.86,y+s*.12),(x+s*.45,y+s*.46),(x-s*.20,y+s*.52),(x-s*.70,y+s*.32)]
    poly(d,pts,w)
    for i,(dx,dy,lw) in enumerate([(-.30,-.10,.34),(.16,.10,.42),(-.10,.28,.26)]):
        d.line([(x+s*dx-s*lw,y+s*dy),(x+s*dx+s*lw,y+s*dy)],fill=(244,236,220),width=max(2,int(s*.07)))
    # kleine Tanne am Ufer
    tree(d,x-s*.95,y-s*.55,s*.42)

def tree(d,x,y,s,col=(92,122,68)):
    poly(d,[(x,y-s*1.0),(x+s*.46,y+s*.10),(x-s*.46,y+s*.10)],col)
    poly(d,[(x,y-s*.55),(x+s*.58,y+s*.55),(x-s*.58,y+s*.55)],col)
    d.line([(x,y+s*.45),(x,y+s*.85)],fill=(110,84,56),width=max(2,int(s*.22)))

# --- Berg mit Windrädern (Knoten) ---
def windmount(d,x,y,s):
    g=(120,142,96); g2=(96,118,76)
    poly(d,[(x-s*1.0,y+s*.55),(x-s*.18,y-s*.35),(x+s*.55,y+s*.55)],g)
    poly(d,[(x-s*.05,y+s*.55),(x+s*.55,y-s*.05),(x+s*1.0,y+s*.55)],g2)
    for bx,bh in ((-s*.42,s*.95),(s*.30,s*.72)):
        tx,ty=x+bx,y-s*.10
        d.line([(tx,ty),(tx,ty-bh)],fill=(250,246,238),width=max(3,int(s*.10)))
        d.line([(tx,ty),(tx,ty-bh)],fill=INK,width=max(1,int(s*.03)))
        hx,hy=tx,ty-bh
        for a in (90,210,330):
            r=math.radians(a)
            d.line([(hx,hy),(hx+math.cos(r)*s*.42,hy-math.sin(r)*s*.42)],fill=(250,246,238),width=max(3,int(s*.085)))
            d.line([(hx,hy),(hx+math.cos(r)*s*.42,hy-math.sin(r)*s*.42)],fill=INK,width=1)
        circ(d,hx,hy,s*.07,(250,246,238),INK,2)

# --- schneller Radweg (Ulmtalradweg) ---
def fastpath(d,x,y,s):
    road=(146,146,142)
    poly(d,[(x-s*.22,y-s*.85),(x+s*.22,y-s*.85),(x+s*.98,y+s*.72),(x-s*.98,y+s*.72)],road)
    n=4
    for k in range(n):
        t0=k/n+.05; t1=(k+1)/n-.18
        y0=y-s*.85+t0*s*1.57; y1=y-s*.85+t1*s*1.57
        d.line([(x,y0),(x,y1)],fill=(250,246,236),width=max(3,int(s*(.07+.16*t0))))
    bike(d,x+s*.02,y+s*.30,s*.56)

def bike(d,x,y,s):
    circ(d,x-s*.55,y+s*.22,s*.34,None,INK,max(2,int(s*.13)))
    circ(d,x+s*.55,y+s*.22,s*.34,None,INK,max(2,int(s*.13)))
    w=max(2,int(s*.13))
    d.line([(x-s*.55,y+s*.22),(x-s*.05,y+s*.22),(x+s*.20,y-s*.32),(x+s*.55,y+s*.22)],fill=INK,width=w)
    d.line([(x-s*.05,y+s*.22),(x+s*.20,y-s*.32)],fill=INK,width=w)
    d.line([(x+s*.20,y-s*.32),(x+s*.60,y-s*.34)],fill=INK,width=w)

# --- Fluss mit Brücke (Lahn) ---
def river(d,x,y,s):
    w=(126,176,198)
    poly(d,[(x-s*1.0,y-s*.55),(x-s*.35,y-s*.30),(x+s*.25,y+s*.20),(x+s*1.0,y+s*.42),
            (x+s*1.0,y+s*.80),(x+s*.10,y+s*.55),(x-s*.55,y+s*.05),(x-s*1.0,y-s*.15)],w)
    # Steinbrücke
    bx,by=x-s*.05,y+s*.02
    poly(d,[(bx-s*.52,by-s*.30),(bx+s*.52,by-s*.02),(bx+s*.52,by+s*.22),(bx-s*.52,by-s*.06)],(214,196,166))
    for t in (-.26,.02,.30):
        d.line([(bx+s*t,by-s*.16+s*t*.28),(bx+s*t,by+s*.10+s*t*.28)],fill=(160,140,112),width=max(2,int(s*.06)))

# --- idyllischer Radweg (Weiltal) ---
def idyllic(d,x,y,s):
    d.line([(x-s*.85,y+s*.62),(x-s*.20,y+s*.10),(x+s*.30,y-s*.28),(x+s*.75,y-s*.62)],
           fill=(240,228,198),width=max(5,int(s*.34)))
    d.line([(x-s*.85,y+s*.62),(x-s*.20,y+s*.10),(x+s*.30,y-s*.28),(x+s*.75,y-s*.62)],
           fill=(186,166,132),width=max(1,int(s*.04)))
    tree(d,x-s*.62,y-s*.10,s*.40,(104,134,74))
    tree(d,x+s*.05,y-s*.50,s*.34,(84,114,62))
    tree(d,x+s*.62,y+s*.34,s*.38,(112,142,80))

# --- Dill-Kraut (Dilltal) ---
def dillherb(d,x,y,s):
    g=(74,116,52)
    d.line([(x,y+s*.85),(x,y-s*.35)],fill=g,width=max(4,int(s*.13)))
    for a in range(0,360,45):
        r=math.radians(a)
        ex,ey=x+math.cos(r)*s*.62, y-s*.35-math.sin(r)*s*.34
        d.line([(x,y-s*.35),(ex,ey)],fill=g,width=max(3,int(s*.075)))
        circ(d,ex,ey,s*.125,(206,222,118),g,2)
    for sy,sx in ((.20,.42),(.48,-.40)):
        d.line([(x,y+s*sy),(x+s*sx,y+s*sy-s*.16)],fill=g,width=max(2,int(s*.05)))

# --- Grube (Grube Fortuna) ---
def mine(d,x,y,s):
    st=(120,96,72); dk=(88,70,52)
    poly(d,[(x-s*.62,y+s*.72),(x-s*.34,y-s*.62),(x+s*.34,y-s*.62),(x+s*.62,y+s*.72)],st)
    d.line([(x-s*.48,y+s*.05),(x+s*.48,y+s*.05)],fill=dk,width=max(2,int(s*.07)))
    d.line([(x-s*.55,y+s*.40),(x+s*.55,y+s*.40)],fill=dk,width=max(2,int(s*.07)))
    d.line([(x-s*.48,y+s*.05),(x+s*.34,y-s*.62)],fill=dk,width=max(2,int(s*.06)))
    circ(d,x,y-s*.72,s*.26,(214,196,166),INK,3)
    d.line([(x,y-s*.72),(x,y-s*.46)],fill=INK,width=2)
    poly(d,[(x-s*.95,y+s*.72),(x+s*.95,y+s*.72),(x+s*.80,y+s*.95),(x-s*.80,y+s*.95)],(150,128,100))

# --- freundlicher Hai (Haiger) ---
def shark(d,x,y,s):
    b=(122,152,172); lt=(226,232,236)
    poly(d,[(x-s*.95,y+s*.02),(x-s*.30,y-s*.42),(x+s*.55,y-s*.30),(x+s*.95,y+s*.10),
            (x+s*.50,y+s*.44),(x-s*.35,y+s*.44)],b)
    poly(d,[(x-s*.35,y+s*.36),(x+s*.55,y+s*.34),(x+s*.80,y+s*.16),(x-s*.85,y+s*.10)],lt,None,0)
    poly(d,[(x-s*.16,y-s*.40),(x+s*.10,y-s*.95),(x+s*.28,y-s*.34)],b)     # Rückenflosse
    poly(d,[(x+s*.90,y+s*.06),(x+s*1.35,y-s*.32),(x+s*1.28,y+s*.40)],b)   # Schwanz
    circ(d,x-s*.55,y-s*.10,s*.10,INK,INK,1)
    circ(d,x-s*.58,y-s*.13,s*.035,(255,255,255),None,0)
    d.arc([x-s*.86,y+s*.00,x-s*.36,y+s*.30],10,150,fill=INK,width=max(2,int(s*.06)))  # Lächeln

# --- Heimat im Wald (Brandoberndorf) ---
def home(d,x,y,s):
    tree(d,x-s*.86,y+s*.18,s*.50,(88,118,66))
    tree(d,x+s*.86,y+s*.12,s*.44,(104,134,74))
    poly(d,[(x-s*.48,y+s*.62),(x-s*.48,y-s*.05),(x+s*.48,y-s*.05),(x+s*.48,y+s*.62)],(240,230,210))
    poly(d,[(x-s*.64,y-s*.02),(x,y-s*.62),(x+s*.64,y-s*.02)],(190,86,66))
    poly(d,[(x-s*.13,y+s*.62),(x-s*.13,y+s*.16),(x+s*.13,y+s*.16),(x+s*.13,y+s*.62)],(150,120,88))
    circ(d,x-s*.30,y+s*.22,s*.10,(214,224,240),INK,2)
    circ(d,x+s*.30,y+s*.22,s*.10,(214,224,240),INK,2)
