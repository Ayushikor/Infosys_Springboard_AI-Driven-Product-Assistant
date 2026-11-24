import { useMemo } from 'react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, PieChart, Pie, Cell, BarChart, Bar } from 'recharts';
import { Download, Sparkles, Target, ShieldAlert, Flag, MessageSquareText } from 'lucide-react';
import { useAppData } from '../context/AppDataContext';
import { useTheme } from '../context/ThemeContext';
import EmptyState from '../components/common/EmptyState';

const colors=['#80503d','#bd8b70','#d9b8a5','#78917c','#a85f4c'];
const sentimentColors={positive:'#78917c',neutral:'#c9a77f',negative:'#a85f4c'};
const fmt=n=>Number(n||0).toLocaleString();
const TooltipBox=({active,payload,label})=>active&&payload?.length?<div className="rounded-lg border bg-white p-3 text-xs shadow-xl dark:border-white/10 dark:bg-[#171717]"><b>{label}</b>{payload.map(x=><p key={x.dataKey} style={{color:x.color}}>{x.name}: {fmt(x.value)}</p>)}</div>:null;

function Card({title,sub,children}){return <section className="card min-w-0 p-5"><h2 className="text-sm font-semibold">{title}</h2>{sub&&<p className="mt-1 text-[10px] text-navy-500">{sub}</p>}<div className="mt-4">{children}</div></section>}

export default function StrategyReport(){
 const {raw,derived,loading,error}=useAppData(); const {isDark}=useTheme();
 const r=useMemo(()=>{
  const feedback=raw?.feedback||[],roadmap=raw?.roadmap||[],features=derived?.prioritized||[];
  const themes=(derived?.themeStats||[]).filter(x=>x.count>0).sort((a,b)=>b.count-a.count);
  const sent=derived?.sentiment||{};
  const pie=[{name:'Positive',value:sent.positive||0},{name:'Neutral',value:sent.neutral||0},{name:'Negative',value:sent.negative||0}].filter(x=>x.value);
  const trend=Array.from({length:6},(_,i)=>{const d=new Date();d.setDate(1);d.setMonth(d.getMonth()-(5-i));return {key:`${d.getFullYear()}-${d.getMonth()}`,month:d.toLocaleDateString(undefined,{month:'short'}),feedback:0,negative:0}});
  feedback.forEach(x=>{const d=new Date(x.createdAt||x.created_at);if(Number.isNaN(d.getTime()))return;const b=trend.find(y=>y.key===`${d.getFullYear()}-${d.getMonth()}`);if(b){b.feedback++;if(String(x.sentiment).toLowerCase()==='negative')b.negative++}});
  const themeBars=themes.slice(0,6).map(x=>({theme:x.name,count:x.count,negative:Math.round(x.count*(x.negativeShare||0)/100)}));
  const high=themes[0],top=features[0],negative=Number(sent.negative||0),total=pie.reduce((a,b)=>a+b.value,0);
  const roadmapDone=roadmap.filter(x=>String(x.status).toLowerCase()==='completed').length;
  const recs=[];
  if(high)recs.push({icon:ShieldAlert,title:`Investigate ${high.name}`,body:`This is the most frequently mentioned theme (${fmt(high.count)} records). Review negative examples and define a measurable improvement target.`,priority:'High'});
  if(top)recs.push({icon:Target,title:`Validate ${top.name||top.title||'the top-ranked feature'}`,body:'Confirm impact, effort assumptions and ownership before committing roadmap capacity.',priority:'High'});
  if(roadmap.length)recs.push({icon:Flag,title:'Review delivery capacity',body:`${fmt(roadmap.length-roadmapDone)} roadmap item(s) are not yet complete. Check dependencies and sequencing before adding scope.`,priority:'Medium'});
  if(!recs.length)recs.push({icon:MessageSquareText,title:'Build the evidence base',body:'Upload customer feedback and run AI analysis to generate data-backed strategic recommendations.',priority:'Medium'});
  return {feedback,roadmap,features,themes,pie,trend,themeBars,total,negative,high,top,roadmapDone,recs};
 },[raw,derived]);
 if(loading)return <div className="card h-64 animate-pulse"/>; if(error)return <EmptyState title="Strategy report unavailable" description={error}/>; if(!raw||!derived)return null;
 const axis=isDark?'#aaa':'#89776d',grid=isDark?'#292929':'#eee5de';
 return <div className="space-y-4">
  <section className="relative overflow-hidden rounded-2xl bg-[#38251f] p-6 text-[#fff8f2] sm:p-8">
   <div className="absolute -right-8 -top-16 h-64 w-64 rounded-full border border-[#d9b8a5]/20"/><div className="absolute -right-1 -top-9 h-48 w-48 rounded-full border border-[#d9b8a5]/20"/>
   <div className="relative flex flex-wrap items-end justify-between gap-5"><div className="max-w-3xl"><p className="mb-3 inline-flex items-center gap-2 rounded-full border border-white/20 px-3 py-1 text-[9px] font-semibold uppercase tracking-[.18em] text-[#e4c5b2]"><Sparkles size={12}/> Stratov intelligence brief</p><h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Product strategy, <span className="font-serif italic text-[#d9b8a5]">in perspective.</span></h1><p className="mt-3 max-w-2xl text-xs leading-6 text-[#e4d1c5]">An executive view of customer signals, portfolio priorities and roadmap progress, assembled from the evidence currently available in your workspace.</p><p className="mt-4 text-[9px] uppercase tracking-[.16em] text-[#c6a895]">Executive strategy report · {new Date().toLocaleDateString()}</p></div><button onClick={()=>window.print()} className="no-print inline-flex items-center gap-2 rounded-lg bg-[#f7eee7] px-4 py-2.5 text-xs font-semibold text-[#503226]"><Download size={14}/> Export / Print</button></div>
  </section>
  <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
   {[['Customer signals',r.feedback.length],['Negative sentiment',`${r.total?Math.round(r.negative/r.total*100):0}%`],['Active themes',r.themes.length],['Roadmap completed',`${r.roadmapDone}/${r.roadmap.length}`]].map(([label,value])=><div className="card p-4" key={label}><p className="text-[10px] text-navy-500">{label}</p><p className="mt-2 text-2xl font-semibold">{typeof value==='number'?fmt(value):value}</p></div>)}
  </div>
  <div className="grid gap-4 xl:grid-cols-[1.5fr_1fr]">
   <Card title="Customer feedback momentum" sub="Monthly feedback volume and negative signals over the last six months"><div className="h-[260px]"><ResponsiveContainer width="100%" height="100%"><AreaChart data={r.trend}><defs><linearGradient id="stratovReportFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#a96c52" stopOpacity=".3"/><stop offset="100%" stopColor="#a96c52" stopOpacity="0"/></linearGradient></defs><CartesianGrid stroke={grid} strokeDasharray="3 5" vertical={false}/><XAxis dataKey="month" tick={{fill:axis,fontSize:10}} axisLine={false} tickLine={false}/><YAxis tick={{fill:axis,fontSize:10}} axisLine={false} tickLine={false}/><Tooltip content={<TooltipBox/>}/><Area dataKey="feedback" name="Feedback" stroke="#80503d" strokeWidth={2.5} fill="url(#stratovReportFill)"/><Area dataKey="negative" name="Negative" stroke="#bd8b70" strokeWidth={2} fill="transparent"/></AreaChart></ResponsiveContainer></div></Card>
   <Card title="Sentiment composition" sub="Share of classified customer feedback"><div className="relative h-[260px]"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={r.pie} dataKey="value" nameKey="name" innerRadius={68} outerRadius={100} paddingAngle={4} stroke="none">{r.pie.map(x=><Cell key={x.name} fill={sentimentColors[x.name.toLowerCase()]}/>)}</Pie><Tooltip formatter={fmt}/></PieChart></ResponsiveContainer><div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center"><b className="text-3xl">{fmt(r.total)}</b><span className="text-[9px] uppercase tracking-widest text-navy-500">classified</span></div></div></Card>
  </div>
  <div className="grid gap-4 xl:grid-cols-2">
   <Card title="Themes driving the conversation" sub="Most-mentioned themes and their negative signal counts">{r.themeBars.length?<div className="h-[285px]"><ResponsiveContainer width="100%" height="100%"><BarChart data={r.themeBars} layout="vertical" margin={{left:8,right:12}}><CartesianGrid stroke={grid} horizontal={false}/><XAxis type="number" tick={{fill:axis,fontSize:10}} axisLine={false} tickLine={false}/><YAxis type="category" dataKey="theme" width={115} tick={{fill:axis,fontSize:10}} axisLine={false} tickLine={false}/><Tooltip content={<TooltipBox/>}/><Bar dataKey="count" name="Mentions" fill="#bd8b70" radius={[0,5,5,0]}/><Bar dataKey="negative" name="Negative signals" fill="#80503d" radius={[0,5,5,0]}/></BarChart></ResponsiveContainer></div>:<p className="py-10 text-center text-xs text-navy-500">No theme data available.</p>}</Card>
   <Card title="Portfolio priority mix" sub="Feature priority distribution"><div className="h-[285px]">{r.features.length?<ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={['High','Medium','Low'].map(name=>({name,value:r.features.filter(x=>String(x.priority).toLowerCase()===name.toLowerCase()).length})).filter(x=>x.value)} dataKey="value" nameKey="name" innerRadius={58} outerRadius={95} paddingAngle={4}>{['High','Medium','Low'].map((name,i)=><Cell key={name} fill={colors[i]}/>)}</Pie><Tooltip formatter={fmt}/></PieChart></ResponsiveContainer>:<p className="py-10 text-center text-xs text-navy-500">No prioritized features yet.</p>}</div></Card>
  </div>
  <Card title="Recommended leadership agenda" sub="Evidence-based recommendations for product and delivery review"><div className="grid gap-3 lg:grid-cols-3">{r.recs.map((x,i)=>{const Icon=x.icon;return <article key={i} className="rounded-xl border border-[#eadfd7] bg-[#fcf8f4] p-4 dark:border-white/10 dark:bg-white/[.035]"><div className="flex items-center justify-between gap-2"><span className="flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-widest text-[#9b725d]"><Icon size={13}/>{x.priority} priority</span></div><h3 className="mt-3 text-sm font-semibold">{x.title}</h3><p className="mt-2 text-xs leading-5 text-navy-500">{x.body}</p></article>})}</div></Card>
  <p className="text-center text-[9px] text-navy-500">Generated from current workspace records. Missing data is not estimated.</p>
 </div>
}
