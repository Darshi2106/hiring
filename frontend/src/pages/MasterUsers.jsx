import { useEffect, useState } from "react";
import { HRNav } from "@/components/Nav";
import { api, formatError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { UserPlus, Power, Shield } from "lucide-react";

export default function MasterUsers() {
  const { user, loading } = useAuth();
  const nav = useNavigate();
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [creating, setCreating] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (loading) return;
    if (!user || user.role !== "master_admin") {
      nav("/hr/dashboard");
      return;
    }
    load();
    setReady(true);
    // eslint-disable-next-line
  }, [user, loading]);

  const load = () => api.get("/master/users").then((r) => setUsers(r.data));

  const create = async (e) => {
    e.preventDefault();
    setCreating(true);
    try {
      await api.post("/master/users", form);
      toast.success("HR user created");
      setForm({ name: "", email: "", password: "" });
      load();
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail) || err.message);
    } finally {
      setCreating(false);
    }
  };

  const toggle = async (id) => {
    try {
      await api.post(`/master/users/${id}/toggle`);
      toast.success("Updated");
      load();
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail) || err.message);
    }
  };

  if (!ready) return null;

  return (
    <div className="min-h-screen bg-white">
      <HRNav />
      <div className="max-w-5xl mx-auto px-6 py-10">
        <div className="mb-8">
          <div className="text-xs uppercase tracking-widest text-zinc-500 flex items-center gap-1">
            <Shield className="w-3 h-3" /> Master admin
          </div>
          <h1 className="font-display font-extrabold text-4xl tracking-tighter">HR user management</h1>
          <p className="mt-2 text-sm text-zinc-500">
            Create and activate/deactivate HR accounts. All invite emails are CC'd to your inbox.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {/* Create form */}
          <form
            onSubmit={create}
            className="border border-zinc-200 p-5 space-y-3"
            data-testid="master-create-form"
          >
            <div className="flex items-center gap-2 mb-2">
              <UserPlus className="w-4 h-4 text-brand" />
              <h2 className="font-display font-extrabold text-lg">New HR user</h2>
            </div>
            <div>
              <Label>Name</Label>
              <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="rounded-none mt-1" data-testid="master-new-name" />
            </div>
            <div>
              <Label>Email</Label>
              <Input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="rounded-none mt-1" data-testid="master-new-email" />
            </div>
            <div>
              <Label>Temporary password (min 6)</Label>
              <Input required minLength={6} type="text" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className="rounded-none mt-1 font-mono" data-testid="master-new-password" />
            </div>
            <Button type="submit" disabled={creating} className="w-full bg-brand rounded-none" data-testid="master-create-btn">
              {creating ? "Creating..." : "Create HR user"}
            </Button>
          </form>

          {/* List */}
          <div className="md:col-span-2 border border-zinc-200">
            <div className="bg-zinc-50 border-b border-zinc-200 px-4 py-3 flex justify-between items-center">
              <h2 className="font-display font-extrabold text-lg">All users</h2>
              <span className="text-xs font-mono text-zinc-500">{users.length}</span>
            </div>
            <div className="divide-y divide-zinc-100">
              {users.map((u) => (
                <div key={u.id} className="px-4 py-3 flex justify-between items-center" data-testid={`master-user-${u.id}`}>
                  <div>
                    <div className="font-medium text-sm flex items-center gap-2">
                      {u.name}
                      {u.role === "master_admin" && (
                        <span className="text-[10px] uppercase font-mono border border-brand text-brand px-1.5 py-0.5">
                          Master
                        </span>
                      )}
                      {!u.is_active && (
                        <span className="text-[10px] uppercase font-mono border border-red-300 text-red-700 bg-red-50 px-1.5 py-0.5">
                          Deactivated
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-zinc-500 font-mono">{u.email}</div>
                  </div>
                  {u.role !== "master_admin" && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="rounded-none"
                      onClick={() => toggle(u.id)}
                      data-testid={`toggle-${u.id}`}
                    >
                      <Power className="w-3.5 h-3.5 mr-1" />
                      {u.is_active ? "Deactivate" : "Activate"}
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
