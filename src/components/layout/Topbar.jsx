import { useEffect, useRef, useState } from 'react';
import { useLocation, Link, useNavigate } from 'react-router-dom';
import { Bell, Menu, Moon, Search, Sun, ChevronDown, UserRound, Settings as SettingsIcon, LogOut, Command, CalendarDays } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { NAV_ITEMS } from './Sidebar';

const LABELS = Object.fromEntries(NAV_ITEMS.map((item) => [item.to, item.label]));

export default function Topbar({ onMenuClick }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const [menuOpen, setMenuOpen] = useState(false);
  const [query, setQuery] = useState('');
  const menuRef = useRef(null);

  const title = LABELS[location.pathname] || 'Overview';
  const crumbs = location.pathname.split('/').filter(Boolean);

  useEffect(() => {
    const close = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) setMenuOpen(false);
    };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, []);

  const onSearch = (event) => {
    event.preventDefault();
    const value = query.trim().toLowerCase();
    if (!value) return;
    const target = value.includes('prd') ? '/prd' : value.includes('theme') ? '/themes' : value.includes('roadmap') || value.includes('milestone') ? '/roadmap' : '/feedback';
    navigate(`${target}?q=${encodeURIComponent(query.trim())}`);
    setQuery('');
  };

  return (
    <header className="sticky top-0 z-30 flex min-h-[78px] items-center gap-3 border-b border-black/[.07] bg-white/25 px-4 backdrop-blur-2xl dark:border-white/[.08] dark:bg-black/20 sm:px-6 lg:px-8">
      <button onClick={onMenuClick} className="btn-ghost p-2 lg:hidden" aria-label="Open navigation"><Menu size={19} /></button>

      <div className="min-w-0 flex-1">
        <nav aria-label="Breadcrumb" className="mb-1 hidden items-center gap-2 text-[10px] font-medium capitalize tracking-wide text-[#a18b7e] sm:flex">
          <Link to="/dashboard" className="hover:text-[#80503d]">Workspace</Link>
          {crumbs.map((crumb, index) => (
            <span key={`${crumb}-${index}`} className="flex items-center gap-2">
              <span className="text-[#c8b6aa]">/</span>
              <span className={index === crumbs.length - 1 ? 'font-semibold text-[#755547] dark:text-[#e5bba5]' : ''}>{crumb.replaceAll('-', ' ')}</span>
            </span>
          ))}
        </nav>
        <h1 className="truncate text-[17px] font-semibold tracking-tight text-[#2d211c] dark:text-[#f4ece6]">{title}</h1>
      </div>

      <form onSubmit={onSearch} className="relative hidden w-full max-w-[300px] lg:block">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9c887c]" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search your workspace..."
          className="h-10 w-full rounded-xl border border-black/10 bg-white/55 pl-9 pr-12 text-xs text-[#392820] outline-none transition placeholder:text-[#ad9a8e] focus:border-[#b88b73] focus:ring-2 focus:ring-[#b88b73]/15 dark:border-white/10 dark:bg-white/[.045] dark:text-[#f4ece6]"
          aria-label="Global search"
        />
        <span className="absolute right-2.5 top-1/2 flex -translate-y-1/2 items-center gap-1 rounded-md border border-[#e5d9d0] bg-white px-1.5 py-1 text-[9px] text-[#9c887c] dark:border-[#49362d] dark:bg-[#30221c]"><Command size={10} /> K</span>
      </form>

      <button className="relative rounded-xl p-2.5 text-[#806b60] transition hover:bg-[#f4ebe4] dark:text-[#c7b4a8] dark:hover:bg-[#2a1e19]" aria-label="Notifications" title="Notifications">
        <Bell size={18} />
        <span className="absolute right-2.5 top-2.5 h-1.5 w-1.5 rounded-full bg-[#a45f43] ring-2 ring-[#fffdfa] dark:ring-[#191311]" />
      </button>
      <button className="rounded-xl p-2.5 text-[#806b60] transition hover:bg-[#f4ebe4] dark:text-[#c7b4a8] dark:hover:bg-[#2a1e19]" aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'} onClick={toggleTheme}>
        {isDark ? <Sun size={18} /> : <Moon size={18} />}
      </button>
      <button className="hidden items-center gap-2 rounded-xl border border-black/10 bg-white/55 px-3 py-2 text-xs font-medium text-[#806b60] transition hover:bg-[#f4ebe4] dark:border-white/10 dark:bg-white/[.045] dark:text-[#c7b4a8] sm:flex">
        <CalendarDays size={15} /> <span>Workspace</span>
      </button>

      <div className="relative" ref={menuRef}>
        <button onClick={() => setMenuOpen((open) => !open)} className="flex items-center gap-2 rounded-xl p-1.5 transition hover:bg-[#f4ebe4] dark:hover:bg-[#2a1e19]" aria-haspopup="menu" aria-expanded={menuOpen}>
          <div className="grid h-8 w-8 place-items-center rounded-full bg-[#d9b8a5] text-xs font-bold text-[#563528]">{(user?.name || 'U')[0].toUpperCase()}</div>
          <ChevronDown size={14} className="hidden text-[#947d70] sm:block" />
        </button>
        {menuOpen && (
          <div role="menu" className="absolute right-0 mt-2 w-60 rounded-2xl border border-black/10 bg-[#fffdfa] p-2 shadow-soft dark:border-white/10 dark:bg-[#211815]">
            <div className="px-3 py-2">
              <p className="truncate text-sm font-semibold text-[#2d211c] dark:text-[#f4ece6]">{user?.name}</p>
              <p className="truncate text-xs text-[#967f72]">{user?.email}</p>
            </div>
            <div className="my-1 border-t border-[#eee5de] dark:border-white/10" />
            <Link role="menuitem" to="/settings" onClick={() => setMenuOpen(false)} className="flex items-center gap-2 rounded-xl px-3 py-2.5 text-xs font-medium text-[#705b50] hover:bg-[#f7f0ea] dark:text-[#d0bdb1] dark:hover:bg-[#30221c]"><UserRound size={15} />Profile</Link>
            <Link role="menuitem" to="/settings" onClick={() => setMenuOpen(false)} className="flex items-center gap-2 rounded-xl px-3 py-2.5 text-xs font-medium text-[#705b50] hover:bg-[#f7f0ea] dark:text-[#d0bdb1] dark:hover:bg-[#30221c]"><SettingsIcon size={15} />Settings</Link>
            <button role="menuitem" onClick={logout} className="flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-xs font-medium text-rose-700 hover:bg-rose-50 dark:text-rose-300 dark:hover:bg-rose-500/10"><LogOut size={15} />Sign out</button>
          </div>
        )}
      </div>
    </header>
  );
}
