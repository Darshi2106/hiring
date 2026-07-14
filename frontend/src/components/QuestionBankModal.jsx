import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { X, BookOpen, Check } from "lucide-react";

/**
 * Modal for HR to browse the question bank and import questions
 * into the current job's assignment.
 *
 * Props: { jobId, onClose, onImported }
 */
export default function QuestionBankModal({ jobId, onClose, onImported }) {
  const [modules, setModules] = useState([]);
  const [category, setCategory] = useState("All");
  const [openModule, setOpenModule] = useState(null); // module_id
  const [moduleDetail, setModuleDetail] = useState(null);
  const [selected, setSelected] = useState(new Set());
  const [importing, setImporting] = useState(false);

  useEffect(() => {
    api.get("/hr/question-bank").then((r) => setModules(r.data));
  }, []);

  useEffect(() => {
    if (!openModule) {
      setModuleDetail(null);
      return;
    }
    api.get(`/hr/question-bank/${openModule}`).then((r) => {
      setModuleDetail(r.data);
      // pre-select all by default
      setSelected(new Set(r.data.questions.map((q) => q.id)));
    });
  }, [openModule]);

  const categories = ["All", ...Array.from(new Set(modules.map((m) => m.category)))];
  const filtered = category === "All" ? modules : modules.filter((m) => m.category === category);

  const toggle = (id) => {
    const s = new Set(selected);
    if (s.has(id)) s.delete(id);
    else s.add(id);
    setSelected(s);
  };

  const doImport = async () => {
    if (selected.size === 0) return toast.warning("Pick at least one question");
    setImporting(true);
    try {
      const r = await api.post(`/hr/jobs/${jobId}/assignment/import`, {
        question_ids: Array.from(selected),
      });
      const total = r.data.added_mcq + r.data.added_sa + r.data.added_code;
      toast.success(
        `Imported ${total} question${total === 1 ? "" : "s"}`,
        {
          description: `MCQ ${r.data.added_mcq} · Short answer ${r.data.added_sa} · Coding ${r.data.added_code}`,
        }
      );
      onImported?.();
      onClose?.();
    } catch (e) {
      toast.error("Import failed");
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-white w-full max-w-5xl max-h-[85vh] flex flex-col border border-zinc-300"
        onClick={(e) => e.stopPropagation()}
        data-testid="qbank-modal"
      >
        {/* Header */}
        <div className="flex justify-between items-center px-5 py-4 border-b border-zinc-200">
          <div className="flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-brand" />
            <h2 className="font-display font-extrabold text-lg">Question Library</h2>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-zinc-100" data-testid="qbank-close">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* Left: modules */}
          <div className="w-72 border-r border-zinc-200 overflow-y-auto">
            <div className="p-3 border-b border-zinc-100 flex flex-wrap gap-1 sticky top-0 bg-white">
              {categories.map((c) => (
                <button
                  key={c}
                  onClick={() => setCategory(c)}
                  className={`text-xs px-2 py-1 border transition-colors ${
                    category === c ? "bg-zinc-900 text-white border-zinc-900" : "border-zinc-300 text-zinc-600 hover:border-zinc-900"
                  }`}
                  data-testid={`qbank-filter-${c.replace(/\s+/g, "-").toLowerCase()}`}
                >
                  {c}
                </button>
              ))}
            </div>
            <ul>
              {filtered.map((m) => (
                <li
                  key={m.id}
                  className={`px-4 py-3 border-b border-zinc-100 cursor-pointer transition-colors ${
                    openModule === m.id ? "bg-zinc-50 border-l-2 border-l-brand" : "hover:bg-zinc-50"
                  }`}
                  onClick={() => setOpenModule(m.id)}
                  data-testid={`qbank-module-${m.id}`}
                >
                  <div className="text-sm font-medium">{m.title}</div>
                  <div className="text-xs text-zinc-500 mt-0.5">{m.count} questions · {m.category}</div>
                </li>
              ))}
            </ul>
          </div>

          {/* Right: questions */}
          <div className="flex-1 overflow-y-auto p-5">
            {!openModule ? (
              <div className="h-full flex items-center justify-center text-sm text-zinc-500">
                Pick a module on the left to preview questions.
              </div>
            ) : !moduleDetail ? (
              <div className="text-sm text-zinc-500">Loading...</div>
            ) : (
              <>
                <div className="mb-4">
                  <h3 className="font-display font-extrabold text-xl">{moduleDetail.title}</h3>
                  <p className="text-sm text-zinc-600 mt-1">{moduleDetail.description}</p>
                  <div className="mt-2 flex items-center gap-2 text-xs">
                    <button
                      onClick={() => setSelected(new Set(moduleDetail.questions.map((q) => q.id)))}
                      className="text-brand hover:underline"
                    >
                      Select all
                    </button>
                    <span className="text-zinc-300">·</span>
                    <button onClick={() => setSelected(new Set())} className="text-zinc-500 hover:underline">
                      Clear
                    </button>
                    <span className="ml-2 text-zinc-500 font-mono">
                      {selected.size}/{moduleDetail.questions.length} selected
                    </span>
                  </div>
                </div>

                <div className="space-y-3">
                  {moduleDetail.questions.map((q, i) => (
                    <div
                      key={q.id}
                      className={`border p-3 cursor-pointer transition-colors ${
                        selected.has(q.id) ? "border-brand bg-zinc-50" : "border-zinc-200 hover:border-zinc-400"
                      }`}
                      onClick={() => toggle(q.id)}
                      data-testid={`qbank-q-${q.id}`}
                    >
                      <div className="flex items-start gap-2">
                        <div className={`w-5 h-5 border flex items-center justify-center shrink-0 mt-0.5 ${
                          selected.has(q.id) ? "bg-brand border-brand text-white" : "border-zinc-400"
                        }`}>
                          {selected.has(q.id) && <Check className="w-3 h-3" />}
                        </div>
                        <div className="flex-1">
                          <div className="text-xs uppercase tracking-widest text-zinc-500 mb-1 font-mono">
                            Q{i + 1} · {q.type.toUpperCase()} · weight {q.weight || 1}
                          </div>
                          <div className="text-sm">{q.question || q.prompt}</div>
                          {q.type === "mcq" && (
                            <ul className="mt-2 text-xs text-zinc-600 space-y-0.5">
                              {q.options.map((o, oi) => (
                                <li key={oi} className={oi === q.correct_index ? "text-green-700 font-medium" : ""}>
                                  {oi === q.correct_index ? "✓" : "○"} {o}
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-zinc-200 px-5 py-3 flex justify-between items-center">
          <div className="text-xs text-zinc-500">
            {selected.size > 0
              ? `${selected.size} questions selected from this module`
              : "Duplicate questions (already added) will be skipped."}
          </div>
          <div className="flex gap-2">
            <Button variant="outline" className="rounded-none" onClick={onClose}>Cancel</Button>
            <Button
              className="bg-brand rounded-none"
              disabled={importing || selected.size === 0}
              onClick={doImport}
              data-testid="qbank-import-btn"
            >
              {importing ? "Importing..." : `Import ${selected.size} into assignment`}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
