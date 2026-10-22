/* Lottery POS panel - tablet-first retailer terminal */
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
.brand{font-weight:800;font-size:22px;letter-spacing:-.5px;margin-right:auto}
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
.ln{display:grid;grid-template-columns:8px auto 1fr auto auto;gap:10px;align-items:center;padding:10px 4px;border-bottom:1px dashed var(--line);font-size:13px;cursor:pointer;animation:pop .2s}
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
@media(max-width:900px){.main{grid-template-columns:1fr}.kpi{display:none}.acts{grid-template-columns:repeat(4,1fr)}}
@media(max-width:620px){.shell{flex-direction:column-reverse}.nav{width:100%;flex-direction:row;justify-content:space-around;padding:6px}.nav .logo{display:none}.nav button{width:auto;flex:1}#scan{width:100%}}
`;

class LotteryPosPanel extends HTMLElement{
  constructor(){super();this.attachShadow({mode:"open"});
    this.s={tab:"sell",sel:[],bt:"",date:today(),num:"",amt:"",field:"num",lines:[],retailer:"",data:null,scan:"",report:null,glogos:{}};
    this._kh=e=>this.onKey(e)}
  connectedCallback(){window.addEventListener("keydown",this._kh)}
  disconnectedCallback(){window.removeEventListener("keydown",this._kh);clearInterval(this._tm)}
  set hass(h){const first=!this._hass;this._hass=h;if(first)this.init()}
  set narrow(v){}set panel(v){}set route(v){}
  ws(type,extra={}){return this._hass.callWS({type:"lottery_pos/"+type,...extra})}
  async init(){const s=this.s;try{s.dark=localStorage.getItem("lottery_pos_dark")==="1"}catch(e){}s.data=await this.ws("state");this._tm=setInterval(()=>this.tick(),30000);s.sel=[s.data.games[0]?.id];s.bt=s.data.bet_types[0]?.key;s.retailer=s.data.retailers[0]?.id;
    this.shadowRoot.addEventListener("click",e=>{const el=e.target.closest("[data-a]");if(el)this.act(el.dataset.a,el.dataset)});this.render()}
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
    const items=[["sell","mdi:cash-register","Sell",1],["results","mdi:numeric","Results",admin],["reports","mdi:chart-box-outline","Reports",admin],["setup","mdi:cog","Setup",admin]];
    const nav=items.filter(i=>i[3]).map(i=>`<button class="${s.tab===i[0]?"on":""}" data-a="tab" data-v="${i[0]}"><ha-icon icon="${i[1]}"></ha-icon>${i[2]}</button>`).join("");
    const body=s.tab==="sell"?this.sellHTML():`<div class="office">${s.tab==="results"?this.resultsHTML():s.tab==="reports"?this.reportsHTML():this.setupHTML()}</div>`;
    this.shadowRoot.innerHTML=`<style>${CSS}</style><div class="shell"><nav class="nav"><div class="logo">${st.logo?`<img src="${st.logo}">`:esc((st.name||"L").slice(0,2).toUpperCase())}</div>${nav}</nav><div class="content"><div class="top">
      <span class="brand">${esc(st.name)}</span>
      <div class="kpi"><span>Sales today</span><b>${d.currency} ${fmt(d.summary.sales_today)}</b></div><div class="kpi"><span>Tickets</span><b>${d.summary.tickets_today}</b></div>
      <input id="scan" placeholder="Scan ticket…" value="${esc(s.scan)}" inputmode="numeric">
      <button class="ic" data-a="replay" title="Replay last ticket"><ha-icon icon="mdi:replay"></ha-icon></button>
      <select id="ret">${d.retailers.map(r=>`<option value="${r.id}" ${r.id===s.retailer?"selected":""}>${r.name}</option>`).join("")}</select>
      <button class="ic" data-a="theme" title="Dark / light"><ha-icon icon="${s.dark?"mdi:weather-sunny":"mdi:weather-night"}"></ha-icon></button></div>${this.tickerHTML()}${body}</div></div>`;
    const q=x=>this.shadowRoot.querySelector(x);
    q("#scan").oninput=e=>s.scan=e.target.value;
    q("#scan").onkeydown=e=>{if(e.key==="Enter")this.scanned(e.target.value.trim())};
    q("#ret").onchange=e=>s.retailer=e.target.value;
    if(q("#date"))q("#date").onchange=e=>s.date=e.target.value;
    if(q("#logofile"))q("#logofile").onchange=async e=>{const f=e.target.files[0];if(!f)return;try{s.nameDraft=q("#bn").value;s.logoDraft=await this.shrink(f);this.render()}catch(x){this.toast(x.message,1)}};
    if(q("#gfile"))q("#gfile").onchange=async e=>{const f=e.target.files[0];if(!f)return;try{s.gameLogo=await this.shrink(f,96);this.toast("Game logo ready - press Add")}catch(x){this.toast(x.message,1)}};
    this.shadowRoot.querySelectorAll(".f-file").forEach(inp=>inp.onchange=async e=>{const f=e.target.files[0];if(!f)return;try{s.glogos[inp.dataset.id]=await this.shrink(f,96);this.toast("Logo ready - press Save on the game")}catch(x){this.toast(x.message,1)}});
    this.paint()}

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
    <div class="entry"><div id="num" class="disp" data-a="field" data-v="num"></div><div id="amt" class="disp" data-a="field" data-v="amt"></div><button class="add" data-a="add">＋ Add to ticket</button></div>
    <div class="pads"><div class="pad">${[1,2,3,4,5,6,7,8,9,"CLR",0,"DEL"].map(k=>`<button data-a="key" data-v="${k}">${k}</button>`).join("")}</div>
      <div class="pre">${PRESETS.map(p=>`<button data-a="preset" data-v="${p}">${p}</button>`).join("")}</div></div>
    <div class="acts">${acts.map(a=>`<button data-a="${a[0]}"><ha-icon icon="${a[1]}"></ha-icon>${a[2]}</button>`).join("")}</div>
  </section><section class="right card"><div class="rhead"><h3>Current ticket</h3><span class="badge" id="cnt">0</span></div><div class="rsub">${s.sel.length} game(s) · tap a play to edit</div>
    <div id="lines"></div><div class="foot"><div><small>Total</small><div class="tot" id="tot"></div></div><button class="send" data-a="send">Send &amp; Print ▶</button></div></section></div>`}

  resultsHTML(){const d=this.s.data;return `<div class="card"><h3>Enter draw results</h3><div class="row"><select id="rg">${d.all_games.map(g=>`<option value="${g.id}">${g.name}</option>`).join("")}</select><input type="date" id="rd" value="${today()}"></div>
      <div class="row"><input id="r1" maxlength="4" placeholder="1st" size="5" inputmode="numeric"><input id="r2" maxlength="4" placeholder="2nd" size="5" inputmode="numeric"><input id="r3" maxlength="4" placeholder="3rd" size="5" inputmode="numeric"></div><button data-a="saveres">Save &amp; settle</button></div>`}
  reportsHTML(){const r=this.s.report,t=today(),c=this.s.data.currency;return `<div class="card" style="grid-column:1/-1"><h3>Settlement report</h3><div class="row"><input type="date" id="f" value="${t}"><input type="date" id="t" value="${t}"><button data-a="runreport">Run</button><button data-a="printreport">Print</button></div>
      ${r?`<div class="kpis"><div class="kc"><span>Sales</span><b>${fmt(r.totals.sales)}</b></div><div class="kc"><span>Commission</span><b>${fmt(r.totals.commission)}</b></div><div class="kc"><span>Prizes</span><b>${fmt(r.totals.prizes)}</b></div><div class="kc"><span>Net (${c})</span><b class="${r.totals.net>=0?"pos":"neg"}">${fmt(r.totals.net)}</b></div></div>
      <table><tr><th>Retailer</th><th>Tickets</th><th>Sales</th><th>Comm.</th><th>Prizes</th><th>Net</th></tr>${r.rows.map(x=>`<tr><td>${x.retailer}</td><td>${x.tickets}</td><td>${fmt(x.sales)}</td><td>${fmt(x.commission)}</td><td>${fmt(x.prizes)}</td><td class="${x.net>=0?"pos":"neg"}">${fmt(x.net)}</td></tr>`).join("")}</table>`:`<div class="empty">Pick dates and press Run</div>`}</div>`}
  setupHTML(){return this.setupBase()+this.tickerCard()+this.gamesCard()+this.btCard()}
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
  setupBase(){const s=this.s,st=s.data.settings,logo=s.logoDraft!==undefined?s.logoDraft:st.logo;return `
    <div class="card"><h3>Branding</h3><div class="row"><input id="bn" value="${esc(s.nameDraft??st.name)}" placeholder="Lottery name" style="flex:1" maxlength="40"></div>
      <div class="row">${logo?`<img class="prev" src="${logo}">`:`<span style="color:#94a3b8">No logo yet</span>`}<input type="file" id="logofile" accept="image/*"><button data-a="clearlogo">Remove logo</button></div>
      <button data-a="savebrand">Save branding</button></div>
    <div class="card"><h3>Add retailer</h3><div class="row"><input id="rn" placeholder="Name"><input id="rc" type="number" placeholder="Commission %" value="10" style="width:120px"><button data-a="addret">Add</button></div></div>
    <div class="card"><h3>Add game</h3><div class="row"><input id="gn" placeholder="Name"><input id="gc" type="color" value="#64748b"><label>Draw <input id="gt" type="time" value="13:00"></label><label>Cut-off <input id="gk" type="time" value="12:45"></label></div>
      <div class="row"><input type="file" id="gfile" accept="image/*"><input id="gl" placeholder="or logo URL (/local/...)" style="flex:1"><button data-a="addgame">Add</button></div></div>`}

  paint(){const s=this.s,q=x=>this.shadowRoot.querySelector(x);if(s.tab!=="sell"||!q("#num"))return;const bt=this.bt(),cur=s.data.currency;if(!bt)return;
    q("#num").innerHTML=`<small>${bt.label}</small>`+Array.from({length:bt.digits},(_,i)=>`<span class="dg ${s.num[i]?"f":""}">${s.num[i]||""}</span>`).join("");
    q("#amt").innerHTML=`<small>Amount ${cur}</small><span class="amtv">${s.amt||"0"}</span>`;
    q("#num").classList.toggle("act",s.field==="num");q("#amt").classList.toggle("act",s.field==="amt");
    const col=k=>s.data.all_games.find(g=>g.id===k)?.color||"#64748b";
    q("#lines").innerHTML=s.lines.map((l,i)=>`<div class="ln" data-a="edit" data-i="${i}"><i style="background:${col(l.game)}"></i><b>${l.number}</b><span>${this.btl(l.bet_type)}<small>${this.gn(l.game)} · ${l.date.slice(5)}</small></span><em>${fmt(l.amount)}</em><button data-a="del" data-i="${i}">✕</button></div>`).join("")||`<div class="empty">🎟️<br>No plays yet</div>`;
    q("#cnt").textContent=s.lines.length;q("#tot").textContent=`${cur} ${fmt(s.lines.reduce((a,l)=>a+l.amount,0))}`}

  onKey(e){const s=this.s;if(!s.data||s.tab!=="sell"||e.composedPath()[0]?.tagName==="INPUT"||e.composedPath()[0]?.tagName==="SELECT")return;
    if(/^\d$/.test(e.key))this.key(e.key);else if(e.key==="Backspace")this.key("DEL");else if(e.key==="Enter"){e.preventDefault();this.add()}else if(e.key==="Tab"){e.preventDefault();s.field=s.field==="num"?"amt":"num";this.paint()}}
  key(k){const s=this.s,f=s.field,bt=this.bt();if(!bt)return;
    if(k==="CLR")s[f]="";else if(k==="DEL")s[f]=s[f].slice(0,-1);
    else if(f==="num"){if(s.num.length<bt.digits)s.num+=k;if(s.num.length===bt.digits)s.field="amt"}
    else if(s.amt.length<7)s.amt=(s.amt==="0"?"":s.amt)+k;
    this.paint()}
  add(){const s=this.s,bt=this.bt(),amt=parseFloat(s.amt);if(!bt)return this.toast("No bet type available",1);
    if(s.num.length!==bt.digits)return this.toast(`${bt.label} needs ${bt.digits} digits`,1);
    if(!(amt>0))return this.toast("Enter an amount",1);
    for(const g of s.sel)s.lines.push({game:g,bet_type:bt.key,number:s.num,amount:amt,date:s.date});
    s.num="";s.field="num";this.paint()}

  async act(a,ds){const s=this.s;
    switch(a){
      case "theme":s.dark=!s.dark;try{localStorage.setItem("lottery_pos_dark",s.dark?"1":"0")}catch(e){}this.render();break;
      case "tab":s.tab=ds.v;this.render();break;
      case "game":s.sel=s.sel.includes(ds.v)?(s.sel.length>1?s.sel.filter(x=>x!==ds.v):s.sel):[...s.sel,ds.v];this.render();break;
      case "bt":s.bt=ds.v;s.num=s.num.slice(0,this.bt().digits);s.field="num";this.render();break;
      case "field":s.field=ds.v;this.paint();break;
      case "key":this.key(ds.v);break;
      case "preset":s.amt=ds.v;s.field="num";this.paint();break;
      case "add":this.add();break;
      case "quick":{const n=this.bt().digits;s.num=Array.from({length:n},()=>Math.floor(Math.random()*10)).join("");s.field="amt";this.paint();break}
      case "clear":s.lines=[];this.paint();break;
      case "del":s.lines.splice(+ds.i,1);this.paint();break;
      case "edit":{const l=s.lines.splice(+ds.i,1)[0];if(!l)break;s.sel=[l.game];s.bt=l.bet_type;s.num=l.number;s.amt=String(l.amount);s.date=l.date;s.field="num";this.render();break}
      case "copy":{const l=s.lines[s.lines.length-1];if(l){s.num=l.number;s.field="amt";this.paint()}break}
      case "send":{if(!s.lines.length)return this.toast("Ticket is empty",1);
        const t=await this.call("sell",{retailer_id:s.retailer,lines:s.lines});if(!t)break;
        s.lines=[];s.data=await this.ws("state");this.print(this.receipt(t,"TICKET"));this.toast(`Sold ${t.id}`);this.render();break}
      case "last":{const t=await this.call("last",{retailer_id:s.retailer});if(t)this.print(this.receipt(t,"REPRINT"));break}
      case "replay":{const t=await this.call("last",{retailer_id:s.retailer});if(t)this.load(t);break}
      case "cancel":{const id=await this.modal({title:"Cancel ticket",input:"Scan or type ticket number",ok:"Cancel ticket"});if(!id)break;const t=await this.call("cancel",{ticket_id:id});if(t){this.print(this.receipt(t,"CANCELLATION RECEIPT"));this.toast("Ticket cancelled")}break}
      case "redeem":{const id=await this.modal({title:"Pay winner",input:"Scan or type ticket number",ok:"Check ticket"});if(id)this.scanned(id);break}
      case "results":{const r=await this.call("draw_results",{date:s.date});if(r)this.print(`<html><body style="font:13px monospace;width:72mm"><h3>RESULTADO ${s.date}</h3>${r.map(x=>`<p><b>${x.game}</b><br>${x.numbers.join(" - ")}</p>`).join("")||"No results yet"}</body></html>`);break}
      case "report1":{const t=today(),r=await this.call("report",{date_from:t,date_to:t});if(r)this.print(this.reportHTML(r));break}
      case "savegame":{const c=this.shadowRoot.querySelector(`.gcard[data-id="${ds.v}"]`),v=x=>c.querySelector(x),all=[...c.querySelectorAll(".f-bt")],pick=all.filter(i=>i.checked).map(i=>i.value);
        if(!pick.length)return this.toast("Pick at least one bet type",1);const days=[...c.querySelectorAll(".f-day")].filter(i=>i.checked).map(i=>+i.value);if(!days.length)return this.toast("Pick at least one draw day",1);
        const msg={id:ds.v,name:v(".f-name").value,color:v(".f-color").value,enabled:v(".f-en").checked,open_time:v(".f-open").value,cutoff:v(".f-cut").value,draw_time:v(".f-draw").value,bet_types:pick.length===all.length?[]:pick,draw_days:days.length===7?[]:days};
        if(s.glogos[ds.v]!==undefined)msg.logo=s.glogos[ds.v];
        if(await this.call("update_game",msg)){delete s.glogos[ds.v];s.data=await this.ws("state");this.toast("Game saved");this.render()}break}
      case "glogoclear":s.glogos[ds.v]="";this.toast("Logo is removed when you press Save");break;
      case "delgame":{if(!await this.modal({title:"Delete game?",text:"Only possible if it has no sales. Otherwise hide it instead.",ok:"Delete"}))break;if(await this.call("delete_game",{id:ds.v})){s.data=await this.ws("state");this.toast("Game deleted");this.render()}break}
      case "savebt":{const r=this.shadowRoot.querySelector(`.btr[data-k="${ds.v}"]`);if(await this.call("update_bet_type",{key:ds.v,label:r.querySelector(".b-label").value,multiplier:+r.querySelector(".b-mult").value,enabled:r.querySelector(".b-en").checked})){s.data=await this.ws("state");this.toast("Bet type saved");this.render()}break}
      case "saveticker":{const q=x=>this.shadowRoot.querySelector(x);if(await this.call("set_ticker",{text:q("#tt").value,enabled:q("#te").checked,speed:+q("#ts").value,color:q("#tc").value})){s.data=await this.ws("state");this.toast("Message saved");this.render()}break}
      case "clearlogo":s.nameDraft=this.shadowRoot.querySelector("#bn")?.value;s.logoDraft="";this.render();break;
      case "savebrand":{const q=x=>this.shadowRoot.querySelector(x).value;const logo=s.logoDraft!==undefined?s.logoDraft:s.data.settings.logo;if(await this.call("set_branding",{name:q("#bn"),logo})){s.data=await this.ws("state");s.logoDraft=undefined;s.nameDraft=undefined;this.toast("Branding saved");this.render()}break}
      case "saveres":{const q=x=>this.shadowRoot.querySelector(x).value;const r=await this.call("set_results",{game:q("#rg"),date:q("#rd"),numbers:[q("#r1"),q("#r2"),q("#r3")].filter(Boolean)});if(r)this.toast(`Settled - ${r.winners.length} winning ticket(s)`);break}
      case "runreport":case "printreport":{const q=x=>this.shadowRoot.querySelector(x).value;const r=await this.call("report",{date_from:q("#f"),date_to:q("#t")});if(!r)break;s.report=r;if(a==="printreport")this.print(this.reportHTML(r));else this.render();break}
      case "addret":{const q=x=>this.shadowRoot.querySelector(x).value;if(await this.call("add_retailer",{name:q("#rn"),commission:+q("#rc")})){s.data=await this.ws("state");this.toast("Retailer added");this.render()}break}
      case "addgame":{const q=x=>this.shadowRoot.querySelector(x).value;if(await this.call("add_game",{name:q("#gn"),color:q("#gc"),draw_time:q("#gt"),cutoff:q("#gk"),logo:s.gameLogo||q("#gl")})){s.gameLogo="";s.data=await this.ws("state");this.toast("Game added");this.render()}break}
    }}

  async scanned(id){if(!id)return;const s=this.s,cur=s.data.currency;s.scan="";
    const t=await this.call("ticket",{ticket_id:id});this.render();if(!t)return;
    if(t.status==="won"){if(await this.modal({title:"🏆 Winner!",big:`${cur} ${fmt(t.prize)}`,text:`Ticket ${t.id}`,ok:"Pay prize",tone:"win"})){const r=await this.call("redeem",{ticket_id:t.id});if(r){this.print(this.receipt(r,"PAID "+fmt(r.prize)));this.toast("Prize paid");s.data=await this.ws("state");this.render()}}}
    else if(t.status==="redeemed")this.toast("Already paid",1);
    else if(t.status==="cancelled")this.toast("Ticket was cancelled",1);
    else if(t.status==="lost"){this.load(t);this.toast("Not a winner - lines loaded to replay")}
    else{this.load(t);this.toast("Draw pending - lines loaded to replay")}}
  load(t){const s=this.s;s.tab="sell";s.lines=t.lines.map(l=>({game:l.game,bet_type:l.bet_type,number:l.number,amount:l.amount,date:l.date<today()?s.date:l.date}));this.render();this.toast(`Replay: ${s.lines.length} line(s) loaded`)}

  receipt(t,title){const c=this.s.data.currency,row=l=>`<div style="display:flex;justify-content:space-between"><span>${this.gn(l.game)} ${l.date.slice(5)}</span><span>${l.number} ${this.btl(l.bet_type)}</span><b>${fmt(l.amount)}</b></div>`;
    return `<html><body style="font:12px monospace;width:72mm;margin:0 auto">${this.s.data.settings.logo?`<div style="text-align:center"><img src="${this.s.data.settings.logo}" style="max-height:50px"></div>`:""}<div style="text-align:center;font-weight:bold">${esc(this.s.data.settings.name)}</div><h3 style="text-align:center;margin:4px">${title}</h3><div>${t.retailer_name}<br>${t.created.replace("T"," ").slice(0,16)}</div><hr>${t.lines.map(row).join("")}<hr><div style="display:flex;justify-content:space-between"><b>TOTAL ${c}</b><b>${fmt(t.total)}</b></div><div style="margin-top:8px">${barcode(t.id)}</div><div style="text-align:center">${t.id}</div></body></html>`}
  reportHTML(r){return `<html><body style="font:12px monospace"><h3>SETTLEMENT ${r.from} → ${r.to}</h3><table border="0" width="100%"><tr><th align=left>Retailer</th><th>Tkts</th><th>Sales</th><th>Comm</th><th>Prizes</th><th>Net</th></tr>${r.rows.map(x=>`<tr><td>${x.retailer}</td><td>${x.tickets}</td><td>${fmt(x.sales)}</td><td>${fmt(x.commission)}</td><td>${fmt(x.prizes)}</td><td>${fmt(x.net)}</td></tr>`).join("")}<tr><th align=left>TOTAL</th><th>${r.totals.tickets}</th><th>${fmt(r.totals.sales)}</th><th>${fmt(r.totals.commission)}</th><th>${fmt(r.totals.prizes)}</th><th>${fmt(r.totals.net)}</th></tr></table></body></html>`}
  print(html){const w=window.open("","_blank","width=380,height=640");if(!w)return this.toast("Allow pop-ups to print",1);w.document.write(html);w.document.close();w.focus();setTimeout(()=>w.print(),300)}
}
customElements.define("lottery-pos-panel",LotteryPosPanel);
