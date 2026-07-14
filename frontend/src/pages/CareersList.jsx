import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PublicNav } from "@/components/Nav";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { MapPin, ArrowRight, Sparkles } from "lucide-react";

export default function CareersList() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("All");

  useEffect(() => {
    api.get("/jobs").then((r) => {
      setJobs(r.data);
      setLoading(false);
    });
  }, []);

  const departments = ["All", ...Array.from(new Set(jobs.map((j) => j.department)))];
  const filtered = filter === "All" ? jobs : jobs.filter((j) => j.department === filter);

  return (
    <div className="min-h-screen bg-white">
      <PublicNav />

      {/* Hero */}
      <section className="border-b border-zinc-200">
        <div className="max-w-7xl mx-auto px-6 py-20 md:py-28 grid md:grid-cols-12 gap-8">
          <div className="md:col-span-8">
            <div className="inline-flex items-center gap-2 border border-zinc-300 px-3 py-1 text-xs text-zinc-600 mb-6">
              <Sparkles className="w-3 h-3" /> We're hiring across teams
            </div>
            <h1 className="font-display font-extrabold text-5xl md:text-6xl lg:text-7xl tracking-tighter leading-[0.95]">
              Build the future of{" "}
              <span className="text-[#0f9394]">AI data infrastructure.</span>
            </h1>
            <p className="mt-6 text-lg text-zinc-600 max-w-2xl leading-relaxed">
              Join CohortData — a team building multimodal AI systems, annotation pipelines,
              and infrastructure powering autonomy, robotics, and enterprise intelligence
              worldwide.
            </p>
            <div className="mt-8 flex gap-3">
              <a href="#roles">
                <Button className="bg-[#0f9394] hover:bg-[#0b7676] rounded-none px-6" data-testid="hero-explore-btn">
                  Explore Open Roles <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </a>
            </div>
          </div>
          <div className="md:col-span-4 flex flex-col justify-end gap-3">
            <div className="border border-zinc-200 p-6">
              <div className="text-4xl font-display font-extrabold">{jobs.length}</div>
              <div className="text-xs uppercase tracking-widest text-zinc-500 mt-1">Open positions</div>
            </div>
            <div className="border border-zinc-200 p-6">
              <div className="text-4xl font-display font-extrabold">Hyderabad</div>
              <div className="text-xs uppercase tracking-widest text-zinc-500 mt-1">Primary hub</div>
            </div>
          </div>
        </div>
      </section>

      {/* Roles */}
      <section id="roles" className="max-w-7xl mx-auto px-6 py-16">
        <div className="flex items-end justify-between mb-8 flex-wrap gap-4">
          <div>
            <div className="text-xs uppercase tracking-widest text-zinc-500 mb-2">We're hiring</div>
            <h2 className="font-display font-extrabold text-4xl tracking-tight">Open roles</h2>
          </div>
          <div className="flex flex-wrap gap-1">
            {departments.map((d) => (
              <button
                key={d}
                onClick={() => setFilter(d)}
                data-testid={`filter-${d.replace(/\s+/g, "-").toLowerCase()}`}
                className={`text-sm px-3 py-1.5 border transition-colors ${
                  filter === d
                    ? "bg-[#09090B] text-white border-[#09090B]"
                    : "bg-white text-zinc-700 border-zinc-300 hover:border-[#09090B]"
                }`}
              >
                {d}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="text-zinc-500 text-sm">Loading roles...</div>
        ) : filtered.length === 0 ? (
          <div className="border border-dashed border-zinc-300 p-12 text-center text-zinc-500">
            No open roles in this category right now.
          </div>
        ) : (
          <div className="grid gap-0 border-t border-zinc-200">
            {filtered.map((job) => (
              <Link
                key={job.id}
                to={`/careers/${job.id}`}
                data-testid={`job-card-${job.id}`}
                className="group border-b border-zinc-200 py-6 flex flex-col md:flex-row md:items-center gap-4 hover:bg-zinc-50 px-4 -mx-4 transition-colors"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1.5">
                    <Badge variant="outline" className="text-xs font-normal rounded-none border-zinc-300">
                      {job.department}
                    </Badge>
                  </div>
                  <h3 className="font-display font-extrabold text-xl md:text-2xl tracking-tight group-hover:text-[#0f9394] transition-colors">
                    {job.title}
                  </h3>
                  <div className="mt-2 flex items-center gap-4 text-sm text-zinc-500">
                    <span className="flex items-center gap-1">
                      <MapPin className="w-3.5 h-3.5" /> {job.location}
                    </span>
                    <span>{job.type}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-sm font-medium text-[#0f9394]">
                  View role <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      <footer className="border-t border-zinc-200 mt-16">
        <div className="max-w-7xl mx-auto px-6 py-8 text-xs text-zinc-500 flex justify-between">
          <span>© CohortData Hiring Portal</span>
          <span>Powered by proctored, AI-guarded assessments.</span>
        </div>
      </footer>
    </div>
  );
}
