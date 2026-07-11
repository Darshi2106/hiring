import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Briefcase, LogOut, LayoutDashboard, Users } from "lucide-react";

export function PublicNav() {
  return (
    <header className="border-b border-zinc-200 bg-white sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <Link to="/careers" data-testid="nav-home-link" className="flex items-center gap-2 group">
          <div className="w-8 h-8 bg-[#002FA7] flex items-center justify-center">
            <span className="text-white font-display font-extrabold text-lg leading-none">C</span>
          </div>
          <span className="font-display font-extrabold text-xl tracking-tight">CohortData</span>
          <span className="text-xs text-zinc-500 border-l border-zinc-300 pl-2 ml-1">Careers</span>
        </Link>
        <div className="flex items-center gap-3">
          <Link
            to="/careers"
            className="text-sm text-zinc-700 hover:text-[#002FA7] transition-colors"
            data-testid="nav-openings-link"
          >
            Open Roles
          </Link>
          <Link to="/hr/login" data-testid="nav-hr-link">
            <Button variant="outline" size="sm" className="border-zinc-300">
              HR Login
            </Button>
          </Link>
        </div>
      </div>
    </header>
  );
}

export function HRNav() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  return (
    <header className="border-b border-zinc-200 bg-white sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
        <Link to="/hr/dashboard" className="flex items-center gap-2" data-testid="hr-nav-home">
          <div className="w-8 h-8 bg-[#002FA7] flex items-center justify-center">
            <span className="text-white font-display font-extrabold text-lg leading-none">C</span>
          </div>
          <span className="font-display font-extrabold text-lg">CohortData HR</span>
        </Link>
        <nav className="flex items-center gap-1">
          <Link to="/hr/dashboard" data-testid="hr-nav-dashboard">
            <Button variant="ghost" size="sm">
              <LayoutDashboard className="w-4 h-4 mr-1.5" /> Dashboard
            </Button>
          </Link>
          <Link to="/hr/jobs" data-testid="hr-nav-jobs">
            <Button variant="ghost" size="sm">
              <Briefcase className="w-4 h-4 mr-1.5" /> Jobs
            </Button>
          </Link>
          <Link to="/hr/applications" data-testid="hr-nav-applications">
            <Button variant="ghost" size="sm">
              <Users className="w-4 h-4 mr-1.5" /> Applications
            </Button>
          </Link>
          <div className="w-px h-6 bg-zinc-200 mx-2" />
          <span className="text-xs text-zinc-500 hidden md:inline">{user?.email}</span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              logout();
              navigate("/hr/login");
            }}
            data-testid="hr-nav-logout"
          >
            <LogOut className="w-4 h-4 mr-1.5" /> Logout
          </Button>
        </nav>
      </div>
    </header>
  );
}
