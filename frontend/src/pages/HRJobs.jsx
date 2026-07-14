import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { HRNav } from "@/components/Nav";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Plus, Trash2, Edit } from "lucide-react";

export default function HRJobs() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = () =>
    api.get("/jobs?status=").then((r) => {
      setJobs(r.data);
      setLoading(false);
    });

  useEffect(() => {
    load();
  }, []);

  const remove = async (id) => {
    if (!window.confirm("Delete this job?")) return;
    await api.delete(`/hr/jobs/${id}`);
    toast.success("Job deleted");
    load();
  };

  return (
    <div className="min-h-screen bg-white">
      <HRNav />
      <div className="max-w-7xl mx-auto px-6 py-10">
        <div className="flex justify-between items-end mb-8">
          <div>
            <div className="text-xs uppercase tracking-widest text-zinc-500 mb-1">Roles</div>
            <h1 className="font-display font-extrabold text-4xl tracking-tighter">Jobs</h1>
          </div>
          <Link to="/hr/jobs/new">
            <Button className="bg-[#0f9394] hover:bg-[#0b7676] rounded-none" data-testid="hr-new-job-btn">
              <Plus className="w-4 h-4 mr-1" /> New role
            </Button>
          </Link>
        </div>

        {loading ? (
          <div className="text-sm text-zinc-500">Loading...</div>
        ) : jobs.length === 0 ? (
          <div className="border border-dashed border-zinc-300 p-16 text-center text-zinc-500">
            No jobs yet. Create your first role.
          </div>
        ) : (
          <div className="border border-zinc-200">
            <table className="w-full text-sm">
              <thead className="bg-zinc-50 border-b border-zinc-200">
                <tr>
                  <th className="text-left px-4 py-3 font-medium">Role</th>
                  <th className="text-left px-4 py-3 font-medium">Department</th>
                  <th className="text-left px-4 py-3 font-medium">Location</th>
                  <th className="text-left px-4 py-3 font-medium">Status</th>
                  <th className="text-right px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((j) => (
                  <tr key={j.id} className="border-b border-zinc-100 hover:bg-zinc-50" data-testid={`hr-job-row-${j.id}`}>
                    <td className="px-4 py-3 font-medium">{j.title}</td>
                    <td className="px-4 py-3 text-zinc-600">{j.department}</td>
                    <td className="px-4 py-3 text-zinc-600">{j.location}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-mono uppercase px-2 py-0.5 border ${j.status === "open" ? "border-green-300 text-green-700 bg-green-50" : "border-zinc-300 text-zinc-600"}`}>
                        {j.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link to={`/hr/jobs/${j.id}/edit`}>
                        <Button size="sm" variant="ghost" data-testid={`hr-edit-${j.id}`}>
                          <Edit className="w-3.5 h-3.5" />
                        </Button>
                      </Link>
                      <Button size="sm" variant="ghost" onClick={() => remove(j.id)} data-testid={`hr-delete-${j.id}`}>
                        <Trash2 className="w-3.5 h-3.5 text-red-600" />
                      </Button>
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
