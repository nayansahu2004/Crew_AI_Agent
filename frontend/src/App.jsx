// File path: frontend/src/App.jsx
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AppShell } from "./components/AppShell";
import { Landing } from "./pages/Landing";
import { HowItWorks, Guide } from "./pages/HowItWorks";
import { Contact } from "./pages/Contact";
import { NotFound } from "./pages/NotFound";
import { SignIn } from "./pages/SignIn";
import { SignUp } from "./pages/SignUp";
import { Dashboard } from "./pages/Dashboard";
import { CampaignCreate } from "./pages/CampaignCreate";
import { CampaignDetail } from "./pages/CampaignDetail";
import { Settings } from "./pages/Settings";

// "/" is the front page for visitors and the campaign list for signed-in
// users.
function Home() {
  const { session, loading } = useAuth();
  if (loading) return null;
  return session ? <Navigate to="/campaigns" replace /> : <Landing />;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public */}
          <Route path="/" element={<Home />} />
          <Route path="/how-it-works" element={<HowItWorks />} />
          <Route path="/contact" element={<Contact />} />
          <Route path="/sign-in" element={<SignIn />} />
          <Route path="/sign-up" element={<SignUp />} />

          {/* Signed in */}
          <Route
            element={
              <ProtectedRoute>
                <AppShell />
              </ProtectedRoute>
            }
          >
            <Route path="/campaigns" element={<Dashboard />} />
            <Route path="/campaigns/new" element={<CampaignCreate />} />
            <Route path="/campaigns/:id" element={<CampaignDetail />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/guide" element={<Guide />} />
          </Route>

          <Route path="*" element={<NotFound />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}