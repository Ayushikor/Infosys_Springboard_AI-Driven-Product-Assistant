import { useEffect, useRef, useState } from 'react';
import { useLocation, Link, useNavigate } from 'react-router-dom';
import { Bell, Menu, Moon, Search, Sun, ChevronDown, User, Settings as SettingsIcon, LogOut } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { NAV_ITEMS } from './Sidebar';

const LABELS = Object.fromEntries(NAV_ITEMS.map((n) => [n.to, n.label]));

export default function Topbar({ onMenuClick }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const [menuOpen, setMenuOpen] = useState(false);
  const [query, setQuery] = useState('');
  const menuRef = useRef(null);

  const title = LABELS[location.pathname] || 'Overview Dashboard';
  const crumbs = location.pathname.split('/').filter(Boolean);

  useEffect(() => {
    const close = (e) => { if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false); };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, []);

  const onSearch = (e) => {
    e.preventDefault();
    const q = query.trim().toLowerCase();
    if (!q) return;
    // Global search routes to the most relevant page; detailed filtering lives on each page.
    const target = q.includes('prd') ? '/prd' : q.includes('theme') ? '/themes' : q.includes('roadmap') ? '/roadmap' : '/feedback';
    navigate(`${target}?q=${encodeURIComponent(query.trim())}`);
    setQuery('');
  };

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-slate-200 bg-white/80 px-4 backdrop-blur dark:border-navy-700 dark:bg-navy-800/80 lg:px-6">
      <button onClick={onMenuClick} className="btn-ghost p-2 lg:hidden" aria-label="Open navigation"><Menu size={18} /></button>

      <div className="min-w-0 flex-1">
        <nav aria-label="Breadcrumb" className="hidden items-center gap-1 text-xs text-navy-500 sm:flex">
          <Link to="/dashboard" className="hover:text-accent">Home</Link>
          {crumbs.map((c, i) => (
            <span key={i} className="flex items-center gap-1">
              <span>/</span>
              <span className="capitalize">{c}</span>
            </span>
          ))}
        </nav>
        <h1 className="truncate text-base font-semibold">{title}</h1>
      </div>

      <form onSubmit={onSearch} className="relative hidden md:block">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-navy-500" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search feedback, PRDs…"
          className="input w-64 pl-9 py-1.5"
          aria-label="Global search"
        />
      </form>

      <button className="btn-ghost relative p-2" aria-label="Notifications" title="Notifications">
        <Bell size={18} />
        <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-accent" />
      </button>

      <button onClick={toggleTheme} className="btn-ghost p-2" aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}>
        {isDark ? <Sun size={18} /> : <Moon size={18} />}
      </button>

      <div className="relative" ref={menuRef}>
        <button onClick={() => setMenuOpen((o) => !o)} className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-slate-100 dark:hover:bg-navy-700" aria-haspopup="menu" aria-expanded={menuOpen}>
          <div className="grid h-7 w-7 place-items-center rounded-full bg-indigo-100 text-xs font-semibold text-accent-600 dark:bg-indigo-500/20 dark:text-indigo-300">
            {(user?.name || 'U')[0]}
          </div>
          <ChevronDown size={14} className="hidden text-navy-500 sm:block" />
        </button>
        {menuOpen && (
          <div role="menu" className="absolute right-0 mt-2 w-56 rounded-xl border border-slate-200 bg-white p-1 shadow-xl dark:border-navy-700 dark:bg-navy-800">
            <div className="px-3 py-2">
              <p className="truncate text-sm font-medium">{user?.name}</p>
              <p className="truncate text-xs text-navy-500">{user?.email}</p>
            </div>
            <hr className="my-1 border-slate-200 dark:border-navy-700" />
            <Link role="menuitem" to="/settings" onClick={() => setMenuOpen(false)} className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm hover:bg-slate-100 dark:hover:bg-navy-700"><User size={15} />Profile</Link>
            <Link role="menuitem" to="/settings" onClick={() => setMenuOpen(false)} className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm hover:bg-slate-100 dark:hover:bg-navy-700"><SettingsIcon size={15} />Settings</Link>
            <button role="menuitem" onClick={logout} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-500/10"><LogOut size={15} />Logout</button>
          </div>
        )}
      </div>
    </header>
  );
}
