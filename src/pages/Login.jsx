import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Eye, EyeOff, Sparkles, Mail, Lock, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import Button from '../components/common/Button';
import Input from '../components/common/Input';

const validate = (email, password) => {
  const e = {};
  if (!email.trim()) e.email = 'Email is required.';
  else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) e.email = 'Enter a valid email address.';
  if (!password) e.password = 'Password is required.';
  return e;
};

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from || '/dashboard';

  const [form, setForm] = useState({ email: '', password: '', remember: true });
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState('');
  const [loading, setLoading] = useState(false);

  const onChange = (e) => {
    const { name, type, checked, value } = e.target;
    setForm((f) => ({ ...f, [name]: type === 'checkbox' ? checked : value }));
    setErrors((er) => ({ ...er, [name]: undefined }));
    setServerError('');
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    const v = validate(form.email, form.password);
    setErrors(v);
    if (Object.keys(v).length) return;
    setLoading(true);
    const res = await login(form.email, form.password, form.remember);
    setLoading(false);
    if (res.success) navigate(from, { replace: true });
    else setServerError(res.message);
  };

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="hidden flex-col justify-between bg-navy-900 p-12 text-white lg:flex">
        <div className="flex items-center gap-2">
          <div className="grid h-9 w-9 place-items-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-500"><Sparkles size={18} /></div>
          <span className="font-semibold">AI Product Manager Copilot</span>
        </div>
        <div className="max-w-md">
          <h2 className="text-3xl font-semibold leading-tight">Turn customer feedback into the next release.</h2>
          <p className="mt-4 text-navy-300">Analyze themes, prioritize with RICE, draft PRDs, and plan your roadmap. Each product manager gets a private workspace.</p>
        </div>
        <p className="text-xs text-navy-300">Demo authentication. Data is stored locally in your browser.</p>
      </div>

      <div className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-sm">
          <h1 className="text-2xl font-semibold">Welcome back</h1>
          <p className="mt-1 text-sm text-navy-500">Sign in to your workspace.</p>

          {serverError && (
            <div role="alert" className="mt-5 flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-300">
              <AlertCircle size={16} className="mt-0.5 shrink-0" />{serverError}
            </div>
          )}

          <form onSubmit={onSubmit} noValidate className="mt-6 space-y-4">
            <div className="relative">
              <Input label="Email" name="email" type="email" autoComplete="email" value={form.email} onChange={onChange} error={errors.email} placeholder="you@company.com" />
              <Mail size={16} className="pointer-events-none absolute right-3 top-[38px] text-navy-500" />
            </div>

            <div className="relative">
              <Input label="Password" name="password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" value={form.password} onChange={onChange} error={errors.password} placeholder="••••••••" />
              <button
                type="button"
                onClick={() => setShowPassword((s) => !s)}
                className="absolute right-3 top-[38px] text-navy-500 hover:text-navy-800"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>

            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-sm text-navy-600 dark:text-slate-300">
                <input type="checkbox" name="remember" checked={form.remember} onChange={onChange} className="h-4 w-4 rounded border-slate-300 text-accent focus:ring-accent" />
                Remember me
              </label>
            </div>

            <Button type="submit" loading={loading} className="w-full">
              {loading ? 'Signing in…' : 'Sign in'}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-navy-500">
            New product manager?{' '}
            <Link to="/register" className="font-medium text-accent hover:text-accent-600">Create an account</Link>
          </p>

          <div className="mt-8 rounded-lg border border-dashed border-slate-300 p-3 text-xs text-navy-500 dark:border-navy-700">
            <p className="font-medium text-navy-700 dark:text-slate-300">Demo account</p>
            <p>admin@copilot.com / Admin123!</p>
          </div>
        </div>
      </div>
    </div>
  );
}
