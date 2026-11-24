import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar from './Topbar';

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem('stratov.sidebar') === 'collapsed'; } catch { return false; }
  });
  const [mobileOpen, setMobileOpen] = useState(false);

  const toggle = () => setCollapsed((current) => {
    const next = !current;
    try { localStorage.setItem('stratov.sidebar', next ? 'collapsed' : 'open'); } catch { /* storage is optional */ }
    return next;
  });

  return (
    <div className="stratov-stage min-h-screen">
      <div className="stratov-window">
        <div className="hidden h-full shrink-0 lg:block">
          <Sidebar collapsed={collapsed} onToggle={toggle} />
        </div>

        {mobileOpen && (
          <div className="fixed inset-0 z-[80] lg:hidden">
            <button aria-label="Close navigation" className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
            <div className="absolute inset-y-0 left-0 shadow-2xl">
              <Sidebar collapsed={false} onToggle={() => {}} onNavigate={() => setMobileOpen(false)} />
            </div>
          </div>
        )}

        <div className="flex min-w-0 flex-1 flex-col">
          <Topbar onMenuClick={() => setMobileOpen(true)} />
          <main className="stratov-main min-h-0 flex-1 overflow-y-auto px-4 pb-6 pt-4 sm:px-5 lg:px-6">
            <div className="mx-auto w-full max-w-[1600px]">
              <Outlet />
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
