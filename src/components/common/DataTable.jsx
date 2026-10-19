// Generic table with header sorting and consistent styling. Pagination handled by caller.
import { ChevronDown, ChevronUp, ChevronsUpDown } from 'lucide-react';

export default function DataTable({ columns, rows, sortKey, sortDir, onSort, rowKey, emptyNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-navy-700">
        <thead className="bg-slate-50 dark:bg-navy-900/40">
          <tr>
            {columns.map((c) => (
              <th key={c.key} scope="col" className={`whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-navy-500 ${c.className || ''}`}>
                {c.sortable ? (
                  <button onClick={() => onSort(c.key)} className="inline-flex items-center gap-1 hover:text-navy-800 dark:hover:text-slate-200">
                    {c.label}
                    {sortKey === c.key ? (sortDir === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />) : <ChevronsUpDown size={14} className="opacity-40" />}
                  </button>
                ) : c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white dark:divide-navy-700 dark:bg-navy-800">
          {rows.length === 0 && (
            <tr><td colSpan={columns.length}>{emptyNode}</td></tr>
          )}
          {rows.map((row) => (
            <tr key={rowKey(row)} className="transition hover:bg-slate-50 dark:hover:bg-navy-700/50">
              {columns.map((c) => (
                <td key={c.key} className={`px-4 py-3 align-middle ${c.cellClassName || ''}`}>
                  {c.render ? c.render(row) : row[c.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
