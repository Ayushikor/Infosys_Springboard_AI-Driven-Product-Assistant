import { useEffect, useRef, useState } from "react";
import { useLocation, Link, useNavigate } from "react-router-dom";

import {
  Bell,
  Menu,
  Moon,
  Search,
  Sun,
  ChevronDown,
  UserRound,
  Settings as SettingsIcon,
  LogOut,
  Command,
  CalendarDays,
  ShieldCheck,
  Check,
  CheckCheck,
  Trash2,
  X,
  Loader2,
} from "lucide-react";

import { useAuth } from "../../context/AuthContext";
import { useTheme } from "../../context/ThemeContext";
import { NAV_ITEMS } from "./Sidebar";
import { apiClient } from "../../api/apiClient";

const LABELS = Object.fromEntries(
  NAV_ITEMS.map((item) => [item.to, item.label])
);

const POLL_INTERVAL = 30000;

function extractData(response) {
  if (!response) return null;

  if (response.data !== undefined) {
    return response.data;
  }

  return response;
}

function extractNotifications(response) {
  const data = extractData(response);

  if (Array.isArray(data)) {
    return data;
  }

  if (Array.isArray(data?.notifications)) {
    return data.notifications;
  }

  if (Array.isArray(data?.items)) {
    return data.items;
  }

  return [];
}

function extractUnreadCount(response) {
  const data = extractData(response);

  if (typeof data === "number") {
    return data;
  }

  return (
    data?.count ??
    data?.unreadCount ??
    data?.unread ??
    0
  );
}

function formatNotificationDate(value) {
  if (!value) return "";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  const now = new Date();
  const diff = now.getTime() - date.getTime();

  if (diff < 60000) return "Just now";

  if (diff < 3600000) {
    return `${Math.floor(diff / 60000)}m ago`;
  }

  if (diff < 86400000) {
    return `${Math.floor(diff / 3600000)}h ago`;
  }

  if (diff < 604800000) {
    return `${Math.floor(diff / 86400000)}d ago`;
  }

  return date.toLocaleDateString();
}

export default function Topbar({ onMenuClick }) {
  const location = useLocation();
  const navigate = useNavigate();

  const { user, logout } = useAuth();
  const { isDark, toggleTheme } = useTheme();

  const [menuOpen, setMenuOpen] = useState(false);
  const [notificationOpen, setNotificationOpen] = useState(false);
  const [query, setQuery] = useState("");

  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notificationsLoading, setNotificationsLoading] =
    useState(false);
  const [notificationError, setNotificationError] =
    useState("");

  const menuRef = useRef(null);
  const notificationRef = useRef(null);

  const title =
    LABELS[location.pathname] ||
    (location.pathname === "/admin/users"
      ? "User administration"
      : "Overview");

  const crumbs = location.pathname
    .split("/")
    .filter(Boolean);

  // ---------------------------------------------------------
  // FETCH NOTIFICATIONS
  // ---------------------------------------------------------

  const fetchNotifications = async (showLoader = false) => {
    if (!user?.id) return;

    if (showLoader) {
      setNotificationsLoading(true);
    }

    try {
      const [
        notificationResponse,
        unreadResponse,
      ] = await Promise.all([
        apiClient.notifications.getAll(50),
        apiClient.notifications.getUnreadCount(),
      ]);

      if (
        notificationResponse?.success === false ||
        unreadResponse?.success === false
      ) {
        throw new Error(
          notificationResponse?.message ||
            unreadResponse?.message ||
            "Unable to load notifications."
        );
      }

      setNotifications(
        extractNotifications(notificationResponse)
      );

      setUnreadCount(
        Number(extractUnreadCount(unreadResponse)) || 0
      );

      setNotificationError("");
    } catch (error) {
      console.error("Notification fetch failed:", error);

      setNotificationError(
        error.message || "Unable to load notifications."
      );
    } finally {
      if (showLoader) {
        setNotificationsLoading(false);
      }
    }
  };

  // Fetch on login/user change and poll periodically.

  useEffect(() => {
    if (!user?.id) {
      setNotifications([]);
      setUnreadCount(0);
      setNotificationError("");
      return undefined;
    }

    fetchNotifications(true);

    const interval = setInterval(() => {
      fetchNotifications(false);
    }, POLL_INTERVAL);

    return () => clearInterval(interval);
  }, [user?.id]);

  // ---------------------------------------------------------
  // CLOSE MENUS WHEN CLICKING OUTSIDE
  // ---------------------------------------------------------

  useEffect(() => {
    const close = (event) => {
      if (
        menuRef.current &&
        !menuRef.current.contains(event.target)
      ) {
        setMenuOpen(false);
      }

      if (
        notificationRef.current &&
        !notificationRef.current.contains(event.target)
      ) {
        setNotificationOpen(false);
      }
    };

    document.addEventListener("mousedown", close);

    return () => {
      document.removeEventListener("mousedown", close);
    };
  }, []);

  // ---------------------------------------------------------
  // SEARCH
  // ---------------------------------------------------------

  const onSearch = (event) => {
    event.preventDefault();

    const value = query.trim().toLowerCase();

    if (!value) return;

    const target = value.includes("prd")
      ? "/prd"
      : value.includes("theme")
        ? "/themes"
        : value.includes("roadmap") ||
            value.includes("milestone")
          ? "/roadmap"
          : "/feedback";

    navigate(
      `${target}?q=${encodeURIComponent(query.trim())}`
    );

    setQuery("");
  };

  // ---------------------------------------------------------
  // MARK ONE NOTIFICATION AS READ
  // ---------------------------------------------------------

  const handleMarkAsRead = async (notification) => {
    if (
      notification.read ||
      notification.isRead ||
      !notification.id
    ) {
      return;
    }

    try {
      const response =
        await apiClient.notifications.markAsRead(
          notification.id
        );

      if (response?.success === false) {
        throw new Error(
          response.message || "Unable to mark as read."
        );
      }

      setNotifications((previous) =>
        previous.map((item) =>
          item.id === notification.id
            ? {
                ...item,
                read: true,
                isRead: true,
              }
            : item
        )
      );

      setUnreadCount((count) =>
        Math.max(0, count - 1)
      );
    } catch (error) {
      console.error(
        "Mark notification read failed:",
        error
      );
    }
  };

  // ---------------------------------------------------------
  // MARK ALL AS READ
  // ---------------------------------------------------------

  const handleMarkAllAsRead = async () => {
    if (unreadCount === 0) return;

    try {
      const response =
        await apiClient.notifications.markAllAsRead();

      if (response?.success === false) {
        throw new Error(
          response.message ||
            "Unable to mark notifications as read."
        );
      }

      setNotifications((previous) =>
        previous.map((item) => ({
          ...item,
          read: true,
          isRead: true,
        }))
      );

      setUnreadCount(0);
    } catch (error) {
      console.error(
        "Mark all notifications read failed:",
        error
      );
    }
  };

  // ---------------------------------------------------------
  // DELETE NOTIFICATION
  // ---------------------------------------------------------

  const handleDeleteNotification = async (
    notification
  ) => {
    if (!notification?.id) return;

    try {
      const response =
        await apiClient.notifications.remove(
          notification.id
        );

      if (response?.success === false) {
        throw new Error(
          response.message ||
            "Unable to delete notification."
        );
      }

      setNotifications((previous) =>
        previous.filter(
          (item) => item.id !== notification.id
        )
      );

      if (
        !notification.read &&
        !notification.isRead
      ) {
        setUnreadCount((count) =>
          Math.max(0, count - 1)
        );
      }
    } catch (error) {
      console.error(
        "Delete notification failed:",
        error
      );
    }
  };

  // ---------------------------------------------------------
  // OPEN NOTIFICATION
  // ---------------------------------------------------------

  const handleNotificationClick = async (
    notification
  ) => {
    await handleMarkAsRead(notification);

    setNotificationOpen(false);

    if (notification.link) {
      navigate(notification.link);
    }
  };

  // ---------------------------------------------------------
  // UI
  // ---------------------------------------------------------

  return (
    <header className="sticky top-0 z-30 flex min-h-[78px] items-center gap-3 border-b border-black/[.07] bg-white/25 px-4 backdrop-blur-2xl dark:border-white/[.08] dark:bg-black/20 sm:px-6 lg:px-8">

      {/* MOBILE MENU */}

      <button
        onClick={onMenuClick}
        className="btn-ghost p-2 lg:hidden"
        aria-label="Open navigation"
      >
        <Menu size={19} />
      </button>

      {/* PAGE TITLE */}

      <div className="min-w-0 flex-1">
        <nav
          aria-label="Breadcrumb"
          className="mb-1 hidden items-center gap-2 text-[10px] font-medium capitalize tracking-wide text-[#a18b7e] sm:flex"
        >
          <Link
            to="/dashboard"
            className="hover:text-[#80503d]"
          >
            Workspace
          </Link>

          {crumbs.map((crumb, index) => (
            <span
              key={`${crumb}-${index}`}
              className="flex items-center gap-2"
            >
              <span className="text-[#c8b6aa]">
                /
              </span>

              <span
                className={
                  index === crumbs.length - 1
                    ? "font-semibold text-[#755547] dark:text-[#e5bba5]"
                    : ""
                }
              >
                {crumb.replaceAll("-", " ")}
              </span>
            </span>
          ))}
        </nav>

        <h1 className="truncate text-[17px] font-semibold tracking-tight text-[#2d211c] dark:text-[#f4ece6]">
          {title}
        </h1>
      </div>

      {/* SEARCH */}

      <form
        onSubmit={onSearch}
        className="relative hidden w-full max-w-[300px] lg:block"
      >
        <Search
          size={15}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9c887c]"
        />

        <input
          value={query}
          onChange={(event) =>
            setQuery(event.target.value)
          }
          placeholder="Search your workspace..."
          className="h-10 w-full rounded-xl border border-black/10 bg-white/55 pl-9 pr-12 text-xs text-[#392820] outline-none transition placeholder:text-[#ad9a8e] focus:border-[#b88b73] focus:ring-2 focus:ring-[#b88b73]/15 dark:border-white/10 dark:bg-white/[.045] dark:text-[#f4ece6]"
          aria-label="Global search"
        />

        <span className="absolute right-2.5 top-1/2 flex -translate-y-1/2 items-center gap-1 rounded-md border border-[#e5d9d0] bg-white px-1.5 py-1 text-[9px] text-[#9c887c] dark:border-[#49362d] dark:bg-[#30221c]">
          <Command size={10} /> K
        </span>
      </form>

      {/* NOTIFICATIONS */}

      <div
        className="relative"
        ref={notificationRef}
      >
        <button
          onClick={() => {
            setNotificationOpen((open) => !open);

            if (!notificationOpen) {
              fetchNotifications(true);
            }
          }}
          className="relative rounded-xl p-2.5 text-[#806b60] transition hover:bg-[#f4ebe4] dark:text-[#c7b4a8] dark:hover:bg-[#2a1e19]"
          aria-label={`Notifications${
            unreadCount > 0
              ? `, ${unreadCount} unread`
              : ""
          }`}
          title="Notifications"
          aria-expanded={notificationOpen}
        >
          <Bell size={18} />

          {unreadCount > 0 && (
            <span className="absolute -right-0.5 -top-0.5 flex min-h-[17px] min-w-[17px] items-center justify-center rounded-full bg-[#a45f43] px-1 text-[9px] font-bold text-white ring-2 ring-[#fffdfa] dark:ring-[#191311]">
              {unreadCount > 99
                ? "99+"
                : unreadCount}
            </span>
          )}
        </button>

        {notificationOpen && (
          <div className="absolute right-0 top-full z-50 mt-3 w-[min(92vw,390px)] overflow-hidden rounded-2xl border border-black/10 bg-[#fffdfa] shadow-2xl dark:border-white/10 dark:bg-[#211815]">

            {/* HEADER */}

            <div className="flex items-center justify-between border-b border-[#eee5de] px-4 py-3 dark:border-white/10">
              <div>
                <h2 className="text-sm font-semibold text-[#392820] dark:text-[#f4ece6]">
                  Notifications
                </h2>

                <p className="mt-0.5 text-[10px] text-[#9c887c]">
                  {unreadCount > 0
                    ? `${unreadCount} unread notification${
                        unreadCount === 1
                          ? ""
                          : "s"
                      }`
                    : "You're all caught up"}
                </p>
              </div>

              <div className="flex items-center gap-1">
                {unreadCount > 0 && (
                  <button
                    onClick={handleMarkAllAsRead}
                    title="Mark all as read"
                    className="rounded-lg p-2 text-[#806b60] transition hover:bg-[#f4ebe4] dark:hover:bg-[#30221c]"
                  >
                    <CheckCheck size={16} />
                  </button>
                )}

                <button
                  onClick={() =>
                    setNotificationOpen(false)
                  }
                  className="rounded-lg p-2 text-[#806b60] transition hover:bg-[#f4ebe4] dark:hover:bg-[#30221c]"
                  aria-label="Close notifications"
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            {/* CONTENT */}

            <div className="max-h-[420px] overflow-y-auto">

              {notificationsLoading && (
                <div className="flex items-center justify-center gap-2 py-10 text-xs text-[#9c887c]">
                  <Loader2
                    size={16}
                    className="animate-spin"
                  />
                  Loading notifications...
                </div>
              )}

              {!notificationsLoading &&
                notificationError && (
                  <div className="px-5 py-8 text-center">
                    <p className="text-xs text-rose-600 dark:text-rose-300">
                      {notificationError}
                    </p>

                    <button
                      onClick={() =>
                        fetchNotifications(true)
                      }
                      className="mt-3 rounded-lg border border-[#d8c4b6] px-3 py-2 text-xs text-[#80503d] hover:bg-[#f4ebe4] dark:border-[#49362d] dark:text-[#d8b5a1]"
                    >
                      Retry
                    </button>
                  </div>
                )}

              {!notificationsLoading &&
                !notificationError &&
                notifications.length === 0 && (
                  <div className="flex flex-col items-center justify-center px-5 py-10 text-center">
                    <div className="mb-3 grid h-12 w-12 place-items-center rounded-full bg-[#f4ebe4] text-[#a78570] dark:bg-[#30221c]">
                      <Bell size={20} />
                    </div>

                    <p className="text-sm font-medium text-[#392820] dark:text-[#f4ece6]">
                      No notifications yet
                    </p>

                    <p className="mt-1 text-xs text-[#9c887c]">
                      Notifications will appear here when events occur.
                    </p>
                  </div>
                )}

              {!notificationsLoading &&
                notifications.map((notification) => {
                  const isRead =
                    notification.read ||
                    notification.isRead;

                  return (
                    <div
                      key={notification.id}
                      className={`group flex gap-3 border-b border-[#eee5de] px-4 py-3 transition hover:bg-[#f8f1eb] dark:border-white/[.06] dark:hover:bg-[#30221c] ${
                        !isRead
                          ? "bg-[#f8f1eb]/70 dark:bg-[#30221c]/50"
                          : ""
                      }`}
                    >
                      <button
                        onClick={() =>
                          handleNotificationClick(
                            notification
                          )
                        }
                        className="flex min-w-0 flex-1 gap-3 text-left"
                      >
                        <div className="mt-1 flex-shrink-0">
                          {!isRead ? (
                            <span className="block h-2 w-2 rounded-full bg-[#a45f43]" />
                          ) : (
                            <span className="block h-2 w-2 rounded-full bg-transparent" />
                          )}
                        </div>

                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-semibold text-[#392820] dark:text-[#f4ece6]">
                            {notification.title ||
                              "Notification"}
                          </p>

                          <p className="mt-1 break-words text-xs leading-5 text-[#806b60] dark:text-[#c7b4a8]">
                            {notification.message ||
                              notification.body ||
                              notification.description ||
                              ""}
                          </p>

                          <p className="mt-1.5 text-[10px] text-[#a18b7e]">
                            {formatNotificationDate(
                              notification.createdAt ||
                                notification.timestamp
                            )}
                          </p>
                        </div>
                      </button>

                      <div className="flex flex-shrink-0 flex-col gap-1 opacity-70 transition group-hover:opacity-100">
                        {!isRead && (
                          <button
                            onClick={() =>
                              handleMarkAsRead(
                                notification
                              )
                            }
                            title="Mark as read"
                            className="rounded-lg p-1.5 text-[#806b60] hover:bg-white dark:hover:bg-[#211815]"
                          >
                            <Check size={14} />
                          </button>
                        )}

                        <button
                          onClick={() =>
                            handleDeleteNotification(
                              notification
                            )
                          }
                          title="Delete notification"
                          className="rounded-lg p-1.5 text-[#9c887c] hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-500/10 dark:hover:text-rose-300"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  );
                })}
            </div>

            {/* FOOTER */}

            {!notificationsLoading &&
              notifications.length > 0 && (
                <div className="flex items-center justify-between border-t border-[#eee5de] px-4 py-2.5 dark:border-white/10">
                  <button
                    onClick={() =>
                      fetchNotifications(true)
                    }
                    className="text-[10px] font-medium text-[#80503d] hover:underline dark:text-[#d8b5a1]"
                  >
                    Refresh
                  </button>

                  <span className="text-[10px] text-[#a18b7e]">
                    Showing latest {notifications.length}
                  </span>
                </div>
              )}
          </div>
        )}
      </div>

      {/* THEME TOGGLE */}

      <button
        className="rounded-xl p-2.5 text-[#806b60] transition hover:bg-[#f4ebe4] dark:text-[#c7b4a8] dark:hover:bg-[#2a1e19]"
        aria-label={
          isDark
            ? "Switch to light mode"
            : "Switch to dark mode"
        }
        onClick={toggleTheme}
      >
        {isDark ? (
          <Sun size={18} />
        ) : (
          <Moon size={18} />
        )}
      </button>

      {/* WORKSPACE BUTTON */}

      <button className="hidden items-center gap-2 rounded-xl border border-black/10 bg-white/55 px-3 py-2 text-xs font-medium text-[#806b60] transition hover:bg-[#f4ebe4] dark:border-white/10 dark:bg-white/[.045] dark:text-[#c7b4a8] sm:flex">
        <CalendarDays size={15} />
        <span>Workspace</span>
      </button>

      {/* PROFILE MENU */}

      <div
        className="relative"
        ref={menuRef}
      >
        <button
          onClick={() =>
            setMenuOpen((open) => !open)
          }
          className="flex items-center gap-2 rounded-xl p-1.5 transition hover:bg-[#f4ebe4] dark:hover:bg-[#2a1e19]"
          aria-haspopup="menu"
          aria-expanded={menuOpen}
        >
          <div className="grid h-8 w-8 place-items-center rounded-full bg-[#d9b8a5] text-xs font-bold text-[#563528]">
            {(user?.name || "U")[0].toUpperCase()}
          </div>

          <ChevronDown
            size={14}
            className="hidden text-[#947d70] sm:block"
          />
        </button>

        {menuOpen && (
          <div
            role="menu"
            className="absolute right-0 mt-2 w-60 rounded-2xl border border-black/10 bg-[#fffdfa] p-2 shadow-soft dark:border-white/10 dark:bg-[#211815]"
          >
            <div className="px-3 py-2">
              <p className="truncate text-sm font-semibold text-[#2d211c] dark:text-[#f4ece6]">
                {user?.name}
              </p>

              <p className="truncate text-xs text-[#967f72]">
                {user?.email}
              </p>
            </div>

            <div className="my-1 border-t border-[#eee5de] dark:border-white/10" />

            <Link
              role="menuitem"
              to="/settings"
              onClick={() => setMenuOpen(false)}
              className="flex items-center gap-2 rounded-xl px-3 py-2.5 text-xs font-medium text-[#705b50] hover:bg-[#f7f0ea] dark:text-[#d0bdb1] dark:hover:bg-[#30221c]"
            >
              <UserRound size={15} />
              Profile
            </Link>

            <Link
              role="menuitem"
              to="/settings"
              onClick={() => setMenuOpen(false)}
              className="flex items-center gap-2 rounded-xl px-3 py-2.5 text-xs font-medium text-[#705b50] hover:bg-[#f7f0ea] dark:text-[#d0bdb1] dark:hover:bg-[#30221c]"
            >
              <SettingsIcon size={15} />
              Settings
            </Link>

            {user?.role === "Admin" && (
              <Link
                role="menuitem"
                to="/admin/users"
                onClick={() => setMenuOpen(false)}
                className="flex items-center gap-2 rounded-xl px-3 py-2.5 text-xs font-medium text-[#705b50] hover:bg-[#f7f0ea] dark:text-[#d0bdb1] dark:hover:bg-[#30221c]"
              >
                <ShieldCheck size={15} />
                User administration
              </Link>
            )}

            <button
              role="menuitem"
              onClick={logout}
              className="flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-xs font-medium text-rose-700 hover:bg-rose-50 dark:text-rose-300 dark:hover:bg-rose-500/10"
            >
              <LogOut size={15} />
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}