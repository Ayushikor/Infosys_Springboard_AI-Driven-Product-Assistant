import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Briefcase, Upload, MessageSquareText, Tags, ListOrdered,
  FileText, Map, Bot, Settings, LogOut, Sparkles, PanelLeftClose, PanelLeftOpen,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export const NAV_ITEMS = [
  { to: '/dashboard', label: 'Overview Dashboard', icon: LayoutDashboard },
  { to: '/workspace', label: 'Workspace', icon: Briefcase },
  { to: '/feedback/upload', label: 'Upload Feedback', icon: Upload },
  { to: '/feedback', label: 'Feedback List', icon: MessageSquareText },
  { to: '/themes', label: 'Themes Dashboard', icon: Tags },
  { to: '/prioritization', label: 'Prioritization', icon: ListOrdered },
  { to: '/prd', label: 'PRD Viewer', icon: FileText },
  { to: '/roadmap', label: 'Roadmap', icon: Map },
  { to: '/chat', label: 'AI Copilot Chat', icon: Bot },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export default function Sidebar({ collapsed, onToggle, onNavigate }) {
  const { user, logout } = useAuth();
  const initials = (user?.name || 'U').split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase();

  return (
    <aside className={`flex h-full flex-col border-r border-slate-200 bg-white transition-all duration-200 dark:border-navy-700 dark:bg-navy-800 ${collapsed ? 'w-[72px]' : 'w-64'}`}>
      <div className="flex h-16 items-center justify-between gap-2 px-4">
        <div className="flex items-center gap-2 overflow-hidden">
          <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-500 text-white">
            <Sparkles size={16} />
          </div>
          {!collapsed && <span className="truncate text-sm font-semibold">PM Copilot</span>}
        </div>
        <button onClick={onToggle} className="btn-ghost hidden p-1.5 lg:inline-flex" aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
          {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
        </button>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-2" aria-label="Main navigation">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onNavigate}
            title={collapsed ? label : undefined}
            className={({ isActive }) =>
              `group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
                isActive
                  ? 'bg-indigo-50 text-accent-600 dark:bg-indigo-500/15 dark:text-indigo-300'
                  : 'text-navy-500 hover:bg-slate-100 hover:text-navy-800 dark:hover:bg-navy-700 dark:hover:text-slate-100'
              } ${collapsed ? 'justify-center' : ''}`
            }
          >
            <Icon size={18} className="shrink-0" />
            {!collapsed && <span className="truncate">{label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-slate-200 p-3 dark:border-navy-700">
        <div className={`flex items-center gap-3 ${collapsed ? 'justify-center' : ''}`}>
          <div className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-indigo-100 text-sm font-semibold text-accent-600 dark:bg-indigo-500/20 dark:text-indigo-300">{initials}</div>
          {!collapsed && (
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{user?.name}</p>
              <p className="truncate text-xs text-navy-500">{user?.role}</p>
            </div>
          )}
        </div>
        <button
          onClick={logout}
          className={`mt-3 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-navy-500 transition hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-500/10 ${collapsed ? 'justify-center' : ''}`}
        >
          <LogOut size={16} />
          {!collapsed && 'Logout'}
        </button>
      </div>
    </aside>
  );
}
