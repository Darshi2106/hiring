import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { HRNav } from "@/components/Nav";
import { api, formatError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Plus, Trash2, ArrowLeft, Save, GripVertical, Check, Code } from "lucide-react";

const emptyMcq = () => ({
  id: `mcq_${Math.random().toString(36).slice(2, 8)}`,
  question: "",
  options: ["", "", "", ""],
  correct_index: 0,
  weight: 1,
});

const emptySA = () => ({
  id: `sa_${Math.random().toString(36).slice(2, 8)}`,
  question: "",
  min_words: 40,
  weight: 1,
});

export default function HRAssignmentEditor() {
  const { jobId } = useParams();
  const nav = useNavigate();
  const [job, setJob] = useState(null);
  const [assignment, setAssignment] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    Promise.all([
      api.get(`/hr/jobs/${jobId}`),
      api.get(`/hr/jobs/${jobId}/assignment`),
    ]).then(([j, a]) => {
      setJob(j.data);
      setAssignment(a.data);
    });
  }, [jobId]);

  if (!assignment) return <div className="min-h-screen"><HRNav /><div className="p-8 text-zinc-500">Loading assignment...</div></div>;

  const updateMcq = (idx, patch) => {
    const next = { ...assignment, mcqs: [...assignment.mcqs] };
    next.mcqs[idx] = { ...next.mcqs[idx], ...patch };
    setAssignment(next);
  };
  const updateSA = (idx, patch) => {
    const next = { ...assignment, short_answers: [...assignment.short_answers] };
    next.short_answers[idx] = { ...next.short_answers[idx], ...patch };
    setAssignment(next);
  };

  const totalWeight =
    assignment.mcqs.reduce((s, m) => s + (m.weight || 1), 0) +
    assignment.short_answers.reduce((s, m) => s + (m.weight || 1), 0) +
    (assignment.coding ? assignment.coding.weight || 1 : 0);

  const save = async () => {
    setSaving(true);
    try {
      // Client-side validation
      for (const m of assignment.mcqs) {
        if (!m.question.trim()) throw new Error("An MCQ has an empty question");
        if (m.options.some((o) => !o.trim())) throw new Error(`MCQ "${m.question.slice(0, 30)}..." has empty options`);
      }
      await api.put(`/hr/jobs/${jobId}/assignment`, assignment);
      toast.success("Assignment saved");
    } catch (e) {
      const detail = e.response?.data?.detail;
      toast.error(formatError(detail) || e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-white">
      <HRNav />
      <div className="max-w-5xl mx-auto px-6 py-8">
        <Link to="/hr/jobs" className="text-sm text-zinc-500 hover:text-brand flex items-center gap-1 mb-3">
          <ArrowLeft className="w-4 h-4" /> Back to jobs
        </Link>
        <div className="flex justify-between items-start flex-wrap gap-4 mb-6">
          <div>
            <div className="text-xs uppercase tracking-widest text-zinc-500">Assignment editor</div>
            <h1 className="font-display font-extrabold text-3xl tracking-tighter">{job?.title}</h1>
            <div className="mt-2 text-xs font-mono text-zinc-500">
              MCQs: {assignment.mcqs.length} · Short answers: {assignment.short_answers.length} ·
              Coding: {assignment.coding ? "1" : "0"} · Total weight: {totalWeight}
            </div>
          </div>
          <Button onClick={save} disabled={saving} className="bg-brand hover:opacity-90 rounded-none" data-testid="save-assignment">
            <Save className="w-4 h-4 mr-1.5" /> {saving ? "Saving..." : "Save assignment"}
          </Button>
        </div>

        {/* Duration */}
        <section className="border border-zinc-200 p-5 mb-6">
          <h2 className="font-display font-extrabold text-lg mb-3">Timing</h2>
          <div className="flex items-center gap-3">
            <Label htmlFor="duration" className="w-32">Duration (min)</Label>
            <Input
              id="duration"
              type="number"
              min="5"
              max="240"
              value={assignment.duration_minutes}
              onChange={(e) => setAssignment({ ...assignment, duration_minutes: Number(e.target.value) })}
              className="rounded-none w-32"
              data-testid="assignment-duration"
            />
            <span className="text-xs text-zinc-500">Between 5 and 240 minutes.</span>
          </div>
        </section>

        {/* MCQs */}
        <section className="border border-zinc-200 p-5 mb-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="font-display font-extrabold text-lg">Multiple choice questions</h2>
            <Button
              size="sm"
              variant="outline"
              className="rounded-none"
              onClick={() => setAssignment({ ...assignment, mcqs: [...assignment.mcqs, emptyMcq()] })}
              data-testid="add-mcq"
            >
              <Plus className="w-3.5 h-3.5 mr-1" /> Add MCQ
            </Button>
          </div>

          {assignment.mcqs.length === 0 && (
            <p className="text-sm text-zinc-500 py-6 text-center border border-dashed border-zinc-300">
              No MCQs. Click "Add MCQ" to create one.
            </p>
          )}

          <div className="space-y-4">
            {assignment.mcqs.map((m, i) => (
              <div key={m.id} className="border border-zinc-200 p-4" data-testid={`mcq-editor-${i}`}>
                <div className="flex justify-between items-start gap-3 mb-2">
                  <div className="text-xs uppercase tracking-widest text-zinc-500 font-mono">Q{i + 1}</div>
                  <div className="flex items-center gap-2">
                    <Label className="text-xs">Weight</Label>
                    <Input
                      type="number"
                      min="1"
                      value={m.weight}
                      onChange={(e) => updateMcq(i, { weight: Number(e.target.value) })}
                      className="rounded-none w-16 h-8"
                      data-testid={`mcq-weight-${i}`}
                    />
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setAssignment({ ...assignment, mcqs: assignment.mcqs.filter((_, k) => k !== i) })}
                      data-testid={`mcq-delete-${i}`}
                    >
                      <Trash2 className="w-4 h-4 text-red-600" />
                    </Button>
                  </div>
                </div>
                <Textarea
                  placeholder="Question text..."
                  value={m.question}
                  onChange={(e) => updateMcq(i, { question: e.target.value })}
                  className="rounded-none"
                  rows={2}
                  data-testid={`mcq-question-${i}`}
                />
                <div className="mt-3 space-y-1.5">
                  {m.options.map((opt, oi) => (
                    <div key={oi} className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => updateMcq(i, { correct_index: oi })}
                        className={`w-6 h-6 border flex items-center justify-center shrink-0 ${
                          m.correct_index === oi ? "bg-brand border-brand text-white" : "border-zinc-300"
                        }`}
                        data-testid={`mcq-${i}-correct-${oi}`}
                        title="Mark as correct answer"
                      >
                        {m.correct_index === oi && <Check className="w-3 h-3" />}
                      </button>
                      <Input
                        placeholder={`Option ${oi + 1}`}
                        value={opt}
                        onChange={(e) => {
                          const opts = [...m.options];
                          opts[oi] = e.target.value;
                          updateMcq(i, { options: opts });
                        }}
                        className="rounded-none"
                        data-testid={`mcq-${i}-option-${oi}`}
                      />
                      {m.options.length > 2 && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => {
                            const opts = m.options.filter((_, k) => k !== oi);
                            const ci = m.correct_index >= opts.length ? 0 : m.correct_index;
                            updateMcq(i, { options: opts, correct_index: ci });
                          }}
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </Button>
                      )}
                    </div>
                  ))}
                  {m.options.length < 6 && (
                    <button
                      type="button"
                      onClick={() => updateMcq(i, { options: [...m.options, ""] })}
                      className="text-xs text-brand hover:underline mt-1"
                      data-testid={`mcq-${i}-add-option`}
                    >
                      + Add option
                    </button>
                  )}
                </div>
                <div className="mt-2 text-xs text-zinc-500">
                  Correct answer: <span className="font-mono">Option {m.correct_index + 1}</span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Short answers */}
        <section className="border border-zinc-200 p-5 mb-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="font-display font-extrabold text-lg">Short-answer questions</h2>
            <Button
              size="sm"
              variant="outline"
              className="rounded-none"
              onClick={() =>
                setAssignment({ ...assignment, short_answers: [...assignment.short_answers, emptySA()] })
              }
              data-testid="add-sa"
            >
              <Plus className="w-3.5 h-3.5 mr-1" /> Add short answer
            </Button>
          </div>

          {assignment.short_answers.length === 0 && (
            <p className="text-sm text-zinc-500 py-6 text-center border border-dashed border-zinc-300">
              No short-answer questions.
            </p>
          )}

          <div className="space-y-4">
            {assignment.short_answers.map((s, i) => (
              <div key={s.id} className="border border-zinc-200 p-4" data-testid={`sa-editor-${i}`}>
                <div className="flex justify-between items-start mb-2">
                  <div className="text-xs uppercase tracking-widest text-zinc-500 font-mono">Q{i + 1}</div>
                  <div className="flex items-center gap-2">
                    <Label className="text-xs">Min words</Label>
                    <Input
                      type="number"
                      min="0"
                      value={s.min_words}
                      onChange={(e) => updateSA(i, { min_words: Number(e.target.value) })}
                      className="rounded-none w-16 h-8"
                      data-testid={`sa-minwords-${i}`}
                    />
                    <Label className="text-xs">Weight</Label>
                    <Input
                      type="number"
                      min="1"
                      value={s.weight}
                      onChange={(e) => updateSA(i, { weight: Number(e.target.value) })}
                      className="rounded-none w-16 h-8"
                      data-testid={`sa-weight-${i}`}
                    />
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() =>
                        setAssignment({
                          ...assignment,
                          short_answers: assignment.short_answers.filter((_, k) => k !== i),
                        })
                      }
                      data-testid={`sa-delete-${i}`}
                    >
                      <Trash2 className="w-4 h-4 text-red-600" />
                    </Button>
                  </div>
                </div>
                <Textarea
                  placeholder="Question..."
                  value={s.question}
                  onChange={(e) => updateSA(i, { question: e.target.value })}
                  rows={2}
                  className="rounded-none"
                  data-testid={`sa-question-${i}`}
                />
              </div>
            ))}
          </div>
        </section>

        {/* Coding */}
        <section className="border border-zinc-200 p-5 mb-10">
          <div className="flex justify-between items-center mb-4">
            <h2 className="font-display font-extrabold text-lg flex items-center gap-2">
              <Code className="w-4 h-4" /> Coding task
            </h2>
            <div className="flex items-center gap-2">
              {assignment.coding ? (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setAssignment({ ...assignment, coding: null })}
                  data-testid="coding-remove"
                >
                  <Trash2 className="w-4 h-4 text-red-600" />
                </Button>
              ) : (
                <Button
                  size="sm"
                  variant="outline"
                  className="rounded-none"
                  onClick={() =>
                    setAssignment({
                      ...assignment,
                      coding: { id: "code1", prompt: "", starter_code: "", weight: 1 },
                    })
                  }
                  data-testid="coding-add"
                >
                  <Plus className="w-3.5 h-3.5 mr-1" /> Add coding task
                </Button>
              )}
            </div>
          </div>

          {assignment.coding && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Label className="w-16 text-xs">Weight</Label>
                <Input
                  type="number"
                  min="1"
                  value={assignment.coding.weight}
                  onChange={(e) =>
                    setAssignment({ ...assignment, coding: { ...assignment.coding, weight: Number(e.target.value) } })
                  }
                  className="rounded-none w-20 h-8"
                  data-testid="coding-weight"
                />
              </div>
              <div>
                <Label className="text-xs">Prompt</Label>
                <Textarea
                  value={assignment.coding.prompt}
                  onChange={(e) =>
                    setAssignment({ ...assignment, coding: { ...assignment.coding, prompt: e.target.value } })
                  }
                  rows={3}
                  className="rounded-none mt-1"
                  data-testid="coding-prompt"
                />
              </div>
              <div>
                <Label className="text-xs">Starter code</Label>
                <textarea
                  className="code-editor mt-1"
                  value={assignment.coding.starter_code}
                  onChange={(e) =>
                    setAssignment({ ...assignment, coding: { ...assignment.coding, starter_code: e.target.value } })
                  }
                  rows={8}
                  data-testid="coding-starter"
                />
              </div>
            </div>
          )}
        </section>

        <div className="sticky bottom-0 bg-white border-t border-zinc-200 py-4 -mx-6 px-6 flex justify-between items-center">
          <div className="text-xs text-zinc-500">
            Changes are not saved until you click <strong>Save assignment</strong>.
          </div>
          <div className="flex gap-2">
            <Button variant="outline" className="rounded-none" onClick={() => nav("/hr/jobs")}>Cancel</Button>
            <Button onClick={save} disabled={saving} className="bg-brand hover:opacity-90 rounded-none" data-testid="save-assignment-bottom">
              <Save className="w-4 h-4 mr-1.5" /> {saving ? "Saving..." : "Save assignment"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
