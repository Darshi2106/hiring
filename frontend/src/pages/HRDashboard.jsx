import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { HRNav } from "@/components/Nav";
import { api } from "@/lib/api";
import { Briefcase, Users, FileCheck, AlertTriangle, ArrowRight, Clock, Trophy } from "lucide-react";

function Stat({ label, value, icon: Icon, testId, tone = "default" }) {
  const toneClasses = {
    default: "border-zinc-200",
    danger: "border-red-200 bg-red-50",
    success: "border-green-200 bg-green-50",
  };
  return (
    <div className={`border p-6 ${toneClasses[tone]}`} data-testid={testId}>
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-widest text-zinc-500">{label}</span>
        <Icon className="w-4 h-4 text-zinc-400" />
      </div>
      <div className="mt-4 font-display font-extrabold text-4xl">{value}</div>
    </div>
  );
}

function fmtHours(h) {
  if (h == null) return "—";
  if (h < 1) return `${Math.round(h * 60)}m`;
  if (h < 48) return `${Math.round(h)}h`;
  return `${(h / 24).toFixed(1)}d`;
}

export default function HRDashboard() {
  const [stats, setStats] = useState(null);
  const [apps, setApps] = useState([]);
  const [tth, setTth] = useState(null);

  useEffect(() => {
    api.get("/hr/stats").then((r) => setStats(r.data));
    api.get("/hr/applications").then((r) => setApps(r.data.slice(0, 6)));
    api.get("/hr/stats/time-to-hire").then((r) => setTth(r.data)).catch(() => {});
  }, []);

  return (
    <div className="min-h-screen bg-white">
      <HRNav />
      <div className="max-w-7xl mx-auto px-6 py-10">
        <div className="flex items-end justify-between mb-8">
          <div>
            <div className="text-xs uppercase tracking-widest text-zinc-500 mb-1">Overview</div>
            <h1 className="font-display font-extrabold text-4xl tracking-tighter">Hiring dashboard</h1>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Stat label="Open jobs" value={stats?.open_jobs ?? "—"} icon={Briefcase} testId="stat-open-jobs" />
          <Stat label="Applications" value={stats?.total_applications ?? "—"} icon={Users} testId="stat-applications" />
          <Stat label="Submissions" value={stats?.submissions ?? "—"} icon={FileCheck} testId="stat-submissions" />
          <Stat
            label="Shortlisted"
            value={stats?.interview_scheduled ?? "—"}
            icon={Trophy}
            testId="stat-shortlisted"
            tone={stats?.interview_scheduled > 0 ? "success" : "default"}
          />
          <Stat
            label="High AI risk"
            value={stats?.high_ai_risk ?? "—"}
            icon={AlertTriangle}
            testId="stat-high-risk"
            tone={stats?.high_ai_risk > 0 ? "danger" : "default"}
          />
        </div>

        {/* Time-to-hire */}
        <div className="mt-8 border border-zinc-200 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Clock className="w-4 h-4 text-brand" />
            <h2 className="font-display font-extrabold text-xl">Time-to-hire (median)</h2>
            <span className="text-xs font-mono text-zinc-500 ml-2">
              n = {tth?.overall?.count ?? 0} applications
            </span>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <TthTile label="Applied → invited" value={fmtHours(tth?.overall?.applied_to_invited_hrs)} />
            <TthTile label="Invited → submitted" value={fmtHours(tth?.overall?.invited_to_submitted_hrs)} />
            <TthTile label="Applied → shortlisted" value={fmtHours(tth?.overall?.applied_to_shortlist_hrs)} />
          </div>

          {tth?.by_source && Object.keys(tth.by_source).length > 0 && (
            <div className="mt-6">
              <div className="text-xs uppercase tracking-widest text-zinc-500 mb-2">By source</div>
              <table className="w-full text-sm">
                <thead className="text-xs text-zinc-500">
                  <tr className="border-b border-zinc-100">
                    <th className="text-left py-2 font-medium">Source</th>
                    <th className="text-right py-2 font-medium">Apps</th>
                    <th className="text-right py-2 font-medium">→ invited</th>
                    <th className="text-right py-2 font-medium">→ submitted</th>
                    <th className="text-right py-2 font-medium">→ shortlisted</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(tth.by_source).map(([src, s]) => (
                    <tr key={src} className="border-b border-zinc-50" data-testid={`tth-source-${src}`}>
                      <td className="py-2 font-mono text-xs">{src}</td>
                      <td className="py-2 text-right font-mono text-xs">{s.count}</td>
                      <td className="py-2 text-right font-mono text-xs">{fmtHours(s.applied_to_invited_hrs)}</td>
                      <td className="py-2 text-right font-mono text-xs">{fmtHours(s.invited_to_submitted_hrs)}</td>
                      <td className="py-2 text-right font-mono text-xs">{fmtHours(s.applied_to_shortlist_hrs)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="mt-8 grid md:grid-cols-2 gap-6">
          <div className="border border-zinc-200 p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="font-display font-extrabold text-xl">Recent applications</h2>
              <Link to="/hr/applications" className="text-sm text-brand hover:underline flex items-center gap-1" data-testid="dashboard-view-all-apps">
                View all <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
            {apps.length === 0 ? (
              <div className="text-sm text-zinc-500 py-8 text-center">No applications yet.</div>
            ) : (
              <div className="divide-y divide-zinc-200">
                {apps.map((a) => (
                  <div key={a.id} className="py-3 flex justify-between items-center">
                    <div>
                      <div className="font-medium text-sm">{a.name}</div>
                      <div className="text-xs text-zinc-500">{a.job_title}</div>
                    </div>
                    <span className="text-xs font-mono uppercase text-zinc-500 border border-zinc-200 px-2 py-0.5">
                      {a.status.replace(/_/g, " ")}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="border border-zinc-200 p-6">
            <h2 className="font-display font-extrabold text-xl mb-4">Quick actions</h2>
            <div className="space-y-2">
              <Link to="/hr/jobs/new" className="block border border-zinc-200 p-3 hover:border-brand transition-colors" data-testid="dashboard-action-new-job">
                <div className="font-medium text-sm">+ Post a new role</div>
                <div className="text-xs text-zinc-500 mt-0.5">Create a job opening with a default proctored assignment.</div>
              </Link>
              <Link to="/hr/applications" className="block border border-zinc-200 p-3 hover:border-brand transition-colors" data-testid="dashboard-action-review">
                <div className="font-medium text-sm">Review applications</div>
                <div className="text-xs text-zinc-500 mt-0.5">Send assignment invites and review submissions.</div>
              </Link>
              <Link to="/hr/jobs" className="block border border-zinc-200 p-3 hover:border-brand transition-colors" data-testid="dashboard-action-jobs">
                <div className="font-medium text-sm">Manage jobs</div>
                <div className="text-xs text-zinc-500 mt-0.5">Edit descriptions, close roles, tune assessments.</div>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function TthTile({ label, value }) {
  return (
    <div className="border-l-2 border-brand pl-3">
      <div className="text-xs uppercase tracking-widest text-zinc-500">{label}</div>
      <div className="mt-1 font-display font-extrabold text-2xl font-mono">{value}</div>
    </div>
  );
}
