import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { PublicNav } from "@/components/Nav";
import { api, formatError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { CheckCircle2 } from "lucide-react";

export default function Apply() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [job, setJob] = useState(null);
  const [form, setForm] = useState({
    name: "",
    email: "",
    phone: "",
    resume_url: "",
    cover_letter: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    api.get(`/jobs/${jobId}`).then((r) => setJob(r.data));
  }, [jobId]);

  const update = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.post("/applications", { job_id: jobId, ...form });
      toast.success("Application submitted");
      setSubmitted(true);
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail) || err.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted)
    return (
      <div className="min-h-screen bg-white">
        <PublicNav />
        <div className="max-w-2xl mx-auto px-6 py-24 text-center">
          <CheckCircle2 className="w-16 h-16 text-[#16A34A] mx-auto mb-4" />
          <h1 className="font-display font-extrabold text-4xl tracking-tighter">Application received</h1>
          <p className="mt-3 text-zinc-600">
            Thanks, {form.name.split(" ")[0]}. Our HR team will review your application for{" "}
            <strong>{job?.title}</strong>. If shortlisted, we'll email you a proctored assessment link.
          </p>
          <Link to="/careers">
            <Button className="mt-8 rounded-none" data-testid="apply-back-home">Browse more roles</Button>
          </Link>
        </div>
      </div>
    );

  return (
    <div className="min-h-screen bg-white">
      <PublicNav />
      <div className="max-w-2xl mx-auto px-6 py-12">
        <Link to={`/careers/${jobId}`} className="text-sm text-zinc-500 hover:text-[#002FA7]">
          ← Back to role
        </Link>
        <div className="text-xs uppercase tracking-widest text-zinc-500 mt-6">Applying for</div>
        <h1 className="font-display font-extrabold text-3xl md:text-4xl tracking-tighter mt-1">
          {job?.title || "..."}
        </h1>

        <form onSubmit={submit} className="mt-10 space-y-5" data-testid="apply-form">
          <div>
            <Label htmlFor="name">Full name *</Label>
            <Input id="name" required value={form.name} onChange={update("name")} className="rounded-none mt-1" data-testid="apply-name" />
          </div>
          <div>
            <Label htmlFor="email">Email *</Label>
            <Input id="email" type="email" required value={form.email} onChange={update("email")} className="rounded-none mt-1" data-testid="apply-email" />
          </div>
          <div>
            <Label htmlFor="phone">Phone</Label>
            <Input id="phone" value={form.phone} onChange={update("phone")} className="rounded-none mt-1" data-testid="apply-phone" />
          </div>
          <div>
            <Label htmlFor="resume">Resume URL (Google Drive / LinkedIn)</Label>
            <Input id="resume" type="url" placeholder="https://..." value={form.resume_url} onChange={update("resume_url")} className="rounded-none mt-1" data-testid="apply-resume" />
          </div>
          <div>
            <Label htmlFor="cover">Cover letter</Label>
            <Textarea id="cover" rows={5} value={form.cover_letter} onChange={update("cover_letter")} className="rounded-none mt-1" data-testid="apply-cover" />
          </div>
          <Button type="submit" disabled={submitting} className="bg-[#002FA7] hover:bg-[#00227A] rounded-none px-8" data-testid="apply-submit">
            {submitting ? "Submitting..." : "Submit application"}
          </Button>
        </form>
      </div>
    </div>
  );
}
