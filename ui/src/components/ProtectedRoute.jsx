import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { getToken } from "../api";

/**
 * A wrapper component for routes that require authentication.
 * If the user is not authenticated, it redirects them to the login page
 * while preserving the intended destination in the state.
 */
export default function ProtectedRoute({ children }) {
    const token = getToken();
    const location = useLocation();

    if (!token) {
        // Redirect to login, but save the current location they were trying to access
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    return children;
}
