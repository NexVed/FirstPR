'use client';

import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowRight, ArrowUpRight, Bookmark, Camera, Check, ChevronRight, CircleAlert, Clock3, Code2, Copy, ExternalLink, FileCode2, FolderGit2, GitBranch, GitPullRequest, Lightbulb, Search, Sparkles, Star, UploadCloud } from 'lucide-react';
import { firstpr, readableDate, repoName, validGithubRepo } from '@/lib/api';
import type { ActivityItem, AnalysisDetail, Recommendation, TriageResult } from '@/lib/types';

function ErrorPanel({ error, retry }: { error: unknown; retry?: () => void }) {
  return <div className="error-card" role="alert"><CircleAlert size={20} /><div><strong>Could not load this section</strong><p>{error instanceof Error ? error.message : 'An unexpected error occurred.'}</p></div>{retry && <button className="button button-outline" onClick={retry}>Try again</button>}</div>;
}
function Loading({ label = 'Loading' }: { label?: string }) { return <div className="loading-card" aria-busy="true"><img src="/firstpr-logo.png" alt="" /><span>{label}…</span></div>; }
function Empty({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return <div className="empty-card"><img src="/firstpr-logo.png" alt="" /><h3>{title}</h3><p>{description}</p>{action}</div>;
}
function Heading({ eyebrow, title, description, action }: { eyebrow: string; title: string; description?: string; action?: ReactNode }) {
  return <div className="section-heading"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1>{description && <p>{description}</p>}</div>{action}</div>;
}
function Stat({ icon, value, label, tone }: { icon: ReactNode; value: number | string; label: string; tone: string }) {
  return <div className={`stat-card ${tone}`}><span className="stat-icon">{icon}</span><div><strong>{value}</strong><small>{label}</small></div></div>;
}
function IssueCard({ issue, repositoryUrl, onPlan, busy }: { issue: Recommendation; repositoryUrl: string; onPlan?: () => void; busy?: boolean }) {
  return <article className="issue-card"><div className="issue-meta"><span className="issue-type"><GitPullRequest size={12} /> ISSUE #{issue.issue_number}</span><span className={`difficulty difficulty-${Math.min(5, Math.max(1, issue.difficulty))}`}>Level {issue.difficulty}/5</span></div>
    <h3>{issue.title}</h3><p>{issue.first_step || issue.approach}</p><div className="tag-row">{issue.labels.slice(0, 3).map(label => <span key={label} className="tag">{label}</span>)}</div>
    <div className="card-bottom"><span>{issue.files.length} relevant {issue.files.length === 1 ? 'file' : 'files'}</span><div>{issue.url && <a href={issue.url} target="_blank" rel="noreferrer" aria-label={`Open issue ${issue.issue_number} on GitHub`}><ArrowUpRight size={17} /></a>}{onPlan && <button className="mini-action" disabled={busy} onClick={onPlan}>Create plan <ArrowRight size={14} /></button>}</div></div>
  </article>;
}

export function DashboardView() {
  const router = useRouter();
  const [url, setUrl] = useState('');
  const [error, setError] = useState('');
  const dashboard = useQuery({ queryKey: ['dashboard'], queryFn: firstpr.dashboard });
  const analyses = useQuery({ queryKey: ['analyses'], queryFn: firstpr.analyses });
  const plans = useQuery({ queryKey: ['plans'], queryFn: firstpr.plans });
  const profile = useQuery({ queryKey: ['profile'], queryFn: firstpr.profile });
  const latest = analyses.data?.[0];
  const latestDetail = useQuery({ queryKey: ['analysis', latest?.id], queryFn: () => firstpr.analysis(latest!.id), enabled: !!latest?.id });
  const submit = (event: FormEvent) => { event.preventDefault(); if (!validGithubRepo(url)) { setError('Enter a public GitHub repository URL like https://github.com/owner/repo.'); return; } router.push(`/repositories?analyze=${encodeURIComponent(url)}`); };
  if (dashboard.isLoading || analyses.isLoading || plans.isLoading) return <Loading label="Loading your dashboard" />;
  if (dashboard.error || analyses.error || plans.error) return <ErrorPanel error={dashboard.error || analyses.error || plans.error} retry={() => { dashboard.refetch(); analyses.refetch(); plans.refetch(); }} />;
  const data = dashboard.data!;
  const firstName = profile.data?.display_name?.split(' ')[0] || 'there';
  return <div className="dashboard-view">
    <div className="dashboard-intro"><div><span className="eyebrow">YOUR CONTRIBUTION SPACE</span><h1>Good morning, {firstName}!</h1><p>Your first pull request starts here. Find an issue worth solving and make a plan.</p></div>
      <div className="stats-grid"><Stat icon={<FolderGit2 size={19} />} value={data.total_analyses} label="Repositories" tone="stat-lime" /><Stat icon={<GitPullRequest size={19} />} value={data.total_plans} label="Plans created" tone="stat-purple" /><Stat icon={<Camera size={19} />} value={data.total_triages} label="Bugs triaged" tone="stat-gold" /><Stat icon={<Lightbulb size={19} />} value={latestDetail.data?.recommendations.length ?? '—'} label="Suggested issues" tone="stat-lavender" /></div>
    </div>
    <div className="dashboard-grid"><div className="dashboard-main">
      <div className="block-head"><h2>Continue exploring</h2><Link href="/repositories" className="text-link">View repositories <ArrowRight size={14} /></Link></div>
      {latest ? <Link className="feature-card" href={`/repositories/${latest.id}`}><div className="feature-graphic"><img src="/firstpr-logo.png" alt="" /><span className="feature-spark">✦</span></div><div className="feature-content"><span className="eyebrow">LATEST REPOSITORY</span><h3>{latest.owner}/{latest.name}</h3><p>Analyzed {readableDate(latest.created_at)} · Explore recommendations and conventions.</p><span className="feature-cta">Open analysis <ArrowRight size={14} /></span></div></Link>
        : <div className="feature-card"><div className="feature-graphic"><img src="/firstpr-logo.png" alt="" /></div><div className="feature-content"><span className="eyebrow">READY WHEN YOU ARE</span><h3>Analyze your first repository</h3><p>Paste a public GitHub URL to discover approachable issues.</p><Link href="/repositories" className="feature-cta">Get started <ArrowRight size={14} /></Link></div></div>}
      <div className="block-head"><h2>Recommended for you</h2><Link href={latest ? `/repositories/${latest.id}` : '/repositories'} className="text-link">See all <ArrowRight size={14} /></Link></div>
      {latestDetail.data?.recommendations.length ? <div className="issues-grid">{latestDetail.data.recommendations.slice(0, 4).map(issue => <IssueCard key={issue.issue_number} issue={issue} repositoryUrl={latest!.repository_url} />)}</div>
        : latestDetail.isLoading ? <Loading label="Finding issues" /> : <Empty title="Recommendations will appear here" description="Analyze a repository to see real issues ranked by difficulty." action={<Link className="button button-dark" href="/repositories">Explore repositories <ArrowRight size={15} /></Link>} />}
    </div><aside className="dashboard-side">
      <div className="block-head"><h2>Quick start</h2></div><div className="quick-card"><span className="quick-icon"><Sparkles size={20} /></span><h3>Find a first issue.</h3><p>Paste a public GitHub repository and let FirstPR surface a clear starting point.</p><form onSubmit={submit}><label htmlFor="quick-url" className="sr-only">GitHub repository URL</label><input id="quick-url" type="url" value={url} onChange={e => { setUrl(e.target.value); setError(''); }} placeholder="github.com/owner/repo" />{error && <small role="alert" className="field-error">{error}</small>}<button className="button button-dark" type="submit">Analyze repository <ArrowRight size={15} /></button></form></div>
      <div className="activity-card"><div className="block-head"><h2>Recent activity</h2><Link href="/history" className="text-link">All <ArrowRight size={13} /></Link></div>{data.recent_activity.length ? <ul>{data.recent_activity.slice(0, 4).map((item, index) => <li key={item.id || index}><span className="activity-dot"><Clock3 size={13} /></span><div><strong>{activityLabel(item)}</strong><small>{readableDate(item.created_at)}</small></div></li>)}</ul> : <p className="muted">Your activity will show here after your first analysis.</p>}</div>
      <Link href="/triage" className="triage-promo"><Camera size={22} /><span><strong>Found a visual bug?</strong><small>Turn a screenshot into an issue draft.</small></span><ArrowUpRight size={18} /></Link>
    </aside></div>
  </div>;
}

export function RepositoriesView() {
  const query = useQuery({ queryKey: ['analyses'], queryFn: firstpr.analyses });
  const qc = useQueryClient(); const router = useRouter();
  const [url, setUrl] = useState(''); const [validation, setValidation] = useState(''); const [search, setSearch] = useState('');
  useEffect(() => { const value = new URLSearchParams(window.location.search).get('analyze'); if (value) setUrl(value); }, []);
  const mutation = useMutation({ mutationFn: firstpr.analyze, onSuccess: result => { void Promise.all([qc.invalidateQueries({ queryKey: ['analyses'] }), qc.invalidateQueries({ queryKey: ['dashboard'] })]); if (result.id) router.push(`/repositories/${result.id}`); else { sessionStorage.setItem('firstpr-analysis-preview', JSON.stringify(result)); router.push('/repositories/preview'); } } });
  const submit = (event: FormEvent) => { event.preventDefault(); if (!validGithubRepo(url)) { setValidation('Use a public GitHub URL in the form https://github.com/owner/repo.'); return; } setValidation(''); mutation.mutate(url.trim()); };
  const list = query.data?.filter(item => `${item.owner}/${item.name}`.toLowerCase().includes(search.toLowerCase())) || [];
  return <div className="page-stack"><Heading eyebrow="REPOSITORY INTELLIGENCE" title="Find your next contribution." description="Analyze a public GitHub repository to see real issues, relevant files, and project conventions." />
    <section className="analyze-panel"><div><span className="eyebrow">START HERE</span><h2>Paste a repository URL</h2><p>FirstPR reads the codebase and finds issues you can tackle.</p></div><form onSubmit={submit}><label htmlFor="repo-url" className="sr-only">Public GitHub repository URL</label><div className="input-action"><input id="repo-url" type="url" value={url} onChange={e => { setUrl(e.target.value); setValidation(''); }} placeholder="https://github.com/owner/repo" /><button className="button button-dark" disabled={mutation.isPending} type="submit">{mutation.isPending ? 'Analyzing…' : 'Analyze'} <ArrowRight size={15} /></button></div>{validation && <small role="alert" className="field-error">{validation}</small>}{mutation.error && <small role="alert" className="field-error">{mutation.error.message}</small>}</form></section>
    <div className="list-heading"><div><h2>Analyzed repositories</h2><p>{query.data?.length || 0} in your workspace</p></div><div className="search-box"><Search size={16} /><input aria-label="Search repositories" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search repositories" /></div></div>
    {query.isLoading ? <Loading label="Loading repositories" /> : query.error ? <ErrorPanel error={query.error} retry={() => query.refetch()} /> : list.length ? <div className="repository-grid">{list.map(item => <Link key={item.id} className="repository-card" href={`/repositories/${item.id}`}><span className="repo-mark"><FolderGit2 size={22} /></span><span className="repo-card-body"><strong>{item.owner}/{item.name}</strong><small>Analyzed {readableDate(item.created_at)}</small></span><ArrowUpRight size={18} /></Link>)}</div> : <Empty title={search ? 'No repositories match your search' : 'No repositories analyzed yet'} description={search ? 'Try a different repository name.' : 'Paste a public GitHub URL above to start.'} />}
  </div>;
}

export function RepositoryView({ id }: { id: string }) {
  const query = useQuery({ queryKey: ['analysis', id], queryFn: () => { if (id === 'preview') { const saved = sessionStorage.getItem('firstpr-analysis-preview'); if (saved) return Promise.resolve(JSON.parse(saved) as AnalysisDetail); throw new Error('This preview has expired. Analyze the repository again.'); } return firstpr.analysis(id); } });
  const qc = useQueryClient(); const router = useRouter();
  const mutation = useMutation({ mutationFn: (issue: number) => firstpr.createPlan(query.data!.repository.html_url, issue), onSuccess: async result => { await Promise.all([qc.invalidateQueries({ queryKey: ['plans'] }), qc.invalidateQueries({ queryKey: ['dashboard'] })]); if (result.id) router.push(`/plans/${result.id}`); } });
  if (query.isLoading) return <Loading label="Opening repository analysis" />;
  if (query.error || !query.data) return <ErrorPanel error={query.error || new Error('Analysis not found.')} retry={() => query.refetch()} />;
  const data = query.data; const repo = data.repository;
  return <div className="page-stack"><Link href="/repositories" className="back-link">← All repositories</Link><Heading eyebrow="REPOSITORY ANALYSIS" title={repo.full_name} description={repo.description || 'Public GitHub repository'} action={<a className="button button-outline" href={repo.html_url} target="_blank" rel="noreferrer">View on GitHub <ExternalLink size={15} /></a>} />
    <div className="repo-summary"><span><Code2 size={17} />{repo.language || 'Language unavailable'}</span><span><Star size={17} />{repo.stargazers_count.toLocaleString()} stars</span><span><GitBranch size={17} />{repo.default_branch || 'Default branch'}</span><span><Sparkles size={17} />{data.recommendations.length} suggested issues</span></div>
    {data.conventions.analysis_warning && <div className="analysis-warning" role="status">{data.conventions.analysis_warning.startsWith('AI suggestions are unavailable until GEMINI_API_KEY') ? 'AI suggestions were unavailable during this scan. Analyze the repository again to retry.' : data.conventions.analysis_warning}</div>}
    <div className="block-head"><h2>Issues to explore</h2><span className="muted">Ranked by approachability</span></div>
    {mutation.error && <ErrorPanel error={mutation.error} />}
    {data.recommendations.length ? <div className="issues-grid">{data.recommendations.map(issue => <IssueCard key={issue.issue_number} issue={issue} repositoryUrl={repo.html_url} onPlan={() => mutation.mutate(issue.issue_number)} busy={mutation.isPending} />)}</div> : <Empty title={data.conventions.analysis_warning ? 'Suggestions unavailable' : 'No suitable issues found'} description={data.conventions.analysis_warning ? 'GitHub repository details were saved. Run the analysis again when the AI provider is available.' : 'Try another repository or run the analysis again later.'} />}
    <div className="details-grid"><section className="detail-panel"><h2>Project setup</h2><p>Commands found in the repository documentation. Review scripts before running them.</p>{data.conventions.setup_commands.length ? data.conventions.setup_commands.map(command => <CodeLine key={command} value={command} />) : <span className="muted">No setup commands found.</span>}{data.conventions.test_command && <><h3>Tests</h3><CodeLine value={data.conventions.test_command} /></>}{data.conventions.lint_command && <><h3>Lint</h3><CodeLine value={data.conventions.lint_command} /></>}</section><section className="detail-panel"><h2>Contribution rules</h2>{data.conventions.pr_rules.length ? <ul className="clean-list">{data.conventions.pr_rules.map(rule => <li key={rule}><Check size={16} />{rule}</li>)}</ul> : <p>No contribution rules were found in the documentation.</p>}</section></div>
  </div>;
}

function CodeLine({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  return <div className="code-line"><code>$ {value}</code><button aria-label={`Copy ${value}`} onClick={async () => { await navigator.clipboard.writeText(value); setCopied(true); setTimeout(() => setCopied(false), 1500); }}>{copied ? <Check size={15} /> : <Copy size={15} />}</button></div>;
}

export function PlansView() {
  const query = useQuery({ queryKey: ['plans'], queryFn: firstpr.plans });
  const [search, setSearch] = useState('');
  const list = useMemo(() => (query.data || []).filter(item => `${item.issue_title} ${item.repository_url}`.toLowerCase().includes(search.toLowerCase())), [query.data, search]);
  return <div className="page-stack"><Heading eyebrow="YOUR ROADMAPS" title="Contribution plans." description="Your generated plans with concrete steps, files to inspect, and PR checklists." action={<Link className="button button-dark" href="/repositories">Find an issue <ArrowRight size={15} /></Link>} />
    <div className="list-heading"><div><h2>All plans</h2><p>{query.data?.length || 0} generated</p></div><div className="search-box"><Search size={16} /><input aria-label="Search plans" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search plans" /></div></div>
    {query.isLoading ? <Loading label="Loading plans" /> : query.error ? <ErrorPanel error={query.error} retry={() => query.refetch()} /> : list.length ? <div className="plans-list">{list.map(item => <Link key={item.id} href={`/plans/${item.id}`} className="plan-row"><span className="plan-icon"><GitPullRequest size={19} /></span><span><small>{repoName(item.repository_url)} · #{item.issue_number}</small><strong>{item.issue_title}</strong></span><span className="plan-date">{readableDate(item.created_at)}</span><ChevronRight size={19} /></Link>)}</div> : <Empty title={search ? 'No plans match your search' : 'No plans yet'} description={search ? 'Try another issue title or repository name.' : 'Analyze a repository and generate a plan from one of its issues.'} action={!search && <Link className="button button-dark" href="/repositories">Explore repositories <ArrowRight size={15} /></Link>} />}
  </div>;
}

export function PlanView({ id }: { id: string }) {
  const query = useQuery({ queryKey: ['plan', id], queryFn: () => firstpr.plan(id) });
  const [copied, setCopied] = useState(false);
  if (query.isLoading) return <Loading label="Opening contribution plan" />;
  if (query.error || !query.data) return <ErrorPanel error={query.error || new Error('Plan not found.')} retry={() => query.refetch()} />;
  const { repository, issue, plan } = query.data;
  const draft = `## Summary\n${plan.overview}\n\n## Implementation\n${plan.implementation_steps.map(step => `- ${step}`).join('\n')}\n\n## Testing\n${plan.testing_strategy}\n\nCloses #${issue.number}`;
  return <div className="page-stack"><Link href="/plans" className="back-link">← All plans</Link><Heading eyebrow={`${repoName(repository.html_url)} · ISSUE #${issue.number}`} title={issue.title} description={plan.overview} action={<a className="button button-outline" href={`${repository.html_url}/issues/${issue.number}`} target="_blank" rel="noreferrer">Open issue <ExternalLink size={15} /></a>} />
    <div className="repo-summary"><span><GitPullRequest size={17} />Difficulty {plan.estimated_difficulty}/5</span><span><FileCode2 size={17} />{plan.files_to_touch.length} relevant files</span><span><Clock3 size={17} />Created {readableDate(query.data.created_at)}</span></div>
    <div className="details-grid plan-details"><section className="detail-panel"><h2>Implementation steps</h2><ol className="step-list">{plan.implementation_steps.map((step, index) => <li key={index}><span>{String(index + 1).padStart(2, '0')}</span><p>{step}</p></li>)}</ol>{plan.setup_steps.length > 0 && <><h3>Setup</h3>{plan.setup_steps.map(step => <CodeLine key={step} value={step} />)}</>}</section><div className="detail-column"><section className="detail-panel"><h2>Files to inspect</h2>{plan.files_to_touch.length ? <ul className="file-list">{plan.files_to_touch.map(file => <li key={file}><Code2 size={16} /><code>{file}</code></li>)}</ul> : <p>No specific files were identified.</p>}</section><section className="detail-panel"><h2>Testing strategy</h2><p>{plan.testing_strategy || 'No testing steps were specified.'}</p></section><section className="detail-panel"><h2>PR checklist</h2><ul className="clean-list">{plan.pr_checklist.map(item => <li key={item}><Check size={16} />{item}</li>)}</ul></section></div></div>
    <section className="draft-panel"><div><span className="eyebrow">READY TO DRAFT</span><h2>Pull request outline</h2><p>Copy this outline, then edit it to reflect what you actually changed and tested.</p></div><button className="button button-dark" onClick={async () => { await navigator.clipboard.writeText(draft); setCopied(true); setTimeout(() => setCopied(false), 1800); }}>{copied ? <Check size={15} /> : <Copy size={15} />}{copied ? 'Copied' : 'Copy outline'}</button></section>
  </div>;
}

export function TriageView() {
  const [url, setUrl] = useState(''); const [note, setNote] = useState(''); const [image, setImage] = useState<File | null>(null); const [validation, setValidation] = useState(''); const [result, setResult] = useState<TriageResult | null>(null); const [copied, setCopied] = useState(false);
  const qc = useQueryClient();
  const mutation = useMutation({ mutationFn: () => firstpr.triage(url.trim(), image!, note), onSuccess: async value => { setResult(value); await Promise.all([qc.invalidateQueries({ queryKey: ['dashboard'] }), qc.invalidateQueries({ queryKey: ['activity'] })]); } });
  const submit = (event: FormEvent) => { event.preventDefault(); if (!validGithubRepo(url)) { setValidation('Enter a public GitHub repository URL.'); return; } if (!image) { setValidation('Choose a PNG, JPEG, or WebP screenshot.'); return; } if (image.size > 4 * 1024 * 1024) { setValidation('Image must be 4 MB or smaller.'); return; } setValidation(''); mutation.mutate(); };
  return <div className="page-stack"><Heading eyebrow="VISUAL BUG TRIAGE" title="Turn a screenshot into a clear issue." description="Upload a real bug screenshot. FirstPR extracts visible errors, suggests files, and drafts an issue report." />
    <div className="triage-layout"><form className="detail-panel triage-form" onSubmit={submit}><label htmlFor="triage-url">GitHub repository URL</label><input id="triage-url" type="url" value={url} onChange={e => setUrl(e.target.value)} placeholder="https://github.com/owner/repo" required />
      <label htmlFor="triage-image">Bug screenshot</label><label className="upload-area" htmlFor="triage-image"><UploadCloud size={28} /><strong>{image ? image.name : 'Choose a screenshot'}</strong><small>PNG, JPEG, or WebP · Up to 4 MB</small></label><input id="triage-image" className="sr-only" type="file" accept="image/png,image/jpeg,image/webp" onChange={e => setImage(e.target.files?.[0] || null)} />
      <label htmlFor="triage-note">What happened? <span className="muted">Optional</span></label><textarea id="triage-note" rows={5} value={note} onChange={e => setNote(e.target.value)} placeholder="Add steps to reproduce or useful context..." />
      {validation && <small role="alert" className="field-error">{validation}</small>}{mutation.error && <small role="alert" className="field-error">{mutation.error.message}</small>}
      <button className="button button-dark" type="submit" disabled={mutation.isPending}>{mutation.isPending ? 'Analyzing screenshot…' : 'Analyze screenshot'} <ArrowRight size={15} /></button></form>
      <div className="triage-explainer"><img src="/firstpr-logo.png" alt="FirstPR" /><span className="eyebrow">WHAT YOU GET</span><h2>A better bug report, faster.</h2><ul><li><Check size={16} />Visible error text and clues</li><li><Check size={16} />Likely code locations</li><li><Check size={16} />Related GitHub issues</li><li><Check size={16} />An issue draft you can edit</li></ul></div></div>
    {result && <div className="result-stack"><div className="block-head"><h2>Analysis result</h2><span className="eyebrow">{result.repository.full_name || repoName(url)}</span></div><div className="details-grid"><section className="detail-panel"><h2>What the screenshot shows</h2><p>{result.analysis.summary}</p>{result.analysis.visible_errors.length > 0 && <><h3>Visible errors</h3>{result.analysis.visible_errors.map((item, index) => <div className="error-note" key={index}><strong>{item.error_type || 'Error'}</strong><p>{item.message}</p>{item.location_hint && <small>{item.location_hint}</small>}</div>)}</>}{result.analysis.candidate_files.length > 0 && <><h3>Candidate files</h3><ul className="file-list">{result.analysis.candidate_files.map(file => <li key={file}><Code2 size={15} /><code>{file}</code></li>)}</ul></>}</section><section className="detail-panel"><div className="block-head"><h2>Draft issue</h2><button className="mini-action" onClick={async () => { await navigator.clipboard.writeText(`# ${result.draft.title}\n\n${result.draft.body}`); setCopied(true); setTimeout(() => setCopied(false), 1800); }}>{copied ? <Check size={14} /> : <Copy size={14} />}{copied ? 'Copied' : 'Copy draft'}</button></div><h3>{result.draft.title}</h3><pre className="draft-body">{result.draft.body}</pre>{result.related_issues.length > 0 && <><h3>Related issues</h3>{result.related_issues.map(item => <a className="related-issue" key={item.number} href={item.url} target="_blank" rel="noreferrer">#{item.number} {item.title}<ArrowUpRight size={14} /></a>)}</>}</section></div></div>}
  </div>;
}

function activityLabel(item: ActivityItem) {
  const repository = typeof item.summary.repository === 'string' ? item.summary.repository : 'repository';
  switch (item.activity_type) { case 'repository_analyzed': return `Analyzed ${repository}`; case 'plan_created': return `Created a plan for ${repository}`; case 'triage_created': return `Triaged a bug in ${repository}`; default: return item.activity_type.replaceAll('_', ' '); }
}

export function HistoryView() {
  const query = useQuery({ queryKey: ['activity'], queryFn: firstpr.activity });
  return <div className="page-stack"><Heading eyebrow="YOUR ACTIVITY" title="What you've been working on." description="A timeline of your repository analyses, contribution plans, and screenshot triage." />
    {query.isLoading ? <Loading label="Loading activity" /> : query.error ? <ErrorPanel error={query.error} retry={() => query.refetch()} /> : query.data?.length ? <div className="timeline">{query.data.map((item, index) => <div className="timeline-item" key={item.id || index}><span className="timeline-icon">{item.activity_type === 'repository_analyzed' ? <FolderGit2 size={17} /> : item.activity_type === 'plan_created' ? <GitPullRequest size={17} /> : <Camera size={17} />}</span><div><strong>{activityLabel(item)}</strong><small>{readableDate(item.created_at)}</small></div></div>)}</div> : <Empty title="Your timeline starts here" description="Analyze a repository or triage a screenshot to create your first activity entry." action={<Link className="button button-dark" href="/repositories">Analyze a repository <ArrowRight size={15} /></Link>} />}
  </div>;
}

export function SettingsView() {
  const profile = useQuery({ queryKey: ['profile'], queryFn: firstpr.profile });
  const health = useQuery({ queryKey: ['health'], queryFn: firstpr.health, retry: false });
  return <div className="page-stack"><Heading eyebrow="YOUR ACCOUNT" title="Settings & connection." description="Your profile and the current backend connection." />
    <div className="settings-grid"><section className="detail-panel"><h2>Profile</h2>{profile.isLoading ? <Loading label="Loading profile" /> : profile.error ? <ErrorPanel error={profile.error} retry={() => profile.refetch()} /> : <div className="profile-detail"><span className="avatar avatar-large">{profile.data?.display_name?.charAt(0).toUpperCase() || '?'}</span><div><strong>{profile.data?.display_name}</strong><small>{profile.data?.email || 'No email available'}</small><code>{profile.data?.user_id}</code></div></div>}</section><section className="detail-panel"><h2>Backend connection</h2>{health.isLoading ? <p>Checking backend…</p> : health.error ? <ErrorPanel error={health.error} retry={() => health.refetch()} /> : <div className="health-list"><div><span>API</span><strong className="status-good">Connected</strong></div><div><span>Database</span><strong>{health.data?.database}</strong></div><div><span>AI provider</span><strong>{health.data?.ai_provider === 'none' ? 'Not configured' : health.data?.ai_provider}</strong></div></div>}</section></div>
    <div className="setup-note"><Bookmark size={18} /><div><strong>Need to configure the project?</strong><p>See the root README for Supabase, GitHub, AI provider, and Bun setup. The model is configured on the backend for the whole deployment.</p></div></div>
  </div>;
}
