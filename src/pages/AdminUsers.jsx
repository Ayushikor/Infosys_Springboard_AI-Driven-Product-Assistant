
import { useCallback, useEffect, useState } from 'react';

import {
  ShieldCheck,
  Users,
  RefreshCw,
  Search,
  UserCheck,
  History,
  Trash2,
} from 'lucide-react';

import { apiClient } from '../api/apiClient';
import { useAuth } from '../context/AuthContext';

const ROLES = [
  'Admin',
  'Product Manager',
  'Developer',
  'Executive',
];

export default function AdminUsers() {
  const { user: currentUser } = useAuth();

  const [users, setUsers] = useState([]);
  const [logs, setLogs] = useState([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [tab, setTab] = useState('users');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const [userRes, logRes] = await Promise.all([
        apiClient.admin.getUsers(),
        apiClient.admin.getAuditLogs(),
      ]);

      if (userRes?.success) {
        setUsers(userRes.data?.users || []);
      } else {
        setError(userRes?.message || 'Unable to load users.');
      }

      if (logRes?.success) {
        setLogs(logRes.data?.logs || []);
      }
    } catch (err) {
      setError('Unable to load administration data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // -------------------------------------------------------
  // CHANGE ROLE
  // -------------------------------------------------------

  const changeRole = async (target, role) => {
    if (target.role === role) return;

    setBusyId(target.id);
    setError('');
    setNotice('');

    try {
      const result = await apiClient.admin.updateRole(
        target.id,
        role
      );

      if (result?.success) {
        setUsers((items) =>
          items.map((item) =>
            item.id === target.id
              ? result.data.user
              : item
          )
        );

        setNotice(
          `${target.name}'s role was updated to ${role}.`
        );

        const refreshed = await apiClient.admin.getAuditLogs();

        if (refreshed?.success) {
          setLogs(refreshed.data.logs || []);
        }
      } else {
        setError(result?.message || 'Could not update role.');
      }
    } catch {
      setError('Could not update the user role.');
    } finally {
      setBusyId('');
    }
  };

  // -------------------------------------------------------
  // ACTIVATE / DEACTIVATE
  // -------------------------------------------------------

  const toggleStatus = async (target) => {
    const next = !target.isActive;

    if (
      !window.confirm(
        `${next ? 'Activate' : 'Deactivate'} ${target.name}'s account?`
      )
    ) {
      return;
    }

    setBusyId(target.id);
    setError('');
    setNotice('');

    try {
      const result = await apiClient.admin.updateStatus(
        target.id,
        next
      );

      if (result?.success) {
        setUsers((items) =>
          items.map((item) =>
            item.id === target.id
              ? result.data.user
              : item
          )
        );

        setNotice(
          `${target.name}'s account was ${
            next ? 'activated' : 'deactivated'
          }.`
        );

        const refreshed = await apiClient.admin.getAuditLogs();

        if (refreshed?.success) {
          setLogs(refreshed.data.logs || []);
        }
      } else {
        setError(
          result?.message || 'Could not update account status.'
        );
      }
    } catch {
      setError('Could not update account status.');
    } finally {
      setBusyId('');
    }
  };

  // -------------------------------------------------------
  // PERMANENT DELETE
  // -------------------------------------------------------

  const deleteUser = async (target) => {
    if (target.id === currentUser?.id) {
      setError('You cannot delete your own administrator account.');
      return;
    }

    const confirmed = window.confirm(
      `PERMANENTLY DELETE ACCOUNT?\n\n` +
      `Name: ${target.name}\n` +
      `Email: ${target.email}\n` +
      `Role: ${target.role}\n\n` +
      `This will permanently delete the account and its associated ` +
      `workspaces, feedback, themes, features, PRDs, roadmap data, ` +
      `analysis records and chat history.\n\n` +
      `This action cannot be undone.\n\n` +
      `Continue?`
    );

    if (!confirmed) return;

    setBusyId(target.id);
    setError('');
    setNotice('');

    try {
      const result = await apiClient.admin.deleteUser(target.id);

      if (result?.success) {
        setUsers((items) =>
          items.filter((item) => item.id !== target.id)
        );

        setNotice(
          `${target.name}'s account and associated data were permanently deleted.`
        );

        const refreshed = await apiClient.admin.getAuditLogs();

        if (refreshed?.success) {
          setLogs(refreshed.data.logs || []);
        }
      } else {
        setError(
          result?.message || 'Could not delete this account.'
        );
      }
    } catch {
      setError('Could not delete this account.');
    } finally {
      setBusyId('');
    }
  };

  // -------------------------------------------------------
  // SEARCH
  // -------------------------------------------------------

  const filtered = users.filter((item) =>
    `${item.name} ${item.email} ${item.username} ${item.role} ${item.designation || ''}`
      .toLowerCase()
      .includes(query.toLowerCase())
  );

  // -------------------------------------------------------
  // UI
  // -------------------------------------------------------

  return (
    <div className="mx-auto max-w-7xl space-y-6 pb-10">

      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-[#b88b73]/25 bg-[#b88b73]/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[.14em] text-[#9b654a]">
            <ShieldCheck size={13} />
            Administration
          </div>

          <h1 className="text-2xl font-semibold tracking-tight text-[#30231d] dark:text-[#f4ece6]">
            User & access management
          </h1>

          <p className="mt-1 text-sm text-[#927d70]">
            Manage workspace members, roles and account access.
          </p>
        </div>

        <button
          onClick={load}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-black/10 bg-white/60 px-4 py-2.5 text-xs font-semibold text-[#705b50] hover:bg-white dark:border-white/10 dark:bg-white/5 dark:text-[#e3d2c8]"
        >
          <RefreshCw size={14} />
          Refresh data
        </button>
      </div>

      {/* STATISTICS */}

      <div className="grid gap-3 sm:grid-cols-3">
        <Stat
          icon={<Users size={17} />}
          label="Total users"
          value={users.length}
        />

        <Stat
          icon={<UserCheck size={17} />}
          label="Active accounts"
          value={users.filter((item) => item.isActive !== false).length}
        />

        <Stat
          icon={<ShieldCheck size={17} />}
          label="Administrators"
          value={
            users.filter(
              (item) =>
                item.role === 'Admin' &&
                item.isActive !== false
            ).length
          }
        />
      </div>

      {/* FEEDBACK MESSAGES */}

      {(error || notice) && (
        <div
          role={error ? 'alert' : 'status'}
          className={`rounded-xl border px-4 py-3 text-sm ${
            error
              ? 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-300'
              : 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300'
          }`}
        >
          {error || notice}
        </div>
      )}

      {/* TABS */}

      <div className="flex gap-2 border-b border-black/10 dark:border-white/10">
        <button
          onClick={() => setTab('users')}
          className={`border-b-2 px-3 py-3 text-sm font-medium ${
            tab === 'users'
              ? 'border-[#a56e51] text-[#80503d]'
              : 'border-transparent text-[#9c887c]'
          }`}
        >
          Users
        </button>

        <button
          onClick={() => setTab('logs')}
          className={`inline-flex items-center gap-2 border-b-2 px-3 py-3 text-sm font-medium ${
            tab === 'logs'
              ? 'border-[#a56e51] text-[#80503d]'
              : 'border-transparent text-[#9c887c]'
          }`}
        >
          <History size={14} />
          Audit log
        </button>
      </div>

      {/* USERS TAB */}

      {tab === 'users' ? (
        <section className="overflow-hidden rounded-2xl border border-black/[.08] bg-white/65 shadow-sm dark:border-white/10 dark:bg-white/[.035]">

          <div className="flex flex-col gap-3 border-b border-black/[.06] p-4 dark:border-white/10 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-sm font-semibold text-[#3b2b23] dark:text-[#f0e5de]">
                Workspace members
              </h2>

              <p className="mt-1 text-xs text-[#9b877a]">
                Assign roles and control account access.
              </p>
            </div>

            <div className="relative w-full sm:max-w-xs">
              <Search
                size={15}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-[#a18b7e]"
              />

              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search users..."
                className="h-10 w-full rounded-xl border border-black/10 bg-white/70 pl-9 pr-3 text-xs outline-none focus:border-[#b88b73] dark:border-white/10 dark:bg-black/10 dark:text-[#f4ece6]"
              />
            </div>
          </div>

          {loading ? (
            <div className="p-10 text-center text-sm text-[#9b877a]">
              Loading users...
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[900px] text-left text-sm">

                <thead className="bg-[#f8f2ed] text-[10px] uppercase tracking-wider text-[#927d70] dark:bg-white/[.04]">
                  <tr>
                    <th className="px-5 py-3">Member</th>
                    <th className="px-5 py-3">Role</th>
                    <th className="px-5 py-3">Status</th>
                    <th className="px-5 py-3">Joined</th>
                    <th className="px-5 py-3 text-right">Access</th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-black/[.05] dark:divide-white/[.07]">

                  {filtered.map((item) => {
                    const isCurrentUser = item.id === currentUser?.id;
                    const isBusy = busyId === item.id;

                    return (
                      <tr
                        key={item.id}
                        className="text-[#59463b] dark:text-[#ddcfc6]"
                      >

                        <td className="px-5 py-4">
                          <div className="flex items-center gap-3">

                            <div className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-[#ead6c8] text-xs font-bold text-[#80503d]">
                              {(item.name || 'U')[0].toUpperCase()}
                            </div>

                            <div>
                              <p className="font-semibold">
                                {item.name}{' '}

                                {isCurrentUser && (
                                  <span className="text-[10px] text-[#a56e51]">
                                    (you)
                                  </span>
                                )}
                              </p>

                              <p className="text-xs text-[#a18b7e]">
                                {item.email}
                              </p>

                              {item.designation && (
                                <p className="mt-0.5 text-[11px] text-[#a18b7e]">
                                  {item.designation}
                                </p>
                              )}
                            </div>

                          </div>
                        </td>

                        <td className="px-5 py-4">
                          <select
                            value={item.role}
                            disabled={isBusy || isCurrentUser}
                            onChange={(event) =>
                              changeRole(item, event.target.value)
                            }
                            className="rounded-lg border border-black/10 bg-white px-2.5 py-2 text-xs outline-none focus:border-[#b88b73] disabled:opacity-50 dark:border-white/10 dark:bg-[#211815] dark:text-[#f4ece6]"
                          >
                            {ROLES.map((role) => (
                              <option key={role} value={role}>
                                {role}
                              </option>
                            ))}
                          </select>
                        </td>

                        <td className="px-5 py-4">
                          <span
                            className={`rounded-full px-2.5 py-1 text-[10px] font-semibold ${
                              item.isActive === false
                                ? 'bg-rose-100 text-rose-700 dark:bg-rose-500/10 dark:text-rose-300'
                                : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300'
                            }`}
                          >
                            {item.isActive === false ? 'Inactive' : 'Active'}
                          </span>
                        </td>

                        <td className="px-5 py-4 text-xs text-[#9b877a]">
                          {item.createdAt
                            ? new Date(item.createdAt).toLocaleDateString()
                            : '—'}
                        </td>

                        <td className="px-5 py-4">
                          <div className="flex items-center justify-end gap-2">

                            <button
                              disabled={isBusy || isCurrentUser}
                              onClick={() => toggleStatus(item)}
                              className="rounded-lg border border-black/10 px-3 py-2 text-xs font-medium hover:bg-[#f7f0ea] disabled:cursor-not-allowed disabled:opacity-40 dark:border-white/10 dark:hover:bg-white/10"
                            >
                              {item.isActive === false
                                ? 'Activate'
                                : 'Deactivate'}
                            </button>

                            <button
                              disabled={isBusy || isCurrentUser}
                              onClick={() => deleteUser(item)}
                              title={
                                isCurrentUser
                                  ? 'You cannot delete your own account'
                                  : 'Permanently delete account'
                              }
                              className="inline-flex items-center gap-1.5 rounded-lg border border-rose-200 px-3 py-2 text-xs font-semibold text-rose-600 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-rose-500/20 dark:text-rose-300 dark:hover:bg-rose-500/10"
                            >
                              <Trash2 size={13} />
                              Delete
                            </button>

                          </div>
                        </td>

                      </tr>
                    );
                  })}

                </tbody>
              </table>

              {filtered.length === 0 && (
                <p className="p-8 text-center text-sm text-[#9b877a]">
                  No matching users.
                </p>
              )}
            </div>
          )}
        </section>
      ) : (

        /* AUDIT LOG TAB */

        <section className="overflow-hidden rounded-2xl border border-black/[.08] bg-white/65 dark:border-white/10 dark:bg-white/[.035]">

          <div className="border-b border-black/[.06] p-4 dark:border-white/10">
            <h2 className="text-sm font-semibold text-[#3b2b23] dark:text-[#f0e5de]">
              Recent administrative activity
            </h2>

            <p className="mt-1 text-xs text-[#9b877a]">
              Latest 100 administrative actions.
            </p>
          </div>

          {logs.length ? (
            <div className="divide-y divide-black/[.05] dark:divide-white/[.07]">

              {logs.map((log, index) => (
                <div
                  key={`${log.createdAt}-${index}`}
                  className="flex flex-col gap-1 px-5 py-4 sm:flex-row sm:items-center sm:justify-between"
                >

                  <div>
                    <p className="text-sm font-medium text-[#59463b] dark:text-[#ddcfc6]">
                      {log.action?.replaceAll('.', ' ')}
                    </p>

                    <p className="mt-1 text-xs text-[#9b877a]">
                      By {log.actorEmail || 'Unknown'} · Target{' '}
                      {log.targetUserId}
                    </p>

                    {log.details?.from && (
                      <p className="mt-1 text-xs text-[#9b877a]">
                        {log.details.from} → {log.details.to}
                      </p>
                    )}

                    {log.details?.deletedEmail && (
                      <p className="mt-1 text-xs text-[#9b877a]">
                        Deleted account: {log.details.deletedEmail}
                      </p>
                    )}
                  </div>

                  <time className="text-[11px] text-[#a18b7e]">
                    {log.createdAt
                      ? new Date(log.createdAt).toLocaleString()
                      : ''}
                  </time>

                </div>
              ))}

            </div>
          ) : (
            <p className="p-8 text-center text-sm text-[#9b877a]">
              No administrative activity recorded yet.
            </p>
          )}

        </section>
      )}

    </div>
  );
}


function Stat({ icon, label, value }) {
  return (
    <div className="rounded-2xl border border-black/[.07] bg-white/60 p-4 dark:border-white/10 dark:bg-white/[.035]">

      <div className="flex items-center justify-between text-[#9b877a]">
        <span className="text-xs">{label}</span>
        {icon}
      </div>

      <p className="mt-3 text-2xl font-semibold tracking-tight text-[#3b2b23] dark:text-[#f4ece6]">
        {value}
      </p>

    </div>
  );
}
