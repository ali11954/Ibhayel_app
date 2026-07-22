import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import Layout from '@/components/Layout';
import LoginPage from '@/pages/LoginPage';
import WelcomePage from '@/pages/WelcomePage';
import DashboardPage from '@/pages/DashboardPage';
import EmployeesPage from '@/pages/EmployeesPage';
import AttendancePage from '@/pages/AttendancePage';
import CompaniesPage from '@/pages/CompaniesPage';
import EvaluationsPage from '@/pages/EvaluationsPage';
import FinancialPage from '@/pages/FinancialPage';
import AccountsPage from '@/pages/AccountsPage';
import SuppliersPage from '@/pages/SuppliersPage';
import ReportsPage from '@/pages/ReportsPage';
import SettingsPage from '@/pages/SettingsPage';
import UsersPage from '@/pages/UsersPage';
import ContractsPage from '@/pages/ContractsPage';
import InvoicesPage from '@/pages/InvoicesPage';
import WorkPlansPage from '@/pages/WorkPlansPage';
import SalariesPage from '@/pages/SalariesPage';
import SupplierInvoicesPage from '@/pages/SupplierInvoicesPage';
import PeriodsPage from '@/pages/PeriodsPage';
import LeavesPage from '@/pages/LeavesPage';
import EmployeePortalPage from '@/pages/EmployeePortalPage';
import AttendanceGridPage from '@/pages/AttendanceGridPage';
import AttendanceReportPage from '@/pages/AttendanceReportPage';
import ProfilePage from '@/pages/ProfilePage';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const [checking, setChecking] = useState(true);
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    fetch('/api/auth/me', { credentials: 'include' })
      .then((res) => {
        if (res.ok) {
          setAuthed(true);
          localStorage.setItem('token', 'session');
        } else {
          localStorage.removeItem('token');
          setAuthed(false);
        }
      })
      .catch(() => {
        localStorage.removeItem('token');
        setAuthed(false);
      })
      .finally(() => setChecking(false));
  }, []);

  if (checking) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="w-8 h-8 border-3 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (!authed) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<WelcomePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Layout><DashboardPage /></Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/employees"
          element={
            <ProtectedRoute>
              <Layout><EmployeesPage /></Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/attendance"
          element={
            <ProtectedRoute>
              <Layout><AttendancePage /></Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/companies"
          element={
            <ProtectedRoute>
              <Layout><CompaniesPage /></Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/contracts"
          element={
            <ProtectedRoute>
              <Layout><ContractsPage /></Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/invoices"
          element={
            <ProtectedRoute>
              <Layout><InvoicesPage /></Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/evaluations"
          element={
            <ProtectedRoute>
              <Layout><EvaluationsPage /></Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/work-plans"
          element={
            <ProtectedRoute>
              <Layout><WorkPlansPage /></Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/salaries"
          element={
            <ProtectedRoute>
              <Layout><SalariesPage /></Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/financial"
          element={
            <ProtectedRoute>
              <Layout><FinancialPage /></Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/accounts"
          element={
            <ProtectedRoute>
              <Layout><AccountsPage /></Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/suppliers"
          element={
            <ProtectedRoute>
              <Layout><SuppliersPage /></Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/supplier-invoices"
          element={
            <ProtectedRoute>
              <Layout><SupplierInvoicesPage /></Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/periods"
          element={
            <ProtectedRoute>
              <Layout><PeriodsPage /></Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/leaves"
          element={
            <ProtectedRoute>
              <Layout><LeavesPage /></Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/my-portal"
          element={
            <ProtectedRoute>
              <Layout><EmployeePortalPage /></Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/reports"
          element={
            <ProtectedRoute>
              <Layout><ReportsPage /></Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/users"
          element={
            <ProtectedRoute>
              <Layout><UsersPage /></Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <Layout><SettingsPage /></Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/attendance-grid"
          element={
            <ProtectedRoute>
              <Layout><AttendanceGridPage /></Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/attendance-report"
          element={
            <ProtectedRoute>
              <Layout><AttendanceReportPage /></Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/profile"
          element={
            <ProtectedRoute>
              <Layout><ProfilePage /></Layout>
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
