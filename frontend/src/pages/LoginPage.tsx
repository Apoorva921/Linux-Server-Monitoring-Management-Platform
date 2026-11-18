import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/AuthContext';
import { extractErrorMessage } from '../utils/format';

export const LoginPage: React.FC = () => {
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const fillDefaultAdmin = () => {
    setMode('login');
    setUsername('admin');
    setPassword('Admin@SentinelOps123!');
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === 'login') {
        await login(username.trim(), password);
      } else {
        await register(username.trim(), email.trim(), password, fullName.trim() || username.trim());
      }
      navigate('/', { replace: true });
    } catch (err) {
      setError(extractErrorMessage(err, 'Authentication failed. Check your credentials.'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4"
      style={{
        background:
          'linear-gradient(135deg, #FFF1F2 0%, #FFFBEB 28%, #ECFDF5 58%, #EEF2FF 100%)',
      }}
    >
      <div className="w-full max-w-md bg-white border border-slate-200/90 rounded-2xl shadow-[0_12px_40px_rgba(15,23,42,0.08)] overflow-hidden">
        {/* Clean multicolor palette bar */}
        <div className="h-1.5 w-full bg-gradient-to-r from-rose-400 via-amber-400 via-emerald-400 to-indigo-500" />

        <div className="p-8">
          <div className="mb-6">
            <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">
              Sentinel<span className="text-indigo-600">Ops</span>
            </h1>
            <p className="text-xs text-slate-500 mt-1">
              Linux Server Monitoring &amp; Management Platform
            </p>
          </div>

          <div className="grid grid-cols-2 gap-1 p-1 bg-slate-100 rounded-xl mb-6">
            <button
              type="button"
              onClick={() => {
                setMode('login');
                setError(null);
              }}
              className={`py-2 text-xs font-semibold rounded-lg transition-all ${
                mode === 'login'
                  ? 'bg-white text-indigo-700 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setMode('register');
                setError(null);
              }}
              className={`py-2 text-xs font-semibold rounded-lg transition-all ${
                mode === 'register'
                  ? 'bg-white text-emerald-700 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Create Account
            </button>
          </div>

          {error && (
            <div
              role="alert"
              className="mb-4 px-3.5 py-2.5 rounded-xl bg-rose-50 border border-rose-200 text-xs font-medium text-rose-700"
            >
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">Username</label>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder={mode === 'login' ? 'admin' : 'choose_username'}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:bg-white focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
              />
            </div>

            {mode === 'register' && (
              <>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Email Address
                  </label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:bg-white focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Full Name
                  </label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Your Name"
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:bg-white focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100"
                  />
                </div>
              </>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Password {mode === 'register' && <span className="font-normal text-slate-400">(min. 8 characters)</span>}
              </label>
              <input
                type="password"
                required
                minLength={mode === 'register' ? 8 : 1}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:bg-white focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className={`w-full py-2.5 px-4 rounded-xl text-white font-semibold text-sm transition-colors disabled:opacity-50 ${
                mode === 'login'
                  ? 'bg-indigo-600 hover:bg-indigo-700'
                  : 'bg-emerald-600 hover:bg-emerald-700'
              }`}
            >
              {submitting
                ? 'Authenticating...'
                : mode === 'login'
                  ? 'Sign In'
                  : 'Create Viewer Account'}
            </button>
          </form>

          {mode === 'login' && (
            <div className="mt-5 p-3.5 rounded-xl bg-amber-50/80 border border-amber-200/80 flex items-center justify-between gap-3">
              <div className="text-xs text-amber-900">
                <p className="font-semibold">Default Admin Account</p>
                <p className="font-mono text-[11px] text-amber-800 mt-0.5">
                  admin / Admin@SentinelOps123!
                </p>
              </div>
              <button
                type="button"
                onClick={fillDefaultAdmin}
                className="px-3 py-1.5 rounded-lg bg-white hover:bg-amber-100 border border-amber-300 text-xs font-semibold text-amber-900 transition-colors shrink-0"
              >
                Auto-fill
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
