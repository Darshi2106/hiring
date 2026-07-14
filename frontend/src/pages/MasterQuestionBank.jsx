import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { HRNav } from "@/components/Nav";
import { api, formatError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Plus, Trash2, BookOpen, Save, Check, X, Lock } from "lucide-react";

function newQ(type = "mcq") {
  const rid = () => `q_${Math.random().toString(36).slice(2, 8)}`;
  if (type === "mcq") return { id: rid(), type: "mcq", question: "", options: ["", "", "", ""], correct_index: 0, weight: 1 };
  if (type === "sa") return { id: rid(), type: "sa", question: "", min_words: 40, weight: 1 };
  return { id: rid(), type: "code", prompt: "", starter_code: "", language: "python", test_code: "", weight: 3 };
}

export default function MasterQuestionBank() {
  const { user, loading } = useAuth();
  const nav = useNavigate();
  const [modules, setModules] = useState([]);
  const [openId, setOpenId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [creating, setCreating] = useState(false);
  const [newForm, setNewForm] = useState({ id: "", title: "", category: "Tech & Eng", description: "" });

  useEffect(() => {
    if (loading) return;
    if (!user || user.role !== "master_admin") {
      nav("/hr/dashboard");
      return;
    }
    load();
    // eslint-disable-next-line
  }, [user, loading]);

  const load = () => api.get("/hr/question-bank").then((r) => setModules(r.data));

  const openModule = async (id) => {
    setOpenId(id);
    const r = await api.get(`/hr/question-bank/${id}`);
    setDetail(r.data);
  };

  const createModule = async (e) => {
    e.preventDefault();
    if (!/^[a-z0-9_]+$/.test(newForm.id)) {
      toast.error("ID must be lowercase letters, digits, or underscores.");
      return;
    }
    try {
      await api.post("/master/question-bank/modules", { ...newForm, questions: [] });
      toast.success("Module created");
      setCreating(false);
      setNewForm({ id: "", title: "", category: "Tech & Eng", description: "" });
      load();
      openModule(newForm.id);
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail) || err.message);
    }
  };

  const saveDetail = async () => {
    try {
      await api.put(`/master/question-bank/modules/${detail.id}`, {
        id: detail.id,
        title: detail.title,
        category: detail.category,
        description: detail.description,
        questions: detail.questions,
      });
      toast.success("Module saved");
      load();
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail) || err.message);
    }
  };

  const deleteModule = async () => {
    if (!window.confirm(`Delete module "${detail.title}"? Custom questions inside will no longer be available for import.`)) return;
    try {
      await api.delete(`/master/question-bank/modules/${detail.id}`);
      toast.success("Deleted");
      setOpenId(null);
      setDetail(null);
      load();
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail) || err.message);
    }
  };

  const updateQ = (idx, patch) => {
    const qs = [...detail.questions];
    qs[idx] = { ...qs[idx], ...patch };
    setDetail({ ...detail, questions: qs });
  };

  return (
    <div className="min-h-screen bg-white">
      <HRNav />
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="flex items-end justify-between mb-6">
          <div>
            <div className="text-xs uppercase tracking-widest text-zinc-500 flex items-center gap-1"><Lock className="w-3 h-3" /> Master admin</div>
            <h1 className="font-display font-extrabold text-4xl tracking-tighter">Question bank</h1>
            <p className="mt-2 text-sm text-zinc-500">Curate seeded modules and add your own. Custom modules become available to all HR immediately.</p>
          </div>
          <Button onClick={() => setCreating(true)} className="bg-brand rounded-none" data-testid="qb-new-module">
            <Plus className="w-4 h-4 mr-1" /> New module
          </Button>
        </div>

        <div className="grid md:grid-cols-4 gap-4">
          {/* Modules list */}
          <div className="border border-zinc-200 max-h-[70vh] overflow-y-auto" data-testid="qb-modules">
            <ul>
              {modules.map((m) => (
                <li
                  key={m.id}
                  onClick={() => openModule(m.id)}
                  className={`px-4 py-3 border-b border-zinc-100 cursor-pointer hover:bg-zinc-50 ${openId === m.id ? "bg-zinc-50 border-l-2 border-l-brand" : ""}`}
                  data-testid={`qb-mod-${m.id}`}
                >
                  <div className="flex items-center justify-between">
                    <div className="font-medium text-sm">{m.title}</div>
                    {m.is_custom ? (
                      <span className="text-[10px] font-mono border border-brand text-brand px-1 py-0.5">CUSTOM</span>
                    ) : (
                      <span className="text-[10px] font-mono border border-zinc-300 text-zinc-500 px-1 py-0.5">SEEDED</span>
                    )}
                  </div>
                  <div className="text-xs text-zinc-500 mt-0.5">{m.count} Qs · {m.category}</div>
                </li>
              ))}
            </ul>
          </div>

          {/* Detail */}
          <div className="md:col-span-3">
            {creating ? (
              <form onSubmit={createModule} className="border border-zinc-200 p-5 space-y-3" data-testid="qb-create-form">
                <h2 className="font-display font-extrabold text-lg">New module</h2>
                <div>
                  <Label>Module ID (lowercase, underscores only)</Label>
                  <Input required value={newForm.id} onChange={(e) => setNewForm({ ...newForm, id: e.target.value })} className="rounded-none mt-1 font-mono" placeholder="mcq_devops" data-testid="qb-new-id" />
                </div>
                <div>
                  <Label>Title</Label>
                  <Input required value={newForm.title} onChange={(e) => setNewForm({ ...newForm, title: e.target.value })} className="rounded-none mt-1" data-testid="qb-new-title" />
                </div>
                <div>
                  <Label>Category</Label>
                  <select value={newForm.category} onChange={(e) => setNewForm({ ...newForm, category: e.target.value })} className="rounded-none mt-1 w-full h-10 border border-zinc-300 px-3 text-sm bg-white" data-testid="qb-new-category">
                    <option>Tech & Eng</option>
                    <option>Business & Sales</option>
                    <option>Operations</option>
                    <option>General</option>
                  </select>
                </div>
                <div>
                  <Label>Description</Label>
                  <Textarea value={newForm.description} onChange={(e) => setNewForm({ ...newForm, description: e.target.value })} rows={2} className="rounded-none mt-1" data-testid="qb-new-desc" />
                </div>
                <div className="flex gap-2">
                  <Button type="submit" className="bg-brand rounded-none" data-testid="qb-new-submit">Create</Button>
                  <Button type="button" variant="outline" className="rounded-none" onClick={() => setCreating(false)}>Cancel</Button>
                </div>
              </form>
            ) : !detail ? (
              <div className="border border-dashed border-zinc-300 p-12 text-center text-zinc-500">
                <BookOpen className="w-8 h-8 mx-auto mb-2 opacity-40" />
                Pick a module on the left to view or edit.
              </div>
            ) : (
              <div className="border border-zinc-200 p-5">
                <div className="flex justify-between items-start mb-4 flex-wrap gap-2">
                  <div>
                    <div className="text-xs font-mono text-zinc-500">{detail.id} · {detail.is_custom ? "CUSTOM" : "SEEDED (read-only)"}</div>
                    <h2 className="font-display font-extrabold text-2xl">{detail.title}</h2>
                    <div className="text-xs text-zinc-500 mt-1">{detail.category}</div>
                  </div>
                  {detail.is_custom && (
                    <div className="flex gap-2">
                      <Button onClick={saveDetail} className="bg-brand rounded-none" data-testid="qb-save"><Save className="w-4 h-4 mr-1" /> Save</Button>
                      <Button variant="outline" className="rounded-none border-red-300 text-red-600" onClick={deleteModule} data-testid="qb-delete"><Trash2 className="w-4 h-4 mr-1" /> Delete</Button>
                    </div>
                  )}
                </div>

                {!detail.is_custom && (
                  <div className="mb-4 border border-zinc-100 bg-zinc-50 p-3 text-xs text-zinc-600">
                    Seeded modules are read-only. Create a custom module to author or override questions.
                  </div>
                )}

                {detail.is_custom && (
                  <div className="mb-4 flex gap-2">
                    <Button size="sm" variant="outline" className="rounded-none" onClick={() => setDetail({ ...detail, questions: [...detail.questions, newQ("mcq")] })} data-testid="qb-add-mcq"><Plus className="w-3.5 h-3.5 mr-1" /> Add MCQ</Button>
                    <Button size="sm" variant="outline" className="rounded-none" onClick={() => setDetail({ ...detail, questions: [...detail.questions, newQ("sa")] })} data-testid="qb-add-sa"><Plus className="w-3.5 h-3.5 mr-1" /> Add short-answer</Button>
                    <Button size="sm" variant="outline" className="rounded-none" onClick={() => setDetail({ ...detail, questions: [...detail.questions, newQ("code")] })} data-testid="qb-add-code"><Plus className="w-3.5 h-3.5 mr-1" /> Add coding</Button>
                  </div>
                )}

                <div className="space-y-3 max-h-[55vh] overflow-y-auto">
                  {detail.questions.map((q, i) => (
                    <div key={q.id} className="border border-zinc-200 p-3" data-testid={`qb-q-${i}`}>
                      <div className="flex justify-between items-center mb-2">
                        <div className="text-xs font-mono uppercase text-zinc-500">Q{i + 1} · {q.type} · weight {q.weight || 1}</div>
                        {detail.is_custom && (
                          <Button size="sm" variant="ghost" onClick={() => setDetail({ ...detail, questions: detail.questions.filter((_, k) => k !== i) })}><Trash2 className="w-4 h-4 text-red-600" /></Button>
                        )}
                      </div>

                      {q.type === "mcq" && (
                        <>
                          <Textarea disabled={!detail.is_custom} value={q.question} onChange={(e) => updateQ(i, { question: e.target.value })} rows={2} className="rounded-none" />
                          <div className="mt-2 space-y-1">
                            {q.options.map((opt, oi) => (
                              <div key={oi} className="flex items-center gap-2">
                                <button type="button" disabled={!detail.is_custom} onClick={() => updateQ(i, { correct_index: oi })} className={`w-5 h-5 border flex items-center justify-center ${q.correct_index === oi ? "bg-brand border-brand text-white" : "border-zinc-300"}`}>{q.correct_index === oi && <Check className="w-3 h-3" />}</button>
                                <Input disabled={!detail.is_custom} value={opt} onChange={(e) => { const opts = [...q.options]; opts[oi] = e.target.value; updateQ(i, { options: opts }); }} className="rounded-none" />
                              </div>
                            ))}
                          </div>
                        </>
                      )}
                      {q.type === "sa" && (
                        <Textarea disabled={!detail.is_custom} value={q.question} onChange={(e) => updateQ(i, { question: e.target.value })} rows={2} className="rounded-none" />
                      )}
                      {q.type === "code" && (
                        <>
                          <div className="flex items-center gap-2 mb-1">
                            <select disabled={!detail.is_custom} value={q.language || "python"} onChange={(e) => updateQ(i, { language: e.target.value })} className="rounded-none border border-zinc-300 text-xs h-8 px-2"><option>python</option><option>javascript</option><option>sql</option></select>
                          </div>
                          <Textarea disabled={!detail.is_custom} value={q.prompt || ""} onChange={(e) => updateQ(i, { prompt: e.target.value })} rows={3} className="rounded-none" placeholder="Prompt" />
                          <textarea disabled={!detail.is_custom} className="code-editor mt-2" value={q.starter_code || ""} onChange={(e) => updateQ(i, { starter_code: e.target.value })} rows={4} placeholder="Starter code" />
                          {(q.language === "python" || q.language === "javascript") && (
                            <textarea disabled={!detail.is_custom} className="code-editor mt-2" value={q.test_code || ""} onChange={(e) => updateQ(i, { test_code: e.target.value })} rows={4} placeholder="# Test harness (auto-grade)" />
                          )}
                        </>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
