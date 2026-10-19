import { forwardRef, useId } from 'react';

// Accessible labelled input with inline error text.
const Input = forwardRef(function Input({ label, error, hint, className = '', ...props }, ref) {
  const id = useId();
  return (
    <div className={className}>
      {label && <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-navy-800 dark:text-slate-200">{label}</label>}
      <input
        id={id}
        ref={ref}
        className={`input ${error ? 'border-red-500 focus:border-red-500 focus:ring-red-500/20' : ''}`}
        aria-invalid={!!error}
        aria-describedby={error ? `${id}-err` : hint ? `${id}-hint` : undefined}
        {...props}
      />
      {error && <p id={`${id}-err`} className="mt-1 text-xs text-red-600">{error}</p>}
      {!error && hint && <p id={`${id}-hint`} className="mt-1 text-xs text-navy-500">{hint}</p>}
    </div>
  );
});

export default Input;
