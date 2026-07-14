import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { HRNav } from "@/components/Nav";
import { api } from "@/lib/api";
import { Briefcase, Users, FileCheck, AlertTriangle, ArrowRight } from "lucide-react";

function Stat({ label, value, icon: Icon, testId, tone = "default" }) {
  const toneClasses = {
    default: "border-zinc-200",
    danger: "border-red-200 bg-red-50",
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

export default function HRDashboard() {
  const [stats, setStats] = useState(null);
  const [apps, setApps] = useState([]);

  useEffect(() => {
    api.get("/hr/stats").then((r) => setStats(r.data));
    api.get("/hr/applications").then((r) => setApps(r.data.slice(0, 6)));
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

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Stat label="Open jobs" value={stats?.open_jobs ?? "—"} icon={Briefcase} testId="stat-open-jobs" />
          <Stat label="Applications" value={stats?.total_applications ?? "—"} icon={Users} testId="stat-applications" />
          <Stat label="Submissions" value={stats?.submissions ?? "—"} icon={FileCheck} testId="stat-submissions" />
          <Stat
            label="High AI risk"
            value={stats?.high_ai_risk ?? "—"}
            icon={AlertTriangle}
            testId="stat-high-risk"
            tone={stats?.high_ai_risk > 0 ? "danger" : "default"}
          />
        </div>

        <div className="mt-12 grid md:grid-cols-2 gap-6">
          <div className="border border-zinc-200 p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="font-display font-extrabold text-xl">Recent applications</h2>
              <Link to="/hr/applications" className="text-sm text-[#0f9394] hover:underline flex items-center gap-1" data-testid="dashboard-view-all-apps">
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
                      {a.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="border border-zinc-200 p-6">
            <h2 className="font-display font-extrabold text-xl mb-4">Quick actions</h2>
            <div className="space-y-2">
              <Link to="/hr/jobs/new" className="block border border-zinc-200 p-3 hover:border-[#0f9394] transition-colors" data-testid="dashboard-action-new-job">
                <div className="font-medium text-sm">+ Post a new role</div>
                <div className="text-xs text-zinc-500 mt-0.5">Create a job opening with a default proctored assignment.</div>
              </Link>
              <Link to="/hr/applications" className="block border border-zinc-200 p-3 hover:border-[#0f9394] transition-colors" data-testid="dashboard-action-review">
                <div className="font-medium text-sm">Review applications</div>
                <div className="text-xs text-zinc-500 mt-0.5">Send assignment invites and review submissions.</div>
              </Link>
              <Link to="/hr/jobs" className="block border border-zinc-200 p-3 hover:border-[#0f9394] transition-colors" data-testid="dashboard-action-jobs">
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
