import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Lock } from "lucide-react";

export default function HRLogin() {
  const { login, user } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("hr@cohortdata.com");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  if (user) {
    nav("/hr/dashboard");
    return null;
  }

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    const r = await login(email, password);
    setLoading(false);
    if (r.ok) {
      toast.success("Welcome back");
      nav("/hr/dashboard");
    } else {
      toast.error(r.error || "Login failed");
    }
  };

  return (
    <div className="min-h-screen bg-white flex">
      {/* left panel */}
      <div className="hidden md:flex md:w-1/2 bg-[#103e43] text-white p-12 flex-col justify-between">
        <Link to="/" className="flex items-center gap-2">
          <img src="/logo/cohortdata-logo.png" alt="CohortData" className="h-8 w-auto bg-white p-1" />
          <span className="text-xs text-zinc-400 border-l border-zinc-600 pl-2">HR Portal</span>
        </Link>
        <div>
          <div className="text-xs uppercase tracking-widest text-zinc-400 mb-3">Hiring workspace</div>
          <h1 className="font-display font-extrabold text-5xl tracking-tighter leading-tight">
            Ship better hires,{" "}
            <span className="text-[#f4b932]">faster.</span>
          </h1>
          <p className="mt-4 text-zinc-400 max-w-md">
            Manage openings, review proctored assessments, and screen AI-generated answers —
            all in one workspace.
          </p>
        </div>
        <div className="text-xs text-zinc-500 font-mono">v1.0 · proctored & AI-guarded</div>
      </div>

      {/* right form */}
      <div className="w-full md:w-1/2 flex items-center justify-center p-6">
        <div className="w-full max-w-md">
          <div className="inline-flex items-center gap-2 border border-zinc-300 px-3 py-1 text-xs mb-6">
            <Lock className="w-3 h-3" /> HR sign-in
          </div>
          <h2 className="font-display font-extrabold text-3xl tracking-tighter">Sign in to HR portal</h2>
          <p className="mt-2 text-sm text-zinc-500">Use your admin credentials to continue.</p>

          <form onSubmit={submit} className="mt-8 space-y-4" data-testid="hr-login-form">
            <div>
              <Label htmlFor="email">Work email</Label>
              <Input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="rounded-none mt-1" data-testid="hr-login-email" />
            </div>
            <div>
              <Label htmlFor="password">Password</Label>
              <Input id="password" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className="rounded-none mt-1" data-testid="hr-login-password" />
            </div>
            <Button type="submit" disabled={loading} className="w-full bg-[#0f9394] hover:bg-[#0b7676] rounded-none" data-testid="hr-login-submit">
              {loading ? "Signing in..." : "Sign in"}
            </Button>
          </form>

          <div className="mt-6 text-xs text-zinc-400">
            Not HR? <Link to="/careers" className="text-[#0f9394] hover:underline">Go to careers page</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
