import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import Layout from '@/components/Layout';
import LoginPage from '@/pages/LoginPage';
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
  return <Layout>{children}</Layout>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <Routes>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/employees" element={<EmployeesPage />} />
                <Route path="/attendance" element={<AttendancePage />} />
                <Route path="/companies" element={<CompaniesPage />} />
                <Route path="/contracts" element={<ContractsPage />} />
                <Route path="/invoices" element={<InvoicesPage />} />
                <Route path="/evaluations" element={<EvaluationsPage />} />
                <Route path="/work-plans" element={<WorkPlansPage />} />
                <Route path="/salaries" element={<SalariesPage />} />
                <Route path="/financial" element={<FinancialPage />} />
                <Route path="/accounts" element={<AccountsPage />} />
                <Route path="/suppliers" element={<SuppliersPage />} />
                <Route path="/supplier-invoices" element={<SupplierInvoicesPage />} />
                <Route path="/periods" element={<PeriodsPage />} />
                <Route path="/leaves" element={<LeavesPage />} />
                <Route path="/my-portal" element={<EmployeePortalPage />} />
                <Route path="/reports" element={<ReportsPage />} />
                <Route path="/users" element={<UsersPage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
