export default function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
      {Icon && <div className="mb-3 rounded-full bg-indigo-50 p-3 text-accent dark:bg-indigo-500/10"><Icon size={22} /></div>}
      <h3 className="text-sm font-semibold">{title}</h3>
      {description && <p className="mt-1 max-w-sm text-sm text-navy-500">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
