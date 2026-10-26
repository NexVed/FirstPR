import { getSupabase } from './supabase';
import type { ActivityItem, AnalysisDetail, AnalysisListItem, Dashboard, PlanDetail, PlanListItem, TriageResult, UserProfile } from './types';

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const supabase = getSupabase();
  if (!supabase) throw new ApiError('Set the Supabase URL and publishable key in frontend/.env.local.', 0);
  const { data: { session }, error } = await supabase.auth.getSession();
  if (error || !session?.access_token) throw new ApiError('Sign in to continue.', 401);
  const headers = new Headers(init.headers);
  headers.set('Authorization', `Bearer ${session.access_token}`);
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  let response: Response;
  try {
    const signal = init.signal ?? (init.method === 'POST' ? AbortSignal.timeout(90000) : undefined);
    response = await fetch(`/api/v1${path}`, { ...init, headers, signal, cache: 'no-store' });
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === 'TimeoutError') throw new ApiError('Analysis took too long. Please try again.', 0);
    throw new ApiError('Could not reach the API. Check that the backend is running.', 0);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const message = body?.error?.message || body?.detail || `Request failed (${response.status}).`;
    throw new ApiError(typeof message === 'string' ? message : 'Request failed.', response.status);
  }
  return response.json() as Promise<T>;
}

export const firstpr = {
  dashboard: () => api<Dashboard>('/dashboard/'),
  profile: () => api<UserProfile>('/users/me'),
  analyses: async () => (await api<{ analyses: AnalysisListItem[] }>('/repositories/')).analyses,
  analysis: (id: string) => api<AnalysisDetail>(`/repositories/${encodeURIComponent(id)}`),
  analyze: (repositoryUrl: string) => api<AnalysisDetail>('/repositories/analyze', { method: 'POST', body: JSON.stringify({ repository_url: repositoryUrl }) }),
  plans: async () => (await api<{ plans: PlanListItem[] }>('/plans/')).plans,
  plan: (id: string) => api<PlanDetail>(`/plans/${encodeURIComponent(id)}`),
  createPlan: (repositoryUrl: string, issueNumber: number) => api<PlanDetail>('/plans/', { method: 'POST', body: JSON.stringify({ repository_url: repositoryUrl, issue_number: issueNumber }) }),
  activity: async () => (await api<{ activity: ActivityItem[] }>('/activity/')).activity,
  triage: (repositoryUrl: string, image: File, note: string) => {
    const body = new FormData();
    body.set('repository_url', repositoryUrl);
    body.set('image', image);
    if (note.trim()) body.set('note', note.trim());
    return api<TriageResult>('/triage/', { method: 'POST', body });
  },
  health: async () => {
    const response = await fetch('/api/v1/health', { cache: 'no-store' });
    if (!response.ok) throw new ApiError('Backend is unavailable.', response.status);
    return response.json() as Promise<{ status: string; ai_provider: string; database: string }>;
  },
};

export function repoName(url: string): string {
  try { return new URL(url).pathname.replace(/^\/+|\/+$/g, ''); } catch { return url; }
}
export function readableDate(date: string | null): string {
  if (!date) return 'Recently';
  const value = new Date(date);
  return Number.isNaN(value.getTime()) ? 'Recently' : value.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}
export function validGithubRepo(url: string): boolean {
  try {
    const parsed = new URL(url.trim());
    const segments = parsed.pathname.split('/').filter(Boolean);
    const name = segments[1]?.replace(/\.git$/, '');
    return parsed.protocol === 'https:' && ['github.com', 'www.github.com'].includes(parsed.hostname)
      && !parsed.username && !parsed.password && !parsed.search && !parsed.hash
      && segments.length === 2 && [segments[0], name].every(segment => !!segment && segment.length <= 100 && /^[A-Za-z0-9_.-]+$/.test(segment) && !segment.startsWith('.') && !segment.endsWith('.'));
  } catch { return false; }
}
