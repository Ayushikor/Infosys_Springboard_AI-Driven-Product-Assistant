import { useState } from 'react';
import { Outlet } from 'react-router-dom';

import Sidebar from './Sidebar';
import Topbar from './Topbar';

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem('stratov.sidebar') === 'collapsed';
    } catch {
      return false;
    }
  });

  const [mobileOpen, setMobileOpen] = useState(false);

  const toggle = () =>
    setCollapsed((current) => {
      const next = !current;

      try {
        localStorage.setItem(
          'stratov.sidebar',
          next ? 'collapsed' : 'open'
        );
      } catch {
        // Storage is optional.
      }

      return next;
    });

  return (
    <div className="h-screen w-screen overflow-hidden">
      <div className="flex h-full w-full overflow-hidden">

        {/* Desktop Sidebar */}
        <div className="hidden h-full shrink-0 lg:block">
          <Sidebar
            collapsed={collapsed}
            onToggle={toggle}
          />
        </div>

        {/* Mobile Sidebar */}
        {mobileOpen && (
          <div className="fixed inset-0 z-[80] lg:hidden">
            <button
              aria-label="Close navigation"
              className="absolute inset-0 bg-black/50 backdrop-blur-sm"
              onClick={() => setMobileOpen(false)}
            />

            <div className="absolute inset-y-0 left-0 shadow-2xl">
              <Sidebar
                collapsed={false}
                onToggle={() => {}}
                onNavigate={() => setMobileOpen(false)}
              />
            </div>
          </div>
        )}

        {/* Main Application */}
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden">

          {/* Topbar */}
          <Topbar
            onMenuClick={() => setMobileOpen(true)}
          />

          {/* Page Content */}
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