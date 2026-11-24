
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Eye,
  EyeOff,
  Sparkles,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import Button from '../components/common/Button';
import Input from '../components/common/Input';

const PASSWORD_RULES = [
  {
    id: 'len',
    label: 'At least 8 characters',
    test: (p) => p.length >= 8,
  },
  {
    id: 'upper',
    label: 'One uppercase letter',
    test: (p) => /[A-Z]/.test(p),
  },
  {
    id: 'lower',
    label: 'One lowercase letter',
    test: (p) => /[a-z]/.test(p),
  },
  {
    id: 'num',
    label: 'One number',
    test: (p) => /[0-9]/.test(p),
  },
];

const DESIGNATIONS = [
  'Product Manager',
  'Associate Product Manager',
  'Senior Product Manager',
  'Product Lead',
  'Head of Product',
];

const EMPTY = {
  name: '',
  username: '',
  email: '',
  designation: '',
  password: '',
  confirmPassword: '',
};

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPw, setShowPw] = useState(false);

  const onChange = (e) => {
    const { name, value } = e.target;

    setForm((f) => ({ ...f, [name]: value }));
    setErrors((er) => ({ ...er, [name]: undefined }));
    setServerError('');
  };

  const onSubmit = async (e) => {
    e.preventDefault();

    setLoading(true);
    setServerError('');

    try {
      const res = await register(form);

      if (res.success) {
        setSuccess(res.message);

        setTimeout(() => {
          navigate('/login', {
            replace: true,
            state: {
              registeredEmail: form.email.trim().toLowerCase(),
            },
          });
        }, 1200);
      } else {
        if (res.data?.errors) {
          setErrors(res.data.errors);
        }

        setServerError(res.message);
      }
    } catch (error) {
      setServerError(
        error.message || 'Unable to create your account. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="mb-6 flex items-center gap-2">
          <div className="grid h-9 w-9 place-items-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-500 text-white">
            <Sparkles size={18} />
          </div>
          <span className="font-semibold">Stratov</span>
        </div>

        <div className="card p-6 sm:p-8">
          <h1 className="text-xl font-semibold">Create your account</h1>

          <p className="mt-1 text-sm text-navy-500">
            Select your professional designation. An administrator manages
            your system access and permissions.
          </p>

          {serverError && (
            <div
              role="alert"
              className="mt-5 flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-300"
            >
              <AlertCircle size={16} className="mt-0.5 shrink-0" />
              {serverError}
            </div>
          )}

          {success && (
            <div
              role="status"
              className="mt-5 flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300"
            >
              <CheckCircle2 size={16} className="mt-0.5 shrink-0" />
              {success} Redirecting to sign in…
            </div>
          )}

          <form onSubmit={onSubmit} noValidate className="mt-6 space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Full name"
                name="name"
                value={form.name}
                onChange={onChange}
                error={errors.name}
                autoComplete="name"
              />

              <Input
                label="Username"
                name="username"
                value={form.username}
                onChange={onChange}
                error={errors.username}
                hint="3–20 letters, numbers, underscores"
                autoComplete="username"
              />
            </div>

            <Input
              label="Work email"
              name="email"
              type="email"
              value={form.email}
              onChange={onChange}
              error={errors.email}
              autoComplete="email"
            />

            {/* Professional designation dropdown */}
            <div>
              <label
                htmlFor="designation"
                className="mb-1.5 block text-sm font-medium text-navy-700 dark:text-navy-200"
              >
                Professional designation
              </label>

              <select
                id="designation"
                name="designation"
                value={form.designation}
                onChange={onChange}
                required
                className="w-full rounded-lg border border-navy-200 bg-white px-3 py-2.5 text-sm text-navy-800 outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/20 dark:border-navy-700 dark:bg-navy-900 dark:text-white"
              >
                <option value="" disabled>
                  Select your designation
                </option>

                {DESIGNATIONS.map((designation) => (
                  <option key={designation} value={designation}>
                    {designation}
                  </option>
                ))}
              </select>

              {errors.designation && (
                <p className="mt-1 text-xs text-rose-500">
                  {errors.designation}
                </p>
              )}
            </div>

            <div className="relative">
              <Input
                label="Password"
                name="password"
                type={showPw ? 'text' : 'password'}
                value={form.password}
                onChange={onChange}
                error={errors.password}
                autoComplete="new-password"
              />

              <button
                type="button"
                onClick={() => setShowPw((s) => !s)}
                className="absolute right-3 top-[38px] text-navy-500 hover:text-navy-800"
                aria-label={showPw ? 'Hide password' : 'Show password'}
              >
                {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>

              <ul className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
                {PASSWORD_RULES.map((r) => {
                  const pass = r.test(form.password);

                  return (
                    <li
                      key={r.id}
                      className={
                        pass ? 'text-emerald-600' : 'text-navy-500'
                      }
                    >
                      {pass ? '✓' : '○'} {r.label}
                    </li>
                  );
                })}
              </ul>
            </div>

            <Input
              label="Confirm password"
              name="confirmPassword"
              type={showPw ? 'text' : 'password'}
              value={form.confirmPassword}
              onChange={onChange}
              error={errors.confirmPassword}
              autoComplete="new-password"
            />

            <Button
              type="submit"
              loading={loading}
              className="w-full"
            >
              {loading ? 'Creating account…' : 'Create account'}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-navy-500">
            Already registered?{' '}
            <Link
              to="/login"
              className="font-medium text-accent hover:text-accent-600"
            >
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
