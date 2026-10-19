import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar from './Topbar';

// Shared shell for every authenticated page.
export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem('copilot.sidebar') === 'collapsed'; } catch { return false; }
  });
  const [mobileOpen, setMobileOpen] = useState(false);

  const toggle = () => setCollapsed((c) => {
    const next = !c;
    try { localStorage.setItem('copilot.sidebar', next ? 'collapsed' : 'open'); } catch { /* ignore */ }
    return next;
  });

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Desktop sidebar */}
      <div className="hidden lg:block"><Sidebar collapsed={collapsed} onToggle={toggle} /></div>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-navy-900/50" onClick={() => setMobileOpen(false)} />
          <div className="absolute left-0 top-0 h-full"><Sidebar collapsed={false} onToggle={() => {}} onNavigate={() => setMobileOpen(false)} /></div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onMenuClick={() => setMobileOpen(true)} />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6">
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
