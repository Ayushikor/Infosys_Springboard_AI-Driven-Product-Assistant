const VARIANTS = {
  primary: 'btn-primary',
  ghost: 'btn-ghost',
  danger: 'inline-flex items-center justify-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-700 disabled:opacity-60',
  outline: 'inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-navy-800 transition hover:bg-slate-50 dark:bg-navy-800 dark:border-navy-700 dark:text-slate-100 dark:hover:bg-navy-700 disabled:opacity-60',
};

export default function Button({ variant = 'primary', loading = false, className = '', children, ...props }) {
  return (
    <button className={`${VARIANTS[variant]} ${className}`} disabled={loading || props.disabled} {...props}>
      {loading && <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" aria-hidden />}
      {children}
    </button>
  );
}
