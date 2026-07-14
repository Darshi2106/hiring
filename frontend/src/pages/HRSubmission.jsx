import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { HRNav } from "@/components/Nav";
import { api } from "@/lib/api";
import { AlertTriangle, ShieldCheck, ArrowLeft, Camera } from "lucide-react";

export default function HRSubmission() {
  const { submissionId } = useParams();
  const [sub, setSub] = useState(null);

  useEffect(() => {
    api.get(`/hr/submissions/${submissionId}`).then((r) => setSub(r.data));
  }, [submissionId]);

  if (!sub) return <div className="min-h-screen"><HRNav /><div className="p-8 text-zinc-500">Loading...</div></div>;

  const riskColor =
    sub.ai_risk_avg >= 70 ? "text-red-600 bg-red-50 border-red-200" :
    sub.ai_risk_avg >= 40 ? "text-amber-700 bg-amber-50 border-amber-200" :
    "text-green-700 bg-green-50 border-green-200";

  return (
    <div className="min-h-screen bg-white">
      <HRNav />
      <div className="max-w-6xl mx-auto px-6 py-10">
        <Link to="/hr/applications" className="text-sm text-zinc-500 hover:text-[#0f9394] flex items-center gap-1 mb-4">
          <ArrowLeft className="w-4 h-4" /> Back to applications
        </Link>

        <div className="grid md:grid-cols-3 gap-4">
          <div className="border border-zinc-200 p-4 md:col-span-2">
            <div className="text-xs uppercase tracking-widest text-zinc-500">Candidate</div>
            <div className="font-display font-extrabold text-2xl mt-1">{sub.candidate_name}</div>
            <div className="text-sm text-zinc-500 font-mono">{sub.candidate_email}</div>
            <div className="mt-4 text-xs text-zinc-500">
              Submitted: <span className="font-mono">{new Date(sub.submitted_at).toLocaleString()}</span> ·
              Time taken: <span className="font-mono">{Math.floor(sub.time_taken_seconds / 60)}m {sub.time_taken_seconds % 60}s</span>
            </div>
          </div>
          <div className={`border p-4 ${riskColor}`} data-testid="sub-ai-score">
            <div className="text-xs uppercase tracking-widest opacity-70">AI-generation risk</div>
            <div className="font-display font-extrabold text-4xl mt-1 font-mono">{sub.ai_risk_avg}%</div>
            <div className="text-xs mt-1 opacity-80">
              MCQ: <span className="font-mono">{sub.mcq_score}/{sub.mcq_total}</span>
            </div>
          </div>
        </div>

        {/* Violations */}
        <div className="mt-8 border border-zinc-200 p-5">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className={`w-4 h-4 ${sub.violations?.length ? "text-red-600" : "text-zinc-400"}`} />
            <h2 className="font-display font-extrabold text-lg">Proctoring log</h2>
            <span className="text-xs text-zinc-500 font-mono">{sub.violations?.length || 0} events</span>
          </div>
          {sub.violations?.length ? (
            <ul className="space-y-1 text-sm font-mono">
              {sub.violations.map((v, i) => (
                <li key={i} className="flex gap-3 py-1 border-b border-zinc-100 last:border-0">
                  <span className="text-red-600 uppercase text-xs w-32">{v.type}</span>
                  <span className="text-zinc-600 text-xs flex-1">{v.detail || ""}</span>
                  <span className="text-zinc-400 text-xs">{v.timestamp || ""}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-sm text-zinc-500 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-green-600" /> No proctoring violations.
            </div>
          )}
        </div>

        {/* Webcam snapshots */}
        {sub.webcam_snapshots?.length > 0 && (
          <div className="mt-6 border border-zinc-200 p-5">
            <div className="flex items-center gap-2 mb-3">
              <Camera className="w-4 h-4 text-zinc-500" />
              <h2 className="font-display font-extrabold text-lg">Webcam snapshots</h2>
              <span className="text-xs text-zinc-500 font-mono">{sub.webcam_snapshots.length}</span>
            </div>
            <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
              {sub.webcam_snapshots.map((src, i) => (
                <img key={i} src={src} alt={`snap-${i}`} className="w-full aspect-square object-cover border border-zinc-200" />
              ))}
            </div>
          </div>
        )}

        {/* Short answers with AI detection */}
        <div className="mt-6">
          <h2 className="font-display font-extrabold text-xl mb-3">Short-answer responses</h2>
          <div className="space-y-4">
            {Object.entries(sub.short_answers || {}).map(([id, text]) => {
              const ai = sub.ai_results?.[id];
              const s = ai?.ai_risk_score;
              const badge =
                s == null || s < 0 ? "border-zinc-300 text-zinc-500" :
                s >= 70 ? "border-red-300 text-red-700 bg-red-50" :
                s >= 40 ? "border-amber-300 text-amber-700 bg-amber-50" :
                "border-green-300 text-green-700 bg-green-50";
              return (
                <div key={id} className="border border-zinc-200 p-4">
                  <div className="flex justify-between items-start gap-3">
                    <div className="text-xs text-zinc-500 uppercase tracking-widest">{id}</div>
                    <div className={`text-xs px-2 py-0.5 border font-mono ${badge}`}>
                      AI risk: {s < 0 || s == null ? "n/a" : `${s}%`}
                    </div>
                  </div>
                  <p className="mt-3 text-sm whitespace-pre-wrap">{text || <em className="text-zinc-400">No answer</em>}</p>
                  {ai?.reasoning && (
                    <div className="mt-3 pt-3 border-t border-zinc-100 text-xs text-zinc-600">
                      <span className="font-medium">Detector reasoning: </span>{ai.reasoning}
                      {ai.signals?.length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {ai.signals.map((s, i) => (
                            <span key={i} className="border border-zinc-200 px-2 py-0.5 font-mono">{s}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Coding */}
        {sub.coding_answer && (
          <div className="mt-6">
            <h2 className="font-display font-extrabold text-xl mb-3">Coding submission</h2>
            <pre className="code-editor whitespace-pre-wrap">{sub.coding_answer}</pre>
          </div>
        )}
      </div>
    </div>
  );
}
