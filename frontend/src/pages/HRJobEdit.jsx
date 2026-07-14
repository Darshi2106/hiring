import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { HRNav } from "@/components/Nav";
import { api, formatError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

export default function HRJobEdit() {
  const { jobId } = useParams();
  const nav = useNavigate();
  const isEdit = Boolean(jobId);
  const [form, setForm] = useState({
    title: "",
    department: "Tech & Eng",
    location: "Hyderabad",
    type: "Full-Time",
    description: "",
    requirements: "",
    status: "open",
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!isEdit) return;
    api.get(`/hr/jobs/${jobId}`).then((r) => {
      setForm({
        ...r.data,
        requirements: (r.data.requirements || []).join("\n"),
      });
    });
  }, [jobId, isEdit]);

  const upd = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        ...form,
        requirements: form.requirements
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean),
      };
      delete payload.id;
      delete payload.created_at;
      delete payload.assignment;
      if (isEdit) await api.put(`/hr/jobs/${jobId}`, payload);
      else await api.post("/hr/jobs", payload);
      toast.success(isEdit ? "Job updated" : "Job created");
      nav("/hr/jobs");
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail) || err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-white">
      <HRNav />
      <div className="max-w-3xl mx-auto px-6 py-10">
        <h1 className="font-display font-extrabold text-4xl tracking-tighter mb-8">
          {isEdit ? "Edit role" : "New role"}
        </h1>

        <form onSubmit={submit} className="space-y-5" data-testid="hr-job-form">
          <div>
            <Label>Title *</Label>
            <Input required value={form.title} onChange={upd("title")} className="rounded-none mt-1" data-testid="hr-job-title" />
          </div>
          <div className="grid md:grid-cols-3 gap-4">
            <div>
              <Label>Department</Label>
              <Input value={form.department} onChange={upd("department")} className="rounded-none mt-1" data-testid="hr-job-department" />
            </div>
            <div>
              <Label>Location</Label>
              <Input value={form.location} onChange={upd("location")} className="rounded-none mt-1" data-testid="hr-job-location" />
            </div>
            <div>
              <Label>Type</Label>
              <Input value={form.type} onChange={upd("type")} className="rounded-none mt-1" data-testid="hr-job-type" />
            </div>
          </div>
          <div>
            <Label>Description *</Label>
            <Textarea rows={4} required value={form.description} onChange={upd("description")} className="rounded-none mt-1" data-testid="hr-job-description" />
          </div>
          <div>
            <Label>Requirements (one per line)</Label>
            <Textarea rows={5} value={form.requirements} onChange={upd("requirements")} className="rounded-none mt-1 font-mono text-xs" data-testid="hr-job-requirements" />
          </div>
          <div>
            <Label>Status</Label>
            <select
              value={form.status}
              onChange={upd("status")}
              className="mt-1 w-full h-10 border border-zinc-300 px-3 text-sm bg-white"
              data-testid="hr-job-status"
            >
              <option value="open">Open</option>
              <option value="closed">Closed</option>
            </select>
          </div>
          <div className="flex gap-2 pt-4">
            <Button type="submit" disabled={saving} className="bg-[#0f9394] hover:bg-[#0b7676] rounded-none" data-testid="hr-job-save">
              {saving ? "Saving..." : isEdit ? "Save changes" : "Create role"}
            </Button>
            <Button type="button" variant="outline" className="rounded-none" onClick={() => nav("/hr/jobs")}>
              Cancel
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
