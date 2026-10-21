/* Lottery POS panel - tablet-first retailer terminal */
const C39={0:"nnnwwnwnn",1:"wnnwnnnnw",2:"nnwwnnnnw",3:"wnwwnnnnn",4:"nnnwwnnnw",5:"wnnwwnnnn",6:"nnwwwnnnn",7:"nnnwnnwnw",8:"wnnwnnwnn",9:"nnwwnnwnn","*":"nwnnwnwnn"};
const barcode=id=>{let x=0,r="";for(const ch of "*"+id+"*"){const p=C39[ch];for(let i=0;i<9;i++){const w=p[i]==="w"?3:1;if(i%2===0)r+=`<rect x="${x}" width="${w}" height="40"/>`;x+=w}x+=1}return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${x} 40" width="100%" height="50" preserveAspectRatio="none">${r}</svg>`};
const today=()=>new Date(Date.now()-new Date().getTimezoneOffset()*6e4).toISOString().slice(0,10);
const fmt=n=>Number(n||0).toFixed(2);
const PRESETS=[".25",".50",".75","1","2","5","10","20"];

const CSS=`
:host{display:block;height:100%;background:#eef1f8;color:#1e293b;font-family:system-ui,Roboto,sans-serif}
*{box-sizing:border-box}button,select,input{font:inherit}
.app{display:flex;flex-direction:column;height:100%}
.top{display:flex;gap:8px;align-items:center;padding:8px 12px;background:#fff;box-shadow:0 1px 6px #0002;flex-wrap:wrap}
.logo{width:96px;height:40px;border-radius:8px;background:#e2e8f0;display:grid;place-items:center;font-weight:700;color:#64748b;overflow:hidden}.logo img{max-width:100%;max-height:100%}
.top input,.top select{height:40px;border:1px solid #cbd5e1;border-radius:10px;padding:0 10px}#scan{flex:1;min-width:140px}
button{border:0;border-radius:12px;padding:10px 14px;background:#e2e8f0;color:#1e293b;font-weight:600;cursor:pointer}button:active{transform:scale(.97)}
.tabs button.on{background:#2563eb;color:#fff}
.main{flex:1;display:grid;grid-template-columns:minmax(0,1.6fr) minmax(280px,1fr);gap:12px;padding:12px;min-height:0}
.card{background:#fff;border-radius:16px;padding:12px;box-shadow:0 2px 10px #0001}
.left{display:flex;flex-direction:column;gap:10px;overflow:auto}
.games,.bts{display:flex;gap:8px;flex-wrap:wrap}
.game{background:color-mix(in srgb,var(--c) 18%,#fff);border:3px solid transparent;color:#0f172a;display:flex;flex-direction:column;align-items:center;min-width:92px}
.game small{font-weight:400;opacity:.7}.game img{height:22px}.game.on{border-color:var(--c);background:var(--c);color:#fff}
.bt.on{background:#f59e0b;color:#fff}
.row{display:flex;gap:8px;align-items:center}.row input{height:40px;border:1px solid #cbd5e1;border-radius:10px;padding:0 10px}
.entry{display:grid;grid-template-columns:1fr 1fr auto;gap:8px}
.disp{height:60px;border:2px solid #cbd5e1;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:30px;font-weight:700;letter-spacing:6px;background:#fff;cursor:pointer}
.disp.act{border-color:#2563eb;box-shadow:0 0 0 3px #2563eb33}.disp small{font-size:12px;letter-spacing:0;margin-right:8px;color:#64748b}
.add{background:#ef4444;color:#fff;font-size:17px}
.pads{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.pad{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.pad button{height:58px;font-size:24px;color:#2563eb;background:#f1f5f9}
.pre{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}.pre button{height:58px;font-size:20px;background:#dbeafe;color:#1d4ed8}
.acts{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.acts button{font-size:13px;padding:12px 4px}
.right{display:flex;flex-direction:column;min-height:0}
.rhead{display:flex;justify-content:space-between;align-items:center;font-size:13px;color:#64748b}
#lines{flex:1;overflow:auto;margin:8px 0}
.ln{display:grid;grid-template-columns:auto 1fr auto auto;gap:8px;align-items:center;padding:8px;border-bottom:1px solid #e2e8f0;font-size:13px;cursor:pointer}
.ln b{font-size:18px;letter-spacing:2px}.ln button{padding:4px 9px;background:#fee2e2;color:#b91c1c}.ln small{color:#64748b;display:block}
.foot{display:flex;justify-content:space-between;align-items:center;gap:8px}.tot{font-size:26px;font-weight:800;color:#dc2626}
.send{background:#16a34a;color:#fff;font-size:18px;padding:14px 22px}
.office{padding:12px;overflow:auto;display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}
.office h3{margin:0 0 8px}.office .row{margin-bottom:8px;flex-wrap:wrap}.office select{height:40px;border-radius:10px;border:1px solid #cbd5e1}
table{width:100%;border-collapse:collapse;font-size:13px}td,th{padding:6px;border-bottom:1px solid #e2e8f0;text-align:right}td:first-child,th:first-child{text-align:left}
.toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);background:#0f172a;color:#fff;padding:12px 20px;border-radius:12px;z-index:9}.toast.err{background:#b91c1c}
@media(max-width:800px){.main{grid-template-columns:1fr}}`;

class LotteryPosPanel extends HTMLElement{
  constructor(){super();this.attachShadow({mode:"open"});
    this.s={tab:"sell",sel:[],bt:"",date:today(),num:"",amt:"",field:"num",lines:[],retailer:"",data:null,scan:"",report:null};
    this._kh=e=>this.onKey(e)}
  connectedCallback(){window.addEventListener("keydown",this._kh)}
  disconnectedCallback(){window.removeEventListener("keydown",this._kh)}
  set hass(h){const first=!this._hass;this._hass=h;if(first)this.init()}
  set narrow(v){}set panel(v){}set route(v){}
  ws(type,extra={}){return this._hass.callWS({type:"lottery_pos/"+type,...extra})}
  async init(){const s=this.s;s.data=await this.ws("state");s.sel=[s.data.games[0]?.id];s.bt=s.data.bet_types[0]?.key;s.retailer=s.data.retailers[0]?.id;
    this.shadowRoot.addEventListener("click",e=>{const el=e.target.closest("[data-a]");if(el)this.act(el.dataset.a,el.dataset)});this.render()}
  bt(){return this.s.data.bet_types.find(b=>b.key===this.s.bt)}
  btl(k){return this.s.data.bet_types.find(b=>b.key===k)?.label||k}
  gn(k){return this.s.data.games.find(g=>g.id===k)?.name||k}
  toast(m,err){const t=document.createElement("div");t.className="toast"+(err?" err":"");t.textContent=m;this.shadowRoot.append(t);setTimeout(()=>t.remove(),3200)}
  async call(type,extra){try{return await this.ws(type,extra)}catch(e){this.toast(e.message||"Error",1);return null}}

  render(){const s=this.s;if(!s.data)return;
    const tabs=`<div class="tabs"><button class="${s.tab==="sell"?"on":""}" data-a="tab" data-v="sell">Sell</button><button class="${s.tab==="office"?"on":""}" data-a="tab" data-v="office">Back office</button></div>`;
    const d=s.data;
    this.shadowRoot.innerHTML=`<style>${CSS}</style><div class="app"><div class="top">
      <div class="logo"><img src="/local/lottery_logo.png" onerror="this.replaceWith('LOGO')"></div>
      <input id="scan" placeholder="Scan ticket (pay winner / replay)" value="${s.scan}" inputmode="numeric">
      <button data-a="replay">⟲ Replay last</button>
      <select id="ret">${d.retailers.map(r=>`<option value="${r.id}" ${r.id===s.retailer?"selected":""}>${r.name}</option>`).join("")}</select>${tabs}</div>
      ${s.tab==="sell"?this.sellHTML():this.officeHTML()}</div>`;
    const q=x=>this.shadowRoot.querySelector(x);
    q("#scan").oninput=e=>s.scan=e.target.value;
    q("#scan").onkeydown=e=>{if(e.key==="Enter")this.scanned(e.target.value.trim())};
    q("#ret").onchange=e=>s.retailer=e.target.value;
    if(q("#date"))q("#date").onchange=e=>s.date=e.target.value;
    this.paint()}

  sellHTML(){const s=this.s,d=s.data;return `<div class="main"><section class="left card">
    <div class="games">${d.games.map(g=>`<button class="game ${s.sel.includes(g.id)?"on":""}" style="--c:${g.color}" data-a="game" data-v="${g.id}">${g.logo?`<img src="${g.logo}">`:""}${g.name}<small>${g.draw_time}</small></button>`).join("")}</div>
    <div class="row"><b>Draw date</b><input type="date" id="date" value="${s.date}" min="${today()}"><small>${s.sel.length} game(s) selected</small></div>
    <div class="bts">${d.bet_types.map(b=>`<button class="bt ${b.key===s.bt?"on":""}" data-a="bt" data-v="${b.key}">${b.label}</button>`).join("")}</div>
    <div class="entry"><div id="num" class="disp" data-a="field" data-v="num"></div><div id="amt" class="disp" data-a="field" data-v="amt"></div><button class="add" data-a="add">＋ Add to ticket</button></div>
    <div class="pads"><div class="pad">${[1,2,3,4,5,6,7,8,9,"CLR",0,"DEL"].map(k=>`<button data-a="key" data-v="${k}">${k}</button>`).join("")}</div>
      <div class="pre">${PRESETS.map(p=>`<button data-a="preset" data-v="${p}">${p}</button>`).join("")}</div></div>
    <div class="acts"><button data-a="quick">🎲 Quick pick</button><button data-a="last">Último ticket</button><button data-a="copy">Copia number</button><button data-a="clear">Clear ticket</button>
      <button data-a="cancel">⛔ Cancel ticket</button><button data-a="redeem">💵 Redeem</button><button data-a="results">🖨 Print resultado</button><button data-a="report1">🖨 Print report</button></div>
  </section><section class="right card"><div class="rhead"><span>Tap a line to edit it</span><span>Today: ${d.currency} ${fmt(d.summary.sales_today)}</span></div>
    <div id="lines"></div><div class="foot"><div><small>Lines <b id="cnt">0</b></small><div class="tot" id="tot"></div></div><button class="send" data-a="send">SEND &amp; PRINT ▶</button></div></section></div>`}

  officeHTML(){const d=this.s.data,r=this.s.report,t=today();return `<div class="office">
    <div class="card"><h3>Enter draw results</h3><div class="row"><select id="rg">${d.games.map(g=>`<option value="${g.id}">${g.name}</option>`).join("")}</select><input type="date" id="rd" value="${t}"></div>
      <div class="row"><input id="r1" maxlength="4" placeholder="1st" size="5"><input id="r2" maxlength="4" placeholder="2nd" size="5"><input id="r3" maxlength="4" placeholder="3rd" size="5"></div><button data-a="saveres">Save &amp; settle</button></div>
    <div class="card"><h3>Settlement report</h3><div class="row"><input type="date" id="f" value="${t}"><input type="date" id="t" value="${t}"><button data-a="runreport">Run</button><button data-a="printreport">Print</button></div>
      ${r?`<table><tr><th>Retailer</th><th>Tickets</th><th>Sales</th><th>Comm.</th><th>Prizes</th><th>Net</th></tr>${r.rows.map(x=>`<tr><td>${x.retailer}</td><td>${x.tickets}</td><td>${fmt(x.sales)}</td><td>${fmt(x.commission)}</td><td>${fmt(x.prizes)}</td><td>${fmt(x.net)}</td></tr>`).join("")}
      <tr><th>Total</th><th>${r.totals.tickets}</th><th>${fmt(r.totals.sales)}</th><th>${fmt(r.totals.commission)}</th><th>${fmt(r.totals.prizes)}</th><th>${fmt(r.totals.net)}</th></tr></table>`:""}</div>
    <div class="card"><h3>Add retailer</h3><div class="row"><input id="rn" placeholder="Name"><input id="rc" type="number" placeholder="Commission %" value="10" style="width:120px"><button data-a="addret">Add</button></div>
      <h3>Add game</h3><div class="row"><input id="gn" placeholder="Name"><input id="gc" type="color" value="#64748b"><input id="gt" type="time" value="13:00"><input id="gk" type="time" value="12:45" title="Sales cutoff"></div>
      <div class="row"><input id="gl" placeholder="Logo URL (/local/...)" style="flex:1"><button data-a="addgame">Add</button></div></div></div>`}

  paint(){const s=this.s,q=x=>this.shadowRoot.querySelector(x);if(s.tab!=="sell"||!q("#num"))return;const bt=this.bt();
    q("#num").innerHTML=`<small>${bt.label}</small>`+(s.num+"•".repeat(Math.max(0,bt.digits-s.num.length)));
    q("#amt").innerHTML=`<small>${s.data.currency}</small>`+(s.amt||"0");
    q("#num").classList.toggle("act",s.field==="num");q("#amt").classList.toggle("act",s.field==="amt");
    q("#lines").innerHTML=s.lines.map((l,i)=>`<div class="ln" data-a="edit" data-i="${i}"><b>${l.number}</b><span>${this.btl(l.bet_type)}<small>${this.gn(l.game)} · ${l.date.slice(5)}</small></span><em>${fmt(l.amount)}</em><button data-a="del" data-i="${i}">✕</button></div>`).join("")||`<p style="color:#94a3b8;text-align:center">No plays yet</p>`;
    q("#cnt").textContent=s.lines.length;q("#tot").textContent=`${s.data.currency} ${fmt(s.lines.reduce((a,l)=>a+l.amount,0))}`}

  onKey(e){const s=this.s;if(!s.data||s.tab!=="sell"||e.composedPath()[0]?.tagName==="INPUT"||e.composedPath()[0]?.tagName==="SELECT")return;
    if(/^\d$/.test(e.key))this.key(e.key);else if(e.key==="Backspace")this.key("DEL");else if(e.key==="Enter"){e.preventDefault();this.add()}else if(e.key==="Tab"){e.preventDefault();s.field=s.field==="num"?"amt":"num";this.paint()}}
  key(k){const s=this.s,f=s.field,bt=this.bt();
    if(k==="CLR")s[f]="";else if(k==="DEL")s[f]=s[f].slice(0,-1);
    else if(f==="num"){if(s.num.length<bt.digits)s.num+=k;if(s.num.length===bt.digits)s.field="amt"}
    else if(s.amt.length<7)s.amt=(s.amt==="0"?"":s.amt)+k;
    this.paint()}
  add(){const s=this.s,bt=this.bt(),amt=parseFloat(s.amt);
    if(s.num.length!==bt.digits)return this.toast(`${bt.label} needs ${bt.digits} digits`,1);
    if(!(amt>0))return this.toast("Enter an amount",1);
    for(const g of s.sel)s.lines.push({game:g,bet_type:bt.key,number:s.num,amount:amt,date:s.date});
    s.num="";s.field="num";this.paint()}

  async act(a,ds){const s=this.s;
    switch(a){
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
      case "cancel":{const id=prompt("Ticket number to cancel (or scan)");if(!id)break;const t=await this.call("cancel",{ticket_id:id.trim()});if(t){this.print(this.receipt(t,"CANCELLATION RECEIPT"));this.toast("Ticket cancelled")}break}
      case "redeem":{const id=prompt("Ticket number to pay (or scan)");if(id)this.scanned(id.trim());break}
      case "results":{const r=await this.call("draw_results",{date:s.date});if(r)this.print(`<html><body style="font:13px monospace;width:72mm"><h3>RESULTADO ${s.date}</h3>${r.map(x=>`<p><b>${x.game}</b><br>${x.numbers.join(" - ")}</p>`).join("")||"No results yet"}</body></html>`);break}
      case "report1":{const t=today(),r=await this.call("report",{date_from:t,date_to:t});if(r)this.print(this.reportHTML(r));break}
      case "saveres":{const q=x=>this.shadowRoot.querySelector(x).value;const r=await this.call("set_results",{game:q("#rg"),date:q("#rd"),numbers:[q("#r1"),q("#r2"),q("#r3")].filter(Boolean)});if(r)this.toast(`Settled - ${r.winners.length} winning ticket(s)`);break}
      case "runreport":case "printreport":{const q=x=>this.shadowRoot.querySelector(x).value;const r=await this.call("report",{date_from:q("#f"),date_to:q("#t")});if(!r)break;s.report=r;if(a==="printreport")this.print(this.reportHTML(r));else this.render();break}
      case "addret":{const q=x=>this.shadowRoot.querySelector(x).value;if(await this.call("add_retailer",{name:q("#rn"),commission:+q("#rc")})){s.data=await this.ws("state");this.toast("Retailer added");this.render()}break}
      case "addgame":{const q=x=>this.shadowRoot.querySelector(x).value;if(await this.call("add_game",{name:q("#gn"),color:q("#gc"),draw_time:q("#gt"),cutoff:q("#gk"),logo:q("#gl")})){s.data=await this.ws("state");this.toast("Game added");this.render()}break}
    }}

  async scanned(id){if(!id)return;const s=this.s;s.scan="";
    const t=await this.call("ticket",{ticket_id:id});this.render();if(!t)return;
    if(t.status==="won"){if(confirm(`WINNER! Pay ${s.data.currency} ${fmt(t.prize)} for ticket ${t.id}?`)){const r=await this.call("redeem",{ticket_id:t.id});if(r){this.print(this.receipt(r,"PAID - "+fmt(r.prize)));this.toast("Prize paid")}}}
    else if(t.status==="redeemed")this.toast("Already paid",1);
    else if(t.status==="cancelled")this.toast("Ticket was cancelled",1);
    else if(t.status==="lost")this.toast("Not a winner - lines loaded to replay"),this.load(t);
    else this.load(t),this.toast("Draw pending - lines loaded to replay")}
  load(t){const s=this.s;s.tab="sell";s.lines=t.lines.map(l=>({game:l.game,bet_type:l.bet_type,number:l.number,amount:l.amount,date:l.date<today()?s.date:l.date}));this.render();this.toast(`Replay: ${s.lines.length} line(s) loaded`)}

  receipt(t,title){const c=this.s.data.currency,row=l=>`<div style="display:flex;justify-content:space-between"><span>${this.gn(l.game)} ${l.date.slice(5)}</span><span>${l.number} ${this.btl(l.bet_type)}</span><b>${fmt(l.amount)}</b></div>`;
    return `<html><body style="font:12px monospace;width:72mm;margin:0 auto"><h3 style="text-align:center;margin:4px">${title}</h3><div>${t.retailer_name}<br>${t.created.replace("T"," ").slice(0,16)}</div><hr>${t.lines.map(row).join("")}<hr><div style="display:flex;justify-content:space-between"><b>TOTAL ${c}</b><b>${fmt(t.total)}</b></div><div style="margin-top:8px">${barcode(t.id)}</div><div style="text-align:center">${t.id}</div></body></html>`}
  reportHTML(r){return `<html><body style="font:12px monospace"><h3>SETTLEMENT ${r.from} → ${r.to}</h3><table border="0" width="100%"><tr><th align=left>Retailer</th><th>Tkts</th><th>Sales</th><th>Comm</th><th>Prizes</th><th>Net</th></tr>${r.rows.map(x=>`<tr><td>${x.retailer}</td><td>${x.tickets}</td><td>${fmt(x.sales)}</td><td>${fmt(x.commission)}</td><td>${fmt(x.prizes)}</td><td>${fmt(x.net)}</td></tr>`).join("")}<tr><th align=left>TOTAL</th><th>${r.totals.tickets}</th><th>${fmt(r.totals.sales)}</th><th>${fmt(r.totals.commission)}</th><th>${fmt(r.totals.prizes)}</th><th>${fmt(r.totals.net)}</th></tr></table></body></html>`}
  print(html){const w=window.open("","_blank","width=380,height=640");if(!w)return this.toast("Allow pop-ups to print",1);w.document.write(html);w.document.close();w.focus();setTimeout(()=>w.print(),300)}
}
customElements.define("lottery-pos-panel",LotteryPosPanel);
