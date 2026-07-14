import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { PublicNav } from "@/components/Nav";
import { useCandidateAuth, candidateApi } from "@/context/CandidateAuthContext";
import { Button } from "@/components/ui/button";
import { ClipboardList, FileCheck2, Clock, ArrowRight } from "lucide-react";

const STATUS_LABEL = {
  applied: "Under review",
  assignment_sent: "Assessment invited",
  assignment_submitted: "Under HR review",
  assignment_rejected_ai: "Not proceeding",
  interview_scheduled: "Schedule your interview",
};

export default function CandidateDashboard() {
  const { user, loading } = useCandidateAuth();
  const nav = useNavigate();
  const [apps, setApps] = useState([]);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      nav("/candidate/login");
      return;
    }
    candidateApi
      .get("/candidate/applications")
      .then((r) => setApps(r.data))
      .finally(() => setFetching(false));
  }, [user, loading, nav]);

  if (loading || !user) return null;

  return (
    <div className="min-h-screen bg-white">
      <PublicNav />
      <div className="max-w-5xl mx-auto px-6 py-10">
        <div className="mb-8">
          <div className="text-xs uppercase tracking-widest text-zinc-500">Welcome back</div>
          <h1 className="font-display font-extrabold text-4xl tracking-tighter">
            Hi, {user.name?.split(" ")[0] || "there"}.
          </h1>
          <p className="mt-2 text-sm text-zinc-500">
            Track your applications and take pending assessments below.
          </p>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-8">
          <StatBlock label="Applications" value={apps.length} icon={ClipboardList} />
          <StatBlock
            label="Pending assessments"
            value={apps.filter((a) => a.invite_token && a.invite_status !== "submitted").length}
            icon={Clock}
          />
          <StatBlock
            label="Submitted"
            value={apps.filter((a) => a.has_submitted).length}
            icon={FileCheck2}
          />
        </div>

        <h2 className="font-display font-extrabold text-2xl mb-4">Your applications</h2>

        {fetching ? (
          <div className="text-sm text-zinc-500">Loading...</div>
        ) : apps.length === 0 ? (
          <div className="border border-dashed border-zinc-300 p-12 text-center">
            <p className="text-zinc-500">You haven't applied to any roles yet.</p>
            <Link to="/careers">
              <Button className="mt-4 bg-brand rounded-none" data-testid="cd-browse-jobs">
                Browse open roles
              </Button>
            </Link>
          </div>
        ) : (
          <div className="border border-zinc-200">
            {apps.map((a) => {
              const canTakeExam =
                a.invite_token && a.invite_status !== "submitted" && !a.has_submitted;
              return (
                <div
                  key={a.id}
                  className="p-5 border-b border-zinc-100 last:border-0 flex flex-col md:flex-row md:items-center gap-3"
                  data-testid={`cd-app-${a.id}`}
                >
                  <div className="flex-1">
                    <div className="font-medium text-lg">{a.job_title}</div>
                    <div className="text-xs text-zinc-500 font-mono mt-1">
                      Applied {new Date(a.created_at).toLocaleDateString()} ·{" "}
                      <span className="uppercase">
                        {STATUS_LABEL[a.status] || a.status.replace(/_/g, " ")}
                      </span>
                    </div>
                  </div>
                  <div>
                    {canTakeExam ? (
                      <Link to={`/exam/${a.invite_token}`}>
                        <Button className="bg-accent-yellow hover:opacity-90 text-brand-dark rounded-none font-medium" data-testid={`cd-take-exam-${a.id}`}>
                          Take assessment <ArrowRight className="w-4 h-4 ml-1" />
                        </Button>
                      </Link>
                    ) : a.status === "interview_scheduled" && a.calendly_url ? (
                      <a href={a.calendly_url} target="_blank" rel="noreferrer">
                        <Button className="bg-accent-yellow hover:opacity-90 text-brand-dark rounded-none font-medium" data-testid={`cd-schedule-${a.id}`}>
                          Schedule interview <ArrowRight className="w-4 h-4 ml-1" />
                        </Button>
                      </a>
                    ) : a.status === "assignment_rejected_ai" ? (
                      <span className="text-xs uppercase font-mono border border-red-300 text-red-700 bg-red-50 px-2 py-1">
                        Not proceeding
                      </span>
                    ) : a.has_submitted ? (
                      <span className="text-xs uppercase font-mono border border-green-300 text-green-700 bg-green-50 px-2 py-1">
                        Under HR review
                      </span>
                    ) : (
                      <span className="text-xs uppercase font-mono border border-zinc-300 text-zinc-500 px-2 py-1">
                        Awaiting HR review
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function StatBlock({ label, value, icon: Icon }) {
  return (
    <div className="border border-zinc-200 p-5">
      <div className="flex justify-between items-center">
        <span className="text-xs uppercase tracking-widest text-zinc-500">{label}</span>
        <Icon className="w-4 h-4 text-zinc-400" />
      </div>
      <div className="mt-3 font-display font-extrabold text-3xl">{value}</div>
    </div>
  );
}
