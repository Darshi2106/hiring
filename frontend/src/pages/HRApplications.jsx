import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { HRNav } from "@/components/Nav";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Copy, Send, ExternalLink, FileText, Calendar, ChevronLeft, ChevronRight } from "lucide-react";

const PAGE_SIZE = 25;

export default function HRApplications() {
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(null);
  const [page, setPage] = useState(1);

  const load = async () => {
    const r = await api.get("/hr/applications");
    setApps(r.data);
    setLoading(false);
  };

  useEffect(() => {
    load();
  }, []);

  const sendInvite = async (appId) => {
    setSending(appId);
    try {
      const r = await api.post("/hr/invite", { application_id: appId });
      const url = `${window.location.origin}/exam/${r.data.token}`;
      await navigator.clipboard.writeText(url).catch(() => {});
      const emailInfo = r.data.email || {};
      if (emailInfo.delivered) {
        toast.success("Invite emailed to candidate", { description: "Link also copied to clipboard." });
      } else if (emailInfo.mocked) {
        toast.warning("Invite created (email in MOCK mode)", {
          description: "Set RESEND_API_KEY in backend/.env to enable delivery. Link copied to clipboard.",
        });
      } else {
        toast.warning("Invite created, email delivery failed", {
          description: (emailInfo.error || "").slice(0, 120) + " — link copied to clipboard.",
        });
      }
      load();
    } catch (e) {
      toast.error("Failed to send invite");
    } finally {
      setSending(null);
    }
  };

  const copyInvite = async (token) => {
    const url = `${window.location.origin}/exam/${token}`;
    await navigator.clipboard.writeText(url).catch(() => {});
    toast.success("Invite link copied");
  };

  const openResume = async (resumeUrl) => {
    if (!resumeUrl) return;
    if (!resumeUrl.startsWith("/api/resumes/")) {
      window.open(resumeUrl, "_blank");
      return;
    }
    try {
      const res = await api.get(resumeUrl.replace("/api", ""), { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      window.open(url, "_blank");
    } catch (e) {
      toast.error("Could not open resume");
    }
  };

  const scheduleInterview = async (appId) => {
    try {
      const r = await api.post("/hr/schedule-interview", { application_id: appId });
      toast.success("Candidate can now schedule via Calendly", {
        description: r.data.calendly_url,
      });
      load();
    } catch (e) {
      const msg = e.response?.data?.detail || "Failed";
      toast.error(msg);
    }
  };

  const riskColor = (score) => {
    if (score == null) return "text-zinc-400";
    if (score >= 70) return "text-red-600";
    if (score >= 40) return "text-amber-600";
    return "text-green-600";
  };

  const totalPages = Math.max(1, Math.ceil(apps.length / PAGE_SIZE));
  const visibleApps = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return apps.slice(start, start + PAGE_SIZE);
  }, [apps, page]);

  useEffect(() => {
    if (page > totalPages) setPage(1);
  }, [totalPages, page]);

  return (
    <div className="min-h-screen bg-white">
      <HRNav />
      <div className="max-w-7xl mx-auto px-6 py-10">
        <div className="mb-8">
          <div className="text-xs uppercase tracking-widest text-zinc-500 mb-1">Pipeline</div>
          <h1 className="font-display font-extrabold text-4xl tracking-tighter">Applications</h1>
          {!loading && apps.length > 0 && (
            <div className="mt-2 text-xs text-zinc-500 font-mono" data-testid="apps-total-count">
              {apps.length} total · page {page} of {totalPages}
            </div>
          )}
        </div>

        {loading ? (
          <div className="text-sm text-zinc-500">Loading...</div>
        ) : apps.length === 0 ? (
          <div className="border border-dashed border-zinc-300 p-16 text-center text-zinc-500">
            No applications yet. Share your careers page to start collecting.
          </div>
        ) : (
          <div className="border border-zinc-200 overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-zinc-50 border-b border-zinc-200">
                <tr>
                  <th className="text-left px-4 py-3 font-medium">Candidate</th>
                  <th className="text-left px-4 py-3 font-medium">Role</th>
                  <th className="text-left px-4 py-3 font-medium">Trust</th>
                  <th className="text-left px-4 py-3 font-medium">Status</th>
                  <th className="text-left px-4 py-3 font-medium">MCQ</th>
                  <th className="text-left px-4 py-3 font-medium">AI risk</th>
                  <th className="text-left px-4 py-3 font-medium">Violations</th>
                  <th className="text-right px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {visibleApps.map((a) => (
                  <tr key={a.id} className="border-b border-zinc-100" data-testid={`app-row-${a.id}`}>
                    <td className="px-4 py-3">
                      <div className="font-medium">{a.name}</div>
                      <div className="text-xs text-zinc-500 font-mono">{a.email}</div>
                      {a.resume_url && (
                        <button
                          type="button"
                          onClick={() => openResume(a.resume_url)}
                          className="mt-1 text-xs text-brand hover:underline inline-flex items-center gap-1"
                          data-testid={`view-resume-${a.id}`}
                        >
                          <FileText className="w-3 h-3" /> Resume
                        </button>
                      )}
                    </td>
                    <td className="px-4 py-3 text-zinc-700">{a.job_title}</td>
                    <td className="px-4 py-3">
                      {a.trust_score != null ? (
                        <span
                          className={`font-mono text-sm font-bold px-2 py-1 border ${
                            a.trust_score >= 75
                              ? "border-green-400 text-green-700 bg-green-50"
                              : a.trust_score >= 50
                              ? "border-amber-400 text-amber-700 bg-amber-50"
                              : "border-red-400 text-red-700 bg-red-50"
                          }`}
                          title="Composite of MCQ %, coding pass rate, AI safety, and proctoring"
                          data-testid={`trust-${a.id}`}
                        >
                          {a.trust_score}
                        </span>
                      ) : (
                        <span className="text-zinc-300 font-mono">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs font-mono uppercase border border-zinc-300 px-2 py-0.5">
                        {a.status.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono">
                      {a.mcq_pct_weighted != null ? `${a.mcq_pct_weighted}%` : (a.mcq_score != null ? `${a.mcq_score}` : <span className="text-zinc-300">—</span>)}
                    </td>
                    <td className={`px-4 py-3 font-mono ${riskColor(a.ai_risk_avg)}`}>
                      {a.ai_risk_avg != null ? `${a.ai_risk_avg}%` : <span className="text-zinc-300">—</span>}
                    </td>
                    <td className="px-4 py-3 font-mono">
                      {a.violation_count > 0 ? (
                        <span className="text-red-600">{a.violation_count}</span>
                      ) : (
                        <span className="text-zinc-300">0</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      {a.submission_id ? (
                        <>
                          <Link to={`/hr/submissions/${a.submission_id}`}>
                            <Button size="sm" variant="outline" className="rounded-none mr-1" data-testid={`view-sub-${a.id}`}>
                              <ExternalLink className="w-3.5 h-3.5 mr-1" /> Review
                            </Button>
                          </Link>
                          {(a.status === "assignment_submitted" || a.status === "interview_scheduled") && (
                            <Button
                              size="sm"
                              className="bg-accent-yellow text-brand-dark hover:opacity-90 rounded-none font-medium"
                              onClick={() => scheduleInterview(a.id)}
                              data-testid={`schedule-${a.id}`}
                            >
                              <Calendar className="w-3.5 h-3.5 mr-1" />
                              {a.status === "interview_scheduled" ? "Resend link" : "Schedule interview"}
                            </Button>
                          )}
                        </>
                      ) : a.invite_sent ? (
                        <Button size="sm" variant="outline" className="rounded-none" onClick={() => copyInvite(a.invite_token)} data-testid={`copy-invite-${a.id}`}>
                          <Copy className="w-3.5 h-3.5 mr-1" /> Copy link
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          className="bg-brand hover:opacity-90 rounded-none"
                          disabled={sending === a.id}
                          onClick={() => sendInvite(a.id)}
                          data-testid={`send-invite-${a.id}`}
                        >
                          <Send className="w-3.5 h-3.5 mr-1" /> {sending === a.id ? "Sending..." : "Send assignment"}
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!loading && totalPages > 1 && (
          <div className="mt-6 flex items-center justify-between border-t border-zinc-200 pt-4">
            <div className="text-xs text-zinc-500 font-mono">
              Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, apps.length)} of {apps.length}
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="rounded-none"
                disabled={page === 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                data-testid="apps-page-prev"
              >
                <ChevronLeft className="w-4 h-4 mr-1" /> Prev
              </Button>
              <span className="text-sm font-mono" data-testid="apps-page-indicator">
                {page} / {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                className="rounded-none"
                disabled={page === totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                data-testid="apps-page-next"
              >
                Next <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
