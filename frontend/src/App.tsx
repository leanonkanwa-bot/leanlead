import { BrowserRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Onboarding from "./pages/Onboarding";
import Dashboard from "./pages/Dashboard";
import Settings from "./pages/Settings";
import VerifyEmail from "./pages/VerifyEmail";
import Admin from "./pages/Admin";
import ReportButton from "./components/ReportButton";

function Guard({ children }: { children: React.ReactNode }) {
  return localStorage.getItem("ll_token") ? <>{children}</> : <Navigate to="/login" replace />;
}

function AuthedLayout() {
  return (
    <>
      <Outlet />
      <ReportButton />
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/verify-email" element={<VerifyEmail />} />
        <Route path="/admin" element={<Admin />} />
        <Route element={<Guard><AuthedLayout /></Guard>}>
          <Route path="/onboarding" element={<Onboarding />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
