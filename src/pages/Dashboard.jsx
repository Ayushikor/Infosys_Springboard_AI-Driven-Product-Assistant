import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid,
  PieChart, Pie, Cell, BarChart, Bar,
} from 'recharts';
import {
  MessageSquareText, Tags, ListOrdered, Map, Download, Search, Bell,
  CalendarDays, ArrowUpRight, Sparkles, FileText, Upload,
} from 'lucide-react';
import { useAppData } from '../context/AppDataContext';
import { useTheme } from '../context/ThemeContext';
import EmptyState from '../components/common/EmptyState';

const COLORS = ['#80503d', '#bd8b70', '#d9b8a5', '#9a7968', '#6f7e72'];
const fmt = (value) => Number(value || 0).toLocaleString();
const Tip = ({active,payload,label}) => active && payload?.length ? (
  <div className="rounded-lg border border-[#e8ddd4] bg-[#fffdfa] px-3 py-2 text-xs shadow-xl dark:border-white/10 dark:bg-[#171717]">
    <p className="mb-1 font-semibold text-[#35251e] dark:text-white">{label}</p>
    {payload.map((p) => <p key={p.dataKey} style={{color:p.color}}>{p.name}: {fmt(p.value)}</p>)}
  </div>
) : null;

function Stat({label,value,sub,icon:Icon,to}) {
  return <Link to={to} className="card group min-w-0 p-4 transition hover:-translate-y-0.5 hover:shadow-soft">
    <div className="flex items-center justify-between gap-2">
      <p className="text-[11px] font-medium text-navy-500">{label}</p>
      <span className="rounded-lg bg-[#f0e2d8] p-2 text-[#80503d] dark:bg-[#38251f] dark:text-[#d9b8a5]"><Icon size={15}/></span>
    </div>
    <p className="mt-2 text-[25px] font-semibold leading-none tracking-tight text-[#211815] dark:text-white">{fmt(value)}</p>
    <p className="mt-2 text-[10px] text-navy-500">{sub}</p>
  </Link>;
}

function Panel({title,subtitle,children,action}) {
  return <section className="card min-w-0 p-4 sm:p-5">
    <div className="mb-4 flex items-start justify-between gap-3">
      <div><h2 className="text-sm font-semibold text-[#211815] dark:text-[#f5eee9]">{title}</h2>{subtitle && <p className="mt-1 text-[10px] text-navy-500">{subtitle}</p>}</div>
      {action}
    </div>
    {children}
  </section>;
}

export default function Dashboard() {
  const {raw,derived,loading,error} = useAppData();
  const {isDark} = useTheme();
  const [period,setPeriod] = useState('Monthly');
  const [range,setRange] = useState('Last 30 days');

  const data = useMemo(() => {
    const feedback=raw?.feedback||[];
    const themes=(derived?.themeStats||[]).filter(x=>x.count>0).sort((a,b)=>b.count-a.count);
    const features=derived?.prioritized||[];
    const roadmap=raw?.roadmap||[];
    const months=period==='Yearly'?12:period==='Daily'?14:6;
    const buckets=Array.from({length:months},(_,i)=>{
      const d=new Date();
      if(period==='Daily') d.setDate(d.getDate()-(months-1-i));
      else {d.setDate(1);d.setMonth(d.getMonth()-(months-1-i));}
      return {key:period==='Daily'?d.toDateString():`${d.getFullYear()}-${d.getMonth()}`,label:d.toLocaleDateString(undefined,period==='Daily'?{month:'short',day:'numeric'}:{month:'short'}),feedback:0,negative:0};
    });
    feedback.forEach(item=>{
      const date=new Date(item.createdAt||item.created_at);
      if(Number.isNaN(date.getTime()))return;
      const key=period==='Daily'?date.toDateString():`${date.getFullYear()}-${date.getMonth()}`;
      const b=buckets.find(x=>x.key===key);
      if(b){b.feedback++;if(String(item.sentiment).toLowerCase()==='negative')b.negative++;}
    });
    const sentiment=derived?.sentiment||{};
    const sentimentData=[{name:'Positive',value:sentiment.positive||0},{name:'Neutral',value:sentiment.neutral||0},{name:'Negative',value:sentiment.negative||0}].filter(x=>x.value>0);
    const sourceMap={};
    feedback.forEach(x=>{const key=x.source||'Unspecified';sourceMap[key]=(sourceMap[key]||0)+1;});
    const sources=Object.entries(sourceMap).map(([name,value])=>({name,value})).sort((a,b)=>b.value-a.value).slice(0,5);
    return {feedback,themes,features,roadmap,buckets,sentimentData,sources};
  },[raw,derived,period]);

  if(loading)return <div className="card h-64 animate-pulse"/>;
  if(error)return <EmptyState title="Could not load dashboard" description={error}/>;
  if(!raw||!derived)return null;

  const axis=isDark?'#aaa':'#86766d';
  const grid=isDark?'#292929':'#eee5de';
  const sourceTotal=data.sources.reduce((a,b)=>a+b.value,0);
  const reportLink=<Link to="/strategy-report" className="inline-flex items-center gap-1 text-[10px] font-semibold text-[#80503d] dark:text-[#d9b8a5]">Open report <ArrowUpRight size={12}/></Link>;

  return <div className="space-y-4">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><div className="mb-1 flex items-center gap-2 text-[10px] text-navy-500"><span>Dashboards</span><span>›</span><span>Analytics</span><span>›</span><strong className="text-[#38251f] dark:text-[#f4ece6]">Overview</strong></div><h1 className="text-xl font-semibold tracking-tight text-[#211815] dark:text-white">Overview</h1></div>
      <div className="flex items-center gap-2">
        <Link to="/feedback/upload" className="btn-outline !px-3 !py-2 text-[11px]"><Upload size={13}/> Upload data</Link>
        <button onClick={()=>window.print()} className="btn-primary !px-3 !py-2 text-[11px]"><Download size={13}/> Export</button>
      </div>
    </div>

    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Stat label="Total feedback" value={derived.feedbackCount} sub="Customer signals in workspace" icon={MessageSquareText} to="/feedback"/>
      <Stat label="Active themes" value={derived.activeThemes} sub="Themes with customer evidence" icon={Tags} to="/themes"/>
      <Stat label="Prioritized features" value={derived.prioritizedCount} sub="Features ranked by RICE" icon={ListOrdered} to="/prioritization"/>
      <Stat label="Roadmap items" value={data.roadmap.length} sub="Planned and tracked initiatives" icon={Map} to="/roadmap"/>
    </div>

    <Panel title="Analysis" subtitle="Understand customer feedback and turn product signals into actionable decisions." action={<div className="flex rounded-lg border border-black/10 p-0.5 text-[10px] dark:border-white/10">{['Daily','Monthly','Yearly'].map(x=><button key={x} onClick={()=>setPeriod(x)} className={`rounded-md px-3 py-1.5 ${period===x?'bg-[#80503d] text-white':'text-navy-500'}`}>{x}</button>)}</div>}>
      <div className="mb-2 flex justify-end gap-4 text-[10px] text-navy-500"><span className="flex items-center gap-1.5"><i className="h-[2px] w-3 bg-[#80503d]"/> Feedback</span><span className="flex items-center gap-1.5"><i className="h-[2px] w-3 bg-[#bd8b70]"/> Negative feedback</span></div>
      <div className="h-[260px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data.buckets} margin={{top:8,right:8,left:-18,bottom:0}}>
            <defs><linearGradient id="stratovArea" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#a96c52" stopOpacity=".28"/><stop offset="95%" stopColor="#a96c52" stopOpacity=".015"/></linearGradient></defs>
            <CartesianGrid stroke={grid} strokeDasharray="3 5" vertical={false}/>
            <XAxis dataKey="label" tick={{fill:axis,fontSize:10}} axisLine={false} tickLine={false}/>
            <YAxis allowDecimals={false} tick={{fill:axis,fontSize:10}} axisLine={false} tickLine={false}/>
            <Tooltip content={<Tip/>}/>
            <Area type="monotone" dataKey="feedback" name="Feedback" stroke="#80503d" strokeWidth={2.5} fill="url(#stratovArea)"/>
            <Area type="monotone" dataKey="negative" name="Negative feedback" stroke="#bd8b70" strokeWidth={2} fill="transparent"/>
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Panel>

    <div className="grid gap-3 xl:grid-cols-3">
      <Panel title="Top themes" subtitle="Most frequent customer topics" action={reportLink}>
        {data.themes.length?<div className="space-y-3">
          <div className="flex h-3 overflow-hidden rounded-full bg-[#eee5de] dark:bg-white/10">{data.themes.slice(0,5).map((x,i)=><div key={x.name} style={{width:`${100*x.count/Math.max(1,data.themes.reduce((s,t)=>s+t.count,0))}%`,background:COLORS[i]}}/>)}</div>
          {data.themes.slice(0,5).map((x,i)=><div key={x.name} className="flex items-center gap-2 border-b border-black/[.06] pb-2 last:border-0 dark:border-white/[.07]"><span className="h-2 w-2 rounded-full" style={{background:COLORS[i]}}/><span className="min-w-0 flex-1 truncate text-[11px]">{x.name}</span><strong className="text-[11px] tabular-nums">{fmt(x.count)}</strong><span className="w-9 text-right text-[10px] text-navy-500">{Math.round(100*x.count/Math.max(1,derived.feedbackCount))}%</span></div>)}
        </div>:<p className="py-8 text-center text-xs text-navy-500">No themes yet</p>}
      </Panel>

      <Panel title="Priority portfolio" subtitle="Highest-ranked feature opportunities" action={<Link to="/prioritization" className="text-[10px] font-semibold text-[#80503d] dark:text-[#d9b8a5]">View all →</Link>}>
        {data.features.length?<div className="space-y-3">{data.features.slice(0,5).map((x,i)=><div key={x.id||x.name||i}><div className="mb-1 flex items-center justify-between gap-2"><span className="truncate text-[11px]">{x.name||x.title||`Feature ${i+1}`}</span><span className="text-[10px] font-semibold tabular-nums">{Number(x.rice||0).toFixed(1)}</span></div><div className="h-1.5 overflow-hidden rounded-full bg-[#eee5de] dark:bg-white/10"><div className="h-full rounded-full" style={{width:`${Math.max(3,Math.min(100,Number(x.rice||0)))}%`,background:COLORS[i%COLORS.length]}}/></div></div>)}</div>:<p className="py-8 text-center text-xs text-navy-500">No prioritized features</p>}
      </Panel>

      <Panel title="Feedback composition" subtitle="Customer sentiment distribution">
        {data.sentimentData.length?<div className="relative h-[220px]">
          <ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={data.sentimentData} dataKey="value" nameKey="name" innerRadius={57} outerRadius={82} paddingAngle={3} stroke="none">{data.sentimentData.map((x,i)=><Cell key={x.name} fill={{Positive:'#78917c',Neutral:'#c9a77f',Negative:'#a85f4c'}[x.name]}/>)}</Pie><Tooltip formatter={fmt}/></PieChart></ResponsiveContainer>
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center"><strong className="text-2xl">{fmt(data.sentimentData.reduce((s,x)=>s+x.value,0))}</strong><span className="text-[9px] uppercase tracking-widest text-navy-500">classified</span></div>
        </div>:<p className="py-8 text-center text-xs text-navy-500">No sentiment data</p>}
        <div className="mt-1 flex flex-wrap justify-center gap-3">{data.sentimentData.map((x)=><span key={x.name} className="flex items-center gap-1.5 text-[10px] text-navy-500"><i className="h-2 w-2 rounded-full" style={{background:({Positive:'#78917c',Neutral:'#c9a77f',Negative:'#a85f4c'}[x.name])}}/>{x.name} {fmt(x.value)}</span>)}</div>
      </Panel>
    </div>

    <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-[#d9c4b5] bg-[#f3e8df] px-4 py-3 text-xs text-[#634638] dark:border-white/10 dark:bg-white/[.04] dark:text-[#d9b8a5]">
      <span className="flex items-center gap-2"><Sparkles size={14}/> Stratov turns feedback into product direction.</span>
      <Link to="/strategy-report" className="font-semibold underline underline-offset-4">Open executive strategy report</Link>
    </div>
  </div>;
}
