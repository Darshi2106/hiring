import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { useCandidateAuth } from "@/context/CandidateAuthContext";
import { Button } from "@/components/ui/button";
import { LogOut, LayoutDashboard, Briefcase, Users, User, Shield } from "lucide-react";

const LOGO_URL = "/logo/cohortdata-logo.png";

function Logo({ variant = "default" }) {
  return (
    <div className="flex items-center gap-2">
      <img src={LOGO_URL} alt="CohortData" className="h-8 w-auto" />
      <span
        className={`text-xs border-l pl-2 ml-1 ${
          variant === "hr"
            ? "text-zinc-500 border-zinc-300"
            : "text-zinc-500 border-zinc-300"
        }`}
      >
        {variant === "hr" ? "HR" : "Careers"}
      </span>
    </div>
  );
}

export function PublicNav() {
  const { user: candidate, logout: candidateLogout } = useCandidateAuth() || {};
  const navigate = useNavigate();

  return (
    <header className="border-b border-zinc-200 bg-white sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
        <Link to="/careers" data-testid="nav-home-link">
          <Logo />
        </Link>
        <div className="flex items-center gap-2">
          <Link
            to="/careers"
            className="text-sm text-zinc-700 hover:text-brand transition-colors px-3"
            data-testid="nav-openings-link"
          >
            Open Roles
          </Link>
          {candidate ? (
            <>
              <Link to="/candidate/dashboard" data-testid="nav-candidate-dashboard">
                <Button variant="ghost" size="sm">
                  <User className="w-4 h-4 mr-1.5" />
                  {candidate.name?.split(" ")[0] || "Account"}
                </Button>
              </Link>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  candidateLogout();
                  navigate("/careers");
                }}
                data-testid="nav-candidate-logout"
              >
                <LogOut className="w-4 h-4" />
              </Button>
            </>
          ) : (
            <>
              <Link to="/candidate/login" data-testid="nav-candidate-login">
                <Button variant="ghost" size="sm">
                  Candidate sign in
                </Button>
              </Link>
              <Link to="/hr/login" data-testid="nav-hr-link">
                <Button variant="outline" size="sm" className="border-zinc-300 rounded-none">
                  HR Login
                </Button>
              </Link>
            </>
          )}
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
        <Link to="/hr/dashboard" data-testid="hr-nav-home">
          <Logo variant="hr" />
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
          {user?.role === "master_admin" && (
            <Link to="/hr/master/users" data-testid="hr-nav-master">
              <Button variant="ghost" size="sm">
                <Shield className="w-4 h-4 mr-1.5" /> Users
              </Button>
            </Link>
          )}
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
