import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users, CalendarCheck, Building2, Star, DollarSign,
  BookOpen, Truck, BarChart3, FileCheck, FileText,
  UserCog, Settings, TrendingUp, TrendingDown, Clock,
  Leaf, Activity, ArrowUpRight, ArrowDownLeft, Briefcase,
  ClipboardList, CheckCircle2, AlertCircle, Loader2,
  Wallet, Target, Zap, Award, AlertTriangle, Info,
  ArrowRightLeft, Receipt, Building, BriefcaseBusiness
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend, AreaChart, Area, RadialBarChart, RadialBar, LineChart, Line } from 'recharts';
import api from '@/api/client';
import { formatNum, formatCurrency } from '@/lib/utils';

const COLORS = ['#10b981', '#f59e0b', '#ef4444', '#6366f1', '#8b5cf6', '#ec4899', '#06b6d4'];

export default function DashboardPage() {
  const [stats, setStats] = useState<any>(null);
  const [reportEmployees, setReportEmployees] = useState<any>(null);
  const [reportAttendance, setReportAttendance] = useState<any>(null);
  const [reportEvaluations, setReportEvaluations] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<any>(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.get('/auth/me').then(res => {
      const u = res.data.data;
      setUser(u);
      if (u?.role === 'employee') {
        navigate('/my-portal', { replace: true });
        return;
      }
    }).catch(() => {});

    Promise.all([
      api.get('/dashboard/stats'),
      api.get('/reports/employees'),
      api.get('/reports/attendance'),
      api.get('/reports/evaluations').catch(() => ({ data: { data: null } })),
    ]).then(([sRes, eRes, aRes, evRes]) => {
      setStats(sRes.data.data);
      setReportEmployees(eRes.data.data);
      setReportAttendance(aRes.data.data);
      setReportEvaluations(evRes.data.data);
    }).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="flex items-center justify-center h-[60vh]">
      <div className="text-center">
        <div className="w-12 h-12 border-4 border-primary-500/20 border-t-primary-500 rounded-full animate-spin mx-auto" />
        <p className="text-gray-400 mt-4 text-sm">جاري التحميل...</p>
      </div>
    </div>
  );

  const attendanceRate = stats?.today_attendance
    ? Math.round((stats.today_attendance / (stats.total_employees || 1)) * 100)
    : 0;

  const workPlanProgress = stats?.work_plan_tasks_total
    ? Math.round((stats.work_plan_tasks_completed / stats.work_plan_tasks_total) * 100)
    : 0;

  return (
    <div className="space-y-6">
      {/* Welcome Header */}
      <div className="bg-gradient-to-l from-primary-600 via-primary-500 to-primary-600 rounded-2xl p-8 text-white relative overflow-hidden">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute -top-20 -left-20 w-64 h-64 bg-white rounded-full blur-3xl" />
          <div className="absolute -bottom-20 -right-20 w-48 h-48 bg-white rounded-full blur-3xl" />
        </div>
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-2">
            <Leaf className="w-8 h-8" />
            <h1 className="text-2xl font-bold">طلعت هائل</h1>
          </div>
          <p className="text-primary-100 text-lg">نظام إدارة الأعمال الزراعية</p>
        </div>
      </div>

      {/* Primary Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'الموظفين النشطين', value: stats?.total_employees || 0, icon: Users, color: 'text-blue-600', bg: 'bg-blue-50', path: '/employees' },
          { label: 'حضور اليوم', value: `${stats?.today_attendance || 0} / ${stats?.total_employees || 0}`, sub: `${attendanceRate}% نسبة الحضور`, icon: CalendarCheck, color: 'text-green-600', bg: 'bg-green-50', path: '/attendance' },
          { label: 'الرواتب المعلقة', value: stats?.pending_salaries || 0, icon: DollarSign, color: 'text-amber-600', bg: 'bg-amber-50', path: '/salaries' },
          { label: 'خطط العمل', value: stats?.work_plans_total || 0, sub: `${workPlanProgress}% مكتمل`, icon: ClipboardList, color: 'text-purple-600', bg: 'bg-purple-50', path: '/work-plans' },
        ].map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className={`${stat.bg} rounded-2xl p-5 border border-gray-100 hover:shadow-md transition-shadow cursor-pointer`} onClick={() => navigate(stat.path)}>
              <div className="flex items-center justify-between mb-3">
                <div className={`w-10 h-10 rounded-xl ${stat.bg} flex items-center justify-center`}>
                  <Icon className={`w-5 h-5 ${stat.color}`} />
                </div>
              </div>
              <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
              <p className="text-sm text-gray-500 mt-1">{stat.label}</p>
              {stat.sub && <p className={`text-xs mt-1 ${stat.color}`}>{stat.sub}</p>}
            </div>
          );
        })}
      </div>

      {/* Secondary Stats Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'الشركات', value: stats?.total_companies || 0, icon: Building2, color: 'text-emerald-600', bg: 'bg-emerald-50', path: '/companies' },
          { label: 'الموردين', value: stats?.total_suppliers || 0, icon: Truck, color: 'text-rose-600', bg: 'bg-rose-50', path: '/suppliers' },
          { label: 'المعاملات المعلقة', value: stats?.pending_transactions || 0, icon: Activity, color: 'text-indigo-600', bg: 'bg-indigo-50', path: '/financial' },
          { label: 'الرواتب المدفوعة', value: formatNum(stats?.total_salaries_paid || 0) + ' ر.ي', icon: CheckCircle2, color: 'text-green-600', bg: 'bg-green-50', path: '/salaries' },
        ].map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className={`${stat.bg} rounded-2xl p-4 border border-gray-100 hover:shadow-md transition-shadow cursor-pointer`} onClick={() => navigate(stat.path)}>
              <div className="flex items-center gap-3 mb-2">
                <div className={`w-9 h-9 rounded-xl ${stat.bg} flex items-center justify-center`}>
                  <Icon className={`w-4.5 h-4.5 ${stat.color}`} />
                </div>
                <p className="text-xl font-bold text-gray-900">{stat.value}</p>
              </div>
              <p className="text-xs text-gray-500">{stat.label}</p>
            </div>
          );
        })}
      </div>

      {/* Financial Overview */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md transition-shadow">
        <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
          <Wallet className="w-5 h-5 text-primary-500" />
          نظرة مالية شاملة
        </h3>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-green-50 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <ArrowUpRight className="w-4 h-4 text-green-600" />
              <span className="text-xs text-green-600 font-medium">الإيرادات</span>
            </div>
            <p className="text-xl font-bold text-green-700">{formatNum(stats?.total_income || 0)} ر.ي</p>
          </div>
          <div className="bg-red-50 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <ArrowDownLeft className="w-4 h-4 text-red-600" />
              <span className="text-xs text-red-600 font-medium">المصروفات</span>
            </div>
            <p className="text-xl font-bold text-red-700">{formatNum(stats?.total_expense || 0)} ر.ي</p>
          </div>
          <div className={`${(stats?.balance || 0) >= 0 ? 'bg-blue-50' : 'bg-amber-50'} rounded-xl p-4`}>
            <div className="flex items-center gap-2 mb-2">
              <Target className={`w-4 h-4 ${(stats?.balance || 0) >= 0 ? 'text-blue-600' : 'text-amber-600'}`} />
              <span className={`text-xs ${(stats?.balance || 0) >= 0 ? 'text-blue-600' : 'text-amber-600'} font-medium`}>صافي الربح</span>
            </div>
            <p className={`text-xl font-bold ${(stats?.balance || 0) >= 0 ? 'text-blue-700' : 'text-amber-700'}`}>{formatNum(stats?.balance || 0)} ر.ي</p>
          </div>
          <div className="bg-purple-50 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <Receipt className="w-4 h-4 text-purple-600" />
              <span className="text-xs text-purple-600 font-medium">الرواتب المستحقة</span>
            </div>
            <p className="text-xl font-bold text-purple-700">{formatNum(stats?.total_salaries_unpaid || 0)} ر.ي</p>
          </div>
        </div>
      </div>

      {/* Smart Alerts */}
      {((stats?.pending_salaries || 0) > 0 || (stats?.pending_transactions || 0) > 0 || (stats?.late_count || 0) > 0 || (stats?.absent_count || 0) > 0) && (
        <div className="bg-gradient-to-l from-amber-50 to-orange-50 rounded-2xl border border-amber-200 p-6">
          <h3 className="font-bold text-amber-800 mb-3 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            تنبيهات ذكية
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {(stats?.pending_salaries || 0) > 0 && (
              <div className="flex items-center gap-3 bg-white rounded-xl p-3">
                <div className="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center">
                  <DollarSign className="w-4 h-4 text-amber-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-800">{stats.pending_salaries} رواتب معلقة</p>
                  <button onClick={() => navigate('/salaries')} className="text-xs text-primary-600 hover:underline">احسب الآن</button>
                </div>
              </div>
            )}
            {(stats?.pending_transactions || 0) > 0 && (
              <div className="flex items-center gap-3 bg-white rounded-xl p-3">
                <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center">
                  <ArrowRightLeft className="w-4 h-4 text-indigo-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-800">{stats.pending_transactions} معاملات معلقة</p>
                  <button onClick={() => navigate('/financial')} className="text-xs text-primary-600 hover:underline">راجع الآن</button>
                </div>
              </div>
            )}
            {(stats?.late_count || 0) > 0 && (
              <div className="flex items-center gap-3 bg-white rounded-xl p-3">
                <div className="w-8 h-8 rounded-lg bg-yellow-100 flex items-center justify-center">
                  <Clock className="w-4 h-4 text-yellow-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-800">{stats.late_count} موظف متأخر اليوم</p>
                  <button onClick={() => navigate('/attendance')} className="text-xs text-primary-600 hover:underline">عرض الحضور</button>
                </div>
              </div>
            )}
            {(stats?.absent_count || 0) > 0 && (
              <div className="flex items-center gap-3 bg-white rounded-xl p-3">
                <div className="w-8 h-8 rounded-lg bg-red-100 flex items-center justify-center">
                  <AlertCircle className="w-4 h-4 text-red-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-800">{stats.absent_count} موظف غائب اليوم</p>
                  <button onClick={() => navigate('/attendance')} className="text-xs text-primary-600 hover:underline">عرض الغياب</button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Employees by Company */}
        <div className="bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md transition-shadow">
          <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
            <Building2 className="w-5 h-5 text-primary-500" />
            توزيع الموظفين حسب الشركة
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={reportEmployees?.by_company || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip formatter={(value: any) => [value, 'الموظفين']} />
              <Bar dataKey="count" fill="#10b981" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Attendance Pie */}
        <div className="bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md transition-shadow">
          <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
            <CalendarCheck className="w-5 h-5 text-green-500" />
            نسبة الحضور (آخر 30 يوم)
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={[
                { name: 'حاضر', value: reportAttendance?.summary?.present || 0 },
                { name: 'متأخر', value: reportAttendance?.summary?.late || 0 },
                { name: 'غائب', value: reportAttendance?.summary?.absent || 0 },
                { name: 'مرضي', value: reportAttendance?.summary?.sick || 0 },
                { name: 'إجازة', value: reportAttendance?.summary?.annual_leave || 0 },
              ].filter((d: any) => d.value > 0)} cx="50%" cy="50%" innerRadius={55} outerRadius={90} paddingAngle={3} dataKey="value">
              </Pie>
              <Tooltip formatter={(value: any) => [value, 'يوم']} />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex flex-wrap gap-3 justify-center mt-2">
            {[
              { label: 'حاضر', color: '#10b981', val: reportAttendance?.summary?.present || 0 },
              { label: 'متأخر', color: '#f59e0b', val: reportAttendance?.summary?.late || 0 },
              { label: 'غائب', color: '#ef4444', val: reportAttendance?.summary?.absent || 0 },
              { label: 'مرضي', color: '#3b82f6', val: reportAttendance?.summary?.sick || 0 },
              { label: 'إجازة', color: '#8b5cf6', val: reportAttendance?.summary?.annual_leave || 0 },
            ].map(i => (
              <div key={i.label} className="flex items-center gap-1.5 text-xs text-gray-600">
                <div className="w-2.5 h-2.5 rounded-full" style={{ background: i.color }} />
                {i.label}: {i.val}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Work Plans Progress + Attendance Today */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Work Plans */}
        <div className="bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-gray-900 flex items-center gap-2">
              <ClipboardList className="w-5 h-5 text-purple-500" />
              خطط العمل
            </h3>
            <button onClick={() => navigate('/work-plans')} className="text-xs text-primary-600 hover:underline">عرض الكل</button>
          </div>
          <div className="space-y-4">
            {[
              { label: 'قيد الانتظار', count: stats?.work_plans_pending || 0, color: 'bg-yellow-400', textColor: 'text-yellow-600' },
              { label: 'قيد التنفيذ', count: stats?.work_plans_in_progress || 0, color: 'bg-blue-400', textColor: 'text-blue-600' },
              { label: 'مكتملة', count: stats?.work_plans_completed || 0, color: 'bg-green-400', textColor: 'text-green-600' },
            ].map(item => (
              <div key={item.label} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${item.color}`} />
                  <span className="text-sm text-gray-700">{item.label}</span>
                </div>
                <span className={`text-lg font-bold ${item.textColor}`}>{item.count}</span>
              </div>
            ))}
          </div>
          {stats?.work_plan_tasks_total > 0 && (
            <div className="mt-4 pt-4 border-t">
              <div className="flex justify-between text-sm text-gray-600 mb-2">
                <span>تقدم المهام</span>
                <span className="font-bold">{stats.work_plan_tasks_completed}/{stats.work_plan_tasks_total}</span>
              </div>
              <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-l from-purple-500 to-primary-500 rounded-full transition-all" style={{ width: `${workPlanProgress}%` }} />
              </div>
            </div>
          )}
        </div>

        {/* Today's Attendance */}
        <div className="bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-gray-900 flex items-center gap-2">
              <Clock className="w-5 h-5 text-blue-500" />
              حضور اليوم
            </h3>
            <button onClick={() => navigate('/attendance')} className="text-xs text-primary-600 hover:underline">عرض الكل</button>
          </div>
          <div className="space-y-3">
            {[
              { label: 'حاضر', count: stats?.today_attendance || 0, icon: CheckCircle2, color: 'text-green-600', bg: 'bg-green-50' },
              { label: 'متأخر', count: stats?.late_count || 0, icon: Clock, color: 'text-yellow-600', bg: 'bg-yellow-50' },
              { label: 'غائب', count: stats?.absent_count || 0, icon: AlertCircle, color: 'text-red-600', bg: 'bg-red-50' },
              { label: 'مرضي', count: stats?.sick_count || 0, icon: Activity, color: 'text-blue-600', bg: 'bg-blue-50' },
              { label: 'إجازة', count: stats?.leave_count || 0, icon: CalendarCheck, color: 'text-purple-600', bg: 'bg-purple-50' },
            ].map(item => {
              const Icon = item.icon;
              return (
                <div key={item.label} className={`flex items-center justify-between p-3 rounded-xl ${item.bg}`}>
                  <div className="flex items-center gap-2">
                    <Icon className={`w-4 h-4 ${item.color}`} />
                    <span className="text-sm text-gray-700">{item.label}</span>
                  </div>
                  <span className={`text-lg font-bold ${item.color}`}>{item.count}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Evaluation Indicators */}
      {reportEvaluations && reportEvaluations.total_evaluations > 0 && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
              <Award className="w-5 h-5 text-amber-500" />
              مؤشرات الأداء والتقييم
            </h2>
            <button onClick={() => navigate('/evaluations')} className="text-xs text-primary-600 hover:underline">عرض الكل</button>
          </div>

          {/* KPI Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-2xl p-5 border border-amber-100">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center">
                  <Star className="w-5 h-5 text-amber-600" />
                </div>
              </div>
              <p className="text-2xl font-bold text-amber-700">{reportEvaluations.total_evaluations}</p>
              <p className="text-sm text-amber-600 mt-1">إجمالي التقييمات</p>
            </div>
            <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-2xl p-5 border border-green-100">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-green-100 flex items-center justify-center">
                  <TrendingUp className="w-5 h-5 text-green-600" />
                </div>
              </div>
              <p className="text-2xl font-bold text-green-700">{reportEvaluations.avg_score}/10</p>
              <p className="text-sm text-green-600 mt-1">متوسط التقييم — {reportEvaluations.avg_rating}</p>
            </div>
            <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-2xl p-5 border border-blue-100">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center">
                  <Users className="w-5 h-5 text-blue-600" />
                </div>
              </div>
              <p className="text-2xl font-bold text-blue-700">{reportEvaluations.top_employees?.length || 0}</p>
              <p className="text-sm text-blue-600 mt-1">الموارد المقيّمة</p>
            </div>
            <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-2xl p-5 border border-purple-100">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-purple-100 flex items-center justify-center">
                  <Target className="w-5 h-5 text-purple-600" />
                </div>
              </div>
              <p className="text-2xl font-bold text-purple-700">{reportEvaluations.rating_distribution?.find((r: any) => r.name === 'ممتاز')?.value || 0}</p>
              <p className="text-sm text-purple-600 mt-1">تقييم "ممتاز"</p>
            </div>
          </div>

          {/* Charts Row */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Rating Distribution Pie */}
            <div className="bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md transition-shadow">
              <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                <Star className="w-5 h-5 text-amber-500" />
                توزيع التقييمات
              </h3>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={reportEvaluations.rating_distribution || []} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value">
                    {(reportEvaluations.rating_distribution || []).map((_: any, idx: number) => (
                      <Cell key={idx} fill={['#10b981', '#3b82f6', '#f59e0b', '#f97316', '#ef4444'][idx] || '#ccc'} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex flex-wrap gap-2 justify-center mt-2">
                {(reportEvaluations.rating_distribution || []).map((r: any, idx: number) => (
                  <div key={r.name} className="flex items-center gap-1.5 text-xs text-gray-600">
                    <div className="w-2.5 h-2.5 rounded-full" style={{ background: ['#10b981', '#3b82f6', '#f59e0b', '#f97316', '#ef4444'][idx] || '#ccc' }} />
                    {r.name}: {r.value}
                  </div>
                ))}
              </div>
            </div>

            {/* Monthly Trend */}
            <div className="bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md transition-shadow">
              <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-green-500" />
                اتجاه التقييمات الشهرية
              </h3>
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={reportEvaluations.monthly_trend || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(value: any, name: any) => [value, name === 'avg' ? 'متوسط' : 'عدد']} />
                  <Area type="monotone" dataKey="avg" stroke="#10b981" fill="#10b98120" strokeWidth={2} />
                  <Area type="monotone" dataKey="count" stroke="#6366f1" fill="#6366f120" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* Top 5 Employees */}
            <div className="bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md transition-shadow">
              <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                <Award className="w-5 h-5 text-amber-500" />
                أفضل 5 موظفين
              </h3>
              <div className="space-y-3">
                {(reportEvaluations.top_employees || []).slice(0, 5).map((emp: any, idx: number) => (
                  <div key={emp.employee_id} className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                      idx === 0 ? 'bg-amber-100 text-amber-700' :
                      idx === 1 ? 'bg-gray-200 text-gray-600' :
                      idx === 2 ? 'bg-orange-100 text-orange-700' :
                      'bg-gray-100 text-gray-500'
                    }`}>
                      {idx + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800 truncate">{emp.name}</p>
                      <p className="text-xs text-gray-500">{emp.job_title} — {emp.eval_count} تقييمات</p>
                    </div>
                    <div className="flex items-center gap-1">
                      <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
                      <span className="text-sm font-bold text-amber-600">{emp.avg_score}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div>
        <h2 className="text-lg font-bold text-gray-900 mb-4">إجراءات سريعة</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
          {[
            { label: 'إضافة موظف', icon: Users, path: '/employees', color: 'bg-blue-500' },
            { label: 'تحضير جماعي', icon: CalendarCheck, path: '/attendance', color: 'bg-green-500' },
            { label: 'خطة عمل', icon: ClipboardList, path: '/work-plans', color: 'bg-purple-500' },
            { label: 'احتساب رواتب', icon: DollarSign, path: '/salaries', color: 'bg-amber-500' },
            { label: 'فاتورة جديدة', icon: FileText, path: '/invoices', color: 'bg-violet-500' },
            { label: 'التقارير', icon: BarChart3, path: '/reports', color: 'bg-pink-500' },
          ].map((action) => {
            const Icon = action.icon;
            return (
              <button key={action.label} onClick={() => navigate(action.path)}
                className="flex items-center gap-3 bg-white rounded-xl p-4 border border-gray-100 hover:border-gray-200 hover:shadow-md transition-all group">
                <div className={`w-10 h-10 rounded-xl ${action.color} flex items-center justify-center group-hover:scale-110 transition-transform`}>
                  <Icon className="w-5 h-5 text-white" />
                </div>
                <span className="text-sm font-medium text-gray-700">{action.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Top Employees & Overdue Plans */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Employees */}
        {stats?.top_employees && stats.top_employees.length > 0 && (
          <div className="bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-gray-900 flex items-center gap-2">
                <Award className="w-5 h-5 text-amber-500" />
                أفضل الموظفين أداءً
              </h3>
              <button onClick={() => navigate('/evaluations')} className="text-xs text-primary-600 hover:underline">عرض الكل</button>
            </div>
            <div className="space-y-3">
              {stats.top_employees.map((emp: any, idx: number) => (
                <div key={emp.name} className="flex items-center gap-3 p-3 bg-gray-50 rounded-xl">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                    idx === 0 ? 'bg-amber-100 text-amber-700' :
                    idx === 1 ? 'bg-gray-200 text-gray-600' :
                    idx === 2 ? 'bg-orange-100 text-orange-700' :
                    'bg-gray-100 text-gray-500'
                  }`}>
                    {idx + 1}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-800">{emp.name}</p>
                    <p className="text-xs text-gray-500">{emp.eval_count} تقييمات</p>
                  </div>
                  <div className="flex items-center gap-1">
                    <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
                    <span className="text-sm font-bold text-amber-600">{emp.avg_score}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Overdue Plans */}
        {stats?.overdue_plans && stats.overdue_plans.length > 0 && (
          <div className="bg-gradient-to-l from-red-50 to-orange-50 rounded-2xl border border-red-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-red-800 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5" />
                خطط عمل متأخرة ({stats.overdue_plans.length})
              </h3>
              <button onClick={() => navigate('/work-plans')} className="text-xs text-red-600 hover:underline">عرض الكل</button>
            </div>
            <div className="space-y-3">
              {stats.overdue_plans.map((plan: any) => (
                <div key={plan.id} className="bg-white rounded-xl p-3 border border-red-100">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-800">{plan.title}</p>
                      <p className="text-xs text-red-600">الموعد النهائي: {plan.due_date}</p>
                    </div>
                    <div className="text-left">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        plan.status === 'in_progress' ? 'bg-blue-100 text-blue-700' : 'bg-yellow-100 text-yellow-700'
                      }`}>
                        {plan.status === 'in_progress' ? 'قيد التنفيذ' : 'قيد الانتظار'}
                      </span>
                      <p className="text-xs text-gray-500 mt-1">التقدم: {plan.progress}%</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* No alerts placeholder */}
        {(!stats?.overdue_plans || stats.overdue_plans.length === 0) && (!stats?.top_employees || stats.top_employees.length === 0) && (
          <div className="bg-white rounded-2xl border border-gray-100 p-6 text-center">
            <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-3" />
            <p className="text-gray-600 font-medium">لا توجد تنبيهات حالياً</p>
            <p className="text-sm text-gray-400 mt-1">كل شيء يعمل بشكل طبيعي</p>
          </div>
        )}
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md transition-shadow">
        <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
          <Zap className="w-5 h-5 text-primary-500" />
          النشاط الأخير
        </h3>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Transactions */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-3">آخر المعاملات المالية</h4>
            <div className="space-y-2">
              {stats?.recent_transactions?.slice(0, 5).map((t: any, idx: number) => (
                <div key={idx} className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                    t.type === 'income' ? 'bg-green-100' : 'bg-red-100'
                  }`}>
                    {t.type === 'income' ?
                      <ArrowUpRight className="w-4 h-4 text-green-600" /> :
                      <ArrowDownLeft className="w-4 h-4 text-red-600" />
                    }
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-800 truncate">{t.description || 'معاملة'}</p>
                    <p className="text-xs text-gray-500">{t.date}</p>
                  </div>
                  <span className={`text-sm font-bold ${t.type === 'income' ? 'text-green-600' : 'text-red-600'}`}>
                    {t.type === 'income' ? '+' : '-'}{formatNum(t.amount)}
                  </span>
                </div>
              ))}
              {(!stats?.recent_transactions || stats.recent_transactions.length === 0) && (
                <p className="text-sm text-gray-400 text-center py-4">لا توجد معاملات</p>
              )}
            </div>
          </div>

          {/* Recent Evaluations */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-3">آخر التقييمات</h4>
            <div className="space-y-2">
              {stats?.recent_evaluations?.slice(0, 5).map((e: any, idx: number) => (
                <div key={idx} className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50">
                  <div className="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center">
                    <Star className="w-4 h-4 text-amber-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-800">{e.employee_name}</p>
                    <p className="text-xs text-gray-500">{e.date}</p>
                  </div>
                  <div className="flex items-center gap-1">
                    <Star className="w-3.5 h-3.5 text-amber-500 fill-amber-500" />
                    <span className="text-sm font-bold text-amber-600">{e.score}</span>
                  </div>
                </div>
              ))}
              {(!stats?.recent_evaluations || stats.recent_evaluations.length === 0) && (
                <p className="text-sm text-gray-400 text-center py-4">لا توجد تقييمات</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
