import { useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { CandidateAuthProvider } from "@/context/CandidateAuthContext";
import CareersList from "@/pages/CareersList";
import JobDetail from "@/pages/JobDetail";
import Apply from "@/pages/Apply";
import Exam from "@/pages/Exam";
import HRLogin from "@/pages/HRLogin";
import HRDashboard from "@/pages/HRDashboard";
import HRJobs from "@/pages/HRJobs";
import HRJobEdit from "@/pages/HRJobEdit";
import HRApplications from "@/pages/HRApplications";
import HRSubmission from "@/pages/HRSubmission";
import CandidateLogin from "@/pages/CandidateLogin";
import CandidateRegister from "@/pages/CandidateRegister";
import CandidateDashboard from "@/pages/CandidateDashboard";

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading)
    return (
      <div className="min-h-screen flex items-center justify-center text-sm text-zinc-500">
        Loading...
      </div>
    );
  if (!user) return <Navigate to="/hr/login" replace />;
  return children;
}

export default function App() {
  return (
    <div className="App">
      <AuthProvider>
        <CandidateAuthProvider>
          <BrowserRouter>
            <Toaster position="top-right" richColors />
            <Routes>
              <Route path="/" element={<CareersList />} />
              <Route path="/careers" element={<CareersList />} />
              <Route path="/careers/:jobId" element={<JobDetail />} />
              <Route path="/careers/:jobId/apply" element={<Apply />} />
              <Route path="/exam/:token" element={<Exam />} />

              {/* Candidate portal */}
              <Route path="/candidate/login" element={<CandidateLogin />} />
              <Route path="/candidate/register" element={<CandidateRegister />} />
              <Route path="/candidate/dashboard" element={<CandidateDashboard />} />

              {/* HR portal */}
              <Route path="/hr/login" element={<HRLogin />} />
              <Route path="/hr/dashboard" element={<Protected><HRDashboard /></Protected>} />
              <Route path="/hr/jobs" element={<Protected><HRJobs /></Protected>} />
              <Route path="/hr/jobs/new" element={<Protected><HRJobEdit /></Protected>} />
              <Route path="/hr/jobs/:jobId/edit" element={<Protected><HRJobEdit /></Protected>} />
              <Route path="/hr/applications" element={<Protected><HRApplications /></Protected>} />
              <Route path="/hr/submissions/:submissionId" element={<Protected><HRSubmission /></Protected>} />
            </Routes>
          </BrowserRouter>
        </CandidateAuthProvider>
      </AuthProvider>
    </div>
  );
}
