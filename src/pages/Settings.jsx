import { useState } from 'react';
import { Moon, Sun, LogOut, Info, Save } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { useAppData } from '../context/AppDataContext';
import { apiClient, isMockMode } from '../api/apiClient';
import { apiConfig } from '../api/apiConfig';
import Button from '../components/common/Button';
import Input from '../components/common/Input';

export default function Settings() {
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const { raw, refresh } = useAppData();
  const [prefs, setPrefs] = useState({ compactTables: raw?.preferences?.compactTables ?? false });
  const [saved, setSaved] = useState('');
  const [profile, setProfile] = useState({ name: user?.name || '', role: user?.role || '' });

  const savePrefs = async () => {
    await apiClient.preferences.update({ ...prefs, theme });
    await refresh();
    setSaved('Preferences saved.');
    setTimeout(() => setSaved(''), 2000);
  };

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <section className="card p-6">
        <h2 className="text-sm font-semibold">User profile</h2>
        <p className="mt-1 text-xs text-navy-500">Signed in as {user?.email} (username @{user?.username}).</p>
        <div className="mt-4 space-y-4">
          <Input label="Display name" value={profile.name} onChange={(e) => setProfile({ ...profile, name: e.target.value })} disabled />
          <Input label="Role" value={profile.role} onChange={(e) => setProfile({ ...profile, role: e.target.value })} disabled />
          <p className="text-xs text-navy-500">Profile fields are set at registration in this demo.</p>
        </div>
      </section>

      <section className="card p-6">
        <h2 className="text-sm font-semibold">Appearance and preferences</h2>
        <div className="mt-4 flex items-center justify-between rounded-lg border border-slate-200 p-4 dark:border-navy-700">
          <div>
            <p className="text-sm font-medium">Theme</p>
            <p className="text-xs text-navy-500">Currently {theme} mode</p>
          </div>
          <div className="inline-flex rounded-lg bg-slate-100 p-1 dark:bg-navy-900" role="radiogroup" aria-label="Theme">
            <button role="radio" aria-checked={theme === 'light'} onClick={() => setTheme('light')} className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm ${theme === 'light' ? 'bg-white shadow-sm dark:bg-navy-700' : 'text-navy-500'}`}><Sun size={14} />Light</button>
            <button role="radio" aria-checked={theme === 'dark'} onClick={() => setTheme('dark')} className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm ${theme === 'dark' ? 'bg-white shadow-sm dark:bg-navy-700' : 'text-navy-500'}`}><Moon size={14} />Dark</button>
          </div>
        </div>
        <label className="mt-4 flex items-center justify-between rounded-lg border border-slate-200 p-4 text-sm dark:border-navy-700">
          <span>Compact tables</span>
          <input type="checkbox" checked={prefs.compactTables} onChange={(e) => setPrefs({ ...prefs, compactTables: e.target.checked })} className="h-4 w-4 rounded border-slate-300 text-accent" />
        </label>
        <div className="mt-4 flex items-center gap-3">
          <Button onClick={savePrefs}><Save size={15} />Save preferences</Button>
          {saved && <span className="text-xs text-emerald-600">{saved}</span>}
        </div>
      </section>

      <section className="card p-6">
        <div className="flex items-center gap-2 text-sm font-semibold"><Info size={15} />Application information</div>
        <dl className="mt-4 space-y-2 text-sm">
          <div className="flex justify-between"><dt className="text-navy-500">Application</dt><dd>AI Product Manager Copilot</dd></div>
          <div className="flex justify-between"><dt className="text-navy-500">Version</dt><dd>1.0.0</dd></div>
          <div className="flex justify-between"><dt className="text-navy-500">Storage</dt><dd>Browser LocalStorage</dd></div>
          <div className="flex justify-between"><dt className="text-navy-500">Current API mode</dt><dd><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${isMockMode ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'}`}>{apiConfig.mode.toUpperCase()}</span></dd></div>
          {!isMockMode && <div className="flex justify-between"><dt className="text-navy-500">Backend URL</dt><dd className="truncate pl-4 text-xs">{apiConfig.baseUrl}</dd></div>}
        </dl>
        <p className="mt-4 text-xs text-navy-500">Demo authentication only. Passwords are hashed in the browser and this is not production-grade security.</p>
      </section>

      <section className="card p-6">
        <h2 className="text-sm font-semibold">Session</h2>
        <p className="mt-1 text-xs text-navy-500">End your session on this device.</p>
        <Button variant="danger" className="mt-4" onClick={logout}><LogOut size={15} />Logout</Button>
      </section>
    </div>
  );
}
