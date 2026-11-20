/* Daily Job Hunter dashboard.
   No framework, no build step, no CDN — this has to run from a plugin folder
   on a machine with nothing installed but python3. */

const $  = (s, r=document) => r.querySelector(s);
const el = (t, c, h) => { const n=document.createElement(t); if(c)n.className=c;
                          if(h!=null)n.innerHTML=h; return n; };
const esc = s => String(s ?? "").replace(/[&<>"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));

const S = { leads:[], briefs:[], raw:{}, stats:{}, checks:{}, study:{}, platforms:{},
            notes:{}, tasks:{}, points:{}, tab:"today", filter:"open", pending:0, load:3,
            events:[], kills:[], leadkills:{}, killPresets:{}, pins:[], history:{}, engine:"", evFilter:"upcoming",
            calMonth:null, calSel:null, thread:[] };

/* ---------- dates: everything is the user's LOCAL day ---------- */
const pad = n => String(n).padStart(2,"0");
const iso = d => `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
const todayISO = () => iso(new Date());
const parseISO = s => { const [y,m,d]=String(s).split("-").map(Number); return new Date(y,(m||1)-1,d||1); };
const DOW = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];
const MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const MONTHS_FULL = ["January","February","March","April","May","June","July","August","September","October","November","December"];
const fmtDay = s => { const d=parseISO(s); return `${DOW[d.getDay()]} ${MON[d.getMonth()]} ${d.getDate()}`; };
const fmt12 = hhmm => { if(!hhmm) return ""; const [h,m]=hhmm.split(":").map(Number);
  return `${(h%12)||12}:${pad(m)} ${h>=12?"PM":"AM"}`; };
const daysFrom = s => Math.round((parseISO(s) - parseISO(todayISO()))/864e5);
const relDay = s => { const n=daysFrom(s); return n===0?"today":n===1?"tomorrow":n===-1?"yesterday":
  n>1&&n<7?`in ${n} days`:n<0?`${-n} days ago`:`in ${n} days`; };

/* How many apply items Today shows. Default 3 protects the bad days; the
   control lets him say "I'm going hard" without me guessing a number for him.
   Persisted, so a catch-up stretch stays set until he dials it back. */
const LOADS = [["3","Easy"],["6","Normal"],["12","Catch-up"],["999","Everything"]];

/* ---------- tiny markdown renderer (enough for our briefs) ---------- */
function md(src){
  if(src==null || src==="") return "";
  const lines = String(src).split("\n");
  let out=[], inTable=false, inCode=false;
  const inline = t => esc(t)
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g,'<a href="$2" target="_blank" rel="noopener">$1</a>')
    .replace(/`([^`]+)`/g,'<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*\n]+)\*/g,'$1<em>$2</em>')
    .replace(/(https?:\/\/[^\s<)]+)/g, m => /href=/.test(m)?m:`<a href="${m}" target="_blank" rel="noopener">${m}</a>`);
  for(let i=0;i<lines.length;i++){
    const L=lines[i], t=L.trim();
    if(t.startsWith("```")){ inCode=!inCode; out.push(inCode?"<pre><code>":"</code></pre>"); continue; }
    if(inCode){ out.push(esc(L)+"\n"); continue; }
    if(t.startsWith("|")){
      const cells=t.replace(/^\||\|$/g,"").split("|").map(c=>c.trim());
      if(cells.every(c=>/^:?-{2,}:?$/.test(c))) continue;
      if(!inTable){ out.push("<table>"); inTable=true; }
      out.push("<tr>"+cells.map(c=>`<td>${inline(c)}</td>`).join("")+"</tr>");
      continue;
    }
    if(inTable){ out.push("</table>"); inTable=false; }
    if(!t){ out.push(""); continue; }
    if(/^#{1,6}\s/.test(t)) { out.push(`<h3>${inline(t.replace(/^#+\s*/,""))}</h3>`); continue; }
    if(/^>\s?/.test(t))     { out.push(`<blockquote>${inline(t.replace(/^>\s?/,""))}</blockquote>`); continue; }
    if(/^[-*•]\s/.test(t))  { out.push(`<div style="padding-left:16px;text-indent:-10px">• ${inline(t.replace(/^[-*•]\s/,""))}</div>`); continue; }
    if(/^\d+\.\s/.test(t))  { out.push(`<div style="padding-left:16px">${inline(t)}</div>`); continue; }
    if(/^-{3,}$/.test(t))   { out.push("<hr style='border:0;border-top:1px solid var(--line);margin:14px 0'>"); continue; }
    out.push(`<p style="margin:7px 0">${inline(t)}</p>`);
  }
  if(inTable) out.push("</table>");
  return out.join("\n");
}

/* inline-only render: no block wrapper, so bullets stay on their own line */
function mdi(t){
  return esc(t)
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g,'<a href="$2" target="_blank" rel="noopener">$1</a>')
    .replace(/`([^`]+)`/g,'<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*\n]+)\*/g,'$1<em>$2</em>');
}
const bullets = arr => arr.map(x =>
  `<div style="padding-left:15px;text-indent:-11px;margin:5px 0">• ${mdi(x)}</div>`).join("");

/* ---------- api ---------- */
async function get(n){ const r=await fetch("/api/"+n); if(!r.ok) return null; return r.json(); }
async function post(n,b){
  const r=await fetch("/api/"+n,{method:"POST",headers:{"Content-Type":"application/json"},
                                 body:JSON.stringify(b)});
  if(r.ok) return r.json();
  // 404 on a known button means the page is newer than the running server.
  if(r.status===404) return {error:"the dashboard server is older than this page. Close it and start it again (with autostart on, it restarts itself)"};
  try{ return await r.json(); }catch(e){ return null; }
}
function toast(html){
  const t=$("#toast"); t.innerHTML=html; t.classList.add("show");
  clearTimeout(t._t); t._t=setTimeout(()=>t.classList.remove("show"),2600);
}

/* ---------- checkbox ---------- */
function checkbox(key, label, kind, url, onDone){
  const on = !!(S.checks[key]||{}).checked;
  const b = el("button","chk",
    `<svg viewBox="0 0 24 24"><polyline points="4,12 10,18 20,6"/></svg>`);
  b.setAttribute("role","checkbox");
  b.setAttribute("aria-checked", on);
  b.setAttribute("aria-label", label);
  b.onclick = async e => {
    e.stopPropagation();
    const next = b.getAttribute("aria-checked")!=="true";
    b.setAttribute("aria-checked", next);
    if(next){ b.classList.add("justdone"); setTimeout(()=>b.classList.remove("justdone"),340); }
    const res = await post("check",{key,checked:next,label,kind,url});
    if(res){
      S.checks = res.checks; S.pending = res.pending;
      get("points").then(pt => { if(pt){ S.points = pt; paintScore(); paintTabs(); } });
      if(next){
        const msgs = {applied:"Logged as applied", study:"Nice — that's today's study done",
                      research:"Marked researched", task:"Done"};
        toast(`<b>✓</b> ${msgs[kind]||"Done"} · <span style="color:var(--fg-faint)">saved, syncs on the next sweep</span>`);
      }
      onDone && onDone(next);
      paintTabs();
    } else {
      b.setAttribute("aria-checked", !next);
      toast("Couldn't save — is the server still running?");
    }
  };
  return b;
}

/* ---------- lead card ---------- */
const ATS = {greenhouse:"GH",lever:"LV",ashby:"AS",workday:"WD",smartrecruiters:"SR",
             workable:"WK",icims:"IC",breezy:"BZ",applicantstack:"AP",paylocity:"PL",
             handshake:"HS",taleo:"TL",recruitee:"RC",jobvite:"JV",rippling:"RP",
             careers:"↗",none:"—"};

function isHot(age){ return /\b(0|1|2)\s*day|hours|today|yesterday/i.test(age||""); }
/* the brief writes "14 days (Lever createdAt 2026-11-04)" -- the pill wants "14 days" */
function shortAge(a){
  if(!a) return "";
  const m = String(a).match(/^\s*(\d+\s*(?:day|days|d|hour|hours|h|week|weeks)\b|today|yesterday)/i);
  return m ? m[1].trim() : String(a).split("(")[0].trim().slice(0,22);
}

/* ---------- kill buttons: red / yellow / dead link ----------
   These write ONE event each to the append-only log, exactly like a checkbox.
   The server still never touches a markdown file; the next sweep drains the
   queue into ghost.md. So a kill survives the laptop being shut immediately,
   and a skipped sweep costs latency and nothing else.

   RED is permanent in ghost.md and never comes off, and YELLOW parks the
   company for three months, so both demand a reason -- preset chips keep it to
   one extra tap. DEAD LINK needs none: the reason is the tier. Undo stays
   available right up until a sweep drains it. */
const killKey = L => "kill-" + L.key;
const isKilled = L => !!S.leadkills[killKey(L)];
const TIER_LABEL = {red:"Red", yellow:"Yellow", dead:"Dead link"};

async function sendKill(L, tier, reason, card){
  const key = killKey(L);
  const res = await post("kill",{key, tier, reason,
    employer:L.employer||"", title:L.title||"", url:L.url||""});
  if(!res || res.error){ toast(`<b>!</b> ${esc((res&&res.error)||"could not save")}`); return; }
  S.leadkills = res.leadkills; S.pending = res.pending;
  const t = el("span",null,
    `<b>${tier==="red"?"⛔":tier==="yellow"?"⚠":"🔗"}</b> ${esc(L.title||"Lead")} marked `
   +`<b>${TIER_LABEL[tier].toLowerCase()}</b> · <span style="color:var(--fg-faint)">`
   +`goes to ghost.md on the next sweep</span> · `);
  const u = el("a","undo","Undo");
  u.href="#"; u.onclick = async e => {
    e.preventDefault();
    const r2 = await post("unkill",{key});
    if(r2){ S.leadkills=r2.leadkills; S.pending=r2.pending;
            toast("<b>↩</b> Put back"); paintTabs(); paint(); }
  };
  const box=el("span"); box.appendChild(t); box.appendChild(u);
  toast(box.innerHTML);
  // rebind: toast() takes html, so wire the undo after it lands
  const live=document.querySelector("#toast .undo");
  if(live) live.onclick = u.onclick;
  paintTabs(); paint();
}

/* ---------- build-materials request ----------
   One tap asks the next sweep to build this lead's folder (resume, jd.md,
   apply-notes). Same contract as everything else: one event in the log, the
   server writes no markdown, the sweep drains it into dashboard-inbox.md. */
const buildKey = L => "build-" + L.key;
const isBuildReq = L => !!(S.buildreqs||{})[buildKey(L)];
async function sendBuild(L, on, note){
  const res = on
    ? await post("build",{key:buildKey(L), employer:L.employer||"", title:L.title||"", url:L.url||"", note:note||""})
    : await post("unbuild",{key:buildKey(L)});
  if(!res || res.error){ toast(`<b>!</b> ${esc((res&&res.error)||"could not save")}`); return; }
  S.buildreqs = res.buildreqs; S.pending = res.pending;
  if(res.status) S.buildstatus = res.status;
  const building = on && ((S.buildstatus||{})[buildKey(L)]||{}).state==="building";
  toast(on ? (building ? `<b>⏳</b> ${esc(L.title||"Lead")}: building now with Claude Code`
                       : `<b>🛠</b> ${esc(L.title||"Lead")}: materials requested · built on the next sweep`)
           : "<b>↩</b> Materials request cancelled");
  paintTabs(); paint();
}
function buildBtn(L){
  if(L.ready) return null;
  const on = isBuildReq(L);
  const st = (S.buildstatus||{})[buildKey(L)] || {};
  if(on && st.state==="building"){
    const b = el("button","bbtn on busy","⏳ Building now… (5–10 min)");
    b.title = "Claude Code is building this on your PC. The card flips to 'materials ready' when it lands.";
    b.onclick = e => e.stopPropagation();
    return b;
  }
  let label = "🛠 Build materials please", tip = S.buildInstant
    ? "Builds right now on your PC with Claude Code (resume, jd.md, apply-notes)."
    : "Queues it for the next 1am/6am sweep (install Claude Code to build instantly).";
  if(on){
    label = st.state==="failed" ? "⚠ Build failed · next sweep will retry · cancel"
          : st.state==="skipped" ? "⛔ Skipped: " + (st.result||"").replace(/^SKIPPED:?\s*/,"").slice(0,60)
          : st.state==="done" ? "✓ Built · refresh"
          : "🛠 Requested · next sweep · cancel";
    tip = st.result || "Queued for the next 1am/6am sweep. Click to cancel.";
  }
  const b = el("button","bbtn"+(on?" on":""), esc(label));
  b.title = tip;
  b.onclick = e => { e.stopPropagation(); on ? sendBuild(L, false) : openBuild(L, b); };
  return b;
}
// While anything is building, check every 15s; when one finishes, reload leads
// (the build re-ran build_site.py) so the card flips to "materials ready".
async function pollBuilds(){
  const r = await get("buildreqs"); if(!r) return;
  const before = Object.values(S.buildstatus||{}).filter(s=>s.state==="building").length;
  S.buildreqs = r.buildreqs||{}; S.buildstatus = r.status||{}; S.buildInstant = !!r.instant;
  const now = Object.values(S.buildstatus).filter(s=>s.state==="building").length;
  if(before && now < before){ S.leads = (await get("leads")) || S.leads;
    toast("<b>✓</b> Materials build finished"); }
  if(before || now) paint();
}
setInterval(()=>{ if(Object.values(S.buildstatus||{}).some(s=>s.state==="building")) pollBuilds(); }, 15000);
// Optional comment with the request ("lead with the Go gap", "skip the cover
// letter", ...). Enter or the button sends; empty is fine.
function openBuild(L, btn){
  const bar = btn.closest(".killbar");
  const old = bar.parentNode.querySelector(".buildpick"); if(old){ old.remove(); return; }
  const pick = el("div","killpick buildpick");
  pick.onclick = e => e.stopPropagation();
  pick.appendChild(el("div","kphead","Build materials for this lead · anything the sweep should know? (optional)"));
  const row = el("div","krow");
  const inp = el("input","kinput"); inp.type="text";
  inp.placeholder = "e.g. lead with the automation project, they asked for a project link";
  const go = el("button","kgo","Request");
  const send = () => { pick.remove(); sendBuild(L, true, inp.value.trim()); };
  go.onclick = send;
  inp.onkeydown = e => { if(e.key==="Enter") send(); if(e.key==="Escape") pick.remove(); };
  const cancel = el("button","kcancel","Cancel"); cancel.onclick = () => pick.remove();
  row.appendChild(inp); row.appendChild(go); row.appendChild(cancel);
  pick.appendChild(row);
  bar.parentNode.insertBefore(pick, bar.nextSibling);
  inp.focus();
}

function killBar(L, card){
  const bar = el("div","killbar");
  const bb = buildBtn(L);
  if(bb){ bar.appendChild(bb); bar.appendChild(el("span","ksep","")); }
  const mk = (tier,label,title) => {
    const b = el("button","kbtn k-"+tier,label);
    b.title = title;
    b.onclick = e => { e.stopPropagation(); openKill(L, tier, bar, card); };
    return b;
  };
  bar.appendChild(el("span","klbl","not for me:"));
  bar.appendChild(mk("red","Red","Permanent. Ethics or scam only — this never comes off."));
  bar.appendChild(mk("yellow","Yellow","Parks this company for three months."));
  bar.appendChild(mk("dead","Dead link","The posting is gone or the link is broken."));
  return bar;
}

function openKill(L, tier, bar, card){
  if(tier === "dead") return sendKill(L, "dead", "", card);   // one tap, no reason

  const old = bar.parentNode.querySelector(".killpick");
  if(old) old.remove();
  const pick = el("div","killpick k-"+tier);
  pick.onclick = e => e.stopPropagation();
  pick.appendChild(el("div","kphead", tier==="red"
    ? "<b>Red is permanent.</b> It never comes off and the whole company is skipped from now on. Pick a reason:"
    : "<b>Yellow</b> parks this company for three months. Pick a reason:"));

  const chips = el("div","kchips");
  (S.killPresets[tier]||[]).forEach(r=>{
    const c=el("button","kchip",esc(r));
    c.onclick = () => { pick.remove(); sendKill(L, tier, r, card); };
    chips.appendChild(c);
  });
  pick.appendChild(chips);

  const row = el("div","krow");
  const inp = el("input","kinput"); inp.type="text";
  inp.placeholder = "or write your own reason";
  const go = el("button","kgo","Save");
  const save = () => { const v=inp.value.trim();
    if(!v){ inp.focus(); inp.classList.add("bad"); setTimeout(()=>inp.classList.remove("bad"),600); return; }
    pick.remove(); sendKill(L, tier, v, card); };
  go.onclick = save;
  inp.onkeydown = e => { if(e.key==="Enter") save(); if(e.key==="Escape") pick.remove(); };
  row.appendChild(inp); row.appendChild(go);
  const cancel = el("button","kcancel","Cancel");
  cancel.onclick = () => pick.remove();
  row.appendChild(cancel);
  pick.appendChild(row);

  bar.parentNode.insertBefore(pick, bar.nextSibling);
  inp.focus();
}

function leadCard(L){
  const key = "applied-"+L.key;
  const done = !!(S.checks[key]||{}).checked;
  const c = el("div","card lead"+(done||L.expired?" done":""));
  const row = el("div","row");

  row.appendChild(checkbox(key, L.title, "applied", L.url||"",
    v => c.classList.toggle("done", v)));

  const meta = el("div","meta");
  const ttl = el("div","ttl");
  if(L.rank && /^\d+$/.test(L.rank)) ttl.appendChild(el("span","tag rank","#"+L.rank));
  ttl.appendChild(el("span",null,esc(L.title)));
  meta.appendChild(ttl);

  const sub = el("div","sub");
  if(L.age){ const t=el("span","tag"+(isHot(L.age)?" hot":""),esc(shortAge(L.age)));
             t.title=L.age; sub.appendChild(t); }
  if(L.comp) sub.appendChild(el("span","tag",esc(L.comp)));
  if(L.location) sub.appendChild(el("span",null,esc(L.location)));
  if(L.deprioritized) sub.appendChild(el("span","tag depri","deprioritized"));
  if(L.sightings>1) sub.appendChild(el("span",null,
      `<span style="color:var(--fg-faint)">seen ${L.sightings}×</span>`));
  if(L.expired) sub.appendChild(el("span","tag expired",
      `expired · ${L.age_days}d`));
  if(L.internship) sub.appendChild(el("span","tag","internship · age exempt"));
  if(L.closes) sub.appendChild(el("span","tag",`closes ${esc(L.closes)}`));
  if(L.ready) sub.appendChild(el("span","tag ready","materials ready"));
  if(L.brief_date) sub.appendChild(el("span",null,esc(L.brief_date)));
  sub.appendChild(el("span",null, `<span style="color:var(--fg-faint)">· click to expand${L.jd?" · JD":""}</span>`));
  meta.appendChild(sub);
  row.appendChild(meta);

  if(L.url){
    const a=el("a","apply"+(L.url_guess?" guess":""));
    a.href=L.url; a.target="_blank"; a.rel="noopener";
    a.innerHTML = `<span class="ats">${L.url_guess?"?":(ATS[L.ats]||"↗")}</span>`
                + `<span class="lbl">${L.url_guess?"Find":"Apply"}</span>`;
    a.title = L.url_guess
      ? "No exact link in the brief — this is a best-guess careers search"
      : L.url;
    a.onclick = e => e.stopPropagation();
    row.appendChild(a);
  }
  c.appendChild(row);

  let body = "";
  if(L.deprioritized && L.depri_reason)
    body += `<blockquote><strong>Deprioritized.</strong> ${mdi(L.depri_reason)}</blockquote>`;
  if(L.url_guess)
    body += `<blockquote><strong>Best-guess link.</strong> The brief had no exact apply URL for this one, so the button runs a scoped careers search instead. Verify before trusting it.</blockquote>`;
  // JD first: the posting is what the user reads; the sweep's analysis
  // is a separate section under it.
  let jd = `<h4 class="xsec">Job description</h4>`;
  jd += L.jd ? `<div class="jdbody">${md(L.jd)}</div>`
             : `<p style="margin:7px 0;color:var(--fg-faint)">Not saved for this lead yet. Open the posting with the Apply button, or tap Build materials and the next sweep saves it.</p>`;
  const B = (S.buildreqs||{})[buildKey(L)];
  if(B && B.note) body = `<blockquote><strong>Your note on the materials request:</strong> ${esc(B.note)}</blockquote>` + body;
  body = jd + `<h4 class="xsec">Sweep notes</h4>` + body
       + (L.detail ? md(L.detail) : `<p style="margin:7px 0;color:var(--fg-faint)">No write-up was captured for this lead.</p>`);
  row.classList.add("click");
  const d = el("div","detail", `<div class="md">${body}</div>`);
  c.appendChild(d);
  row.onclick = () => d.classList.toggle("open");

  const K = S.leadkills[killKey(L)];
  if(K){
    c.classList.add("killed","killed-"+K.tier);
    const note = el("div","killnote");
    note.innerHTML = `<span class="tag k-${K.tier}">${TIER_LABEL[K.tier]}</span> `
      + (K.reason ? esc(K.reason)+" · " : "")
      + `<span style="color:var(--fg-faint)">queued for ghost.md</span> · `;
    const un = el("a","undo","Put back");
    un.href="#"; un.onclick = async e => { e.preventDefault(); e.stopPropagation();
      const r = await post("unkill",{key:killKey(L)});
      if(r){ S.leadkills=r.leadkills; S.pending=r.pending; toast("<b>↩</b> Put back"); paintTabs(); paint(); } };
    note.appendChild(un);
    note.onclick = e => e.stopPropagation();
    c.appendChild(note);
  } else {
    c.appendChild(killBar(L, c));
  }
  return c;
}

/* ---------- score ---------- */
function paintScore(){
  const P = S.points || {}, host = document.getElementById("score");
  if(!host) return;
  const pct = Math.min(100, Math.round(((P.today||0) / (P.daily_target||25)) * 100));
  const done = P.day_done;
  host.innerHTML =
    `<div class="score-ring${done?" done":""}" title="${P.today||0} of ${P.daily_target||25} points today">
       <svg viewBox="0 0 36 36">
         <circle class="bg" cx="18" cy="18" r="15.9"/>
         <circle class="fg" cx="18" cy="18" r="15.9"
                 stroke-dasharray="${pct} ${100-pct}" stroke-dashoffset="25"/>
       </svg>
       <b>${done?"✓":(P.today||0)}</b>
     </div>
     <div class="score-txt">
       <span class="score-lead">${done?"Day done":`${P.today||0} / ${P.daily_target||25} today`}</span>
       <span class="score-sub">${P.streak?`${P.streak} day streak · `:""}${P.week||0} this week</span>
     </div>`;
}

/* ---------- tabs ---------- */
const TABS = [
  {id:"today",    label:"Today"},
  {id:"calendar", label:"Calendar"},
  {id:"events",   label:"Events"},
  {id:"leads",    label:"Leads"},
  {id:"log",      label:"Log"},
  {id:"study",    label:"Study"},
  {id:"ai",       label:"AI Work"},
  {id:"briefs",   label:"Briefs"},
  {id:"notes",    label:"Notes"},
];
function go(tab){ S.tab=tab; try{localStorage.setItem("jh.tab",tab);}catch(e){} paintTabs(); paint(); }

function todayCount(){
  return ((S.history.days||{})[todayISO()]||[]).filter(x=>x.kind!=="sweep").length;
}

function paintTabs(){
  const n=$("#tabs"); n.innerHTML="";
  TABS.forEach(t=>{
    const b=el("button",null,esc(t.label));
    b.setAttribute("aria-selected", S.tab===t.id);
    if(t.id==="leads"){
      const open = S.leads.filter(L=>!(S.checks["applied-"+L.key]||{}).checked && !isKilled(L)).length;
      b.innerHTML += `<span class="pip">${open}</span>`;
    }
    if(t.id==="today"){
      const c=todayCount(); if(c) b.innerHTML += `<span class="pip">${c}</span>`;
    }
    if(t.id==="events"){
      const n=upcomingEvents(14).length; if(n) b.innerHTML += `<span class="pip">${n}</span>`;
    }
    b.setAttribute("role","tab");
    b.onclick=()=>go(t.id);
    n.appendChild(b);
  });
}

/* ---------- views ---------- */
function viewToday(v){
  const sp=el("div","split"), main=el("div");
  viewTodayMain(main); sp.appendChild(main); sp.appendChild(rail()); v.appendChild(sp);
}

function viewTodayMain(v){
  const st=S.stats, hr=new Date().getHours();
  const greet = hr<5?"Still up" : hr<12?"Morning" : hr<18?"Afternoon" : "Evening";
  const open = S.leads.filter(L=>!(S.checks["applied-"+L.key]||{}).checked && !L.expired && !isKilled(L));
  const fresh = open.filter(L=>isHot(L.age));
  const ready = open.filter(L=>L.ready);
  const lanes = (S.study.lanes)||[];
  const steps = lanes.map(L=>{
    const next = (L.modules||[]).find(m=>!(S.checks[m.key]||{}).checked);
    return next ? Object.assign({lane:L.name}, next) : null;
  }).filter(Boolean).slice(0,3);
  const stepsDone = lanes.reduce((n,L)=>
    n + (L.modules||[]).filter(m=>(S.checks[m.key]||{}).checked).length, 0);

  /* Load is the user's dial, not a guess. Default 3 protects the bad days;
     Catch-up exists because some days he wants to go hard. What the dial can
     NEVER do is surface an expired lead -- the 14-day rule is a kill, not a
     preference, so those are gone at every setting. */
  const MAX_TODAY = S.load, RECENT_DAYS = 14;
  const cutoff = new Date(Date.now() - RECENT_DAYS*864e5).toISOString().slice(0,10);
  const recent = open.filter(L => !L.expired && !isKilled(L) && (L.brief_date||"") >= cutoff);
  const company = L => (L.title||"").split(/[—\-–|(]/)[0].trim().toLowerCase();
  const picks = [], seenCo = new Set();
  const push = L => {
    const c = company(L);
    if(picks.length>=MAX_TODAY || seenCo.has(c)) return;
    seenCo.add(c); picks.push(L);
  };
  /* Deprioritised companies are excluded from the first three passes entirely.
     Freshness normally wins, but "Acme posted something an hour ago" is not a
     reason to put Acme back at the top when several of their reqs have already
     gone unanswered. They only appear once nothing else can fill the slot. */
  const live = recent.filter(L=>!L.deprioritized);
  live.filter(L=>isHot(L.age)).forEach(push);     // freshest first
  live.filter(L=>L.ready).forEach(push);          // then anything already built
  live.forEach(push);                             // then fill
  recent.filter(L=>L.deprioritized).forEach(push);// deprioritised last, if at all

  const totalToday = picks.length + (steps.length?1:0);
  const doneToday  = picks.filter(L=>(S.checks["applied-"+L.key]||{}).checked).length
                   + (stepsDone>0?1:0);

  const h=el("div","hero");
  h.appendChild(el("h1",null,`${greet}${S.stats.user_name ? ", "+esc(S.stats.user_name) : ""}.`));
  const restN = open.length - picks.length;
  h.appendChild(el("p",null, picks.length
    ? `${picks.length} thing${picks.length===1?"":"s"} worth doing today. Tick as you go — nothing has to happen all at once.`
    : (st.stale ? `Last brief was ${esc(st.latest_brief||"—")}. Nothing new has landed since.`
                : `Nothing urgent today. That's allowed.`)));
  v.appendChild(h);

  const pr=el("div","progress");
  pr.innerHTML = `<div class="bar"><i style="width:${totalToday?Math.round(doneToday/totalToday*100):0}%"></i></div>
                  <span>${doneToday} of ${totalToday}</span>`;
  v.appendChild(pr);

  const lc = el("div","filters");
  lc.appendChild(el("span",null,
    `<span style="font-size:12px;color:var(--fg-faint);align-self:center;margin-right:4px">Today's load</span>`));
  LOADS.forEach(([n,label])=>{
    const b=el("button",null,label);
    b.setAttribute("aria-pressed", String(S.load)===n);
    b.onclick=()=>{ S.load=+n; try{localStorage.setItem("jh.load",n);}catch(e){} paint(); };
    lc.appendChild(b);
  });
  v.appendChild(lc);

  const P = S.points||{};
  if(P.daily_target){
    v.appendChild(el("h2","sec","Progress"));
    const c=el("div","card"); const b=el("div","scoreboard");
    [["Today",P.today,P.daily_target],["This week",P.week,P.weekly_target],
     ["This month",P.month,P.monthly_target]].forEach(([lab,got,goal])=>{
      const pct=Math.min(100,Math.round((got||0)/(goal||1)*100));
      const cell=el("div","sb-cell");
      cell.innerHTML=`<div class="sb-lab">${lab}</div>
        <div class="sb-num">${got||0}<span>/${goal}</span></div>
        <div class="bar"><i style="width:${pct}%"></i></div>`;
      b.appendChild(cell);
    });
    c.appendChild(b);
    const h=el("div","spark");
    const max=Math.max(1,...(P.history||[]).map(x=>x.pts));
    (P.history||[]).forEach(x=>{
      const bar=el("i"); bar.style.height=Math.max(3,Math.round(x.pts/max*34))+"px";
      if(x.pts>=(P.daily_target||25)) bar.className="hit";
      bar.title=`${x.day}: ${x.pts} pts`;
      h.appendChild(bar);
    });
    c.appendChild(h);
    const legend = Object.entries(P.values||{})
      .map(([k,val])=>`<span class="tag">${k} +${val}</span>`).join(" ");
    c.appendChild(el("div","sb-foot",
      `${P.streak?`<b>${P.streak} day streak.</b> `:""}Last 14 days. ${legend}`));
    v.appendChild(c);
  }

  if(picks.length){
    v.appendChild(el("h2","sec","Apply"));
    picks.forEach(L=>v.appendChild(leadCard(L)));
  } else {
    v.appendChild(el("div","quiet","No fresh leads in the last week. That's a normal stretch — an empty brief is a valid output."));
  }
  if(restN>0){
    const more=el("div","quiet",
      `${restN} more open lead${restN===1?"":"s"} in the back catalogue — <a href="#" id="golead">Leads tab</a> when you want them.`);
    v.appendChild(more);
    const lk=more.querySelector("#golead");
    if(lk) lk.onclick=e=>{e.preventDefault();S.tab="leads";paintTabs();paint();};
  }

  if(steps.length){
    v.appendChild(el("h2","sec",`Study — pick any one (${stepsDone} done overall)`));
    const c=el("div","card");
    steps.forEach(s=>{
      const r=el("div","row");
      r.appendChild(checkbox(s.key,s.label,"study","",()=>{ paintTabs(); }));
      const m=el("div","meta");
      m.appendChild(el("div","ttl",esc(s.label)));
      const sb=el("div","sub");
      sb.appendChild(el("span","tag",`${s.hours}h`));
      sb.appendChild(el("span",null,esc(s.lane)));
      m.appendChild(sb); r.appendChild(m); c.appendChild(r);
    });
    v.appendChild(c);
  }

  const T = S.tasks||{};
  if((T.real||[]).length || (T.freebies||[]).length){
    v.appendChild(el("h2","sec","Checklist"));
    const c=el("div","card");
    (T.real||[]).concat(T.freebies||[]).forEach(t=>{
      const isFree=(T.freebies||[]).some(f=>f.key===t.key);
      const r=el("div","row");
      r.appendChild(checkbox(t.key,t.label,isFree?"freebie":"task",""));
      const m=el("div","meta");
      const tl=el("div","ttl",esc(t.label));
      if(t.needs_input) tl.appendChild(el("span","tag depri","needs a date from you"));
      m.appendChild(tl);
      const sb=el("div","sub");
      if(isFree) sb.appendChild(el("span","tag free","freebie +5"));
      if(t.mins) sb.appendChild(el("span","tag",`${t.mins} min`));
      if(t.deadline && t.deadline!=="UNKNOWN") sb.appendChild(el("span","tag hot",esc(t.deadline)));
      if(t.why) sb.appendChild(el("span",null,esc(t.why)));
      m.appendChild(sb); r.appendChild(m); c.appendChild(r);
    });
    v.appendChild(c);
  }

  const pinned=(S.notes.pinned||[]);
  if(pinned.length){
    v.appendChild(el("h2","sec","Worth knowing"));
    pinned.forEach(n=>v.appendChild(el("div","note",
      `<span class="when">${esc(n.date)} · ${esc(n.from||"")}</span>${md(n.text)}`)));
  }
}

function viewLeads(v){
  const f=el("div","filters");
  const nKilled = S.leads.filter(isKilled).length;
  [["open","Live"],["ready","Materials ready"],["fresh","Fresh"],["all","All"],
   ["expired","Expired"],["done","Applied"],
   ["killed", nKilled ? `Killed (${nKilled})` : "Killed"]]
    .forEach(([id,label])=>{
      const b=el("button",null,label);
      b.setAttribute("aria-pressed",S.filter===id);
      b.onclick=()=>{S.filter=id;paint();};
      f.appendChild(b);
    });
  v.appendChild(f);

  let list=S.leads.slice();
  // Killed leads drop out of every view except their own. His call: the red
  // filtering stays mostly out of sight, the count is the only thing on show.
  list = S.filter==="killed" ? list.filter(isKilled) : list.filter(L=>!isKilled(L));
  if(S.filter!=="all" && S.filter!=="expired" && S.filter!=="done" && S.filter!=="killed")
    list = list.filter(L=>!L.expired);
  const isDone=L=>!!(S.checks["applied-"+L.key]||{}).checked;
  if(S.filter==="open")  list=list.filter(L=>!isDone(L) && !L.expired);
  if(S.filter==="expired") list=list.filter(L=>L.expired);
  if(S.filter==="done")  list=list.filter(isDone);
  if(S.filter==="ready") list=list.filter(L=>L.ready&&!isDone(L));
  if(S.filter==="fresh") list=list.filter(L=>isHot(L.age) && !L.expired);

  if(!list.length){ v.appendChild(el("div","quiet","Nothing here.")); return; }
  let last="";
  list.forEach(L=>{
    if(L.brief_date!==last){ last=L.brief_date; v.appendChild(el("h2","sec",esc(last||"undated"))); }
    v.appendChild(leadCard(L));
  });
}

function viewStudy(v){
  const st=S.study||{}, gs=st.grad_school||{}, d=st.demand||{}, pend=st.pending_input;

  v.appendChild(el("div","hero",
    `<h1>Study</h1><p>${esc(st.how_this_works||"")}</p>`));

  if(pend){
    v.appendChild(el("div","note",
      `<span class="when">waiting on you · ${esc(pend.what||"")}</span>${md(pend.why||"")}
       <br><br><em>${esc(pend.until_then||"")}</em>`));
  }

  (st.lanes||[]).forEach(lane=>{
    const mods = lane.modules||[];
    const done = mods.filter(m=>(S.checks[m.key]||{}).checked).length;
    v.appendChild(el("h2","sec",`${esc(lane.name)} — ${done}/${mods.length}`));

    const c = el("div","card");
    const head = el("div","row click");
    const hm = el("div","meta");
    hm.appendChild(el("div","ttl",
      `<span class="tag">${esc(lane.status||"").split("—")[0].trim()}</span> ${esc(lane.name)}`));
    hm.appendChild(el("div","sub",
      `<span style="color:var(--fg-faint)">why this lane · click to expand</span>`));
    head.appendChild(hm); c.appendChild(head);
    const hd = el("div","detail",
      `<div class="md"><p style="margin:7px 0"><strong>${esc(lane.status||"")}</strong></p>
       ${md(lane.evidence||"")}${lane.note?`<blockquote>${mdi(lane.note)}</blockquote>`:""}</div>`);
    c.appendChild(hd);
    head.onclick = () => hd.classList.toggle("open");

    mods.forEach(m=>{
      const r=el("div","row");
      r.appendChild(checkbox(m.key, m.label, "study", "", ()=>{ paintTabs(); }));
      const mm=el("div","meta");
      mm.appendChild(el("div","ttl",esc(m.label)));
      const sb=el("div","sub");
      if(m.hours) sb.appendChild(el("span","tag",`${m.hours}h`));
      if(m.why) sb.appendChild(el("span",null,esc(m.why)));
      mm.appendChild(sb); r.appendChild(mm); c.appendChild(r);
    });
    v.appendChild(c);
  });

  /* grad school */
  v.appendChild(el("h2","sec","Grad school — open question"));
  const gc=el("div","card"); const gr=el("div","row click");
  const gm=el("div","meta");
  gm.appendChild(el("div","ttl",
    `Is a master's the unlock? <span class="tag">${esc(gs.status||"open")}</span>`));
  gm.appendChild(el("div","sub",`<span style="color:var(--fg-faint)">click to open — the case, both ways</span>`));
  gr.appendChild(gm); gc.appendChild(gr);

  let body = "";
  if(gs.the_unfinished_thread) body += `<h3>The thread you never finished</h3>${md(gs.the_unfinished_thread)}`;
  if(gs.what_you_have_said){
    body += `<h3>What you've said</h3>`;
    gs.what_you_have_said.forEach(q=>{ body += `<blockquote>${esc(q.quote)}<br><span style="color:var(--fg-faint);font-size:12px">— you, ${esc(q.date)}</span></blockquote>`; });
  }
  if(gs.what_was_answered_then) body += `<h3>What you were told then</h3>${md(gs.what_was_answered_then)}`;
  if(gs.what_changed) body += `<h3>What changed</h3>${md(gs.what_changed)}`;
  if(gs.the_honest_frame) body += `<h3>The honest frame</h3>${md(gs.the_honest_frame)}`;
  if(gs.concrete_option){
    const o=gs.concrete_option;
    body += `<h3>The one concrete option</h3><dl class="kv">
      <dt>Program</dt><dd><a href="${esc(o.url)}" target="_blank" rel="noopener">${esc(o.name)}</a></dd>
      <dt>Cost</dt><dd>${esc(o.cost)}</dd><dt>Format</dt><dd>${esc(o.format)}</dd>
      <dt>GPA floor</dt><dd>${esc(o.gpa_floor)}</dd></dl>${md(o.note)}`;
  }
  if(gs.before_any_application) body += `<h3>Before any application</h3>${md(gs.before_any_application)}`;
  if(gs.not_a_recommendation) body += `<h3>Not a recommendation</h3>${md(gs.not_a_recommendation)}`;
  const gd=el("div","detail",`<div class="md">${body}</div>`);
  gc.appendChild(gd); gr.onclick=()=>gd.classList.toggle("open");
  v.appendChild(gc);

  const J = st.what_the_jds_actually_say;
  if(J){
    v.appendChild(el("h2","sec","What the JDs actually say"));
    v.appendChild(el("div","note",
      `<span class="when">from the requirement bodies these sweeps have read</span>${mdi(J.note||"")}`));
    const mkJ=(title,arr)=>{ if(arr&&arr.length)
      v.appendChild(el("div","note", `<span class="when">${title}</span>` + bullets(arr))); };
    mkJ("what actually bites", J.what_actually_bites);
    mkJ("what shows up at zero years", J.what_reliably_appears_at_zero_years);
    mkJ("how to frame a study on a resume", J.how_to_frame_a_study_on_a_resume);
    mkJ("pragmatic vs dead end", J.pragmatic_vs_dead_end);
  }

  v.appendChild(el("h2","sec","Skill demand"));
  const mk=(title,arr)=>{ if(arr&&arr.length)
    v.appendChild(el("div","note", `<span class="when">${title}</span>` + bullets(arr))); };
  mk("you already clear these", d.clears_already);
  mk("cheap wins", d.cheap_wins);
  mk("structurally closed — stop spending time here", d.structurally_closed);
}

function viewAI(v){
  const p=S.platforms||{}, src=p.source||{};
  v.appendChild(el("div","hero",
    `<h1>AI training work</h1><p>${esc(p.why_this_tab_exists||"")}</p>`));
  v.appendChild(el("div","note",
    `<span class="when">source · ${esc(src.author||"")}</span>
     <a href="${esc(src.url||"#")}" target="_blank" rel="noopener">${esc(src.name||"")}</a> — ${md(src.why_trusted||"")}
     <br><br><b>${esc(src.his_totals||"")}</b>`));

  v.appendChild(el("h2","sec","Platforms"));
  (p.platforms||[]).forEach(pl=>{
    const c=el("div","card"); const r=el("div","row");
    r.appendChild(checkbox(pl.key,"Signed up: "+pl.name,"research",pl.url||""));
    r.appendChild(el("span","tier "+esc(pl.tier),esc(pl.tier)));
    const m=el("div","meta");
    m.appendChild(el("div","ttl",esc(pl.name)));
    m.appendChild(el("div","sub",
      `<span class="tag">paid ${esc(pl.paid)}</span><span class="tag">${esc(pl.rate)}</span>`));
    r.appendChild(m);
    if(pl.url){
      const a=el("a","apply"); a.href=pl.url; a.target="_blank"; a.rel="noopener";
      a.innerHTML=`<span class="ats">↗</span><span class="lbl">Review</span>`;
      a.onclick=e=>e.stopPropagation(); r.appendChild(a);
    }
    c.appendChild(r);
    if(pl.detail){
      const d=el("div","detail",`<div class="md">${md(pl.detail)}</div>`);
      c.appendChild(d); r.classList.add("click"); r.onclick=()=>d.classList.toggle("open");
    }
    v.appendChild(c);
  });

  if(p.screening_rules){
    v.appendChild(el("h2","sec","Screening rules — same bar as any lead"));
    v.appendChild(el("div","note", bullets(p.screening_rules)));
  }
}

function viewBriefs(v){
  v.appendChild(el("div","hero",
    `<h1>Briefs</h1><p>${S.briefs.length} sweeps archived. Newest first.</p>`));
  S.briefs.forEach(b=>{
    const c=el("div","card"); const r=el("div","row click");
    const m=el("div","meta");
    m.appendChild(el("div","ttl",`${esc(b.date)} <span class="tag">${esc(b.slot)}</span>`));
    m.appendChild(el("div","sub",
      `<span>${b.leads.length} lead${b.leads.length===1?"":"s"}</span>
       <span style="color:var(--fg-faint)">· ${Math.round((b.bytes||0)/1024)} KB</span>`));
    r.appendChild(m); c.appendChild(r);
    const d=el("div","detail",`<div class="md" data-file="${esc(b.file)}">…</div>`);
    c.appendChild(d);
    r.onclick=()=>{
      d.classList.toggle("open");
      const tgt=d.querySelector(".md");
      if(tgt.dataset.loaded) return;
      tgt.innerHTML = md(S.raw[b.file] || "_Brief body not cached — open the file directly._");
      tgt.dataset.loaded="1";
    };
    v.appendChild(c);
  });
}

function viewNotes(v){
  v.appendChild(el("div","hero",
    `<h1>Notes</h1><p>Yours and the pipeline's. Anything you write here lands in the next sweep.</p>`));
  const ta=el("textarea","jot"); ta.placeholder="Something to remember, a question for the next sweep, a correction…";
  const b=el("button","btn","Save note");
  b.onclick=async()=>{
    const t=ta.value.trim(); if(!t) return;
    const r=await post("note",{text:t,tab:"notes"});
    if(r){ ta.value=""; S.pending=r.pending;
           toast("<b>✓</b> Saved · the next sweep will read it"); paint(); }
  };
  v.appendChild(ta); v.appendChild(b);

  if((S.notes.pinned||[]).length){
    v.appendChild(el("h2","sec","Pinned"));
    S.notes.pinned.forEach(n=>v.appendChild(el("div","note",
      `<span class="when">${esc(n.date)} · ${esc(n.from||"")}</span>${md(n.text)}`)));
  }
  if((S.notes.from_the_plugin||[]).length){
    v.appendChild(el("h2","sec","From the sweeps"));
    S.notes.from_the_plugin.forEach(n=>v.appendChild(el("div","note",
      `<span class="when">${esc(n.date)}</span>${md(n.text)}`)));
  }
  if(S.pending){
    v.appendChild(el("h2","sec","Queued"));
    v.appendChild(el("div","note",
      `<b>${S.pending}</b> tick${S.pending===1?"":"s"} and note${S.pending===1?"":"s"} waiting for the next sweep.
       They're saved to disk — shutting down or skipping a run can't lose them.`));
  }
}

/* =====================================================================
   Events · Calendar · Log · Ask bar
   Events come from events.md (the IRL event finder). Pins and wins go
   through the same fsync'd event log as a checkbox, so they survive a
   shutdown and the next sweep sees them.
   ===================================================================== */

async function refreshCal(){
  const [p,h] = await Promise.all([get("pins"), get("history")]);
  if(p) S.pins=p.pins||[]; if(h) S.history=h;
}

function upcomingEvents(days=60){
  const t=todayISO();
  const lim=iso(new Date(Date.now()+days*864e5));
  return S.events.filter(e=>e.date>=t && e.date<=lim && !e.killed && !e.social);
}

function whenLine(e){
  const parts=[];
  parts.push(`<span class="start">${e.start?`Starts ${esc(e.start)}`:"Time TBD"} ${esc(fmtDay(e.date))}</span>`);
  if(e.leave_by) parts.push(`<span class="leave">Leave by ${esc(e.leave_by)}</span>`);
  if(e.end) parts.push(`<span>ends ${esc(e.end)}</span>`);
  parts.push(`<span class="faint">${esc(relDay(e.date))}</span>`);
  return `<div class="when-line">${parts.join('<span class="sep">/</span>')}</div>`;
}

function pinnedFor(e){ return S.pins.find(p=>p.event_id===e.id); }

async function pinEvent(e, btn){
  const existing = pinnedFor(e);
  if(existing){
    const r=await post("unpin",{id:existing.id});
    if(r){ S.pins=r.pins; toast("Unpinned"); }
  } else {
    const r=await post("pin",{date:e.date,time:e.start24||"",title:e.title,
      note:[e.leave_by?`Leave by ${e.leave_by}`:"", e.venue||"", e.url||""].filter(Boolean).join(" · "),
      event_id:e.id});
    if(r){ S.pins=r.pins; toast(`<b>✓</b> Pinned to ${esc(fmtDay(e.date))}`); }
  }
  paint();
}

async function markWent(e){
  await post("check",{key:"event-went-"+e.id,checked:true,label:`Went to ${e.title}`,kind:"event",url:e.url||""});
  await refreshCal(); get("points").then(pt=>{ if(pt){S.points=pt; paintScore();} });
  toast(`<b>✓</b> Logged · ${esc(e.title)}`); paint();
}

function eventCard(e){
  const past = e.date < todayISO();
  const went = e.status==="WENT" || e.status==="ATTENDED" || !!(S.checks["event-went-"+e.id]||{}).checked;
  const c=el("div",`card ev${past?" past":""}${went?" went":""}${e.killed?" killed":""}`);
  const r=el("div","row click");
  const m=el("div","meta");
  m.innerHTML = whenLine(e)
    + `<h3 class="ev-title">${esc(e.title)}</h3>`
    + `<div class="ev-where">${esc(e.venue||"Venue not captured")}</div>`;
  const tags=el("div","sub"); tags.style.marginTop="9px";
  if(e.tier) tags.appendChild(el("span","tag tier",esc(e.tier)));
  if(e.cost) tags.appendChild(el("span","tag"+(/free/i.test(e.cost)?" free":""),esc(e.cost.split(/[,(]/)[0])));
  if(went) tags.appendChild(el("span","tag went","went"));
  else if(e.status) tags.appendChild(el("span","tag",esc(e.status.toLowerCase())));
  if(pinnedFor(e)) tags.appendChild(el("span","tag hot","pinned"));
  if(e.killed) tags.appendChild(el("span","tag expired","killed"));
  if(e.runs>1) tags.appendChild(el("span","faint",`seen in ${e.runs} runs`));
  m.appendChild(tags);
  if(e.status_note) m.appendChild(el("div","ev-catch",`<b>YOU</b>${mdi(e.status_note)}`)).style.background="var(--good-soft)";
  else if(e.catch && !past) m.appendChild(el("div","ev-catch",`<b>CATCH</b>${mdi(e.catch)}`));
  r.appendChild(m);

  const side=el("div","ev-side");
  if(e.url){
    const a=el("a","apply"); a.href=e.url; a.target="_blank"; a.rel="noopener";
    a.innerHTML=`<span class="ats">↗</span><span class="lbl">Event page</span>`;
    a.onclick=ev=>ev.stopPropagation(); side.appendChild(a);
  }
  r.appendChild(side);
  c.appendChild(r);

  const acts=el("div","ev-actions");
  if(!past && !e.killed){
    const pb=el("button","btn sm "+(pinnedFor(e)?"ghost":"accent"), pinnedFor(e)?"Unpin":"Pin to calendar");
    pb.onclick=ev=>{ev.stopPropagation(); pinEvent(e,pb);};
    acts.appendChild(pb);
  }
  if(past && !went && !e.killed){
    const wb=el("button","btn sm ghost","I went");
    wb.onclick=ev=>{ev.stopPropagation(); markWent(e);};
    acts.appendChild(wb);
  }
  const cb=el("button","btn sm ghost","Show on calendar");
  cb.onclick=ev=>{ev.stopPropagation(); const d=parseISO(e.date); S.calMonth=[d.getFullYear(),d.getMonth()]; S.calSel=e.date; go("calendar");};
  acts.appendChild(cb);
  m.appendChild(acts);

  let body = e.desc ? `<p style="margin:0 0 10px">${mdi(e.desc)}</p>` : "";
  body += `<h3>As logged by the event finder</h3>` + (e.history||[{run:e.last_seen,line:e.line}])
     .slice().reverse().map(h=>`<p style="margin:8px 0"><span class="mono faint" style="font-size:11px">${esc(h.run)} run</span><br>${mdi(h.line.replace(/^[-*\s]+/,""))}</p>`).join("");
  if((e.aliases||[]).length) body += `<p class="faint" style="font-size:12px">Also logged as: ${e.aliases.map(esc).join(" · ")}</p>`;
  const d=el("div","detail",`<div class="md">${body}</div>`);
  c.appendChild(d);
  r.onclick=()=>d.classList.toggle("open");
  return c;
}

function viewEvents(v){
  const up=upcomingEvents(120);
  const h=el("div","hero");
  h.innerHTML=`<div><span class="eyebrow">IRL event finder · runs Mon + Thu</span><h1>Events</h1>
    <p>${up.length?`${up.length} upcoming, ranked by who's in the room and whether you can get in. Pin one and it lands on the calendar.`:"Nothing upcoming in the log. The next run will fill this."}</p></div>`;
  v.appendChild(h);
  const f=el("div","filters");
  [["upcoming","Upcoming"],["week","Next 7 days"],["went","Went"],["past","Past"],["social","Social"],["kills","Kill log"]].forEach(([id,label])=>{
    const b=el("button",null,label); b.setAttribute("aria-pressed",S.evFilter===id);
    b.onclick=()=>{S.evFilter=id; paint();}; f.appendChild(b);
  });
  v.appendChild(f);

  if(S.evFilter==="kills"){
    v.appendChild(el("h2","sec",`Killed <span class="count">${S.kills.length}</span>`));
    v.appendChild(el("p","faint","Logged so the next run doesn't re-chase dead ends. Newest first."));
    S.kills.slice().reverse().slice(0,250).forEach(k=>{
      v.appendChild(el("div","kill-row",`<span class="k-run">${esc(k.run)}</span><span class="k-ev">${esc(k.event)}</span><span class="k-why">${mdi(k.reason)}</span>`));
    });
    return;
  }
  const t=todayISO();
  let list;
  if(S.evFilter==="upcoming") list=up;
  else if(S.evFilter==="week") list=upcomingEvents(7);
  else if(S.evFilter==="social") list=S.events.filter(e=>e.social && e.date>=t);
  else if(S.evFilter==="went") list=S.events.filter(e=>e.status==="WENT"||e.status==="ATTENDED"||(S.checks["event-went-"+e.id]||{}).checked).reverse();
  else list=S.events.filter(e=>e.date<t).reverse();
  if(!list.length){ v.appendChild(el("div","quiet","Nothing here.")); return; }
  let last="";
  list.forEach(e=>{
    const d=parseISO(e.date);
    const wk = S.evFilter==="past"||S.evFilter==="went" ? `${MONTHS_FULL[d.getMonth()]} ${d.getFullYear()}`
      : daysFrom(e.date)<7 ? "This week" : daysFrom(e.date)<14 ? "Next week" : `${MONTHS_FULL[d.getMonth()]}`;
    if(wk!==last){ last=wk; v.appendChild(el("h2","sec",esc(wk))); }
    v.appendChild(eventCard(e));
  });
}

/* ---------- calendar ---------- */
function itemsForDay(ds){
  const evs=S.events.filter(e=>e.date===ds && !e.killed);
  const pins=S.pins.filter(p=>p.date===ds);
  const done=((S.history.days||{})[ds]||[]).filter(x=>x.kind!=="sweep");
  return {evs,pins,done};
}

function viewCalendar(v){
  const now=new Date();
  if(!S.calMonth) S.calMonth=[now.getFullYear(),now.getMonth()];
  if(!S.calSel) S.calSel=todayISO();
  const [Y,M]=S.calMonth;
  const head=el("div","cal-head");
  head.innerHTML=`<div><span class="eyebrow">Events, pins and everything you got done</span>
    <h1>${MONTHS_FULL[M]} <span>${Y}</span></h1></div>`;
  const nav=el("div","cal-nav");
  const mv=delta=>{ let y=Y, m=M+delta; if(m<0){m=11;y--;} if(m>11){m=0;y++;} S.calMonth=[y,m]; paint(); };
  [["‹",()=>mv(-1),"Previous month"],["Today",()=>{S.calMonth=[now.getFullYear(),now.getMonth()];S.calSel=todayISO();paint();},"Jump to today"],["›",()=>mv(1),"Next month"]]
    .forEach(([t,fn,lab])=>{const b=el("button",null,t); b.onclick=fn; b.setAttribute("aria-label",lab); nav.appendChild(b);});
  head.appendChild(nav); v.appendChild(head);

  v.appendChild(el("div","cal-legend",
    `<span><i style="background:var(--ev)"></i>event</span><span><i style="background:var(--accent)"></i>pinned</span>
     <span><i style="background:var(--good);border-radius:50%"></i>something you did</span>`));

  const g=el("div","calendar");
  ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"].forEach(d=>g.appendChild(el("div","dow",d)));
  const first=new Date(Y,M,1);
  const start=new Date(Y,M,1-((first.getDay()+6)%7));
  const t=todayISO();
  for(let i=0;i<42;i++){
    const d=new Date(start.getFullYear(),start.getMonth(),start.getDate()+i);
    if(i>=35 && d.getMonth()!==M) break;
    const ds=iso(d);
    const {evs,pins,done}=itemsForDay(ds);
    const cell=el("button","day"+(d.getMonth()!==M?" out":"")+(ds===t?" today":"")+(ds===S.calSel?" sel":""));
    cell.setAttribute("aria-label",`${fmtDay(ds)}: ${evs.length} events, ${pins.length} pins, ${done.length} done`);
    cell.innerHTML=`<span class="dn"><b>${d.getDate()}</b>${done.length?`<span class="done-count">${done.length} done</span>`:""}</span>`;
    const pinnedIds=new Set(pins.map(p=>p.event_id).filter(Boolean));
    const chips=[];
    pins.forEach(p=>chips.push(`<span class="chip pin">${p.time?`<span class="tm">${esc(fmt12(p.time).replace(":00",""))}</span>`:""}${esc(p.title)}</span>`));
    evs.filter(e=>!pinnedIds.has(e.id)).forEach(e=>{
      const went=e.status==="WENT"||(S.checks["event-went-"+e.id]||{}).checked;
      chips.push(`<span class="chip ev${e.social?" social":""}${went?" went":""}${ds<t?" past":""}">${e.start?`<span class="tm">${esc(e.start.replace(":00","").replace(" ",""))}</span>`:""}${esc(e.title)}</span>`);
    });
    cell.innerHTML += chips.slice(0,3).join("") + (chips.length>3?`<span class="chip more">+${chips.length-3} more</span>`:"");
    cell.onclick=()=>{ S.calSel=ds; paint(); setTimeout(()=>$("#dayview")?.scrollIntoView({behavior:"smooth",block:"start"}),30); };
    g.appendChild(cell);
  }
  v.appendChild(g);

  /* ---- the selected day ---- */
  const ds=S.calSel, {evs,pins,done}=itemsForDay(ds);
  const dv=el("div","dayview"); dv.id="dayview";
  const dd=parseISO(ds);
  dv.appendChild(el("h2","big",`${["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"][dd.getDay()]}, ${MONTHS_FULL[dd.getMonth()]} ${dd.getDate()} <span class="faint" style="font-size:15px;font-family:var(--mono);font-weight:400">· ${esc(relDay(ds))}</span>`));

  const left=el("div");
  left.appendChild(el("h2","sec",`On the calendar <span class="count">${evs.length+pins.length}</span>`));
  const sched=[...pins.map(p=>({t:p.time||"99",p})), ...evs.filter(e=>!pins.some(p=>p.event_id===e.id)).map(e=>({t:e.start24||"99",e}))]
    .sort((a,b)=>a.t.localeCompare(b.t));
  if(!sched.length) left.appendChild(el("div","faint",`<p style="font-size:13.5px;margin:10px 0">Nothing scheduled.</p>`));
  sched.forEach(({p,e})=>{
    const it=el("div","item");
    if(p){
      const ev=p.event_id && S.events.find(x=>x.id===p.event_id);
      it.innerHTML=`<span class="k pin"></span><div class="body">
        <div class="when-line" style="margin-bottom:3px"><span class="leave">${p.time?"Starts "+esc(fmt12(p.time)):"All day"}</span>${ev&&ev.leave_by?`<span class="sep">/</span><span class="leave">Leave by ${esc(ev.leave_by)}</span>`:""}</div>
        <div><b>${esc(p.title)}</b></div>${p.note?`<div class="s">${mdi(p.note)}</div>`:""}
        ${ev&&ev.catch?`<div class="s" style="color:var(--warn)">Catch: ${mdi(ev.catch)}</div>`:""}</div>`;
      const x=el("button","x","remove"); x.title="Unpin";
      x.onclick=async()=>{ const r=await post("unpin",{id:p.id}); if(r){S.pins=r.pins; toast("Unpinned"); paint();} };
      it.appendChild(x);
    } else {
      it.innerHTML=`<span class="k ev"></span><div class="body">${whenLine(e).replace('class="when-line"','class="when-line" style="margin-bottom:3px"')}
        <div><b>${esc(e.title)}</b> ${e.tier?`<span class="tag tier">${esc(e.tier)}</span>`:""}</div>
        <div class="s">${esc(e.venue||"")}${e.cost?" · "+esc(e.cost.split(/[,(]/)[0]):""}</div>
        ${e.catch&&ds>=todayISO()?`<div class="s" style="color:var(--warn)">Catch: ${mdi(e.catch)}</div>`:""}
        ${e.url?`<div class="s"><a href="${esc(e.url)}" target="_blank" rel="noopener">${esc(e.url.replace(/^https?:\/\//,""))}</a></div>`:""}</div>`;
      if(ds>=todayISO()){
        const pb=el("button","x","pin"); pb.title="Pin to calendar"; pb.onclick=()=>pinEvent(e); it.appendChild(pb);
      }
    }
    left.appendChild(it);
  });
  const pf=el("form","inline-form");
  pf.innerHTML=`<input class="field time" type="time" aria-label="Time (optional)"><input class="field" placeholder="Pin something to ${esc(fmtDay(ds))}…" aria-label="What to pin"><button class="btn sm accent" type="submit">Pin</button>`;
  pf.onsubmit=async ev=>{ ev.preventDefault();
    const [tm,tt]=pf.querySelectorAll("input"); if(!tt.value.trim()) return;
    const r=await post("pin",{date:ds,time:tm.value,title:tt.value.trim()});
    if(r){ S.pins=r.pins; toast(`<b>✓</b> Pinned to ${esc(fmtDay(ds))}`); paint(); } };
  left.appendChild(pf);
  dv.appendChild(left);

  const right=el("div");
  right.appendChild(el("h2","sec",`Done <span class="count">${done.length}</span>`));
  if(!done.length) right.appendChild(el("div","faint",`<p style="font-size:13.5px;margin:10px 0">${ds>todayISO()?"Hasn't happened yet.":"Nothing logged for this day."}</p>`));
  done.forEach(x=>right.appendChild(logItem(x)));
  const sweeps=((S.history.days||{})[ds]||[]).filter(x=>x.kind==="sweep");
  sweeps.forEach(x=>right.appendChild(logItem(x)));
  if(ds<=todayISO()) right.appendChild(winForm(ds));
  dv.appendChild(right);
  v.appendChild(dv);
}

function logItem(x){
  const it=el("div","item");
  const src = x.source==="applied.md"?"applied.md":x.source==="events.md"?"event finder":x.source==="you"?"you logged this":x.source==="workspace"?"pipeline":x.kind;
  it.innerHTML=`<span class="k ${esc(x.kind)}"></span><div class="body"><div>${mdi(x.label)}</div>
    <div class="s">${esc(src)}${x.detail?" · "+mdi(x.detail):""}</div></div>`;
  return it;
}

function winForm(ds){
  const f=el("form","inline-form");
  f.innerHTML=`<input class="field" placeholder="${ds===todayISO()?"Log something you did today…":"Log something you did on "+esc(fmtDay(ds))+"…"}" aria-label="Log something you did"><button class="btn sm" type="submit">Log it</button>`;
  f.onsubmit=async ev=>{ ev.preventDefault(); const i=f.querySelector("input"); const t=i.value.trim(); if(!t) return;
    const r=await post("win",{date:ds,text:t});
    if(r){ S.history=r.history; get("points").then(pt=>{ if(pt){S.points=pt; paintScore();} });
      toast("<b>✓</b> Logged"); paint(); } };
  return f;
}

/* ---------- running log ---------- */
function viewLog(v){
  const days=S.history.days||{};
  const keys=Object.keys(days).filter(d=>d<=todayISO()).sort().reverse();
  const total=keys.reduce((n,d)=>n+days[d].filter(x=>x.kind!=="sweep").length,0);
  v.appendChild(el("div","hero",`<div><span class="eyebrow">Running history</span><h1>Log</h1>
    <p>${total} things done across ${keys.filter(d=>days[d].some(x=>x.kind!=="sweep")).length} days. Applications, study, events, and anything you log by hand or through the ask bar.</p></div>`));
  v.appendChild(winForm(todayISO()));
  let shown=0;
  keys.forEach(d=>{
    const items=days[d].filter(x=>x.kind!=="sweep");
    if(!items.length || shown>90) return;
    shown++;
    const row=el("div","log-day");
    const dd=parseISO(d);
    row.appendChild(el("div","log-date",`<b>${MON[dd.getMonth()]} ${dd.getDate()}</b><span>${DOW[dd.getDay()]} · ${items.length} done</span>`));
    const col=el("div"); items.forEach(x=>col.appendChild(logItem(x)));
    row.appendChild(col); v.appendChild(row);
  });
  if(!shown) v.appendChild(el("div","quiet","Nothing logged yet."));
}

/* ---------- the rail on Today ---------- */
function upNext(limit=6){
  const t=todayISO(), lim=iso(new Date(Date.now()+21*864e5));
  const pinnedIds=new Set(S.pins.map(p=>p.event_id).filter(Boolean));
  const items=[
    ...S.pins.filter(p=>p.date>=t && p.date<=lim).map(p=>({date:p.date,t:p.time||"99",pin:p})),
    ...upcomingEvents(21).filter(e=>!pinnedIds.has(e.id)).map(e=>({date:e.date,t:e.start24||"99",ev:e})),
  ].sort((a,b)=>(a.date+a.t).localeCompare(b.date+b.t));
  return items.slice(0,limit);
}

function rail(){
  const r=el("aside","rail");
  r.appendChild(el("h2","sec","Up next"));
  const items=upNext(6);
  if(!items.length) r.appendChild(el("p","faint","Nothing on the calendar for three weeks."));
  const ul=el("ul","upnext");
  items.forEach(x=>{
    const d=parseISO(x.date);
    const li=el("li", x.pin?"pin":"");
    const title = x.pin ? x.pin.title : x.ev.title;
    const time = x.pin ? (x.pin.time?fmt12(x.pin.time):"") : (x.ev.start||"");
    const extra = x.pin ? "pinned" : (x.ev.leave_by?`leave ${x.ev.leave_by}`:(x.ev.cost||"").split(/[,(]/)[0]);
    li.innerHTML=`<div class="d"><b>${d.getDate()}</b><span>${DOW[d.getDay()]}</span></div>
      <div><div class="t">${esc(title)}</div><div class="s">${time?`<span class="start">${esc(time)}</span> · `:""}${esc(extra||"")}</div></div>`;
    li.onclick=()=>{ S.calMonth=[d.getFullYear(),d.getMonth()]; S.calSel=x.date; go("calendar"); };
    ul.appendChild(li);
  });
  r.appendChild(ul);
  const done=((S.history.days||{})[todayISO()]||[]).filter(x=>x.kind!=="sweep");
  r.appendChild(el("h2","sec",`Today's log <span class="count">${done.length}</span>`));
  done.slice(0,8).forEach(x=>r.appendChild(logItem(x)));
  r.appendChild(winForm(todayISO()));
  return r;
}

/* ---------- ask bar ---------- */
function paintThread(){
  const t=$("#thread");
  if(!S.thread.length){ t.hidden=true; return; }
  t.hidden=false;
  const box=el("div","thread-in");
  S.thread.slice(-8).forEach(m=>{
    const d=el("div","msg "+m.role);
    d.innerHTML=`<span class="who">${m.role==="q"?"you":esc(m.engine==="local"?"dashboard":m.engine==="offline"?"offline":"claude")}</span><div class="body">${m.role==="a"?mdi(m.text):esc(m.text)}</div>`;
    if(m.acts&&m.acts.length){
      const a=el("div","acts");
      m.acts.forEach(x=>a.appendChild(el("span","tag "+(x.k==="pin"?"hot":"went"),esc(x.t))));
      d.appendChild(a);
    }
    box.appendChild(d);
  });
  const foot=el("div","thread-foot");
  foot.innerHTML=`<span>pin · remind · log are instant · everything else asks ${S.engine==="offline"?"(no model found)":"Claude"}</span>`;
  const cl=el("button",null,"clear"); cl.onclick=()=>{S.thread=[]; paintThread();};
  foot.appendChild(cl); box.appendChild(foot);
  t.innerHTML=""; t.appendChild(box);
  box.scrollTop=box.scrollHeight;
}

function wireAsk(){
  const f=$("#ask"), q=$("#askq");
  document.addEventListener("keydown",e=>{
    if(e.key==="/" && !/input|textarea/i.test(document.activeElement.tagName)){ e.preventDefault(); q.focus(); }
    if(e.key==="Escape" && document.activeElement===q){ q.blur(); $("#thread").hidden=true; }
  });
  q.addEventListener("focus",()=>{ if(S.thread.length) $("#thread").hidden=false; });
  f.onsubmit=async e=>{
    e.preventDefault();
    const text=q.value.trim(); if(!text) return;
    q.value=""; S.thread.push({role:"q",text}); paintThread();
    f.classList.add("busy"); q.placeholder="Thinking…";
    let r=null;
    try{ r=await post("ask",{q:text}); }catch(err){ r=null; }
    f.classList.remove("busy"); q.placeholder="Ask anything · pin agent fair dec 15 6pm · log got 2 refs";
    if(!r){ S.thread.push({role:"a",text:"Couldn't reach the dashboard server.",engine:"offline"}); paintThread(); return; }
    const acts=[...(r.pins||[]).map(p=>({k:"pin",t:`pinned ${fmtDay(p.date)}${p.time?" "+fmt12(p.time):""}: ${p.title}`})),
                ...(r.wins||[]).map(w=>({k:"win",t:`logged ${fmtDay(w.date)}`}))];
    S.thread.push({role:"a",text:r.reply||"",engine:r.engine,acts}); paintThread();
    if(acts.length){ await refreshCal(); get("points").then(pt=>{ if(pt){S.points=pt; paintScore();} }); paintTabs(); paint(); }
  };
}

function paint(){
  const v=$("#view"); v.innerHTML="";
  ({today:viewToday,calendar:viewCalendar,events:viewEvents,log:viewLog,leads:viewLeads,study:viewStudy,
    ai:viewAI,briefs:viewBriefs,notes:viewNotes}[S.tab]||viewToday)(v);
  window.scrollTo({top:0,behavior:"instant"});
}

/* ---------- boot ---------- */
(async function(){
  wireAsk();
  $("#theme").onclick=()=>{
    const cur=document.documentElement.getAttribute("data-theme")==="light"?"dark":"light";
    document.documentElement.setAttribute("data-theme",cur);
    try{localStorage.setItem("jh.theme",cur);}catch(e){}
  };
  try{ const t=localStorage.getItem("jh.theme"); if(t) document.documentElement.setAttribute("data-theme",t);
       const tb=localStorage.getItem("jh.tab"); if(tb) S.tab=tb;
       const ld=localStorage.getItem("jh.load"); if(ld) S.load=+ld; }catch(e){}

  const [leads,briefs,raw,stats,checks,study,platforms,notes,queue,tasks,events,pins,history,engine,lk] = await Promise.all(
    ["leads","briefs","briefs_raw","stats","checks","study","platforms","notes","queue","tasks",
     "events","pins","history","engine","leadkills"].map(get));
  { const br = (await get("buildreqs"))||{};
    S.buildreqs = br.buildreqs||{}; S.buildstatus = br.status||{}; S.buildInstant = !!br.instant; }
  S.leadkills=(lk||{}).leadkills||{}; S.killPresets=(lk||{}).presets||{};
  S.events=(events||{}).events||[]; S.kills=(events||{}).kills||[];
  S.pins=(pins||{}).pins||[]; S.history=history||{days:{}};
  S.engine=(engine||{}).engine||"offline";
  const eng=$("#askeng");
  if(eng){ eng.textContent = S.engine==="offline" ? "offline" : S.engine==="api" ? "Claude API" : "Claude";
           eng.classList.toggle("live", S.engine!=="offline");
           eng.title = S.engine==="offline"
             ? "No model found: pin/log commands still work. Install Claude Code or set ANTHROPIC_API_KEY for answers."
             : "Questions go to "+(S.engine==="api"?"the Anthropic API":"your Claude Code CLI"); }
  S.points = (await get("points")) || {};
  S.tasks = tasks||{};
  S.leads=leads||[]; S.briefs=briefs||[]; S.raw=raw||{}; S.stats=stats||{};
  S.checks=(checks||{}).checks||{}; S.study=study||{}; S.platforms=platforms||{};
  S.notes=notes||{}; S.pending=(queue||{}).pending||0;

  $("#brandsub").textContent =
    `${S.stats.applied_count||0} applied · ${(S.stats.screened_out||0).toLocaleString()} screened · sweep ${S.stats.latest_brief||"—"}`;

  paintTabs(); paintScore(); paint();
})();
