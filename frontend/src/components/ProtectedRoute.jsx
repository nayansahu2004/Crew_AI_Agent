// File path: frontend/src/components/ProtectedRoute.jsx
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function ProtectedRoute({ children }) {
  const { session, loading } = useAuth();

  if (loading) {
    // Avoids a flash-redirect to /sign-in while the initial session
    // check is still in flight on page load/refresh.
    return null;
  }

  if (!session) {
    return <Navigate to="/sign-in" replace />;
  }

  return children;
}