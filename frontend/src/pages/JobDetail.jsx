import { useEffect, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { PublicNav } from "@/components/Nav";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { MapPin, Clock, CheckCircle2, ArrowLeft, ShieldCheck } from "lucide-react";

export default function JobDetail() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [job, setJob] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get(`/jobs/${jobId}`).then((r) => setJob(r.data)).catch(() => setErr("Job not found"));
  }, [jobId]);

  if (err) return <div className="p-8 text-red-600">{err}</div>;
  if (!job) return <div className="p-8 text-zinc-500">Loading...</div>;

  return (
    <div className="min-h-screen bg-white">
      <PublicNav />
      <div className="max-w-4xl mx-auto px-6 py-12">
        <button
          onClick={() => navigate(-1)}
          className="text-sm text-zinc-500 hover:text-[#002FA7] flex items-center gap-1 mb-6 transition-colors"
          data-testid="job-detail-back"
        >
          <ArrowLeft className="w-4 h-4" /> Back to roles
        </button>

        <Badge variant="outline" className="rounded-none border-zinc-300 mb-3">
          {job.department}
        </Badge>
        <h1 className="font-display font-extrabold text-4xl md:text-5xl tracking-tighter leading-tight" data-testid="job-title">
          {job.title}
        </h1>

        <div className="mt-4 flex flex-wrap gap-4 text-sm text-zinc-600">
          <span className="flex items-center gap-1.5"><MapPin className="w-4 h-4" /> {job.location}</span>
          <span className="flex items-center gap-1.5"><Clock className="w-4 h-4" /> {job.type}</span>
        </div>

        <div className="mt-8 divider" />

        <section className="mt-8">
          <h2 className="font-display font-extrabold text-xl tracking-tight">About the role</h2>
          <p className="mt-3 text-zinc-700 leading-relaxed">{job.description}</p>
        </section>

        {job.requirements?.length > 0 && (
          <section className="mt-8">
            <h2 className="font-display font-extrabold text-xl tracking-tight">Requirements</h2>
            <ul className="mt-3 space-y-2">
              {job.requirements.map((r, i) => (
                <li key={i} className="flex items-start gap-2 text-zinc-700">
                  <CheckCircle2 className="w-4 h-4 mt-0.5 text-[#002FA7] shrink-0" /> {r}
                </li>
              ))}
            </ul>
          </section>
        )}

        <section className="mt-8 border border-zinc-200 p-5 bg-zinc-50">
          <div className="flex items-center gap-2 text-sm font-medium">
            <ShieldCheck className="w-4 h-4 text-[#002FA7]" /> Proctored, AI-guarded assessment
          </div>
          <p className="mt-2 text-xs text-zinc-600">
            After applying, if shortlisted, HR will invite you via a unique one-time link to a
            proctored assessment. The assessment is timed, disables copy/paste, monitors tab
            switches and webcam presence, and screens written answers for AI-generated content.
          </p>
          {job.assignment_summary && (
            <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
              <div className="border-l-2 border-[#002FA7] pl-2">
                <div className="font-mono">{job.assignment_summary.duration_minutes} min</div>
                <div className="text-zinc-500">Duration</div>
              </div>
              <div className="border-l-2 border-[#002FA7] pl-2">
                <div className="font-mono">{job.assignment_summary.mcq_count}</div>
                <div className="text-zinc-500">MCQs</div>
              </div>
              <div className="border-l-2 border-[#002FA7] pl-2">
                <div className="font-mono">{job.assignment_summary.sa_count}</div>
                <div className="text-zinc-500">Short answers</div>
              </div>
              <div className="border-l-2 border-[#002FA7] pl-2">
                <div className="font-mono">{job.assignment_summary.has_coding ? "Yes" : "No"}</div>
                <div className="text-zinc-500">Coding task</div>
              </div>
            </div>
          )}
        </section>

        <div className="mt-10">
          <Link to={`/careers/${job.id}/apply`}>
            <Button className="bg-[#002FA7] hover:bg-[#00227A] rounded-none px-8 py-6" data-testid="apply-btn">
              Apply for this role
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
