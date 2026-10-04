#!/usr/bin/env python3
"""Render the conceptual layer as one interactive field: forces, pushes, phases, chains, assumptions.

Self contained HTML: the data is inlined, the layout and the interaction run in the page. This is the
representation for reading the mechanism, not for auditing the index.

    python3 scripts/render_concept_field.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN = ROOT / "docs" / "scan"
OUT = SCAN / "field.html"


def load(name: str) -> list[dict]:
    path = SCAN / name
    return [json.loads(line) for line in path.open() if line.strip()] if path.exists() else []


def main() -> int:
    forces = load("forces.jsonl")
    interactions = load("interactions.jsonl")
    assumptions = load("assumptions.jsonl")
    chains = load("conceptual-chains.jsonl")
    summary = json.loads((SCAN / "conceptual-summary.json").read_text()) if (SCAN / "conceptual-summary.json").exists() else {}

    payload = {
        "forces": [{k: f.get(k) for k in ("id", "domain", "name", "meaning", "direction", "observables", "payer",
                                            "out_interactions", "in_interactions", "degree")} for f in forces],
        "interactions": [{k: i.get(k) for k in ("from", "to", "relation", "channel", "condition", "assumption",
                                                "kill", "lag", "load", "sign_by_phase", "evidence")}
                         for i in interactions],
        "assumptions": [{k: a.get(k) for k in ("id", "statement", "test", "kill", "owner", "load")}
                        for a in assumptions],
        "chains": [{k: c.get(k) for k in ("id", "title", "hops", "intuition", "greatest_assumption",
                                          "observation", "sign_by_phase")} for c in chains],
        "summary": summary,
    }
    data = json.dumps(payload, separators=(",", ":"))

    OUT.write_text(HTML.replace("__DATA__", data))
    print(f"wrote {OUT.relative_to(ROOT)}: {len(forces)} forces, {len(interactions)} interactions, "
          f"{len(chains)} chains, {len(assumptions)} assumptions")
    return 0


HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>The field: forces, pushes, phases, chains</title>
<style>
 :root{--bg:#0b0e13;--panel:#121722;--line:#232b3a;--text:#e6edf3;--dim:#8b949e;--drive:#3fb950;--dampen:#f85149;
  --gate:#d29922;--sub:#a371f7;--reveal:#58a6ff;--crowd:#39c5cf;--fin:#2dd4bf;--price:#e3b341;--mix:#db6d28;}
 *{box-sizing:border-box}
 body{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
 header{padding:1.1rem 1.4rem;border-bottom:1px solid var(--line);display:flex;gap:2rem;flex-wrap:wrap;align-items:baseline}
 header h1{font-size:1.15rem;margin:0}
 header .meta{color:var(--dim);font-size:.82rem}
 main{display:grid;grid-template-columns:minmax(0,1fr) 380px;gap:0;height:calc(100vh - 62px)}
 #left{position:relative;overflow:hidden;border-right:1px solid var(--line)}
 #right{overflow:auto;padding:1rem 1.1rem 3rem}
 .controls{position:absolute;top:.7rem;left:.7rem;z-index:5;background:rgba(18,23,34,.92);border:1px solid var(--line);
  border-radius:10px;padding:.6rem .7rem;font-size:.78rem;max-width:330px}
 .controls label{display:inline-flex;align-items:center;gap:.3rem;margin:.1rem .45rem .1rem 0;cursor:pointer}
 .controls select,.controls input[type=range],.controls input[type=text]{background:#0e131c;color:var(--text);
  border:1px solid var(--line);border-radius:6px;padding:.15rem .3rem;font-size:.78rem}
 .legend{display:flex;flex-wrap:wrap;gap:.5rem;margin-top:.4rem;color:var(--dim)}
 .legend span{display:inline-flex;align-items:center;gap:.3rem}
 .swatch{width:12px;height:3px;border-radius:2px;display:inline-block}
 svg{display:block;width:100%;height:100%}
 .edge{stroke-opacity:.55}
 .edge.dim{stroke-opacity:.06}
 .node circle{stroke:#0b0e13;stroke-width:1.5;cursor:pointer}
 .node text{fill:var(--dim);font-size:8.5px;pointer-events:none}
 .node.hidden{display:none}
 h2{font-size:.95rem;margin:1.1rem 0 .4rem}
 h3{font-size:.85rem;margin:.9rem 0 .3rem;color:var(--text)}
 .card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:.6rem .7rem;margin:.45rem 0}
 .card .why{color:var(--dim);font-size:.78rem}
 .io{display:grid;grid-template-columns:1fr;gap:.25rem;font-size:.78rem}
 .io div span{color:var(--dim)}
 .pill{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:.05rem .45rem;margin:.1rem .15rem;
  font-size:.72rem;cursor:pointer;color:var(--text);background:#0e131c}
 .pill:hover{border-color:#58a6ff}
 .chain{border-left:2px solid var(--line);padding-left:.6rem;margin:.6rem 0}
 .chain .hops{display:flex;flex-wrap:wrap;gap:.3rem;align-items:center}
 .arrow{color:var(--dim)}
 table{border-collapse:collapse;width:100%;font-size:.72rem;margin-top:.3rem}
 th,td{border:1px solid var(--line);padding:.16rem .3rem;text-align:left;white-space:nowrap}
 th{background:#0e131c;color:var(--dim);font-weight:500}
 td.pos{background:rgba(63,185,80,.22)} td.neg{background:rgba(248,81,73,.22)} td.zero{background:#0e131c;color:var(--dim)}
</style></head><body>
<header>
 <h1>The field</h1>
 <div class="meta" id="headline"></div>
 <div class="meta">every edge is an inference: it carries a condition, an assumption and a kill. Click any force.</div>
</header>
<main>
 <div id="left">
  <div class="controls">
   <div><input id="search" type="text" placeholder="search a force" style="width:150px">
    load at least <input id="load" type="range" min="1" max="5" value="1" style="width:80px"><span id="loadval">1</span>
    phase <select id="phase"><option value="">stable only</option><option value="shortage">shortage</option>
     <option value="buildout">buildout</option><option value="overbuild">overbuild</option>
     <option value="shakeout">shakeout</option><option value="second_wave">second wave</option></select></div>
   <div id="relations" style="margin-top:.3rem"></div>
   <div class="legend" id="legend"></div>
  </div>
  <svg id="map"></svg>
 </div>
 <div id="right">
  <div id="detail"></div>
  <h2>Chains, the intuition made addressable</h2>
  <div id="chains"></div>
  <h2>Phase field, net sign per force</h2>
  <div id="matrix"></div>
 </div>
</main>
<script>
const DATA = __DATA__;
const RELCOLOR = {drives:"var(--drive)",dampens:"var(--dampen)",gates:"var(--gate)",delays:"var(--gate)",
 accelerates:"var(--drive)",substitutes:"var(--sub)",complements:"var(--fin)",competes_for:"var(--sub)",
 crowds_in:"var(--crowd)",crowds_out:"var(--crowd)",transmits:"var(--reveal)",reveals:"var(--reveal)",
 conditions:"var(--price)",prices:"var(--price)",re_rates:"var(--price)",finances:"var(--fin)",
 hedges:"var(--fin)",signals:"var(--reveal)",invalidates:"var(--dampen)",bounds:"var(--mix)",
 bounded_by:"var(--mix)",bears_on:"var(--mix)",amplifies:"var(--drive)"};
const PHASES = ["shortage","buildout","overbuild","shakeout","second_wave"];
const forces = DATA.forces, interactions = DATA.interactions, chains = DATA.chains, assumptions = DATA.assumptions;
const byId = Object.fromEntries(forces.map(f=>[f.id,f]));
const domains = [...new Set(forces.map(f=>f.domain))].sort();
const RELS = [...new Set(interactions.map(i=>i.relation))].sort();

document.getElementById("headline").textContent =
 `${forces.length} forces in ${domains.length} domains, ${interactions.length} typed pushes, ${chains.length} chains, ${assumptions.length} assumptions, ` +
 `mean load ${DATA.summary.mean_load}, ${DATA.summary.high_load_links} at load four or five`;

// controls
const relBox = document.getElementById("relations");
relBox.innerHTML = RELS.map(r=>`<label><input type="checkbox" class="rel" value="${r}" checked> <span class="swatch" style="background:${RELCOLOR[r]||"#666"}"></span>${r}</label>`).join("");
const legend = document.getElementById("legend");
legend.innerHTML = RELS.map(r=>`<span><span class="swatch" style="background:${RELCOLOR[r]||"#666"}"></span>${r}</span>`).join("");

// layout: domains on a ring, forces inside their domain, then springs
const W=1000,H=760, cx=W/2, cy=H/2, ring=Math.min(W,H)/2-90;
const pos={}; const domainCenter={};
domains.forEach((d,i)=>{const a=2*Math.PI*i/domains.length - Math.PI/2; domainCenter[d]={x:cx+ring*Math.cos(a),y:cy+ring*Math.sin(a)};});
domains.forEach(d=>{const members=forces.filter(f=>f.domain===d);members.forEach((f,j)=>{const a=2*Math.PI*j/Math.max(1,members.length);
 pos[f.id]={x:domainCenter[d].x+34*Math.cos(a),y:domainCenter[d].y+34*Math.sin(a)};});});
for(let step=0;step<260;step++){
 const disp={}; forces.forEach(f=>disp[f.id]={x:0,y:0});
 for(let i=0;i<forces.length;i++)for(let j=i+1;j<forces.length;j++){
  const a=forces[i].id,b=forces[j].id,dx=pos[a].x-pos[b].x,dy=pos[a].y-pos[b].y,d2=dx*dx+dy*dy+1,d=Math.sqrt(d2);
  const push=1400/d2; disp[a].x+=push*dx/d;disp[a].y+=push*dy/d;disp[b].x-=push*dx/d;disp[b].y-=push*dy/d;}
 interactions.forEach(e=>{const a=pos[e.from],b=pos[e.to];if(!a||!b)return;const dx=b.x-a.x,dy=b.y-a.y,d=Math.sqrt(dx*dx+dy*dy)+.01;
  const pull=(d-90)*0.012;disp[e.from].x+=pull*dx/d;disp[e.from].y+=pull*dy/d;disp[e.to].x-=pull*dx/d;disp[e.to].y-=pull*dy/d;});
 forces.forEach(f=>{const c=domainCenter[f.domain];disp[f.id].x+=(c.x-pos[f.id].x)*0.02;disp[f.id].y+=(c.y-pos[f.id].y)*0.02;});
 forces.forEach(f=>{pos[f.id].x+=Math.max(-8,Math.min(8,disp[f.id].x));pos[f.id].y+=Math.max(-8,Math.min(8,disp[f.id].y));});
}

const svg=document.getElementById("map");
function render(){
 const relAllowed=Object.fromEntries([...document.querySelectorAll(".rel")].map(c=>[c.value,c.checked]));
 const minLoad=+document.getElementById("load").value;
 const phase=document.getElementById("phase").value;
 const query=document.getElementById("search").value.toLowerCase();
 let edges="",nodes="";
 interactions.forEach(e=>{
  if(!relAllowed[e.relation]||e.load<minLoad)return;
  if(phase&&!e.sign_by_phase[phase])return;
  const a=pos[e.from],b=pos[e.to];if(!a||!b)return;
  const color=RELCOLOR[e.relation]||"#666";
  const dash=(e.relation==="substitutes"||e.relation==="competes_for")?"stroke-dasharray='5 4'":"";
  const width=Math.max(1,e.load*0.8);
  const opacity=e.load>=4?0.85:0.45;
  edges+=`<line class="edge" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" stroke="${color}" stroke-width="${width}" ${dash} style="stroke-opacity:${opacity}"><title>${e.from.split(':').slice(1).join(':')} ${e.relation} ${e.to.split(':').slice(1).join(':')} | ${e.channel} | kill: ${e.kill}</title></line>`;
 });
 forces.forEach(f=>{
  const hidden=query&&!(f.id+f.name+f.meaning).toLowerCase().includes(query);
  const p=pos[f.id];
  const sign=netSign(f);
  const r=6+Math.min(6,(f.out_interactions||0)/3);
  nodes+=`<g class="node${hidden?" hidden":""}" data-id="${f.id}"><circle cx="${p.x}" cy="${p.y}" r="${r}" fill="${sign>0?"#3fb950":sign<0?"#f85149":"#8b949e"}"></circle><text x="${p.x+r+2}" y="${p.y+3}">${f.name}</text></g>`;
 });
 svg.innerHTML=`<g>${edges}${nodes}</g>`;
 svg.setAttribute("viewBox",`0 0 ${W} ${H}`);
 svg.querySelectorAll(".node").forEach(g=>g.addEventListener("click",()=>show(g.dataset.id)));
}
function netSign(f){
 let s=0; interactions.forEach(e=>{if(e.from===f.id)s+=signFor(e);});
 return s;
}
function signFor(e){
 const dir={drives:1,amplifies:1,accelerates:1,feeds:1,prices:1,crowds_in:1,gates:-1,dampens:-1,delays:-1,
  substitutes:-1,competes_for:-1,crowds_out:-1,bounds:-1,invalidates:-1}[e.relation];
 return dir===undefined?0:dir;
}
function show(id){
 const f=byId[id];if(!f)return;
 const out=interactions.filter(e=>e.from===id), inc=interactions.filter(e=>e.to===id);
 const mine=assumptions.filter(a=>a.owner===id||a.owner===`interaction:${id}`);
 const card=(e,reverse)=>`<div class="card"><div><b>${reverse?"from":"to"} ${e[reverse?"from":"to"].split(':').slice(1).join(':')}</b>
  <span class="why"> ${e.relation}, load ${e.load}, lag ${e.lag}</span></div>
  <div class="why">${e.channel}</div>
  <div class="io"><div><span>condition</span> ${e.condition}</div><div><span>assumption</span> ${e.assumption}</div>
  <div><span>kill</span> ${e.kill}</div>${Object.keys(e.sign_by_phase).length?`<div><span>signs</span> ${JSON.stringify(e.sign_by_phase)}</div>`:""}</div></div>`;
 const chainList=chains.filter(c=>c.hops.includes(id)).map(c=>`<span class="pill" data-force="${c.hops[0]}">${c.title}</span>`).join(" ");
 document.getElementById("detail").innerHTML=`<h2>${f.name}</h2>
  <div class="card"><div>${f.meaning}</div><div class="why">${f.direction}</div>
  <div class="io"><div><span>domain</span> ${f.domain}</div><div><span>observables</span> ${f.observables}</div>
  <div><span>payer</span> ${f.payer}</div><div><span>net push</span> ${netSign(f)>0?"expands":netSign(f)<0?"contracts":"balanced"}</div></div></div>
  ${chainList?`<h3>chains</h3><div>${chainList}</div>`:""}
  <h3>pushes out (${out.length})</h3>${out.map(e=>card(e,false)).join("")}
  <h3>pushed by (${inc.length})</h3>${inc.map(e=>card(e,true)).join("")}
  ${mine.length?`<h3>assumptions it rests on</h3>${mine.map(a=>`<div class="card"><div>${a.statement}</div><div class="why">test: ${a.test} | kill: ${a.kill}</div></div>`).join("")}`:""}`;
 document.querySelectorAll("#detail .pill").forEach(p=>p.addEventListener("click",()=>{show(p.dataset.force);}));
}

document.getElementById("chains").innerHTML = chains.map(c=>`<div class="chain"><div><b>${c.title}</b>
 <span class="why">(${c.hops.length} hops)</span></div>
 <div class="hops">${c.hops.map((h,i)=>`<span class="pill" data-force="${h}">${byId[h]?byId[h].name:h}</span>${i<c.hops.length-1?'<span class="arrow">&rarr;</span>':''}`).join("")}</div>
 <div class="why">${c.intuition}</div><div class="why">rests on: ${c.greatest_assumption}</div>
 ${Object.keys(c.sign_by_phase||{}).length?`<div class="why">signs: ${Object.entries(c.sign_by_phase).map(([k,v])=>`${k} ${v>0?"+":"-"} `).join(" / ")}</div>`:""}</div>`).join("");
document.querySelectorAll("#chains .pill").forEach(p=>p.addEventListener("click",()=>show(p.dataset.force)));

const matrixRows = forces.filter(f=>interactions.some(e=>e.from===f.id&&Object.keys(e.sign_by_phase).length));
document.getElementById("matrix").innerHTML = `<table><thead><tr><th>force</th>${PHASES.map(p=>`<th>${p}</th>`).join("")}</tr></thead><tbody>`+
 matrixRows.map(f=>{const cells=PHASES.map(p=>{let s=0;interactions.forEach(e=>{if(e.from===f.id&&e.sign_by_phase[p])s+=signFor(e)*e.sign_by_phase[p];});
  return `<td class="${s>0?"pos":s<0?"neg":"zero"}">${s>0?"+":s<0?"-":"0"}</td>`;}).join("");
  return `<tr><td>${f.name}</td>${cells}</tr>`;}).join("")+"</tbody></table>";

document.getElementById("load").addEventListener("input",e=>{document.getElementById("loadval").textContent=e.target.value;render();});
["phase","search"].forEach(id=>document.getElementById(id).addEventListener("input",render));
document.querySelectorAll(".rel").forEach(c=>c.addEventListener("change",render));
render();
const first = interactions.sort((a,b)=>b.load-a.load)[0];
if(first) show(first.from);
</script></body></html>
"""

if __name__ == "__main__":
    raise SystemExit(main())
