import { createContext, useContext, useEffect, useState } from "react";
import axios from "axios";
import { formatError } from "@/lib/api";

const BASE = process.env.REACT_APP_BACKEND_URL;
const API = `${BASE}/api`;
const KEY = "candidate_token";

// Independent axios instance so it never sends HR token
const capi = axios.create({ baseURL: API });
capi.interceptors.request.use((cfg) => {
  const t = localStorage.getItem(KEY);
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

const CandidateAuthContext = createContext(null);

export function CandidateAuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const t = localStorage.getItem(KEY);
    if (!t) {
      setLoading(false);
      return;
    }
    capi
      .get("/candidate/me")
      .then((r) => setUser(r.data))
      .catch(() => localStorage.removeItem(KEY))
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    try {
      const { data } = await capi.post("/candidate/login", { email, password });
      localStorage.setItem(KEY, data.token);
      setUser(data.user);
      return { ok: true };
    } catch (e) {
      return { ok: false, error: formatError(e.response?.data?.detail) || e.message };
    }
  };

  const register = async (name, email, password) => {
    try {
      const { data } = await capi.post("/candidate/register", { name, email, password });
      localStorage.setItem(KEY, data.token);
      setUser(data.user);
      return { ok: true };
    } catch (e) {
      return { ok: false, error: formatError(e.response?.data?.detail) || e.message };
    }
  };

  const logout = () => {
    localStorage.removeItem(KEY);
    setUser(null);
  };

  return (
    <CandidateAuthContext.Provider value={{ user, loading, login, register, logout, capi }}>
      {children}
    </CandidateAuthContext.Provider>
  );
}

export const useCandidateAuth = () => useContext(CandidateAuthContext);
export { capi as candidateApi };
