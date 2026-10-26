export type RepositorySummary = {
  owner: string; name: string; full_name: string; description: string | null;
  default_branch: string; stargazers_count: number; language: string | null; html_url: string;
};
export type Conventions = { setup_commands: string[]; test_command: string | null; lint_command: string | null; pr_rules: string[]; analysis_warning?: string | null };
export type Recommendation = {
  issue_number: number; title: string; url: string; labels: string[]; difficulty: number;
  files: string[]; approach: string; first_step: string; screenshots_analyzed: boolean;
};
export type AnalysisListItem = { id: string; repository_url: string; owner: string; name: string; created_at: string | null };
export type AnalysisDetail = { id: string | null; repository: RepositorySummary; conventions: Conventions; recommendations: Recommendation[]; created_at: string | null };
export type PlanListItem = { id: string; repository_url: string; issue_number: number; issue_title: string; created_at: string | null };
export type ContributionPlanDraft = { overview: string; setup_steps: string[]; implementation_steps: string[]; files_to_touch: string[]; testing_strategy: string; pr_checklist: string[]; estimated_difficulty: number };
export type PlanDetail = { id: string | null; repository: { owner: string; name: string; html_url: string; full_name?: string }; issue: { number: number; title: string }; plan: ContributionPlanDraft; created_at: string | null };
export type ActivityItem = { id: string | null; activity_type: string; summary: Record<string, unknown>; entity_id: string | null; created_at: string | null };
export type Dashboard = { total_analyses: number; total_plans: number; total_triages: number; recent_activity: ActivityItem[] };
export type UserProfile = { user_id: string; email: string | null; display_name: string };
export type TriageResult = {
  id: string | null;
  repository: { full_name?: string; html_url?: string; default_branch?: string };
  analysis: { summary: string; visible_errors: { error_type: string; message: string; location_hint: string | null }[]; candidate_files: string[]; search_terms: string[] };
  related_issues: { number: number; title: string; url: string; score: number }[];
  draft: { title: string; body: string };
  created_at: string | null;
};
