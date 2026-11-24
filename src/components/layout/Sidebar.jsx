import { NavLink } from 'react-router-dom';
import {
  Home, BarChart3, Briefcase, Lightbulb, FileText,
  MessageSquare, Settings, Headphones, LogOut,
  Users, Megaphone, Package, UsersRound, Search,
  BookOpen, PanelLeftClose, PanelLeftOpen, Layers3,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

const GROUPS = [
  {
    label: 'DASHBOARDS',
    items: [
      { to: '/dashboard', label: 'Home', icon: Home },
      { to: '/strategy-report', label: 'Analytics', icon: BarChart3 },
      { to: '/workspace', label: 'Workspace', icon: Briefcase },
      { to: '/themes', label: 'Insights', icon: Lightbulb },
      { to: '/prd', label: 'Reports', icon: FileText },
      { to: '/chat', label: 'Messages', icon: MessageSquare },
    ],
  },
  {
    label: 'TEAMS & INSIGHTS',
    items: [
      { to: '/feedback', label: 'Operations', icon: Headphones },
      { to: '/feedback/upload', label: 'Marketing', icon: Megaphone },
      { to: '/prioritization', label: 'Commercial', icon: Briefcase },
      { to: '/roadmap', label: 'Product', icon: Package },
      { to: '/workspace', label: 'People & Culture', icon: UsersRound },
      { to: '/themes', label: 'Market research', icon: Search },
      { to: '/prd', label: 'Knowledge share', icon: BookOpen },
    ],
  },
];

export const NAV_ITEMS = GROUPS.flatMap((group) => group.items).concat([
  { to: '/settings', label: 'System settings', icon: Settings },
]);

export default function Sidebar({ collapsed, onToggle, onNavigate }) {
  const { user, logout } = useAuth();
  const initials = (user?.name || 'User').split(' ').map((part) => part[0]).slice(0, 2).join('').toUpperCase();

  return (
    <aside className={`stratov-sidebar relative flex h-full shrink-0 flex-col transition-[width] duration-300 ${collapsed ? 'w-[76px]' : 'w-[224px] xl:w-[250px]'}`}>
      <div className={`flex h-[76px] items-center ${collapsed ? 'justify-center px-2' : 'justify-between px-5'}`}>
        <div className="flex min-w-0 items-center gap-3">
          <div className="stratov-mark grid h-9 w-9 shrink-0 place-items-center rounded-full text-white">
            <Layers3 size={18} strokeWidth={1.8} />
          </div>
          {!collapsed && <div className="min-w-0">
            <p className="truncate text-[15px] font-bold tracking-tight text-[#211815] dark:text-[#f7f0eb]">Stratov</p>
            <p className="text-[9px] font-semibold uppercase tracking-[.18em] text-[#8e766a] dark:text-[#b9a49a]">Product intelligence</p>
          </div>}
        </div>
        <button onClick={onToggle} className="sidebar-icon-btn hidden p-1.5 lg:inline-flex" aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
          {collapsed ? <PanelLeftOpen size={16}/> : <PanelLeftClose size={16}/>}
        </button>
      </div>

      <div className="mx-4 border-t border-black/10 dark:border-white/10" />

      <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-4" aria-label="Main navigation">
        {GROUPS.map((group) => <section key={group.label}>
          {!collapsed && <p className="mb-2 px-2 text-[9px] font-bold tracking-[.15em] text-[#8e766a] dark:text-[#9d8b83]">{group.label}</p>}
          <div className="space-y-0.5">
            {group.items.map(({to,label,icon:Icon}) => <NavLink
              key={`${to}-${label}`} to={to} onClick={onNavigate} title={collapsed ? label : undefined}
              className={({isActive}) => `stratov-navlink group flex items-center gap-3 rounded-lg px-2.5 py-[9px] text-[12px] font-medium transition-all ${collapsed ? 'justify-center px-2' : ''} ${isActive ? 'is-active' : ''}`}
            >
              <Icon size={15} strokeWidth={1.9} className="shrink-0"/>
              {!collapsed && <span className="truncate">{label}</span>}
              {!collapsed && label === 'Messages' && <span className="ml-auto grid h-[17px] min-w-[17px] place-items-center rounded-full bg-[#70402f] px-1 text-[9px] text-white">5</span>}
            </NavLink>)}
          </div>
        </section>)}
        <section>
          {!collapsed && <p className="mb-2 px-2 text-[9px] font-bold tracking-[.15em] text-[#8e766a] dark:text-[#9d8b83]">SETTINGS</p>}
          <NavLink to="/settings" onClick={onNavigate} title={collapsed ? 'System settings' : undefined} className={({isActive}) => `stratov-navlink flex items-center gap-3 rounded-lg px-2.5 py-[9px] text-[12px] font-medium ${collapsed ? 'justify-center px-2' : ''} ${isActive ? 'is-active' : ''}`}>
            <Settings size={15}/>{!collapsed && 'System settings'}
          </NavLink>
        </section>
      </nav>

      <div className="border-t border-black/10 p-3 dark:border-white/10">
        <div className={`flex items-center gap-2 rounded-xl px-2 py-2 ${collapsed ? 'justify-center' : 'stratov-profile'}`}>
          <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[#d8b49f] text-[10px] font-bold text-[#503326]">{initials}</div>
          {!collapsed && <div className="min-w-0 flex-1">
            <p className="truncate text-[10px] font-semibold text-[#30231e] dark:text-[#f3eae4]">{user?.name || 'Workspace user'}</p>
            <p className="truncate text-[9px] text-[#8d786d] dark:text-[#b7a49a]">{user?.email || 'Product team'}</p>
          </div>}
          {!collapsed && <span className="text-xs text-[#8d786d]">⌄</span>}
        </div>
        <button onClick={logout} title="Sign out" className={`mt-1 flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-[11px] text-[#866d61] transition hover:bg-[#ead9ce] dark:text-[#b8a49a] dark:hover:bg-white/10 ${collapsed ? 'justify-center' : ''}`}>
          <LogOut size={14}/>{!collapsed && 'Sign out'}
        </button>
      </div>
    </aside>
  );
}
