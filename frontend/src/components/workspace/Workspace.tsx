'use client';

import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import type { Session } from '@supabase/supabase-js';
import { usePathname, useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowRight, Camera, ChartNoAxesCombined, ChevronDown, CircleHelp, Clock3, FolderGit2, GitPullRequest, LogOut, Menu, Settings2, Sparkles, X } from 'lucide-react';
import { getSupabase } from '@/lib/supabase';
import { firstpr } from '@/lib/api';
import { DashboardView, HistoryView, PlansView, RepositoryView, RepositoriesView, SettingsView, TriageView, PlanView } from './views';

const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false } } });
const nav = [
  { href: '/dashboard', label: 'Dashboard', icon: ChartNoAxesCombined },
  { href: '/repositories', label: 'Repositories', icon: FolderGit2 },
  { href: '/plans', label: 'Plans', icon: GitPullRequest },
  { href: '/triage', label: 'Bug triage', icon: Camera },
  { href: '/history', label: 'History', icon: Clock3 },
];

function Brand({ compact = false }: { compact?: boolean }) {
  return <Link href="/dashboard" className={`brand ${compact ? 'brand-compact' : ''}`} aria-label="FirstPR home">
    {/* The supplied artwork is the source for every branded image. */}
    <img src="/firstpr-logo.png" alt="FirstPR logo" className="brand-art" />
    <span>First<span className="brand-accent">PR</span></span>
  </Link>;
}

function SetupScreen() {
  return <div className="auth-backdrop"><div className="auth-card"><Brand /><span className="eyebrow">Setup required</span>
    <h1>Connect your Supabase project</h1><p>Add <code>NEXT_PUBLIC_SUPABASE_URL</code> and <code>NEXT_PUBLIC_SUPABASE_ANON_KEY</code> to <code>frontend/.env.local</code>, then restart the frontend.</p>
    <p className="muted">The full setup steps are in the project README.</p></div></div>;
}

function AuthScreen() {
  const [mode, setMode] = useState<'sign-in' | 'sign-up'>('sign-in');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setMessage('');
    const auth = getSupabase()!.auth;
    const result = mode === 'sign-in'
      ? await auth.signInWithPassword({ email, password })
      : await auth.signUp({ email, password });
    setBusy(false);
    if (result.error) setMessage(result.error.message);
    else if (mode === 'sign-up' && !result.data.session) setMessage('Check your email to confirm your account, then sign in.');
  };
  return <div className="auth-backdrop"><div className="auth-card"><Brand />
    <span className="eyebrow">Your contribution workspace</span>
    <h1>{mode === 'sign-in' ? 'Welcome back.' : 'Start your first PR.'}</h1>
    <p>Discover open source issues, understand the codebase, and build a clear contribution plan.</p>
    <form onSubmit={submit} className="auth-form">
      <label>Email address<input type="email" autoComplete="email" required value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" /></label>
      <label>Password<input type="password" autoComplete={mode === 'sign-in' ? 'current-password' : 'new-password'} minLength={6} required value={password} onChange={e => setPassword(e.target.value)} placeholder="At least 6 characters" /></label>
      {message && <p role="status" className="form-message">{message}</p>}
      <button className="button button-dark" disabled={busy}>{busy ? 'Please wait…' : mode === 'sign-in' ? 'Sign in' : 'Create account'} <ArrowRight size={16} /></button>
    </form>
    <button className="text-link auth-switch" onClick={() => { setMode(mode === 'sign-in' ? 'sign-up' : 'sign-in'); setMessage(''); }}>
      {mode === 'sign-in' ? 'New here? Create an account' : 'Already have an account? Sign in'}
    </button>
  </div></div>;
}

function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname() || '/';
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { data: profile } = useQuery({ queryKey: ['profile'], queryFn: firstpr.profile });
  const title = pathname.startsWith('/repositories') ? 'Repositories' : pathname.startsWith('/plans') ? 'Contribution plans' : pathname.startsWith('/triage') ? 'Bug triage' : pathname.startsWith('/history') ? 'Activity' : pathname.startsWith('/settings') ? 'Settings' : 'Dashboard';
  return <div className="app-shell">
    <header className="topbar">
      <Brand compact />
      <nav className="topnav" aria-label="Primary navigation">{nav.map(item => <Link key={item.href} href={item.href} className={`topnav-link ${pathname === item.href || pathname.startsWith(item.href + '/') ? 'active' : ''}`}><item.icon size={15} /><span>{item.label}</span></Link>)}</nav>
      <div className="top-actions"><Link href="/settings" className="profile-chip" aria-label="Open settings"><span className="avatar">{profile?.display_name?.charAt(0).toUpperCase() || '?'}</span><span className="profile-label"><strong>{profile?.display_name || 'My account'}</strong><small>{profile?.email || 'Account settings'}</small></span><ChevronDown size={13} /></Link>
        <button className="mobile-menu-button" onClick={() => setMobileOpen(!mobileOpen)} aria-label="Toggle navigation" aria-expanded={mobileOpen}>{mobileOpen ? <X size={19} /> : <Menu size={19} />}</button>
      </div>
    </header>
    {mobileOpen && <nav className="mobile-nav" aria-label="Mobile navigation">{nav.map(item => <Link key={item.href} href={item.href} onClick={() => setMobileOpen(false)}><item.icon size={17} />{item.label}</Link>)}<Link href="/settings" onClick={() => setMobileOpen(false)}><Settings2 size={17} />Settings</Link></nav>}
    <div className="main-frame"><div className="page-topline"><span className="breadcrumbs">WORKSPACE <span>/</span> {title.toUpperCase()}</span><Link href="/settings" className="help-link"><CircleHelp size={14} /> Account & setup</Link></div><main>{children}</main></div>
    <footer className="site-footer"><Brand compact /><span>Your first pull request starts here.</span><button onClick={async () => { await getSupabase()?.auth.signOut(); queryClient.clear(); router.push('/dashboard'); }}><LogOut size={14} /> Sign out</button></footer>
  </div>;
}

function RouteView() {
  const pathname = usePathname() || '/';
  const parts = pathname.split('/').filter(Boolean);
  if (!parts.length || parts[0] === 'dashboard') return <DashboardView />;
  if (parts[0] === 'repositories' && parts[1]) return <RepositoryView id={parts[1]} />;
  if (parts[0] === 'repositories') return <RepositoriesView />;
  if (parts[0] === 'plans' && parts[1]) return <PlanView id={parts[1]} />;
  if (parts[0] === 'plans') return <PlansView />;
  if (parts[0] === 'triage') return <TriageView />;
  if (parts[0] === 'history') return <HistoryView />;
  if (parts[0] === 'settings') return <SettingsView />;
  return <div className="empty-card"><Brand compact /><h1>Page not found</h1><Link className="button button-dark" href="/dashboard">Back to dashboard <ArrowRight size={16} /></Link></div>;
}

function AuthGate() {
  const [ready, setReady] = useState(false);
  const [session, setSession] = useState<Session | null>(null);
  useEffect(() => {
    const supabase = getSupabase();
    if (!supabase) { setReady(true); return; }
    supabase.auth.getSession().then(({ data }) => { setSession(data.session); setReady(true); });
    const { data: listener } = supabase.auth.onAuthStateChange((_event, next) => { setSession(next); queryClient.clear(); });
    return () => listener.subscription.unsubscribe();
  }, []);
  if (!getSupabase()) return <SetupScreen />;
  if (!ready) return <div className="auth-backdrop"><div className="loading-brand"><img src="/firstpr-logo.png" alt="FirstPR" /><span>Opening your workspace…</span></div></div>;
  if (!session) return <AuthScreen />;
  return <AppShell><RouteView /></AppShell>;
}

export function Workspace() { return <QueryClientProvider client={queryClient}><AuthGate /></QueryClientProvider>; }
