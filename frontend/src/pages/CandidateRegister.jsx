import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useCandidateAuth } from "@/context/CandidateAuthContext";
import { PublicNav } from "@/components/Nav";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";

export default function CandidateRegister() {
  const { register, user } = useCandidateAuth();
  const nav = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [loading, setLoading] = useState(false);

  if (user) {
    nav("/candidate/dashboard");
    return null;
  }

  const upd = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    const r = await register(form.name, form.email, form.password);
    setLoading(false);
    if (r.ok) {
      toast.success("Account created");
      nav("/candidate/dashboard");
    } else {
      toast.error(r.error || "Registration failed");
    }
  };

  return (
    <div className="min-h-screen bg-white">
      <PublicNav />
      <div className="max-w-md mx-auto px-6 py-16">
        <h1 className="font-display font-extrabold text-3xl tracking-tighter">Create your account</h1>
        <p className="mt-2 text-sm text-zinc-500">
          One account · apply to multiple roles · track your assessments.
        </p>
        <form onSubmit={submit} className="mt-8 space-y-4" data-testid="candidate-register-form">
          <div>
            <Label>Full name</Label>
            <Input required value={form.name} onChange={upd("name")} className="rounded-none mt-1" data-testid="candidate-register-name" />
          </div>
          <div>
            <Label>Email</Label>
            <Input type="email" required value={form.email} onChange={upd("email")} className="rounded-none mt-1" data-testid="candidate-register-email" />
          </div>
          <div>
            <Label>Password (min 6 chars)</Label>
            <Input type="password" required minLength={6} value={form.password} onChange={upd("password")} className="rounded-none mt-1" data-testid="candidate-register-password" />
          </div>
          <Button type="submit" disabled={loading} className="w-full bg-brand hover:opacity-90 rounded-none" data-testid="candidate-register-submit">
            {loading ? "Creating..." : "Create account"}
          </Button>
        </form>
        <div className="mt-6 text-sm text-zinc-500">
          Already have an account? <Link to="/candidate/login" className="text-brand hover:underline">Sign in</Link>
        </div>
      </div>
    </div>
  );
}
