/* Lottery POS panel - tablet-first retailer terminal */
/* Minimal QR Code encoder (byte mode, ECC level M, versions 1-10). Algorithm after Nayuki's public-domain-style reference. */
const QR=(()=>{
const EPB=[-1,10,16,26,18,24,16,18,22,22,26],NB=[-1,1,1,1,2,2,4,4,4,5,5];
const ALIGN=[null,[],[6,18],[6,22],[6,26],[6,30],[6,34],[6,22,38],[6,24,42],[6,26,46],[6,28,50]];
const raw=v=>{let r=(16*v+128)*v+64;if(v>=2){const n=Math.floor(v/7)+2;r-=(25*n-10)*n-55;if(v>=7)r-=36}return r};
const dataCw=v=>Math.floor(raw(v)/8)-EPB[v]*NB[v];
const gmul=(x,y)=>{let z=0;for(let i=7;i>=0;i--){z=(z<<1)^((z>>>7)*0x11D);z^=((y>>>i)&1)*x}return z};
const rsDiv=d=>{const r=new Array(d).fill(0);r[d-1]=1;let root=1;for(let i=0;i<d;i++){for(let j=0;j<d;j++){r[j]=gmul(r[j],root);if(j+1<d)r[j]^=r[j+1]}root=gmul(root,2)}return r};
const rsRem=(data,div)=>{const r=new Array(div.length).fill(0);for(const b of data){const f=b^r.shift();r.push(0);div.forEach((c,i)=>{r[i]^=gmul(c,f)})}return r};
const MASKS=[(x,y)=>(x+y)%2===0,(x,y)=>y%2===0,(x,y)=>x%3===0,(x,y)=>(x+y)%3===0,(x,y)=>(Math.floor(x/3)+Math.floor(y/2))%2===0,(x,y)=>x*y%2+x*y%3===0,(x,y)=>(x*y%2+x*y%3)%2===0,(x,y)=>((x+y)%2+x*y%3)%2===0];
function penalty(m,size){let p=0;
 for(let pass=0;pass<2;pass++){for(let a=0;a<size;a++){let run=1,hist=[];let prev=null;const line=[];for(let b=0;b<size;b++)line.push(pass?m[b][a]:m[a][b]);
  for(let b=0;b<size;b++){if(b>0&&line[b]===line[b-1]){run++;if(run===5)p+=3;else if(run>5)p++}else run=1}
  const s=line.map(v=>v?1:0).join("");for(const pat of["10111010000","00001011101"]){let i=-1;while((i=s.indexOf(pat,i+1))>=0)p+=40}}}
 for(let y=0;y<size-1;y++)for(let x=0;x<size-1;x++){const c=m[y][x];if(c===m[y][x+1]&&c===m[y+1][x]&&c===m[y+1][x+1])p+=3}
 let dark=0;for(const r of m)for(const c of r)if(c)dark++;const tot=size*size;p+=Math.floor(Math.abs(dark*20-tot*10)/tot)*10;return p}
function encode(text){
 const bytes=[...new TextEncoder().encode(text)];let ver=1;
 for(;ver<=10;ver++){if(4+(ver<=9?8:16)+bytes.length*8<=dataCw(ver)*8)break}
 if(ver>10)throw new Error("QR text too long");
 const bits=[],put=(v,l)=>{for(let i=l-1;i>=0;i--)bits.push((v>>>i)&1)};
 put(4,4);put(bytes.length,ver<=9?8:16);bytes.forEach(b=>put(b,8));
 const cap=dataCw(ver)*8;put(0,Math.min(4,cap-bits.length));put(0,(8-bits.length%8)%8);
 for(let pad=0xEC;bits.length<cap;pad^=0xEC^0x11)put(pad,8);
 const data=[];for(let i=0;i<bits.length;i+=8){let b=0;for(let j=0;j<8;j++)b=(b<<1)|bits[i+j];data.push(b)}
 const nb=NB[ver],eb=EPB[ver],rawCw=Math.floor(raw(ver)/8),nShort=nb-rawCw%nb,shortLen=Math.floor(rawCw/nb),div=rsDiv(eb),blocks=[];
 for(let i=0,k=0;i<nb;i++){const len=shortLen-eb+(i<nShort?0:1),dat=data.slice(k,k+len);k+=len;const ecc=rsRem(dat,div);if(i<nShort)dat.push(0);blocks.push(dat.concat(ecc))}
 const out=[];for(let i=0;i<blocks[0].length;i++)blocks.forEach((b,j)=>{if(i!==shortLen-eb||j>=nShort)out.push(b[i])});
 const size=ver*4+17,mk=()=>Array.from({length:size},()=>new Array(size).fill(false)),m=mk(),fn=mk();
 const set=(x,y,v)=>{m[y][x]=v;fn[y][x]=true};
 for(let i=0;i<size;i++){set(6,i,i%2===0);set(i,6,i%2===0)}
 const finder=(cx,cy)=>{for(let dy=-4;dy<=4;dy++)for(let dx=-4;dx<=4;dx++){const d=Math.max(Math.abs(dx),Math.abs(dy)),x=cx+dx,y=cy+dy;if(x>=0&&x<size&&y>=0&&y<size)set(x,y,d!==2&&d!==4)}};
 finder(3,3);finder(size-4,3);finder(3,size-4);
 const ap=ALIGN[ver],n=ap.length;
 for(let i=0;i<n;i++)for(let j=0;j<n;j++){if((i===0&&j===0)||(i===0&&j===n-1)||(i===n-1&&j===0))continue;for(let dy=-2;dy<=2;dy++)for(let dx=-2;dx<=2;dx++)set(ap[i]+dx,ap[j]+dy,Math.max(Math.abs(dx),Math.abs(dy))!==1)}
 const fmt=(mx,mask,mark)=>{const w=(x,y,v)=>{mx[y][x]=v;if(mark)fn[y][x]=true};let rem=mask;for(let i=0;i<10;i++)rem=(rem<<1)^((rem>>>9)*0x537);const bits=((mask<<10)|rem)^0x5412,bit=i=>((bits>>>i)&1)!==0;
  for(let i=0;i<=5;i++)w(8,i,bit(i));w(8,7,bit(6));w(8,8,bit(7));w(7,8,bit(8));for(let i=9;i<15;i++)w(14-i,8,bit(i));
  for(let i=0;i<8;i++)w(size-1-i,8,bit(i));for(let i=8;i<15;i++)w(8,size-15+i,bit(i));w(8,size-8,true)};
 fmt(m,0,true);
 if(ver>=7){let rem=ver;for(let i=0;i<12;i++)rem=(rem<<1)^((rem>>>11)*0x1F25);const bits=(ver<<12)|rem;for(let i=0;i<18;i++){const b=((bits>>>i)&1)!==0,a=size-11+i%3,c=Math.floor(i/3);set(a,c,b);set(c,a,b)}}
 let bi=0;for(let right=size-1;right>=1;right-=2){if(right===6)right=5;for(let vert=0;vert<size;vert++){for(let j=0;j<2;j++){const x=right-j,up=((right+1)&2)===0,y=up?size-1-vert:vert;if(!fn[y][x]&&bi<out.length*8){m[y][x]=((out[bi>>>3]>>>(7-(bi&7)))&1)!==0;bi++}}}}
 let best=null,bp=1e9;
 for(let mask=0;mask<8;mask++){const c=m.map(r=>r.slice());for(let y=0;y<size;y++)for(let x=0;x<size;x++)if(!fn[y][x]&&MASKS[mask](x,y))c[y][x]=!c[y][x];fmt(c,mask,false);const p=penalty(c,size);if(p<bp){bp=p;best=c}}
 return {size,m:best}}
function svg(text){const {size,m}=encode(text),q=2;let d="";for(let y=0;y<size;y++)for(let x=0;x<size;x++)if(m[y][x])d+=`M${x+q},${y+q}h1v1h-1z`;const t=size+q*2;return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${t} ${t}" shape-rendering="crispEdges" width="100%"><rect width="${t}" height="${t}" fill="#fff"/><path d="${d}" fill="#000"/></svg>`}
return {encode,svg}})();
const qrSVG=t=>QR.svg(t);

const ago=n=>new Date(Date.now()-new Date().getTimezoneOffset()*6e4-n*864e5).toISOString().slice(0,10);
const C39={0:"nnnwwnwnn",1:"wnnwnnnnw",2:"nnwwnnnnw",3:"wnwwnnnnn",4:"nnnwwnnnw",5:"wnnwwnnnn",6:"nnwwwnnnn",7:"nnnwnnwnw",8:"wnnwnnwnn",9:"nnwwnnwnn","*":"nwnnwnwnn"};
const barcode=id=>{let x=0,r="";for(const ch of "*"+id+"*"){const p=C39[ch];for(let i=0;i<9;i++){const w=p[i]==="w"?3:1;if(i%2===0)r+=`<rect x="${x}" width="${w}" height="40"/>`;x+=w}x+=1}return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${x} 40" width="100%" height="50" preserveAspectRatio="none">${r}</svg>`};
const today=()=>new Date(Date.now()-new Date().getTimezoneOffset()*6e4).toISOString().slice(0,10);
const esc=v=>String(v??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const fmt=n=>Number(n||0).toFixed(2);
const DAYS=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
const PRESETS=[".25",".50",".75","1","2","5","10","20"];

const CSS=`
:host{--bg:#f2f4fa;--card:#fff;--ink:#0f172a;--mut:#64748b;--line:#e4e8f2;--pri:#4f46e5;--pri2:#7c3aed;--ok:#16a34a;--bad:#e11d48;--key:#f0f3fa;--nav:#0b1020;--sh:0 10px 30px #1e293b14;display:block;height:100%;background:var(--bg);color:var(--ink);font-family:Inter,system-ui,Roboto,sans-serif}
:host(.dark){--bg:#0a0f1e;--card:#131a2e;--ink:#e8ecf8;--mut:#8b97b5;--line:#232c47;--key:#1b2440;--nav:#060a14;--sh:0 10px 30px #0007}
*{box-sizing:border-box}button,select,input{font:inherit;color:inherit}
button{border:0;border-radius:14px;padding:10px 14px;background:var(--key);font-weight:600;cursor:pointer;transition:transform .08s,box-shadow .15s,background .15s}button:active{transform:scale(.96)}
.shell{display:flex;height:100%}.content{flex:1;display:flex;flex-direction:column;min-width:0}
.nav{width:84px;background:var(--nav);display:flex;flex-direction:column;align-items:center;padding:12px 6px;gap:8px}
.nav button{width:70px;background:transparent;color:#7d89a8;display:flex;flex-direction:column;align-items:center;gap:3px;font-size:11px;padding:10px 2px;border-radius:16px}
.nav button.on{background:linear-gradient(135deg,var(--pri),var(--pri2));color:#fff;box-shadow:0 6px 18px #4f46e566}.nav ha-icon{--mdc-icon-size:26px}
.logo{width:60px;height:60px;border-radius:18px;background:#1b2440;color:#fff;font-weight:800;font-size:20px;display:grid;place-items:center;overflow:hidden;margin-bottom:10px}.logo img{max-width:100%;max-height:100%}
.top{display:flex;gap:10px;align-items:center;padding:12px 16px;flex-wrap:wrap}
.brand{font-weight:800;font-size:22px;letter-spacing:-.5px;white-space:nowrap}
.kpi{background:var(--card);border-radius:14px;padding:6px 14px;box-shadow:var(--sh);line-height:1.15}.kpi span{display:block;font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:.6px}.kpi b{font-size:17px}
.top input,.top select{height:44px;border:1px solid var(--line);background:var(--card);border-radius:14px;padding:0 12px}#scan{width:240px}
.ic{width:44px;height:44px;padding:0;display:grid;place-items:center;background:var(--card);box-shadow:var(--sh)}
.main{flex:1;display:grid;grid-template-columns:minmax(0,1.7fr) minmax(300px,1fr);gap:16px;padding:0 16px 16px;min-height:0}
.card{background:var(--card);border-radius:22px;padding:16px;box-shadow:var(--sh)}
.left{display:flex;flex-direction:column;gap:14px;overflow:auto}
.games{display:grid;grid-template-columns:repeat(auto-fill,minmax(128px,1fr));gap:10px}
.game{position:relative;background:linear-gradient(135deg,var(--c),color-mix(in srgb,var(--c) 55%,#000));color:#fff;display:flex;flex-direction:column;align-items:flex-start;gap:2px;padding:12px;border-radius:18px;opacity:.55;text-align:left;box-shadow:0 4px 12px color-mix(in srgb,var(--c) 40%,transparent)}
.game b{font-size:16px}.game small{font-weight:500;opacity:.9}.gi{width:34px;height:34px;border-radius:50%;background:#ffffff33;display:grid;place-items:center;font-weight:800;margin-bottom:4px;overflow:hidden}.gi img{max-width:100%;max-height:100%}
.game .chk{position:absolute;right:10px;top:10px;width:22px;height:22px;border-radius:50%;background:#fff;color:var(--c);display:none;place-items:center;font-size:13px;font-weight:900}
.game.on{opacity:1;box-shadow:0 0 0 3px var(--card),0 0 0 6px var(--c),0 10px 22px color-mix(in srgb,var(--c) 50%,transparent)}.game.on .chk{display:grid}
.game.closed{filter:grayscale(1);opacity:.35;pointer-events:none}
.ctl{display:flex;gap:10px;flex-wrap:wrap;align-items:center}.ctl input[type=date]{height:40px;border:1px solid var(--line);border-radius:12px;background:var(--key);padding:0 10px}
.bts{display:flex;gap:6px;flex-wrap:wrap}.bt{border-radius:999px;padding:8px 14px;font-size:13px}.bt.on{background:var(--ink);color:var(--card)}
.entry{display:grid;grid-template-columns:1.3fr 1fr;gap:10px}
.disp{min-height:74px;border:2px solid var(--line);border-radius:18px;display:flex;align-items:center;justify-content:center;gap:6px;cursor:pointer;background:var(--card);position:relative;padding-top:12px}
.disp.act{border-color:var(--pri);box-shadow:0 0 0 4px #4f46e522}.disp small{position:absolute;left:12px;top:6px;font-size:10px;text-transform:uppercase;letter-spacing:.7px;color:var(--mut)}
.dg{width:46px;height:54px;border-radius:12px;background:var(--key);display:grid;place-items:center;font-size:32px;font-weight:800;color:var(--pri)}.dg.f{background:#4f46e51a}
.amtv{font-size:34px;font-weight:800}
.add{grid-column:1/-1;background:linear-gradient(135deg,#f43f5e,#e11d48);color:#fff;font-size:18px;height:54px;box-shadow:0 8px 20px #e11d4855}
.pads{display:grid;grid-template-columns:1.5fr 1fr;gap:14px}
.pad{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.pad button{height:62px;font-size:26px;font-weight:700;background:var(--key)}.pad button:hover{background:#4f46e51f}
.pre{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}.pre button{height:62px;font-size:20px;background:linear-gradient(135deg,#4f46e515,#7c3aed25);color:var(--pri)}
.acts{display:grid;grid-template-columns:repeat(8,1fr);gap:8px}.acts button{display:flex;flex-direction:column;align-items:center;gap:2px;font-size:11px;padding:10px 2px;font-weight:600}.acts ha-icon{--mdc-icon-size:22px;color:var(--pri)}
.right{display:flex;flex-direction:column;min-height:0;position:relative}
.rhead{display:flex;justify-content:space-between;align-items:center}.rhead h3{margin:0;font-size:17px}.badge{background:var(--pri);color:#fff;border-radius:999px;padding:2px 10px;font-size:12px;font-weight:700}
.rsub{font-size:12px;color:var(--mut);margin:2px 0 8px}
#lines{flex:1;overflow:auto;background:var(--key);border-radius:16px;padding:6px 8px;margin-bottom:12px}
.ln{display:grid;grid-template-columns:8px auto 1fr auto auto auto;gap:10px;align-items:center;padding:10px 4px;border-bottom:1px dashed var(--line);font-size:13px;cursor:pointer;animation:pop .2s}
@keyframes pop{from{opacity:0;transform:translateY(-6px)}}
.ln i{width:8px;height:34px;border-radius:4px}.ln b{font-size:20px;letter-spacing:2px}.ln small{display:block;color:var(--mut)}.ln em{font-style:normal;font-weight:700}
.ln button{padding:4px 9px;background:#e11d4822;color:var(--bad);border-radius:10px}
.empty{color:var(--mut);text-align:center;padding:36px 10px}
.foot{display:flex;justify-content:space-between;align-items:center;gap:10px}.foot small{color:var(--mut)}.tot{font-size:28px;font-weight:800}
.send{background:linear-gradient(135deg,#22c55e,#15803d);color:#fff;font-size:18px;padding:16px 24px;box-shadow:0 10px 24px #16a34a55}
.office{padding:0 16px 16px;overflow:auto;display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));align-content:start}
.office h3{margin:0 0 12px}.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:10px}
.office input:not([type=color]):not([type=file]):not([type=checkbox]),.office select{height:42px;border:1px solid var(--line);background:var(--key);border-radius:12px;padding:0 12px}
.office button:not(.ghost){background:linear-gradient(135deg,var(--pri),var(--pri2));color:#fff}
.prev{max-height:64px;max-width:180px;border:1px dashed var(--line);border-radius:12px;padding:4px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin:6px 0 14px}.kc{background:var(--key);border-radius:16px;padding:12px}.kc span{font-size:11px;color:var(--mut);text-transform:uppercase}.kc b{display:block;font-size:22px}
.pos{color:var(--ok)}.neg{color:var(--bad)}
table{width:100%;border-collapse:collapse;font-size:13px}td,th{padding:9px 6px;border-bottom:1px solid var(--line);text-align:right}td:first-child,th:first-child{text-align:left}th{color:var(--mut);font-weight:600}tr:nth-child(even) td{background:var(--key)}
.toast{position:fixed;left:50%;bottom:28px;transform:translateX(-50%);background:#0f172a;color:#fff;padding:13px 22px;border-radius:16px;z-index:99;box-shadow:0 12px 30px #0006;animation:pop .2s}.toast.err{background:#be123c}
.modal{position:fixed;inset:0;background:#020617aa;backdrop-filter:blur(4px);display:grid;place-items:center;z-index:100}
.mbox{background:var(--card);border-radius:24px;padding:24px;width:min(380px,92vw);text-align:center;box-shadow:0 30px 70px #0008;animation:pop .2s}.mbox h3{margin:0 0 8px;font-size:22px}.mbox p{color:var(--mut);margin:8px 0 16px;word-break:break-all}
.mbox input{width:100%;height:50px;border:2px solid var(--line);border-radius:14px;padding:0 14px;font-size:18px;background:var(--key);margin-bottom:14px;text-align:center}
.mbox .big{font-size:42px;font-weight:900;color:var(--ok)}.mbox.win{background:linear-gradient(160deg,var(--card),#16a34a22)}
.mrow{display:flex;gap:10px}.mrow button{flex:1;height:50px}.mrow .primary{background:linear-gradient(135deg,var(--pri),var(--pri2));color:#fff}.mbox.win .primary{background:linear-gradient(135deg,#22c55e,#15803d)}
.ticker{margin:0 16px 12px;height:48px;border-radius:12px;background:#000;overflow:hidden;position:relative;box-shadow:inset 0 0 0 2px #1f2937,var(--sh)}
.ticker:after{content:"";position:absolute;inset:0;background:radial-gradient(circle,#0000 52%,#000b 62%) 0 0/4px 4px;pointer-events:none}
.tk{position:absolute;left:0;top:0;white-space:nowrap;line-height:48px;font:700 26px "Courier New",monospace;letter-spacing:3px;text-shadow:0 0 10px currentColor;animation:scrollx linear infinite}
@keyframes scrollx{from{transform:translateX(100vw)}to{transform:translateX(-100%)}}
.gl{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:12px}.gcard{border:2px solid var(--line);border-left:8px solid var(--c);border-radius:16px;padding:12px}
.gcard label,.office label{font-size:12px;color:var(--mut);display:flex;gap:4px;align-items:center}.chip{background:var(--key);border-radius:999px;padding:4px 10px}
.ghost{background:var(--key)!important;color:var(--ink)!important}.dng{color:var(--bad)!important}
.top .ticker{flex:1;margin:0;height:44px;min-width:180px}.top .tk{line-height:44px;font-size:22px}
.ln .ed{background:#4f46e522;color:var(--pri)}.ln.editing{background:#4f46e51a;border-radius:10px;outline:2px solid var(--pri)}
.add.upd{background:linear-gradient(135deg,#4f46e5,#7c3aed);box-shadow:0 8px 20px #4f46e555}
.editbar{grid-column:1/-1;background:#4f46e51a;color:var(--pri);border-radius:12px;padding:8px 12px;font-weight:600;font-size:13px}
.office{flex:1;min-height:0;align-content:start}
.subtabs{display:flex;gap:8px;padding:0 16px 12px;overflow:auto}.subtabs button{display:flex;gap:6px;align-items:center;white-space:nowrap;background:var(--card);box-shadow:var(--sh)}
.subtabs button.on{background:linear-gradient(135deg,var(--pri),var(--pri2));color:#fff}.subtabs ha-icon{--mdc-icon-size:20px}
.paper{background:#fff;color:#000;padding:10px 4px;margin:0 auto;box-shadow:0 4px 18px #0003;border-radius:4px;max-width:100%;overflow:hidden}
.st{padding:2px 9px;border-radius:999px;font-size:11px;font-weight:700}.st.paid{background:#16a34a22;color:#15803d}.st.unpaid{background:#e11d4822;color:#be123c}.st.pending{background:#f59e0b33;color:#b45309}
.note{font-size:12px;color:var(--mut);margin:6px 0}.office h4{margin:16px 0 6px}
@media(max-width:900px){.top .ticker{order:10;flex-basis:100%}.main{grid-template-columns:1fr}.kpi{display:none}.acts{grid-template-columns:repeat(4,1fr)}}

.promo-block{border:1.5px dashed #000;padding:6px 4px;margin:6px 0;text-align:center}
.promo-block .plabel{font-size:0.9em;text-transform:uppercase;letter-spacing:.04em}
.promo-block .pcode{font-size:1.55em;font-weight:900;letter-spacing:.18em;margin:4px 0}
.promo-block .pinstr{font-size:0.82em;line-height:1.25;margin-top:4px}
.promo-card{border:1px solid var(--line);border-radius:16px;padding:14px;margin-bottom:12px;background:var(--key)}
.promo-card h4{margin:0 0 8px;display:flex;align-items:center;gap:8px}
.promo-card .meta{font-size:12px;color:var(--mut);margin-bottom:8px}
@media(max-width:620px){.shell{flex-direction:column-reverse}.nav{width:100%;flex-direction:row;justify-content:space-around;padding:6px}.nav .logo{display:none}.nav button{width:auto;flex:1}#scan{width:100%}}
`;

class LotteryPosPanel extends HTMLElement{
  constructor(){super();this.attachShadow({mode:"open"});
    this.s={tab:"sell",sel:[],bt:"",date:today(),num:"",amt:"",field:"num",lines:[],retailer:"",data:null,scan:"",report:null,glogos:{},sub:"games"};
    this._kh=e=>this.onKey(e)}
  connectedCallback(){window.addEventListener("keydown",this._kh)}
  disconnectedCallback(){window.removeEventListener("keydown",this._kh);clearInterval(this._tm)}
  set hass(h){const first=!this._hass;this._hass=h;if(first)this.init()}
  set narrow(v){}set panel(v){}set route(v){}
  ws(type,extra={}){return this._hass.callWS({type:"lottery_pos/"+type,...extra})}
  async init(){const s=this.s;try{s.dark=localStorage.getItem("lottery_pos_dark")==="1"}catch(e){}
    this._posTerminal=location.hash.includes("pos-terminal");
    if(this._posTerminal){s.tab="sell";document.title=(document.title||"Lottery POS")+" — Terminal"}
    s.data=await this.ws("state");this._tm=setInterval(()=>this.tick(),30000);s.sel=[s.data.games[0]?.id];s.bt=s.data.bet_types[0]?.key;s.retailer=s.data.retailers[0]?.id;
    this.shadowRoot.addEventListener("click",e=>{const el=e.target.closest("[data-a]");if(el)this.act(el.dataset.a,el.dataset)});
    this.render();
    if(this._posTerminal){try{await this.requestFullscreen?.()||this.shadowRoot.host?.requestFullscreen?.()}catch(e){}}}
  bt(){return this.s.data.all_bet_types.find(b=>b.key===this.s.bt)}
  allowedBTs(){const s=this.s,d=s.data,sel=s.sel.map(id=>d.all_games.find(g=>g.id===id)).filter(Boolean);return d.bet_types.filter(b=>sel.every(g=>!g.bet_types?.length||g.bet_types.includes(b.key)))}
  btl(k){return this.s.data.all_bet_types.find(b=>b.key===k)?.label||k}
  gn(k){return this.s.data.all_games.find(g=>g.id===k)?.name||k}
  toast(m,err){const t=document.createElement("div");t.className="toast"+(err?" err":"");t.textContent=(err?"⚠ ":"✓ ")+m;this.shadowRoot.append(t);setTimeout(()=>t.remove(),3200)}
  modal({title,text="",input,ok="OK",tone="",big=""}){return new Promise(res=>{const m=document.createElement("div");m.className="modal";
    m.innerHTML=`<div class="mbox ${tone}"><h3>${title}</h3>${big?`<div class="big">${big}</div>`:""}<p>${text}</p>${input?`<input id="mi" placeholder="${input}" inputmode="numeric">`:""}<div class="mrow"><button class="ghost" data-x="0">Cancel</button><button class="primary" data-x="1">${ok}</button></div></div>`;
    const done=v=>{m.remove();res(v)};m.onclick=e=>{const x=e.target.dataset.x;if(x==="0"||e.target===m)done(null);else if(x==="1")done(input?m.querySelector("#mi").value.trim():true)};
    m.querySelector("#mi")?.addEventListener("keydown",e=>{if(e.key==="Enter")done(e.target.value.trim())});this.shadowRoot.append(m);setTimeout(()=>m.querySelector("#mi")?.focus(),60)})}
  cd(g){const s=this.s,t=today(),wd=(new Date(s.date+"T12:00:00").getDay()+6)%7;if(g.draw_days?.length&&!g.draw_days.includes(wd))return{open:0,txt:`No draw ${DAYS[wd]}`};if(s.date>t)return{open:1,txt:"Open"};if(s.date<t)return{open:0,txt:"Closed"};const n=new Date(),nm=n.getHours()*60+n.getMinutes(),[oh,om]=(g.open_time||"00:00").split(":");if(nm<oh*60+ +om)return{open:0,txt:`Opens ${g.open_time}`};const [h,m]=g.cutoff.split(":"),d=h*60+ +m-(n.getHours()*60+n.getMinutes());return d<=0?{open:0,txt:"Closed"}:{open:1,txt:d>=60?`Closes in ${Math.floor(d/60)}h ${d%60}m`:`Closes in ${d}m`}}
  tick(){const s=this.s;if(!s.data||s.tab!=="sell")return;let sig="";for(const g of s.data.games){const c=this.cd(g);sig+=c.open?1:0;const el=this.shadowRoot.querySelector(`[data-cd="${g.id}"]`);if(el)el.textContent=c.txt}if(sig!==this._sig)this.render()}
  async call(type,extra){try{return await this.ws(type,extra)}catch(e){this.toast(e.message||"Error",1);return null}}

  shrink(file,max=240){return new Promise((res,rej)=>{const img=new Image(),u=URL.createObjectURL(file);img.onload=()=>{const k=Math.min(1,max/Math.max(img.width,img.height)),c=document.createElement("canvas");c.width=Math.round(img.width*k);c.height=Math.round(img.height*k);c.getContext("2d").drawImage(img,0,0,c.width,c.height);URL.revokeObjectURL(u);res(c.toDataURL("image/png"))};img.onerror=()=>rej(new Error("Not an image"));img.src=u})}
  render(){const s=this.s;if(!s.data)return;this.classList.toggle("dark",!!s.dark);const d=s.data,st=d.settings,admin=!!this._hass.user?.is_admin;
    if(!admin&&s.tab!=="sell")s.tab="sell";
    const posOnly=!!this._posTerminal;
    if(posOnly)s.tab="sell";
    const items=[["sell","mdi:cash-register","Sell",1],["office","mdi:cog","Back office",admin&&!posOnly]];
    const nav=items.filter(i=>i[3]).map(i=>`<button class="${s.tab===i[0]?"on":""}" data-a="tab" data-v="${i[0]}"><ha-icon icon="${i[1]}"></ha-icon>${i[2]}</button>`).join("");
    const body=s.tab==="sell"?this.sellHTML():`${this.subTabs()}<div class="office">${this.officeBody()}</div>`;
    this.shadowRoot.innerHTML=`<style>${CSS}</style><div class="shell"><nav class="nav"><div class="logo">${st.logo?`<img src="${st.logo}">`:esc((st.name||"L").slice(0,2).toUpperCase())}</div>${nav}</nav><div class="content"><div class="top">
      <span class="brand">${esc(st.name)}</span>${this.tickerHTML()||`<span style="flex:1"></span>`}
      <div class="kpi"><span>Sales today</span><b>${d.currency} ${fmt(d.summary.sales_today)}</b></div><div class="kpi"><span>Tickets</span><b>${d.summary.tickets_today}</b></div>
      <input id="scan" placeholder="Scan ticket…" value="${esc(s.scan)}" inputmode="numeric">
      <button class="ic" data-a="replay" title="Replay last ticket"><ha-icon icon="mdi:replay"></ha-icon></button>
      <select id="ret">${d.retailers.map(r=>`<option value="${r.id}" ${r.id===s.retailer?"selected":""}>${r.name}</option>`).join("")}</select>
      <button class="ic" data-a="theme" title="Dark / light"><ha-icon icon="${s.dark?"mdi:weather-sunny":"mdi:weather-night"}"></ha-icon></button></div>${body}</div></div>`;
    const q=x=>this.shadowRoot.querySelector(x);
    q("#scan").oninput=e=>s.scan=e.target.value;
    q("#scan").onkeydown=e=>{if(e.key==="Enter")this.scanned(e.target.value.trim())};
    q("#ret").onchange=e=>s.retailer=e.target.value;
    if(q("#date"))q("#date").onchange=e=>s.date=e.target.value;
    if(q("#logofile"))q("#logofile").onchange=async e=>{const f=e.target.files[0];if(!f)return;try{s.nameDraft=q("#bn").value;s.logoDraft=await this.shrink(f);this.render()}catch(x){this.toast(x.message,1)}};
    if(q("#gfile"))q("#gfile").onchange=async e=>{const f=e.target.files[0];if(!f)return;try{s.gameLogo=await this.shrink(f,96);this.toast("Game logo ready - press Add")}catch(x){this.toast(x.message,1)}};
    this.shadowRoot.querySelectorAll(".f-file").forEach(inp=>inp.onchange=async e=>{const f=e.target.files[0];if(!f)return;try{s.glogos[inp.dataset.id]=await this.shrink(f,96);this.toast("Logo ready - press Save on the game")}catch(x){this.toast(x.message,1)}});
    this.shadowRoot.querySelectorAll(".d-f").forEach(el=>{const h=()=>{const k=el.dataset.k,d=this.design();d[k]=el.type==="checkbox"?el.checked:["size","qr_size","width","logo_height"].includes(k)?+el.value:el.value;this.refreshPreview()};el.addEventListener("input",h);el.addEventListener("change",h)});
    this.refreshPreview();this.paint()}

  tickerHTML(){const t=this.s.data.settings.ticker;if(!t||!t.enabled||!t.text)return"";const w=t.text.length*18+1000,dur=Math.max(8,w/(30+t.speed*30));return `<div class="ticker"><div class="tk" style="color:${t.color};animation-duration:${dur.toFixed(1)}s">${esc(t.text)}</div></div>`}

  sellHTML(){const s=this.s,d=s.data;
    s.sel=s.sel.filter(id=>{const g=d.games.find(x=>x.id===id);return g&&this.cd(g).open});
    if(!s.sel.length){const g=d.games.find(x=>this.cd(x).open);if(g)s.sel=[g.id]}
    this._sig=d.games.map(g=>this.cd(g).open?1:0).join("");const ok=this.allowedBTs();if(ok.length&&!ok.find(b=>b.key===s.bt)){s.bt=ok[0].key;s.num=s.num.slice(0,ok[0].digits)}
    const games=d.games.map(g=>{const c=this.cd(g);return `<button class="game ${s.sel.includes(g.id)?"on":""} ${c.open?"":"closed"}" style="--c:${g.color}" data-a="game" data-v="${g.id}"><span class="gi">${g.logo?`<img src="${g.logo}">`:esc(g.name[0])}</span><b>${esc(g.name)}</b><small>Draw ${g.draw_time}${g.draw_days?.length&&g.draw_days.length<7?" · "+g.draw_days.map(i=>DAYS[i]).join(" "):""}</small><small data-cd="${g.id}">${c.txt}</small><span class="chk">✓</span></button>`}).join("");
    const acts=[["quick","mdi:dice-multiple","Quick pick"],["last","mdi:receipt-text-outline","Último"],["copy","mdi:content-copy","Copia"],["clear","mdi:delete-sweep-outline","Clear"],["cancel","mdi:cancel","Cancel"],["redeem","mdi:cash-check","Redeem"],["results","mdi:printer","Resultado"],["report1","mdi:file-chart-outline","Report"]];
    return `<div class="main"><section class="left card">
    <div class="games">${games}</div>
    <div class="ctl"><input type="date" id="date" value="${s.date}" min="${today()}"><div class="bts">${ok.map(b=>`<button class="bt ${b.key===s.bt?"on":""}" data-a="bt" data-v="${b.key}">${b.label}</button>`).join("")}</div></div>
    <div class="entry"><div id="num" class="disp" data-a="field" data-v="num"></div><div id="amt" class="disp" data-a="field" data-v="amt"></div>${s.editIdx!=null?`<div class="editbar">✎ Editing play ${s.editIdx+1} — type the new number / amount, then press Update</div><button class="add upd" data-a="add">✔ Update play</button><button class="cancel" data-a="canceledit" style="grid-column:1/-1">Cancel edit</button>`:`<button class="add" data-a="add">＋ Add to ticket</button>`}</div>
    <div class="pads"><div class="pad">${[1,2,3,4,5,6,7,8,9,"CLR",0,"DEL"].map(k=>`<button data-a="key" data-v="${k}">${k}</button>`).join("")}</div>
      <div class="pre">${PRESETS.map(p=>`<button data-a="preset" data-v="${p}">${p}</button>`).join("")}</div></div>
    <div class="acts">${acts.map(a=>`<button data-a="${a[0]}"><ha-icon icon="${a[1]}"></ha-icon>${a[2]}</button>`).join("")}</div>
  </section><section class="right card"><div class="rhead"><h3>Current ticket</h3><span class="badge" id="cnt">0</span></div><div class="rsub">${s.sel.length} game(s) · tap ✎ to edit a play</div>
    <div id="lines"></div><div class="foot"><div><small>Total</small><div class="tot" id="tot"></div></div><button class="send" data-a="send">Send &amp; Print ▶</button></div></section></div>`}

  async loadResults(){const s=this.s;s.rf=s.rf||ago(6);s.rt=s.rt||today();const r=await this.call("results_summary",{date_from:s.rf,date_to:s.rt});if(r)s.rs=r;this.render()}
  resultsHTML(){const s=this.s,d=s.data,cur=d.currency,r=s.rs,lab={redeemed:["paid","Paid"],won:["unpaid","Unpaid"],active:["pending","Pending"]};
    const badge=x=>`<span class="st ${(lab[x]||["pending",x])[0]}">${(lab[x]||["",x])[1]}</span>`;
    const form=`<div class="card"><h3>Enter draw results</h3><div class="row"><select id="rg">${d.all_games.map(g=>`<option value="${g.id}">${esc(g.name)}</option>`).join("")}</select><input type="date" id="rd" value="${today()}"></div>
      <div class="row"><input id="r1" maxlength="4" placeholder="1st" size="5" inputmode="numeric"><input id="r2" maxlength="4" placeholder="2nd" size="5" inputmode="numeric"><input id="r3" maxlength="4" placeholder="3rd" size="5" inputmode="numeric"></div><button data-a="saveres">Save &amp; settle</button></div>`;
    const kc=(l,v,c="")=>`<div class="kc"><span>${l}</span><b class="${c}">${v}</b></div>`;
    const kp=r?`<div class="kpis">${kc("Winning tickets",r.totals.winners)}${kc("Prizes won ("+cur+")",fmt(r.totals.prizes))}${kc("Paid",fmt(r.totals.paid),"pos")}${kc("Unpaid liability",fmt(r.totals.unpaid),r.totals.unpaid>0?"neg":"")}</div>`:"";
    const draws=!r?`<div class="empty">Loading…</div>`:r.draws.length?`<table><tr><th>Game</th><th>Date</th><th>Numbers</th><th>Tickets</th><th>Winners</th><th>Sales</th><th>Prizes</th></tr>${r.draws.map(x=>`<tr><td>${esc(x.game_name)}</td><td>${x.date}</td><td>${x.numbers.join(" · ")}</td><td>${x.tickets}</td><td><b>${x.winners}</b></td><td>${fmt(x.sales)}</td><td>${fmt(x.prizes)}</td></tr>`).join("")}</table>`:`<div class="empty">No results entered in this range</div>`;
    const wins=r&&r.winners.length?`<h4>Winning tickets</h4><table><tr><th>Ticket</th><th>Retailer</th><th style="text-align:left">Winning plays</th><th>Prize</th><th>Status</th><th></th></tr>${r.winners.map(w=>`<tr><td>…${w.id.slice(-8)}</td><td>${esc(w.retailer)}</td><td style="text-align:left">${w.lines.map(l=>`${esc(l.game)} ${l.date.slice(5)} <b>${l.number}</b> ${esc(this.btl(l.bet_type))} → ${fmt(l.prize)}`).join("<br>")}</td><td><b>${fmt(w.prize)}</b></td><td>${badge(w.status)}</td><td>${w.status==="won"?`<button data-a="paywin" data-v="${w.id}">Pay</button>`:""}</td></tr>`).join("")}</table>`:"";
    return form+`<div class="card" style="grid-column:1/-1"><h3>Draws &amp; winners</h3><div class="row"><input type="date" id="rf" value="${s.rf||ago(6)}"><input type="date" id="rt" value="${s.rt||today()}"><button data-a="loadrs">Show</button></div>${kp}${draws}${wins}</div>`}
  reportsHTML(){const s=this.s,r=s.report,c=s.data.currency,kc=(l,v,cl="")=>`<div class="kc"><span>${l}</span><b class="${cl}">${v}</b></div>`;
    const head=`<div class="card" style="grid-column:1/-1"><h3>Sales &amp; liability report</h3><div class="row"><input type="date" id="f" value="${s.rpf||today()}"><input type="date" id="t" value="${s.rpt||today()}"><button data-a="runreport">Run</button><button class="ghost" data-a="printreport">Print</button><button class="ghost" data-a="csv">Download CSV</button><small style="color:var(--mut)">by draw date</small></div>`;
    if(!r)return head+`<div class="empty">Pick dates and press Run</div></div>`;const T=r.totals;
    return head+`<div class="kpis">${kc("Tickets sold",T.tickets)}${kc("Cancelled",T.cancelled)}${kc("Plays",T.lines)}${kc("Sales ("+c+")",fmt(T.sales))}${kc("Commission",fmt(T.commission))}${kc("Prizes won",fmt(T.prizes))}${kc("Prizes paid",fmt(T.paid),"pos")}${kc("Unpaid liability",fmt(T.unpaid),T.unpaid>0?"neg":"")}${kc("Open exposure",fmt(T.exposure))}${kc("Net",fmt(T.net),T.net>=0?"pos":"neg")}</div>
      <p class="note">Open exposure = the most you could owe on draws that have no results yet if every open play won.</p>
      <h4>By retailer</h4><table><tr><th>Retailer</th><th>Tickets</th><th>Plays</th><th>Sales</th><th>Comm.</th><th>Prizes</th><th>Unpaid</th><th>Net</th></tr>${r.rows.map(x=>`<tr><td>${esc(x.retailer)}</td><td>${x.tickets}</td><td>${x.lines}</td><td>${fmt(x.sales)}</td><td>${fmt(x.commission)}</td><td>${fmt(x.prizes)}</td><td>${fmt(x.unpaid)}</td><td class="${x.net>=0?"pos":"neg"}">${fmt(x.net)}</td></tr>`).join("")}</table>
      <h4>By game</h4>${r.games.length?`<table><tr><th>Game</th><th>Tickets</th><th>Sales</th><th>Prizes</th><th>Net</th></tr>${r.games.map(x=>`<tr><td>${esc(x.game)}</td><td>${x.tickets}</td><td>${fmt(x.sales)}</td><td>${fmt(x.prizes)}</td><td class="${x.net>=0?"pos":"neg"}">${fmt(x.net)}</td></tr>`).join("")}</table>`:`<div class="empty">No sales in this range</div>`}</div>`}
  subTabs(){const s=this.s,t=[["games","mdi:calendar-clock","Games & schedule"],["brand","mdi:palette-outline","Branding & message"],["ticket","mdi:receipt-text-outline","Ticket design"],["promos","mdi:gift-outline","Promotions"],["results","mdi:trophy-outline","Results & winners"],["reports","mdi:chart-box-outline","Reports"],["retailers","mdi:store-outline","Retailers"]];
    return `<div class="subtabs">${t.map(x=>`<button class="${s.sub===x[0]?"on":""}" data-a="sub" data-v="${x[0]}"><ha-icon icon="${x[1]}"></ha-icon>${x[2]}</button>`).join("")}</div>`}
  officeBody(){const f={games:()=>this.gamesCard()+this.btCard()+this.addGameCard(),brand:()=>this.brandCard()+this.tickerCard(),ticket:()=>this.designCard(),promos:()=>this.promosCard(),results:()=>this.resultsHTML(),reports:()=>this.reportsHTML(),retailers:()=>this.retailersCard()};return (f[this.s.sub]||f.games)()}
  tickerCard(){const t=this.s.data.settings.ticker||{},cols=[["#39ff14","Green"],["#ffb000","Amber"],["#ff3b3b","Red"],["#ffffff","White"],["#22d3ee","Cyan"]];return `<div class="card"><h3>Scrolling message</h3>
    <div class="row"><input id="tt" value="${esc(t.text)}" style="flex:1;min-width:220px" maxlength="200" placeholder="Message for the scrolling display"></div>
    <div class="row"><label>Speed <select id="ts">${[1,2,3,4,5,6,7,8,9,10].map(n=>`<option ${n===t.speed?"selected":""}>${n}</option>`).join("")}</select></label>
    <label>Color <select id="tc">${cols.map(c=>`<option value="${c[0]}" ${c[0]===t.color?"selected":""}>${c[1]}</option>`).join("")}</select></label>
    <label><input type="checkbox" id="te" ${t.enabled?"checked":""}> Show on screen</label></div><button data-a="saveticker">Save message</button></div>`}
  gamesCard(){const d=this.s.data;return `<div class="card" style="grid-column:1/-1"><h3>Games &amp; draw schedule</h3><div class="gl">${d.all_games.map(g=>`<div class="gcard" data-id="${g.id}" style="--c:${g.color}">
    <div class="row"><input class="f-name" value="${esc(g.name)}" style="flex:1;min-width:120px"><input type="color" class="f-color" value="${g.color}"><label><input type="checkbox" class="f-en" ${g.enabled!==false?"checked":""}> Show on sell screen</label></div>
    <div class="row"><label>Opens <input type="time" class="f-open" value="${g.open_time}"></label><label>Cut-off <input type="time" class="f-cut" value="${g.cutoff}"></label><label>Draw <input type="time" class="f-draw" value="${g.draw_time}"></label></div>
    <div class="row">${DAYS.map((n,i)=>`<label class="chip"><input type="checkbox" class="f-day" value="${i}" ${!g.draw_days?.length||g.draw_days.includes(i)?"checked":""}> ${n}</label>`).join("")}</div>
    <div class="row">${d.all_bet_types.map(b=>`<label class="chip"><input type="checkbox" class="f-bt" value="${b.key}" ${!g.bet_types.length||g.bet_types.includes(b.key)?"checked":""}> ${b.label}</label>`).join("")}</div>
    <div class="row"><input type="file" class="f-file" data-id="${g.id}" accept="image/*" style="max-width:190px"><button class="ghost" data-a="glogoclear" data-v="${g.id}">Remove logo</button><span style="flex:1"></span><button data-a="savegame" data-v="${g.id}">Save</button><button class="ghost dng" data-a="delgame" data-v="${g.id}">Delete</button></div></div>`).join("")}</div></div>`}
  btCard(){const d=this.s.data;return `<div class="card" style="grid-column:1/-1"><h3>Bet types &amp; payouts</h3><table><tr><th>Type</th><th>Label</th><th>Payout ×</th><th>On</th><th></th></tr>${d.all_bet_types.map(b=>`<tr class="btr" data-k="${b.key}"><td>${b.digits} digits · ${b.mode}</td><td><input class="b-label" value="${esc(b.label)}" style="width:130px"></td><td><input class="b-mult" type="number" step="any" value="${b.multiplier}" style="width:90px"></td><td><input type="checkbox" class="b-en" ${b.enabled!==false?"checked":""}></td><td><button data-a="savebt" data-v="${b.key}">Save</button></td></tr>`).join("")}</table></div>`}
  brandCard(){const s=this.s,st=s.data.settings,logo=s.logoDraft!==undefined?s.logoDraft:st.logo;return `<div class="card"><h3>Branding</h3><div class="row"><input id="bn" value="${esc(s.nameDraft??st.name)}" placeholder="Lottery name" style="flex:1" maxlength="40"></div>
      <div class="row">${logo?`<img class="prev" src="${logo}">`:`<span style="color:#94a3b8">No logo yet</span>`}<input type="file" id="logofile" accept="image/*"><button class="ghost" data-a="clearlogo">Remove logo</button></div>
      <button data-a="savebrand">Save branding</button></div>`}
  addGameCard(){return `<div class="card"><h3>Add game</h3><div class="row"><input id="gn" placeholder="Name"><input id="gc" type="color" value="#64748b"><label>Draw <input id="gt" type="time" value="13:00"></label><label>Cut-off <input id="gk" type="time" value="12:45"></label></div>
      <div class="row"><input type="file" id="gfile" accept="image/*"><input id="gl" placeholder="or logo URL (/local/...)" style="flex:1"><button data-a="addgame">Add</button></div></div>`}
  retailersCard(){const d=this.s.data;return `<div class="card" style="grid-column:1/-1"><h3>Retailers</h3><table><tr><th>Name</th><th>Commission %</th><th>Active</th><th></th></tr>${d.all_retailers.map(r=>`<tr class="rtr" data-id="${r.id}"><td><input class="r-name" value="${esc(r.name)}"></td><td><input class="r-com" type="number" step="any" min="0" max="100" value="${r.commission}" style="width:90px"></td><td><input class="r-act" type="checkbox" ${r.active!==false?"checked":""}></td><td><button data-a="saveret" data-v="${r.id}">Save</button></td></tr>`).join("")}</table></div>
    <div class="card"><h3>Add retailer</h3><div class="row"><input id="rn" placeholder="Name"><input id="rc" type="number" placeholder="Commission %" value="10" style="width:120px"><button data-a="addret">Add</button></div></div>`}
  promosCard(){const s=this.s,list=s.data.promotions||[],games=s.data.all_games||[],cur=s.data.currency||"";
    const trigLabel={min_plays:"Min. plays",min_games:"Min. distinct games",min_amount:"Min. purchase amount",min_lines:"Min. plays"};
    const gameChecks=(sel,cls)=>games.map(g=>`<label class="chip"><input type="checkbox" class="${cls}" value="${esc(g.id)}" ${(sel||[]).includes(g.id)?"checked":""}> ${esc(g.name)}</label>`).join("")||`<span class="note">No games defined</span>`;
    const scopeTxt=p=>{const g=p.games||[];return g.length?g.map(id=>games.find(x=>x.id===id)?.name||id).join(", "):"All games"};
    const cards=list.map(p=>{
      const trig=p.trigger==="min_lines"?"min_plays":(p.trigger||"min_plays");
      const valLabel=trig==="min_amount"?`${cur} ${Number(p.trigger_value).toFixed(2)}`:p.trigger_value;
      return `<div class="promo-card" data-pid="${esc(p.id)}">
      <h4><ha-icon icon="mdi:gift-outline"></ha-icon> ${esc(p.name)} ${p.enabled!==false?`<span class="st paid">ON</span>`:`<span class="st unpaid">OFF</span>`}</h4>
      <div class="meta">${trigLabel[trig]||trig}: <b>${valLabel}</b> · scope: ${esc(scopeTxt(p))} · ${p.code_digits||6}-digit code${Number(p.prize)>0?` · prize <b>${cur} ${Number(p.prize).toFixed(2)}</b>`:""}${(p.start_at||p.end_at)?` · ${p.start_at?esc(p.start_at):"…"} → ${p.end_at?esc(p.end_at):"…"}`:""}</div>
      <div class="row"><label>Name <input class="p-name" value="${esc(p.name)}" style="width:180px"></label>
        <label>Trigger <select class="p-trig">
          <option value="min_plays" ${trig==="min_plays"?"selected":""}>Min. plays (lines)</option>
          <option value="min_games" ${trig==="min_games"?"selected":""}>Min. distinct games</option>
          <option value="min_amount" ${trig==="min_amount"?"selected":""}>Min. purchase amount (${cur})</option>
        </select></label>
        <label>Value <input class="p-val" type="number" step="any" min="0" value="${p.trigger_value}" style="width:90px"></label>
        <label>Digits <input class="p-dig" type="number" min="4" max="10" value="${p.code_digits||6}" style="width:70px"></label></div>
      <div class="row"><span class="note" style="width:100%">Games in this promo (none selected = entire ticket / all games):</span>${gameChecks(p.games||[],"p-game")}</div>
      <div class="row"><label>Start <input class="p-start" type="datetime-local" value="${esc((p.start_at||"").replace(" ","T").slice(0,16))}"></label>
        <label>End <input class="p-end" type="datetime-local" value="${esc((p.end_at||"").replace(" ","T").slice(0,16))}"></label>
        <label>Prize (${cur}) <input class="p-prize" type="number" step="any" min="0" value="${Number(p.prize)||0}" style="width:100px" title="Prize amount for winners who check the code on the website"></label></div>
      <div class="row"><input class="p-label" placeholder="Label on ticket" value="${esc(p.label||"")}" style="flex:1" maxlength="80"></div>
      <div class="row"><input class="p-instr" placeholder="Instruction under the code" value="${esc(p.instruction||"")}" style="flex:1" maxlength="200"></div>
      <div class="row"><input class="p-url" placeholder="URL" value="${esc(p.url||"")}" style="flex:1" maxlength="120">
        <label class="chip"><input type="checkbox" class="p-en" ${p.enabled!==false?"checked":""}> Enabled</label>
        <button data-a="savepromo" data-v="${esc(p.id)}">Save</button>
        <button class="ghost" data-a="delpromo" data-v="${esc(p.id)}">Delete</button></div>
      <div class="note">Preview on ticket:</div>
      <div class="paper" style="width:58mm;margin:8px 0">${this.promoBlockHTML({label:p.label,code:String(Math.floor(Math.random()*1e6)).padStart(p.code_digits||6,"0").slice(-(p.code_digits||6)),instruction:p.instruction})}</div>
    </div>`}).join("")||`<div class="empty">No promotions yet — create one below</div>`;
    return `<div class="card" style="grid-column:1/-1"><h3>Promotions</h3>
      <p class="note">When a ticket meets a trigger within the start/end window, a unique code is printed under the plays. Set a prize so winners who visit the promo URL can see what they won. Choose which games count, then set plays, distinct games, or total stake.</p>
      ${cards}
      <h3>Add promotion</h3>
      <div class="row"><input id="pn" placeholder="Name (e.g. Buy 3 Diario)" style="flex:1;min-width:160px" maxlength="60">
        <select id="pt">
          <option value="min_plays">Min. plays (lines)</option>
          <option value="min_games">Min. distinct games</option>
          <option value="min_amount">Min. purchase amount (${cur})</option>
        </select>
        <input id="pv" type="number" step="any" min="0" value="3" style="width:90px" title="Trigger value">
        <input id="pd" type="number" min="4" max="10" value="6" style="width:70px" title="Code digits"></div>
      <div class="row"><span class="note" style="width:100%">Games in this promo (none = all games on the ticket):</span>${gameChecks([],"n-game")}</div>
      <div class="row"><label>Start <input id="ps" type="datetime-local"></label>
        <label>End <input id="pe" type="datetime-local"></label>
        <label>Prize (${cur}) <input id="pp" type="number" step="any" min="0" value="0" style="width:100px" title="Prize for winners who check the code on the website"></label></div>
      <div class="row"><input id="pl" placeholder="Label on ticket" value="Qualified for promotion" style="flex:1" maxlength="80"></div>
      <div class="row"><input id="pi" placeholder="Instruction" value="Visit www.shocolottery.com and check if you have won" style="flex:1" maxlength="200"></div>
      <div class="row"><input id="pu" placeholder="URL" value="https://www.shocolottery.com" style="flex:1" maxlength="120">
        <button data-a="addpromo">Create promotion</button></div>
      <p class="note">Leave start/end empty for no time limit. Prize is the amount shown when a player checks their promo code on the website.</p>
    </div>`}
  promoBlockHTML(p){return `<div class="promo-block" style="border:1.5px dashed #000;padding:6px 4px;margin:6px 0;text-align:center;color:#000;font-family:monospace">
      <div style="font-size:0.9em;text-transform:uppercase;letter-spacing:.04em">${esc(p.label||"Qualified for promotion")}</div>
      <div style="font-size:1.55em;font-weight:900;letter-spacing:.18em;margin:4px 0">${esc(p.code||"000000")}</div>
      <div style="font-size:0.82em;line-height:1.25;margin-top:4px">${esc(p.instruction||"Visit www.shocolottery.com and check if you have won")}</div>
    </div>`}
    designDefaults(){return {font:"mono",size:12,width:72,align:"center",header:"",footer:"Good luck!",show_logo:true,logo_height:40,show_name:true,show_retailer:true,show_datetime:true,bold_total:true,show_barcode:true,show_qr:false,qr_size:28,qr_prefix:""}}
  saved(){return {...this.designDefaults(),...(this.s.data.settings.ticket||{})}}
  design(){return this.s.design||(this.s.design={...this.saved()})}
  designCard(){const d=this.design(),chk=(k,l)=>`<label class="chip"><input type="checkbox" class="d-f" data-k="${k}" ${d[k]?"checked":""}> ${l}</label>`,opt=(arr,cur)=>arr.map(a=>`<option value="${a[0]}" ${String(cur)===String(a[0])?"selected":""}>${a[1]}</option>`).join("");
    return `<div class="card"><h3>Ticket layout</h3>
    <div class="row"><label>Font <select class="d-f" data-k="font">${opt([["mono","Monospace (thermal)"],["sans","Sans-serif"],["serif","Serif"],["condensed","Condensed"]],d.font)}</select></label>
      <label>Size <input class="d-f" data-k="size" type="number" min="9" max="18" value="${d.size}" style="width:70px"></label>
      <label>Paper <select class="d-f" data-k="width">${opt([[48,"48 mm"],[58,"58 mm"],[72,"72 mm"],[80,"80 mm"]],d.width)}</select></label>
      <label>Align <select class="d-f" data-k="align">${opt([["center","Center"],["left","Left"]],d.align)}</select></label></div>
    <div class="row">${chk("show_logo","Logo on top")}${chk("show_name","Lottery name")}${chk("show_retailer","Retailer")}${chk("show_datetime","Date &amp; time")}${chk("bold_total","Bold total")}</div>
    <div class="row"><label>Logo height <input class="d-f" data-k="logo_height" type="number" min="20" max="80" value="${d.logo_height||40}" style="width:70px"> px</label>
      <span class="note">Uses the branding logo. Toggle &quot;Logo on top&quot; to show it at the top of every ticket.</span></div>
    <div class="row"><input class="d-f" data-k="header" placeholder="Header text (under the name)" value="${esc(d.header)}" maxlength="120" style="flex:1"></div>
    <div class="row"><input class="d-f" data-k="footer" placeholder="Footer text" value="${esc(d.footer)}" maxlength="200" style="flex:1"></div>
    <h3>Scan codes</h3><div class="row">${chk("show_barcode","Barcode (Code 39)")}${chk("show_qr","QR code")}<label>QR size <input class="d-f" data-k="qr_size" type="number" min="15" max="45" value="${d.qr_size}" style="width:70px"> mm</label></div>
    <div class="row"><input class="d-f" data-k="qr_prefix" placeholder="Optional text before the ticket number inside the QR" value="${esc(d.qr_prefix)}" maxlength="40" style="flex:1"></div>
    <p class="note">Barcode scanners and 2D/QR scanners type the code into the scan box on the Sell screen. The ticket number is read from the end of the code, so a prefix is fine.</p>
    <div class="row"><button data-a="savedesign">Save ticket layout</button><button class="ghost" data-a="resetdesign">Reset</button><button class="ghost" data-a="testprint">Print test ticket</button></div></div>
    <div class="card"><h3>Preview</h3><div id="prev" class="paper"></div></div>`}
  sampleTicket(){const d=this.s.data,g=d.all_games,b=d.all_bet_types,gm=i=>g[i%g.length]?.id,bt=i=>b[i%b.length]?.key;
    const lines=[{game:gm(0),bet_type:bt(0),number:"1234".slice(0,b[0]?.digits||4),amount:2.5,date:today()},{game:gm(1),bet_type:bt(2),number:"56".padEnd(b[2%b.length]?.digits||2,"7").slice(0,b[2%b.length]?.digits||2),amount:1,date:today()}];
    const promos=(d.promotions||[]).filter(p=>p.enabled!==false).slice(0,1).map(p=>({id:p.id,name:p.name,code:"1".repeat(p.code_digits||6).replace(/./g,(_,i)=>String((i*3+7)%10)),label:p.label,instruction:p.instruction,url:p.url,prize:p.prize||0}));
    return {id:"261022000112345678",retailer_name:d.retailers[0]?.name||"Retailer",created:new Date(Date.now()-new Date().getTimezoneOffset()*6e4).toISOString(),lines,total:3.5,promotions:promos}}
  refreshPreview(){const p=this.shadowRoot.querySelector("#prev");if(!p)return;const d=this.design();p.style.width=d.width+"mm";p.innerHTML=this.receiptInner(this.sampleTicket(),"TICKET",d)}
  receiptInner(t,title,d){const st=this.s.data.settings,c=this.s.data.currency,al=d.align==="left"?"left":"center",
      fam={mono:'"Courier New",monospace',sans:"Arial,Helvetica,sans-serif",serif:"Georgia,serif",condensed:'"Arial Narrow","Roboto Condensed",Arial,sans-serif'}[d.font]||"monospace",
      row=l=>`<div style="display:flex;justify-content:space-between;gap:6px"><span>${esc(this.gn(l.game))} ${l.date.slice(5)}</span><span>${l.number} ${esc(this.btl(l.bet_type))}</span><b>${fmt(l.amount)}</b></div>`,
      hr='<hr style="border:0;border-top:1px dashed #000;margin:4px 0">';
    return `<div style="font:${d.size}px/1.35 ${fam};width:${d.width-4}mm;margin:0 auto;color:#000">`
      +(d.show_logo&&st.logo?`<div style="text-align:${al}"><img src="${st.logo}" style="max-height:${d.logo_height||40}px;max-width:100%"></div>`:"")
      +(d.show_name?`<div style="text-align:${al};font-weight:bold;font-size:${d.size+3}px">${esc(st.name)}</div>`:"")
      +(d.header?`<div style="text-align:${al}">${esc(d.header)}</div>`:"")
      +`<div style="text-align:${al};font-weight:bold;margin:4px 0">${esc(title)}</div>`
      +(d.show_retailer?`<div>${esc(t.retailer_name||"")}</div>`:"")+(d.show_datetime?`<div>${t.created.replace("T"," ").slice(0,16)}</div>`:"")
      +hr+t.lines.map(row).join("")+hr
      +(t.promotions&&t.promotions.length?t.promotions.map(p=>`<div class="promo-block" style="border:1.5px dashed #000;padding:6px 4px;margin:6px 0;text-align:center"><div class="plabel" style="font-size:0.9em;text-transform:uppercase;letter-spacing:.04em">${esc(p.label||"Qualified for promotion")}</div><div class="pcode" style="font-size:1.55em;font-weight:900;letter-spacing:.18em;margin:4px 0">${esc(p.code)}</div><div class="pinstr" style="font-size:0.82em;line-height:1.25;margin-top:4px">${esc(p.instruction||"Visit www.shocolottery.com and check if you have won")}</div></div>`).join(""):"")
      +`<div style="display:flex;justify-content:space-between;${d.bold_total?`font-weight:bold;font-size:${d.size+3}px`:""}"><span>TOTAL ${c}</span><span>${fmt(t.total)}</span></div>`
      +(d.show_barcode?`<div style="margin-top:8px">${barcode(t.id)}</div>`:"")
      +(d.show_qr?`<div style="margin-top:8px"><div style="width:${d.qr_size}mm;max-width:100%;margin:0 auto">${qrSVG((d.qr_prefix||"")+t.id)}</div></div>`:"")
      +`<div style="text-align:center;font-size:${Math.max(8,d.size-1)}px">${t.id}</div>`
      +(d.footer?`<div style="text-align:center;margin-top:6px">${esc(d.footer)}</div>`:"")+`</div>`}

  paint(){const s=this.s,q=x=>this.shadowRoot.querySelector(x);if(s.tab!=="sell"||!q("#num"))return;const bt=this.bt(),cur=s.data.currency;if(!bt)return;
    q("#num").innerHTML=`<small>${bt.label}</small>`+Array.from({length:bt.digits},(_,i)=>`<span class="dg ${s.num[i]?"f":""}">${s.num[i]||""}</span>`).join("");
    q("#amt").innerHTML=`<small>Amount ${cur}</small><span class="amtv">${s.amt||"0"}</span>`;
    q("#num").classList.toggle("act",s.field==="num");q("#amt").classList.toggle("act",s.field==="amt");
    const col=k=>s.data.all_games.find(g=>g.id===k)?.color||"#64748b";
    q("#lines").innerHTML=s.lines.map((l,i)=>`<div class="ln ${s.editIdx===i?"editing":""}" data-a="edit" data-i="${i}"><i style="background:${col(l.game)}"></i><b>${l.number}</b><span>${this.btl(l.bet_type)}<small>${this.gn(l.game)} · ${l.date.slice(5)}</small></span><em>${fmt(l.amount)}</em><button class="ed" data-a="edit" data-i="${i}" title="Edit">✎</button><button data-a="del" data-i="${i}" title="Remove">✕</button></div>`).join("")||`<div class="empty">🎟️<br>No plays yet</div>`;
    q("#cnt").textContent=s.lines.length;q("#tot").textContent=`${cur} ${fmt(s.lines.reduce((a,l)=>a+l.amount,0))}`}

  onKey(e){const s=this.s;if(!s.data||s.tab!=="sell"||e.composedPath()[0]?.tagName==="INPUT"||e.composedPath()[0]?.tagName==="SELECT")return;
    if(/^\d$/.test(e.key))this.key(e.key);else if(e.key==="Backspace")this.key("DEL");else if(e.key==="Enter"){e.preventDefault();this.add()}else if(e.key==="Tab"){e.preventDefault();s.field=s.field==="num"?"amt":"num";this.paint()}}
  key(k){const s=this.s,f=s.field,bt=this.bt();if(!bt)return;if(s.fresh?.[f]){s.fresh[f]=false;if(k!=="CLR"&&k!=="DEL")s[f]=""}
    if(k==="CLR")s[f]="";else if(k==="DEL")s[f]=s[f].slice(0,-1);
    else if(f==="num"){if(s.num.length<bt.digits)s.num+=k;if(s.num.length===bt.digits)s.field="amt"}
    else if(s.amt.length<7)s.amt=(s.amt==="0"?"":s.amt)+k;
    this.paint()}
  add(){const s=this.s,bt=this.bt(),amt=parseFloat(s.amt);if(!bt)return this.toast("No bet type available",1);
    if(s.num.length!==bt.digits)return this.toast(`${bt.label} needs ${bt.digits} digits`,1);
    if(!(amt>0))return this.toast("Enter an amount",1);
    if(s.editIdx!=null){s.lines[s.editIdx]={game:s.sel[0],bet_type:bt.key,number:s.num,amount:amt,date:s.date};s.editIdx=null;s.fresh=null;s.num="";s.field="num";this.toast("Play updated");return this.render()}
    for(const g of s.sel)s.lines.push({game:g,bet_type:bt.key,number:s.num,amount:amt,date:s.date});
    s.num="";s.field="num";this.paint()}

  async act(a,ds){const s=this.s;
    switch(a){
      case "theme":s.dark=!s.dark;try{localStorage.setItem("lottery_pos_dark",s.dark?"1":"0")}catch(e){}this.render();break;
      case "tab":{
        if(ds.v==="sell"&&!this._posTerminal){
          const url=new URL(location.href);
          url.hash="pos-terminal";
          const w=window.open(url.toString(),"lottery_pos_terminal","noopener,noreferrer");
          if(w){
            try{w.moveTo(0,0);w.resizeTo(screen.availWidth,screen.availHeight)}catch(e){}
            this.toast("POS terminal opened in a new window");
          }else{
            this.toast("Allow pop-ups to open the full-screen POS",1);
            s.tab="sell";this.render();
          }
          break;
        }
        s.tab=ds.v;this.render();break;
      }
      case "game":s.sel=s.sel.includes(ds.v)?(s.sel.length>1?s.sel.filter(x=>x!==ds.v):s.sel):[...s.sel,ds.v];this.render();break;
      case "bt":s.bt=ds.v;s.num=s.num.slice(0,this.bt().digits);s.field="num";this.render();break;
      case "field":s.field=ds.v;this.paint();break;
      case "key":this.key(ds.v);break;
      case "preset":s.amt=ds.v;if(s.fresh)s.fresh.amt=false;s.field="num";this.paint();break;
      case "add":this.add();break;
      case "quick":{const n=this.bt().digits;s.num=Array.from({length:n},()=>Math.floor(Math.random()*10)).join("");s.field="amt";this.paint();break}
      case "clear":s.lines=[];s.editIdx=null;s.fresh=null;this.render();break;
      case "del":{const i=+ds.i;s.lines.splice(i,1);if(s.editIdx===i){s.editIdx=null;s.fresh=null;s.num=""}else if(s.editIdx>i)s.editIdx--;this.render();break}
      case "edit":{const l=s.lines[+ds.i];if(!l)break;s.editIdx=+ds.i;s.sel=[l.game];s.bt=l.bet_type;s.num=l.number;s.amt=String(l.amount);s.date=l.date;s.field="num";s.fresh={num:true,amt:true};this.render();break}
      case "canceledit":s.editIdx=null;s.fresh=null;s.num="";s.amt="";s.field="num";this.render();break;
      case "copy":{const l=s.lines[s.lines.length-1];if(l){s.num=l.number;s.field="amt";this.paint()}break}
      case "send":{if(!s.lines.length)return this.toast("Ticket is empty",1);
        const t=await this.call("sell",{retailer_id:s.retailer,lines:s.lines});if(!t)break;
        s.lines=[];s.editIdx=null;s.fresh=null;s.data=await this.ws("state");this.print(this.receipt(t,"TICKET"));this.toast(`Sold ${t.id}`);this.render();break}
      case "last":{const t=await this.call("last",{retailer_id:s.retailer});if(t)this.print(this.receipt(t,"REPRINT"));break}
      case "replay":{const t=await this.call("last",{retailer_id:s.retailer});if(t)this.load(t);break}
      case "cancel":{const id=await this.modal({title:"Cancel ticket",input:"Scan or type ticket number",ok:"Cancel ticket"});if(!id)break;const t=await this.call("cancel",{ticket_id:(String(id).match(/\d{12,}$/)||[String(id)])[0]});if(t){this.print(this.receipt(t,"CANCELLATION RECEIPT"));this.toast("Ticket cancelled")}break}
      case "redeem":{const id=await this.modal({title:"Pay winner",input:"Scan or type ticket number",ok:"Check ticket"});if(id)this.scanned(id);break}
      case "results":{const r=await this.call("draw_results",{date:s.date});if(r)this.print(`<html><body style="font:13px monospace;width:72mm"><h3>RESULTADO ${s.date}</h3>${r.map(x=>`<p><b>${x.game}</b><br>${x.numbers.join(" - ")}</p>`).join("")||"No results yet"}</body></html>`);break}
      case "report1":{const t=today(),r=await this.call("report",{date_from:t,date_to:t});if(r)this.print(this.reportHTML(r));break}
      case "savegame":{const c=this.shadowRoot.querySelector(`.gcard[data-id="${ds.v}"]`),v=x=>c.querySelector(x),all=[...c.querySelectorAll(".f-bt")],pick=all.filter(i=>i.checked).map(i=>i.value);
        if(!pick.length)return this.toast("Pick at least one bet type",1);const days=[...c.querySelectorAll(".f-day")].filter(i=>i.checked).map(i=>+i.value);if(!days.length)return this.toast("Pick at least one draw day",1);
        const msg={game_id:String(ds.v),name:v(".f-name").value,color:v(".f-color").value,enabled:v(".f-en").checked,open_time:v(".f-open").value,cutoff:v(".f-cut").value,draw_time:v(".f-draw").value,bet_types:pick.length===all.length?[]:pick,draw_days:days.length===7?[]:days};
        if(s.glogos[ds.v]!==undefined)msg.logo=s.glogos[ds.v];
        if(await this.call("update_game",msg)){delete s.glogos[ds.v];s.data=await this.ws("state");this.toast("Game saved");this.render()}break}
      case "glogoclear":s.glogos[ds.v]="";this.toast("Logo is removed when you press Save");break;
      case "delgame":{if(!await this.modal({title:"Delete game?",text:"Only possible if it has no sales. Otherwise hide it instead.",ok:"Delete"}))break;if(await this.call("delete_game",{game_id:String(ds.v)})){s.data=await this.ws("state");this.toast("Game deleted");this.render()}break}
      case "savebt":{const r=this.shadowRoot.querySelector(`.btr[data-k="${ds.v}"]`);if(await this.call("update_bet_type",{key:ds.v,label:r.querySelector(".b-label").value,multiplier:+r.querySelector(".b-mult").value,enabled:r.querySelector(".b-en").checked})){s.data=await this.ws("state");this.toast("Bet type saved");this.render()}break}
      case "saveticker":{const q=x=>this.shadowRoot.querySelector(x);if(await this.call("set_ticker",{text:q("#tt").value,enabled:q("#te").checked,speed:+q("#ts").value,color:q("#tc").value})){s.data=await this.ws("state");this.toast("Message saved");this.render()}break}
      case "clearlogo":s.nameDraft=this.shadowRoot.querySelector("#bn")?.value;s.logoDraft="";this.render();break;
      case "savebrand":{const q=x=>this.shadowRoot.querySelector(x).value;const logo=s.logoDraft!==undefined?s.logoDraft:s.data.settings.logo;if(await this.call("set_branding",{name:q("#bn"),logo})){s.data=await this.ws("state");s.logoDraft=undefined;s.nameDraft=undefined;this.toast("Branding saved");this.render()}break}
      case "saveres":{const q=x=>this.shadowRoot.querySelector(x).value;const dt=q("#rd"),r=await this.call("set_results",{game:q("#rg"),date:dt,numbers:[q("#r1"),q("#r2"),q("#r3")].filter(Boolean)});if(r){this.toast(`Settled - ${r.winners.length} winning ticket(s)`);s.rf=!s.rf||dt<s.rf?dt:s.rf;s.rt=!s.rt||dt>s.rt?dt:s.rt;await this.loadResults()}break}
      case "runreport":case "printreport":{const q=x=>this.shadowRoot.querySelector(x).value;s.rpf=q("#f");s.rpt=q("#t");const r=await this.call("report",{date_from:s.rpf,date_to:s.rpt});if(!r)break;s.report=r;if(a==="printreport")this.print(this.reportHTML(r));else this.render();break}
      case "csv":{const r=s.report;if(!r)return this.toast("Run the report first",1);const L=[["Retailer","Tickets","Plays","Sales","Commission","Prizes","Paid","Unpaid","Net"],...r.rows.map(x=>[x.retailer,x.tickets,x.lines,x.sales,x.commission,x.prizes,x.paid,x.unpaid,x.net]),[],["Game","Tickets","Sales","Prizes","Net"],...r.games.map(x=>[x.game,x.tickets,x.sales,x.prizes,x.net]),[],["Totals"],...Object.entries(r.totals)];const csv=L.map(row=>row.map(v=>`"${String(v).replace(/"/g,'""')}"`).join(",")).join("\n"),el=document.createElement("a");el.href=URL.createObjectURL(new Blob([csv],{type:"text/csv"}));el.download=`lottery-report-${r.from}_${r.to}.csv`;el.click();break}
      case "sub":s.sub=ds.v;if(ds.v==="results"&&!s.rs)await this.loadResults();else this.render();break;
      case "loadrs":{const q=x=>this.shadowRoot.querySelector(x).value;s.rf=q("#rf");s.rt=q("#rt");await this.loadResults();break}
      case "paywin":{if(!await this.modal({title:"Pay prize",text:`Ticket ${ds.v}`,ok:"Mark as paid"}))break;const r=await this.call("redeem",{ticket_id:ds.v});if(r){this.print(this.receipt(r,"PAID "+fmt(r.prize)));await this.loadResults()}break}
      case "saveret":{const r=this.shadowRoot.querySelector(`.rtr[data-id="${ds.v}"]`);if(await this.call("update_retailer",{retailer_id:String(ds.v),name:r.querySelector(".r-name").value,commission:+r.querySelector(".r-com").value,active:r.querySelector(".r-act").checked})){s.data=await this.ws("state");this.toast("Retailer saved");this.render()}break}
      case "savedesign":{const r=await this.call("set_ticket_design",{design:this.design()});if(r){s.data=await this.ws("state");s.design=null;this.toast("Ticket layout saved");this.render()}break}
      case "resetdesign":s.design={...this.designDefaults()};this.render();break;
      case "testprint":{const d=this.design();this.print(this.docHTML(this.receiptInner(this.sampleTicket(),"TEST TICKET",d),d));break}
      case "addpromo":{const q=x=>this.shadowRoot.querySelector(x);
        const games=[...this.shadowRoot.querySelectorAll(".n-game:checked")].map(el=>el.value);
        const r=await this.call("add_promotion",{name:q("#pn").value,trigger:q("#pt").value,trigger_value:+q("#pv").value,code_digits:+q("#pd").value,games,label:q("#pl").value,instruction:q("#pi").value,url:q("#pu").value,enabled:true,start_at:q("#ps").value,end_at:q("#pe").value,prize:+q("#pp").value||0});
        if(r){s.data=await this.ws("state");this.toast("Promotion created");this.render()}break}
      case "savepromo":{const c=this.shadowRoot.querySelector(`.promo-card[data-pid="${ds.v}"]`);if(!c)break;
        const v=sel=>c.querySelector(sel);
        const games=[...c.querySelectorAll(".p-game:checked")].map(el=>el.value);
        const r=await this.call("update_promotion",{promotion_id:String(ds.v),name:v(".p-name").value,trigger:v(".p-trig").value,trigger_value:+v(".p-val").value,code_digits:+v(".p-dig").value,games,label:v(".p-label").value,instruction:v(".p-instr").value,url:v(".p-url").value,enabled:v(".p-en").checked,start_at:v(".p-start").value,end_at:v(".p-end").value,prize:+v(".p-prize").value||0});
        if(r){s.data=await this.ws("state");this.toast("Promotion saved");this.render()}break}
      case "delpromo":{if(!await this.modal({title:"Delete promotion",text:"Remove this promotion? Existing ticket codes stay valid.",ok:"Delete"}))break;
        const r=await this.call("delete_promotion",{promotion_id:String(ds.v)});
        if(r!==null){s.data=await this.ws("state");this.toast("Deleted");this.render()}break}
      case "addret":{const q=x=>this.shadowRoot.querySelector(x).value;if(await this.call("add_retailer",{name:q("#rn"),commission:+q("#rc")})){s.data=await this.ws("state");this.toast("Retailer added");this.render()}break}
      case "addgame":{const q=x=>this.shadowRoot.querySelector(x).value;if(await this.call("add_game",{name:q("#gn"),color:q("#gc"),draw_time:q("#gt"),cutoff:q("#gk"),logo:s.gameLogo||q("#gl")})){s.gameLogo="";s.data=await this.ws("state");this.toast("Game added");this.render()}break}
    }}

  async scanned(id){if(!id)return;id=(String(id).match(/\d{12,}$/)||[String(id)])[0];const s=this.s,cur=s.data.currency;s.scan="";
    const t=await this.call("ticket",{ticket_id:id});this.render();if(!t)return;
    if(t.status==="won"){if(await this.modal({title:"🏆 Winner!",big:`${cur} ${fmt(t.prize)}`,text:`Ticket ${t.id}`,ok:"Pay prize",tone:"win"})){const r=await this.call("redeem",{ticket_id:t.id});if(r){this.print(this.receipt(r,"PAID "+fmt(r.prize)));this.toast("Prize paid");s.data=await this.ws("state");this.render()}}}
    else if(t.status==="redeemed")this.toast("Already paid",1);
    else if(t.status==="cancelled")this.toast("Ticket was cancelled",1);
    else if(t.status==="lost"){this.load(t);this.toast("Not a winner - lines loaded to replay")}
    else{this.load(t);this.toast("Draw pending - lines loaded to replay")}}
  load(t){const s=this.s;s.tab="sell";s.editIdx=null;s.lines=t.lines.map(l=>({game:l.game,bet_type:l.bet_type,number:l.number,amount:l.amount,date:l.date<today()?s.date:l.date}));this.render();this.toast(`Replay: ${s.lines.length} line(s) loaded`)}

  docHTML(inner,d){return `<html><head><style>@page{margin:0}body{margin:0;padding:2mm;width:${d.width}mm}</style></head><body>${inner}</body></html>`}
  receipt(t,title){const d=this.saved();return this.docHTML(this.receiptInner(t,title,d),d)}
  reportHTML(r){const T=r.totals,c=this.s.data.currency,k=(l,v)=>`<tr><td>${l}</td><td align=right><b>${v}</b></td></tr>`;
    return `<html><body style="font:12px Arial,sans-serif;margin:16px"><h3>${esc(this.s.data.settings.name)} - report ${r.from} → ${r.to}</h3><table width="300">${k("Tickets sold",T.tickets)}${k("Cancelled",T.cancelled)}${k("Plays",T.lines)}${k("Sales "+c,fmt(T.sales))}${k("Commission",fmt(T.commission))}${k("Prizes won",fmt(T.prizes))}${k("Prizes paid",fmt(T.paid))}${k("Unpaid liability",fmt(T.unpaid))}${k("Open exposure",fmt(T.exposure))}${k("NET",fmt(T.net))}</table>
    <h4>By retailer</h4><table width="100%" border="0"><tr align=left><th>Retailer</th><th>Tkts</th><th>Sales</th><th>Comm</th><th>Prizes</th><th>Unpaid</th><th>Net</th></tr>${r.rows.map(x=>`<tr><td>${esc(x.retailer)}</td><td>${x.tickets}</td><td>${fmt(x.sales)}</td><td>${fmt(x.commission)}</td><td>${fmt(x.prizes)}</td><td>${fmt(x.unpaid)}</td><td>${fmt(x.net)}</td></tr>`).join("")}</table>
    <h4>By game</h4><table width="100%"><tr align=left><th>Game</th><th>Tkts</th><th>Sales</th><th>Prizes</th><th>Net</th></tr>${r.games.map(x=>`<tr><td>${esc(x.game)}</td><td>${x.tickets}</td><td>${fmt(x.sales)}</td><td>${fmt(x.prizes)}</td><td>${fmt(x.net)}</td></tr>`).join("")}</table></body></html>`}
  print(html){const w=window.open("","_blank","width=380,height=640");if(!w)return this.toast("Allow pop-ups to print",1);w.document.write(html);w.document.close();w.focus();setTimeout(()=>w.print(),300)}
}
customElements.define("lottery-pos-panel",LotteryPosPanel);
