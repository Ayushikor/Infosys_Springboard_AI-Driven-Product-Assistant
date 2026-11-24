import { NavLink } from 'react-router-dom';
import {
  Home,
  BarChart3,
  Briefcase,
  Lightbulb,
  FileText,
  MessageSquare,
  Settings,
  Headphones,
  LogOut,
  Megaphone,
  Package,
  PanelLeftClose,
  PanelLeftOpen,
  Layers3,
  ShieldCheck,
} from 'lucide-react';

import { useAuth } from '../../context/AuthContext';

// --------------------------------------------------
// ROLE-BASED NAVIGATION
// --------------------------------------------------

const ROLE_GROUPS = {
  admin: [
    {
      label: 'ADMINISTRATION',
      items: [
        { to: '/dashboard', label: 'Dashboard', icon: Home },
        {
          to: '/admin/users',
          label: 'User Administration',
          icon: ShieldCheck,
        },
      ],
    },
  ],

  'product manager': [
    {
      label: 'DASHBOARDS',
      items: [
        { to: '/dashboard', label: 'Dashboard', icon: Home },
        { to: '/strategy-report', label: 'Strategy Analytics', icon: BarChart3 },
        { to: '/workspace', label: 'Workspace', icon: Briefcase },
        { to: '/themes', label: 'Feedback Insights', icon: Lightbulb },
        { to: '/prd', label: 'PRD Viewer', icon: FileText },
        { to: '/chat', label: 'AI Assistant', icon: MessageSquare },
      ],
    },
    {
      label: 'TEAMS & INSIGHTS',
      items: [
        { to: '/feedback', label: 'Feedback Analysis', icon: Headphones },
        { to: '/feedback/upload', label: 'CSV Upload', icon: Megaphone },
        {
          to: '/prioritization',
          label: 'Feature Prioritization',
          icon: Briefcase,
        },
        { to: '/roadmap', label: 'Product Roadmap', icon: Package },
      ],
    },
  ],

  developer: [
    {
      label: 'DEVELOPMENT',
      items: [
        { to: '/dashboard', label: 'Dashboard', icon: Home },
        { to: '/workspace', label: 'Workspace', icon: Briefcase },
        { to: '/prd', label: 'PRD Viewer', icon: FileText },
        { to: '/chat', label: 'AI Assistant', icon: MessageSquare },
        { to: '/roadmap', label: 'Product Roadmap', icon: Package },
      ],
    },
  ],

  executive: [
    {
      label: 'OVERVIEW',
      items: [
        { to: '/dashboard', label: 'Dashboard', icon: Home },
        { to: '/strategy-report', label: 'Strategy Analytics', icon: BarChart3 },
        { to: '/themes', label: 'Feedback Insights', icon: Lightbulb },
        { to: '/prd', label: 'PRD Viewer', icon: FileText },
        { to: '/roadmap', label: 'Product Roadmap', icon: Package },
      ],
    },
  ],
};

// --------------------------------------------------
// EXPORT NAVIGATION ITEMS
// Preserves compatibility with existing imports.
// --------------------------------------------------

export const NAV_ITEMS = Object.values(ROLE_GROUPS)
  .flatMap((groups) => groups.flatMap((group) => group.items))
  .concat([
    { to: '/settings', label: 'System settings', icon: Settings },
    {
      to: '/admin/users',
      label: 'User Administration',
      icon: ShieldCheck,
    },
  ]);

// --------------------------------------------------
// SIDEBAR COMPONENT
// --------------------------------------------------

export default function Sidebar({
  collapsed,
  onToggle,
  onNavigate,
}) {
  const { user, logout } = useAuth();

  // Normalize role names received from MongoDB/API.
  const role = String(user?.role || 'Product Manager')
    .trim()
    .toLowerCase()
    .replace(/_/g, ' ');

  // Select navigation based on authenticated role.
  const GROUPS = ROLE_GROUPS[role] || ROLE_GROUPS['product manager'];

  const isAdmin = role === 'admin';

  const initials = (user?.name || 'User')
    .split(' ')
    .map((part) => part[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();

  return (
    <aside
      className={`stratov-sidebar relative flex h-full shrink-0 flex-col transition-[width] duration-300 ${
        collapsed ? 'w-[76px]' : 'w-[224px] xl:w-[250px]'
      }`}
    >
      {/* BRAND */}

      <div
        className={`flex h-[76px] items-center ${
          collapsed ? 'justify-center px-2' : 'justify-between px-5'
        }`}
      >
        <div className="flex min-w-0 items-center gap-3">
          <img
  src="/images/Stratovlogo.png"
  alt="Stratov Logo"
  className="h-12 w-12 shrink-0 rounded-lg object-contain"
/>

          {!collapsed && (
            <div className="min-w-0">
              <p className="truncate text-[15px] font-bold tracking-tight text-[#211815] dark:text-[#f7f0eb]">
                Stratov
              </p>

              <p className="text-[9px] font-semibold uppercase tracking-[.18em] text-[#8e766a] dark:text-[#b9a49a]">
                Product intelligence
              </p>
            </div>
          )}
        </div>

        <button
          onClick={onToggle}
          className="sidebar-icon-btn hidden p-1.5 lg:inline-flex"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? (
            <PanelLeftOpen size={16} />
          ) : (
            <PanelLeftClose size={16} />
          )}
        </button>
      </div>

      <div className="mx-4 border-t border-black/10 dark:border-white/10" />

      {/* ROLE INDICATOR */}

      {!collapsed && (
        <div className="px-5 pt-3">
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-1 text-[9px] font-bold uppercase tracking-wider ${
              isAdmin
                ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300'
                : role === 'developer'
                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                : role === 'executive'
                ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
                : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
            }`}
          >
            {user?.role || 'Product Manager'}
          </span>
        </div>
      )}

      {/* NAVIGATION */}

      <nav
        className="flex-1 space-y-5 overflow-y-auto px-3 py-4"
        aria-label="Main navigation"
      >
        {GROUPS.map((group) => (
          <section key={group.label}>
            {!collapsed && (
              <p className="mb-2 px-2 text-[9px] font-bold tracking-[.15em] text-[#8e766a] dark:text-[#9d8b83]">
                {group.label}
              </p>
            )}

            <div className="space-y-0.5">
              {group.items.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  onClick={onNavigate}
                  title={collapsed ? label : undefined}
                  className={({ isActive }) =>
                    `stratov-navlink group flex items-center gap-3 rounded-lg px-2.5 py-[9px] text-[12px] font-medium transition-all ${
                      collapsed ? 'justify-center px-2' : ''
                    } ${isActive ? 'is-active' : ''}`
                  }
                >
                  <Icon
                    size={15}
                    strokeWidth={1.9}
                    className="shrink-0"
                  />

                  {!collapsed && (
                    <span className="truncate">{label}</span>
                  )}

                  {!collapsed && label === 'AI Assistant' && (
                    <span className="ml-auto grid h-[17px] min-w-[17px] place-items-center rounded-full bg-[#70402f] px-1 text-[9px] text-white">
                      5
                    </span>
                  )}
                </NavLink>
              ))}
            </div>
          </section>
        ))}

        {/* SETTINGS */}

        <section>
          {!collapsed && (
            <p className="mb-2 px-2 text-[9px] font-bold tracking-[.15em] text-[#8e766a] dark:text-[#9d8b83]">
              SETTINGS
            </p>
          )}

          <NavLink
            to="/settings"
            onClick={onNavigate}
            title={collapsed ? 'System settings' : undefined}
            className={({ isActive }) =>
              `stratov-navlink flex items-center gap-3 rounded-lg px-2.5 py-[9px] text-[12px] font-medium ${
                collapsed ? 'justify-center px-2' : ''
              } ${isActive ? 'is-active' : ''}`
            }
          >
            <Settings size={15} />
            {!collapsed && 'System settings'}
          </NavLink>
        </section>
      </nav>

      {/* USER PROFILE */}

      <div className="border-t border-black/10 p-3 dark:border-white/10">
        <div
          className={`flex items-center gap-2 rounded-xl px-2 py-2 ${
            collapsed ? 'justify-center' : 'stratov-profile'
          }`}
        >
          <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[#d8b49f] text-[10px] font-bold text-[#503326]">
            {initials}
          </div>

          {!collapsed && (
            <div className="min-w-0 flex-1">
              <p className="truncate text-[10px] font-semibold text-[#30231e] dark:text-[#f3eae4]">
                {user?.name || 'Workspace user'}
              </p>

              <p className="truncate text-[9px] text-[#8d786d] dark:text-[#b7a49a]">
                {user?.email || 'Product team'}
              </p>
            </div>
          )}

          {!collapsed && (
            <span className="text-xs text-[#8d786d]">⌄</span>
          )}
        </div>

        <button
          onClick={logout}
          title="Sign out"
          className={`mt-1 flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-[11px] text-[#866d61] transition hover:bg-[#ead9ce] dark:text-[#b8a49a] dark:hover:bg-white/10 ${
            collapsed ? 'justify-center' : ''
          }`}
        >
          <LogOut size={14} />
          {!collapsed && 'Sign out'}
        </button>
      </div>
    </aside>
  );
}