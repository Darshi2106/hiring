import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { HRNav } from "@/components/Nav";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Copy, Send, ExternalLink, FileText } from "lucide-react";

export default function HRApplications() {
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(null);

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
      // external link
      window.open(resumeUrl, "_blank");
      return;
    }
    try {
      const res = await api.get(resumeUrl.replace("/api", ""), { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      window.open(url, "_blank");
      // note: URL not revoked to allow viewing; browser will GC on tab close
    } catch (e) {
      toast.error("Could not open resume");
    }
  };

  const riskColor = (score) => {
    if (score == null) return "text-zinc-400";
    if (score >= 70) return "text-red-600";
    if (score >= 40) return "text-amber-600";
    return "text-green-600";
  };

  return (
    <div className="min-h-screen bg-white">
      <HRNav />
      <div className="max-w-7xl mx-auto px-6 py-10">
        <div className="mb-8">
          <div className="text-xs uppercase tracking-widest text-zinc-500 mb-1">Pipeline</div>
          <h1 className="font-display font-extrabold text-4xl tracking-tighter">Applications</h1>
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
                  <th className="text-left px-4 py-3 font-medium">Status</th>
                  <th className="text-left px-4 py-3 font-medium">MCQ</th>
                  <th className="text-left px-4 py-3 font-medium">AI risk</th>
                  <th className="text-left px-4 py-3 font-medium">Violations</th>
                  <th className="text-right px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {apps.map((a) => (
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
                      <span className="text-xs font-mono uppercase border border-zinc-300 px-2 py-0.5">
                        {a.status.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono">
                      {a.mcq_score != null ? `${a.mcq_score}` : <span className="text-zinc-300">—</span>}
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
                        <Link to={`/hr/submissions/${a.submission_id}`}>
                          <Button size="sm" variant="outline" className="rounded-none" data-testid={`view-sub-${a.id}`}>
                            <ExternalLink className="w-3.5 h-3.5 mr-1" /> Review
                          </Button>
                        </Link>
                      ) : a.invite_sent ? (
                        <Button size="sm" variant="outline" className="rounded-none" onClick={() => copyInvite(a.invite_token)} data-testid={`copy-invite-${a.id}`}>
                          <Copy className="w-3.5 h-3.5 mr-1" /> Copy link
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          className="bg-[#0f9394] hover:bg-[#0b7676] rounded-none"
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
      </div>
    </div>
  );
}
