import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useCandidateAuth } from "@/context/CandidateAuthContext";
import { PublicNav } from "@/components/Nav";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";

export default function CandidateLogin() {
  const { login, user } = useCandidateAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  if (user) {
    nav("/candidate/dashboard");
    return null;
  }

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    const r = await login(email, password);
    setLoading(false);
    if (r.ok) {
      toast.success("Welcome back");
      nav("/candidate/dashboard");
    } else {
      toast.error(r.error || "Login failed");
    }
  };

  return (
    <div className="min-h-screen bg-white">
      <PublicNav />
      <div className="max-w-md mx-auto px-6 py-16">
        <h1 className="font-display font-extrabold text-3xl tracking-tighter">Candidate sign in</h1>
        <p className="mt-2 text-sm text-zinc-500">
          Sign in to track your applications and take assessments.
        </p>
        <form onSubmit={submit} className="mt-8 space-y-4" data-testid="candidate-login-form">
          <div>
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="rounded-none mt-1" data-testid="candidate-login-email" />
          </div>
          <div>
            <Label htmlFor="password">Password</Label>
            <Input id="password" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className="rounded-none mt-1" data-testid="candidate-login-password" />
          </div>
          <Button type="submit" disabled={loading} className="w-full bg-brand hover:opacity-90 rounded-none" data-testid="candidate-login-submit">
            {loading ? "Signing in..." : "Sign in"}
          </Button>
        </form>
        <div className="mt-6 text-sm text-zinc-500">
          New here? <Link to="/candidate/register" className="text-brand hover:underline" data-testid="candidate-register-link">Create an account</Link>
        </div>
      </div>
    </div>
  );
}
