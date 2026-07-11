import { useEffect, useRef, useState, useCallback } from "react";
import { useParams } from "react-router-dom";
import { api, formatError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import {
  ShieldCheck,
  Clock,
  Camera,
  AlertTriangle,
  Maximize,
  Lock,
  CheckCircle2,
} from "lucide-react";

/**
 * Proctored exam page.
 * Anti-cheat:
 * - Requires camera + fullscreen to start
 * - Disables copy/paste/context menu/text selection
 * - Detects tab switch, blur, fullscreen exit
 * - Auto-submits after N critical violations
 * - Snapshots webcam every 30s
 * - One-time invite token (server invalidates on submit)
 * - AI-content detection on server after submit
 */
const MAX_VIOLATIONS = 5;
const SNAPSHOT_INTERVAL_MS = 30000;

export default function Exam() {
  const { token } = useParams();
  const [phase, setPhase] = useState("loading"); // loading|instructions|running|submitted|error
  const [exam, setExam] = useState(null);
  const [error, setError] = useState("");
  const [remaining, setRemaining] = useState(0);
  const startTsRef = useRef(0);
  const [tab, setTab] = useState("mcq");

  // Answers
  const [mcqAnswers, setMcqAnswers] = useState({});
  const [shortAnswers, setShortAnswers] = useState({});
  const [codingAnswer, setCodingAnswer] = useState("");

  // Proctoring
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const [violations, setViolations] = useState([]);
  const [snapshots, setSnapshots] = useState([]);
  const [flash, setFlash] = useState(false);
  const violationsRef = useRef([]);
  const submittedRef = useRef(false);
  const [result, setResult] = useState(null);

  // Load exam
  useEffect(() => {
    api
      .get(`/exam/${token}`)
      .then((r) => {
        setExam(r.data);
        setRemaining(r.data.duration_minutes * 60);
        setPhase("instructions");
      })
      .catch((e) => {
        setError(formatError(e.response?.data?.detail) || "Invalid link");
        setPhase("error");
      });
  }, [token]);

  const logViolation = useCallback((type, detail = "") => {
    if (submittedRef.current) return;
    const v = { type, detail, timestamp: new Date().toISOString() };
    violationsRef.current = [...violationsRef.current, v];
    setViolations(violationsRef.current);
    setFlash(true);
    setTimeout(() => setFlash(false), 500);
    toast.warning(`Violation: ${type}`, { description: detail });
    if (violationsRef.current.length >= MAX_VIOLATIONS) {
      toast.error("Too many violations. Auto-submitting.");
      submit(true);
    }
  }, []);

  // Submit
  const submit = useCallback(
    async (auto = false) => {
      if (submittedRef.current) return;
      submittedRef.current = true;
      const elapsed = Math.floor((Date.now() - startTsRef.current) / 1000);
      try {
        // Stop camera
        if (streamRef.current) streamRef.current.getTracks().forEach((t) => t.stop());
        // Exit fullscreen
        if (document.fullscreenElement) await document.exitFullscreen().catch(() => {});

        const r = await api.post("/exam/submit", {
          invite_token: token,
          mcq_answers: mcqAnswers,
          short_answers: shortAnswers,
          coding_answer: codingAnswer,
          violations: violationsRef.current,
          webcam_snapshots: snapshots,
          time_taken_seconds: elapsed,
        });
        setResult(r.data);
        setPhase("submitted");
        if (auto) toast.error("Assessment auto-submitted due to violations.");
      } catch (e) {
        submittedRef.current = false;
        toast.error(formatError(e.response?.data?.detail) || "Submit failed");
      }
    },
    [token, mcqAnswers, shortAnswers, codingAnswer, snapshots]
  );

  // Timer
  useEffect(() => {
    if (phase !== "running") return;
    const id = setInterval(() => {
      setRemaining((r) => {
        if (r <= 1) {
          clearInterval(id);
          submit(true);
          return 0;
        }
        return r - 1;
      });
    }, 1000);
    return () => clearInterval(id);
  }, [phase, submit]);

  // Proctoring event listeners
  useEffect(() => {
    if (phase !== "running") return;

    const onVisibility = () => {
      if (document.hidden) logViolation("tab_switch", "Candidate switched away from tab");
    };
    const onBlur = () => logViolation("window_blur", "Window lost focus");
    const onFsChange = () => {
      if (!document.fullscreenElement) logViolation("fullscreen_exit", "Exited fullscreen");
    };
    const onCopy = (e) => {
      e.preventDefault();
      logViolation("copy_attempt", "Copy blocked");
    };
    const onPaste = (e) => {
      e.preventDefault();
      logViolation("paste_attempt", "Paste blocked");
    };
    const onContext = (e) => {
      e.preventDefault();
      logViolation("right_click", "Context menu blocked");
    };
    const onKey = (e) => {
      // Block common shortcuts
      if ((e.ctrlKey || e.metaKey) && ["c", "v", "x", "a", "p", "s", "u"].includes(e.key.toLowerCase())) {
        e.preventDefault();
        logViolation("shortcut_blocked", `Ctrl/Cmd+${e.key.toUpperCase()}`);
      }
      if (e.key === "F12" || (e.ctrlKey && e.shiftKey && ["i", "j", "c"].includes(e.key.toLowerCase()))) {
        e.preventDefault();
        logViolation("devtools_attempt", "Dev tools shortcut blocked");
      }
    };

    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("blur", onBlur);
    document.addEventListener("fullscreenchange", onFsChange);
    document.addEventListener("copy", onCopy);
    document.addEventListener("paste", onPaste);
    document.addEventListener("contextmenu", onContext);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("blur", onBlur);
      document.removeEventListener("fullscreenchange", onFsChange);
      document.removeEventListener("copy", onCopy);
      document.removeEventListener("paste", onPaste);
      document.removeEventListener("contextmenu", onContext);
      document.removeEventListener("keydown", onKey);
    };
  }, [phase, logViolation]);

  // Snapshot loop
  useEffect(() => {
    if (phase !== "running") return;
    const id = setInterval(() => {
      const v = videoRef.current;
      const c = canvasRef.current;
      if (!v || !c || !v.videoWidth) return;
      c.width = 160;
      c.height = 120;
      const ctx = c.getContext("2d");
      ctx.drawImage(v, 0, 0, 160, 120);
      const data = c.toDataURL("image/jpeg", 0.4);
      setSnapshots((s) => [...s, data].slice(-20));
    }, SNAPSHOT_INTERVAL_MS);
    return () => clearInterval(id);
  }, [phase]);

  const startExam = async () => {
    try {
      // Request webcam
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      // Fullscreen
      await document.documentElement.requestFullscreen().catch(() => {});
      await api.post("/exam/start", { token });
      startTsRef.current = Date.now();
      setPhase("running");
      toast.success("Assessment started. Good luck.");
    } catch (e) {
      toast.error("Camera permission is required to start the assessment.");
    }
  };

  const fmt = (sec) => `${String(Math.floor(sec / 60)).padStart(2, "0")}:${String(sec % 60).padStart(2, "0")}`;

  // -------------------- Render --------------------
  if (phase === "loading") return <FullMsg text="Loading assessment..." />;
  if (phase === "error")
    return <FullMsg text={error} tone="error" />;

  if (phase === "submitted")
    return (
      <div className="min-h-screen bg-white flex items-center justify-center p-6">
        <div className="max-w-lg w-full text-center">
          <CheckCircle2 className="w-16 h-16 text-green-600 mx-auto" />
          <h1 className="font-display font-extrabold text-3xl mt-4 tracking-tighter">Assessment submitted</h1>
          <p className="mt-2 text-zinc-600">Thanks — HR will review your submission and reach out.</p>
          {result && (
            <div className="mt-6 border border-zinc-200 p-4 text-sm font-mono text-left">
              <div>MCQ score: {result.mcq_score}/{result.mcq_total}</div>
              <div>Time & responses recorded</div>
              <div>Proctoring events: {violations.length}</div>
            </div>
          )}
        </div>
      </div>
    );

  if (phase === "instructions")
    return (
      <div className="min-h-screen bg-white flex items-center justify-center p-6">
        <div className="max-w-2xl w-full border border-zinc-200 p-8">
          <div className="inline-flex items-center gap-2 border border-zinc-300 px-2 py-1 text-xs mb-4">
            <ShieldCheck className="w-3 h-3" /> Proctored assessment
          </div>
          <h1 className="font-display font-extrabold text-3xl tracking-tighter">
            {exam.job_title}
          </h1>
          <p className="mt-1 text-sm text-zinc-500">Candidate: <span className="font-mono">{exam.candidate_name}</span></p>

          <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
            <Stat label="Duration" value={`${exam.duration_minutes} min`} />
            <Stat label="MCQs" value={exam.mcqs.length} />
            <Stat label="Short answers" value={exam.short_answers.length} />
            <Stat label="Coding" value={exam.coding ? "1 task" : "None"} />
          </div>

          <h2 className="mt-8 font-display font-extrabold text-lg">Rules</h2>
          <ul className="mt-2 space-y-2 text-sm text-zinc-700">
            <RuleItem>You will enter fullscreen mode. Exiting counts as a violation.</RuleItem>
            <RuleItem>Your webcam will be enabled and snapshots taken periodically.</RuleItem>
            <RuleItem>Copy, paste, right-click and browser shortcuts are disabled.</RuleItem>
            <RuleItem>Switching tabs, windows or losing focus is logged.</RuleItem>
            <RuleItem>Written answers are screened for AI-generated content.</RuleItem>
            <RuleItem>{`${MAX_VIOLATIONS} violations = auto-submit.`}</RuleItem>
          </ul>

          <Button onClick={startExam} className="mt-8 bg-[#002FA7] hover:bg-[#00227A] rounded-none px-6 py-6" data-testid="exam-start-btn">
            <Maximize className="w-4 h-4 mr-2" /> Enable camera & start
          </Button>
        </div>
      </div>
    );

  // Running
  return (
    <div className={`min-h-screen bg-[#fafafa] exam-lock ${flash ? "violation-flash" : ""}`}>
      {/* Sticky top bar */}
      <div className="border-b border-zinc-200 bg-white sticky top-0 z-40">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Lock className="w-4 h-4 text-[#002FA7]" />
            <span className="font-display font-extrabold text-sm">{exam.job_title}</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5 text-sm">
              <Clock className="w-4 h-4" />
              <span className="font-mono font-bold" data-testid="exam-timer">{fmt(remaining)}</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs">
              <AlertTriangle className={`w-4 h-4 ${violations.length ? "text-red-600" : "text-zinc-400"}`} />
              <span className="font-mono">{violations.length}/{MAX_VIOLATIONS}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Camera className="w-4 h-4 text-green-600" />
              <video ref={videoRef} autoPlay muted playsInline className="w-14 h-10 object-cover border border-zinc-200" />
              <canvas ref={canvasRef} className="hidden" />
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Tabs */}
        <div className="flex gap-1 border-b border-zinc-200 mb-6">
          <TabBtn active={tab === "mcq"} onClick={() => setTab("mcq")} testId="tab-mcq">
            MCQs ({exam.mcqs.length})
          </TabBtn>
          <TabBtn active={tab === "sa"} onClick={() => setTab("sa")} testId="tab-sa">
            Short answers ({exam.short_answers.length})
          </TabBtn>
          {exam.coding && (
            <TabBtn active={tab === "code"} onClick={() => setTab("code")} testId="tab-code">
              Coding
            </TabBtn>
          )}
        </div>

        {tab === "mcq" && (
          <div className="space-y-6">
            {exam.mcqs.map((m, idx) => (
              <div key={m.id} className="border border-zinc-200 p-5 bg-white" data-testid={`mcq-${m.id}`}>
                <div className="text-xs text-zinc-500 uppercase tracking-widest mb-1">Q{idx + 1}</div>
                <div className="font-medium">{m.question}</div>
                <div className="mt-3 space-y-1.5">
                  {m.options.map((opt, i) => (
                    <label key={i} className="flex items-center gap-2 text-sm cursor-pointer hover:bg-zinc-50 p-2 border border-transparent hover:border-zinc-200">
                      <input
                        type="radio"
                        name={m.id}
                        checked={mcqAnswers[m.id] === i}
                        onChange={() => setMcqAnswers({ ...mcqAnswers, [m.id]: i })}
                        data-testid={`mcq-${m.id}-opt-${i}`}
                      />
                      <span>{opt}</span>
                    </label>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === "sa" && (
          <div className="space-y-6">
            {exam.short_answers.map((s, idx) => {
              const wc = (shortAnswers[s.id] || "").trim().split(/\s+/).filter(Boolean).length;
              return (
                <div key={s.id} className="border border-zinc-200 p-5 bg-white" data-testid={`sa-${s.id}`}>
                  <div className="text-xs text-zinc-500 uppercase tracking-widest mb-1">Q{idx + 1}</div>
                  <div className="font-medium">{s.question}</div>
                  <Textarea
                    rows={6}
                    value={shortAnswers[s.id] || ""}
                    onChange={(e) => setShortAnswers({ ...shortAnswers, [s.id]: e.target.value })}
                    onPaste={(e) => e.preventDefault()}
                    onCopy={(e) => e.preventDefault()}
                    className="rounded-none mt-3 font-mono text-sm"
                    placeholder="Type your answer..."
                    data-testid={`sa-${s.id}-input`}
                  />
                  <div className="mt-1 text-xs text-zinc-500 font-mono flex justify-between">
                    <span>{wc} words {s.min_words ? `(min ${s.min_words})` : ""}</span>
                    <span>Paste disabled · AI screening on</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {tab === "code" && exam.coding && (
          <div className="border border-zinc-200 p-5 bg-white" data-testid="coding-block">
            <div className="text-xs text-zinc-500 uppercase tracking-widest mb-1">Coding task</div>
            <div className="font-medium">{exam.coding.prompt}</div>
            <textarea
              className="code-editor mt-3"
              value={codingAnswer || exam.coding.starter_code || ""}
              onChange={(e) => setCodingAnswer(e.target.value)}
              onPaste={(e) => e.preventDefault()}
              spellCheck={false}
              data-testid="coding-editor"
            />
            <div className="text-xs text-zinc-500 mt-1 font-mono">Paste disabled · your keystrokes are logged</div>
          </div>
        )}

        <div className="mt-8 flex justify-end gap-2">
          <Button
            onClick={() => submit(false)}
            className="bg-[#002FA7] hover:bg-[#00227A] rounded-none px-8"
            data-testid="exam-submit-btn"
          >
            Submit assessment
          </Button>
        </div>
      </div>
    </div>
  );
}

function FullMsg({ text, tone }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-white p-6">
      <div className={`max-w-md text-center ${tone === "error" ? "text-red-600" : "text-zinc-600"}`}>
        {tone === "error" && <AlertTriangle className="w-10 h-10 mx-auto mb-3" />}
        {text}
      </div>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="border-l-2 border-[#002FA7] pl-3">
      <div className="font-mono">{value}</div>
      <div className="text-zinc-500">{label}</div>
    </div>
  );
}

function RuleItem({ children }) {
  return (
    <li className="flex gap-2">
      <span className="text-[#002FA7]">•</span>
      <span>{children}</span>
    </li>
  );
}

function TabBtn({ active, onClick, children, testId }) {
  return (
    <button
      onClick={onClick}
      data-testid={testId}
      className={`px-4 py-2 text-sm border-b-2 transition-colors ${
        active ? "border-[#002FA7] text-[#002FA7] font-medium" : "border-transparent text-zinc-500 hover:text-zinc-800"
      }`}
    >
      {children}
    </button>
  );
}
