export interface User {
  id: number;
  username: string;
  full_name: string;
  role: string;
}

export interface Employee {
  id: number;
  name: string;
  card_number: string;
  code: string;
  job_title: string;
  region: string;
  is_resident: boolean;
  phone: string;
  salary: number;
  total_salary: number;
  company_id: number | null;
  company_name?: string;
  employee_type: string;
  is_active: boolean;
  supervisor_id: number | null;
}

export interface Attendance {
  id: number;
  employee_id: number;
  employee_name?: string;
  date: string;
  attendance_status: string;
  late_minutes: number;
  check_in_time: string;
  check_out_time: string;
  notes: string;
}

export interface Company {
  id: number;
  name: string;
  contact_person: string;
  phone: string;
  email: string;
  address: string;
}

export interface Region {
  id: number;
  name: string;
  company_id: number;
}

export interface Location {
  id: number;
  name: string;
  region_id: number;
}

export interface Evaluation {
  id: number;
  employee_id: number;
  employee_name?: string;
  evaluation_date: string;
  score: number;
  notes: string;
}

export interface FinancialTransaction {
  id: number;
  description: string;
  amount: number;
  transaction_type: string;
  date: string;
  is_settled: boolean;
}

export interface Salary {
  id: number;
  employee_id: number;
  employee_name?: string;
  month_year: string;
  attendance_days: number;
  attendance_amount: number;
  daily_allowance_amount: number;
  overtime_amount: number;
  advance_amount: number;
  deduction_amount: number;
  penalty_amount: number;
  total_salary: number;
  is_paid: boolean;
}

export interface Contract {
  id: number;
  title: string;
  company_id: number;
  start_date: string;
  end_date: string;
  value: number;
}

export interface Invoice {
  id: number;
  invoice_number: string;
  company_id: number;
  company_name?: string;
  amount: number;
  paid_amount: number;
  remaining_amount: number;
  invoice_date: string;
  status: string;
}

export interface Supplier {
  id: number;
  name: string;
  contact_person: string;
  phone: string;
  email: string;
}

export interface SupplierInvoice {
  id: number;
  invoice_number: string;
  supplier_id: number;
  supplier_name?: string;
  amount: number;
  paid_amount: number;
  invoice_date: string;
  status: string;
}

export interface Account {
  id: number;
  code: string;
  name: string;
  account_type: string;
  parent_id: number | null;
  is_active: boolean;
  balance: number;
}

export interface JournalEntry {
  id: number;
  entry_number: string;
  date: string;
  description: string;
  debit_total: number;
  credit_total: number;
  is_posted: boolean;
}

export interface DashboardStats {
  total_employees: number;
  today_attendance: number;
  pending_transactions: number;
  pending_salaries: number;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  total?: number;
  page?: number;
  per_page?: number;
}
