import { useState, useEffect } from 'react';
import { BarChart3, Users, Building2, DollarSign, CalendarCheck, Download, Printer, TrendingUp, TrendingDown, PieChart as PieIcon, Activity, ClipboardList, Briefcase, Star, Award, Target, TrendingUpIcon, Filter, ArrowLeftRight } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line, Legend, AreaChart, Area, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ComposedChart } from 'recharts';
import api from '@/api/client';
import { formatNum } from '@/lib/utils';

const COLORS = ['#10b981', '#f59e0b', '#ef4444', '#6366f1', '#8b5cf6', '#ec4899', '#06b6d4'];

export default function ReportsPage() {
  const [stats, setStats] = useState<any>(null);
  const [employees, setEmployees] = useState<any>(null);
  const [attendance, setAttendance] = useState<any>(null);
  const [attendanceComp, setAttendanceComp] = useState<any>(null);
  const [financial, setFinancial] = useState<any>(null);
  const [financialComp, setFinancialComp] = useState<any>(null);
  const [workPlans, setWorkPlans] = useState<any[]>([]);
  const [evaluations, setEvaluations] = useState<any>(null);
  const [contractorProfit, setContractorProfit] = useState<any>(null);
  const [companies, setCompanies] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  const [dateFrom, setDateFrom] = useState(() => {
    const d = new Date(); d.setDate(d.getDate() - 30); return d.toISOString().split('T')[0];
  });
  const [dateTo, setDateTo] = useState(() => new Date().toISOString().split('T')[0]);
  const [companyFilter, setCompanyFilter] = useState('');
  const [compareMode, setCompareMode] = useState(false);
  const [comparePeriod, setComparePeriod] = useState<'prev_month' | 'prev_quarter' | 'prev_year'>('prev_month');
  const [showFilters, setShowFilters] = useState(false);

  const loadData = () => {
    setLoading(true);
    const params: Record<string, string> = {};
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    if (companyFilter) params.company_id = companyFilter;

    const qs = new URLSearchParams(params).toString();
    const attUrl = '/reports/attendance' + (qs ? '?' + qs : '');

    Promise.all([
      api.get('/dashboard/stats'),
      api.get('/reports/employees'),
      api.get(attUrl),
      api.get('/reports/financial'),
      api.get('/work-plans'),
      api.get('/reports/evaluations').catch(() => ({ data: { data: { total_evaluations: 0, avg_score: 0, avg_rating: '-', rating_distribution: [], type_distribution: [], top_employees: [], monthly_trend: [], all_employees: [] } } })),
      api.get('/reports/contractor-profit').catch(() => ({ data: { data: { employees: [], summary: {} } } })),
      api.get('/companies'),
    ]).then(([sRes, eRes, aRes, fRes, wRes, evRes, cpRes, cRes]) => {
      setStats(sRes.data.data);
      setEmployees(eRes.data.data);
      setAttendance(aRes.data.data);
      setFinancial(fRes.data.data);
      setWorkPlans(wRes.data.data || []);
      setEvaluations(evRes.data.data);
      setContractorProfit(cpRes.data.data);
      setCompanies(cRes.data.data || []);
    }).catch(console.error).finally(() => setLoading(false));
  };

  const loadComparison = () => {
    if (!compareMode) { setAttendanceComp(null); setFinancialComp(null); return; }
    const today = new Date();
    let compFrom: Date, compTo: Date;
    if (comparePeriod === 'prev_month') {
      compTo = new Date(today.getFullYear(), today.getMonth(), 0);
      compFrom = new Date(compTo.getFullYear(), compTo.getMonth(), 1);
    } else if (comparePeriod === 'prev_quarter') {
      compTo = new Date(today.getFullYear(), today.getMonth(), 0);
      compFrom = new Date(compTo.getFullYear(), compTo.getMonth() - 2, 1);
    } else {
      compTo = new Date(today.getFullYear() - 1, 11, 31);
      compFrom = new Date(today.getFullYear() - 1, 0, 1);
    }
    const params: Record<string, string> = {
      date_from: compFrom.toISOString().split('T')[0],
      date_to: compTo.toISOString().split('T')[0],
    };
    if (companyFilter) params.company_id = companyFilter;
    const qs = new URLSearchParams(params).toString();
    Promise.all([
      api.get('/reports/attendance?' + qs),
      api.get('/reports/financial'),
    ]).then(([aRes, fRes]) => {
      setAttendanceComp(aRes.data.data);
      setFinancialComp(fRes.data.data);
    }).catch(console.error);
  };

  useEffect(() => { loadData(); }, [dateFrom, dateTo, companyFilter]);
  useEffect(() => { if (compareMode) loadComparison(); }, [compareMode, comparePeriod, dateFrom, dateTo, companyFilter]);

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-3 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" /></div>;

  const tabs = [
    { id: 'overview', label: 'نظرة عامة', icon: Activity },
    { id: 'employees', label: 'الموظفين', icon: Users },
    { id: 'attendance', label: 'الحضور', icon: CalendarCheck },
    { id: 'evaluations', label: 'التقييمات', icon: Star },
    { id: 'workplans', label: 'خطط العمل', icon: ClipboardList },
    { id: 'financial', label: 'المالية', icon: DollarSign },
    { id: 'contractor', label: 'أرباح المتعهد', icon: TrendingUpIcon },
  ];

  const plansByType = {
    daily: workPlans.filter(p => p.plan_type === 'daily'),
    monthly: workPlans.filter(p => p.plan_type === 'monthly'),
    yearly: workPlans.filter(p => p.plan_type === 'yearly'),
  };

  const workPlanPieData = [
    { name: 'قيد الانتظار', value: stats?.work_plans_pending || 0 },
    { name: 'قيد التنفيذ', value: stats?.work_plans_in_progress || 0 },
    { name: 'مكتملة', value: stats?.work_plans_completed || 0 },
  ].filter(d => d.value > 0);

  const workPlanTypeData = [
    { name: 'يومي', count: plansByType.daily.length },
    { name: 'شهري', count: plansByType.monthly.length },
    { name: 'سنوي', count: plansByType.yearly.length },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">التقارير والتحليلات</h1>
          <p className="text-gray-500 text-sm mt-1">لوحة تحليلات شاملة مع رسوم بيانية تفاعلية</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => window.print()}><Printer className="w-4 h-4" /> طباعة</Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-xl overflow-x-auto">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${activeTab === tab.id ? 'bg-white text-primary-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}>
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Filter Bar */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center gap-3">
            <button onClick={() => setShowFilters(!showFilters)} className="flex items-center gap-2 text-sm font-medium text-gray-600 hover:text-primary-600 transition-colors">
              <Filter className="w-4 h-4" />
              الفلاتر
              {(dateFrom || dateTo || companyFilter) && <span className="w-2 h-2 bg-primary-500 rounded-full" />}
            </button>
            {showFilters && (
              <>
                <div className="flex items-center gap-2">
                  <label className="text-xs text-gray-500">من:</label>
                  <Input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} className="w-36 text-sm" />
                </div>
                <div className="flex items-center gap-2">
                  <label className="text-xs text-gray-500">إلى:</label>
                  <Input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} className="w-36 text-sm" />
                </div>
                <select value={companyFilter} onChange={e => setCompanyFilter(e.target.value)}
                  className="w-44 text-sm border border-gray-300 rounded-lg px-3 py-2 bg-white">
                  <option value="">جميع الشركات</option>
                  {companies.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
                <div className="flex gap-1">
                  {[
                    { label: '30 يوم', from: () => { const d = new Date(); d.setDate(d.getDate()-30); return d.toISOString().split('T')[0]; } },
                    { label: '3 أشهر', from: () => { const d = new Date(); d.setMonth(d.getMonth()-3); return d.toISOString().split('T')[0]; } },
                    { label: '6 أشهر', from: () => { const d = new Date(); d.setMonth(d.getMonth()-6); return d.toISOString().split('T')[0]; } },
                    { label: 'سنة', from: () => { const d = new Date(); d.setFullYear(d.getFullYear()-1); return d.toISOString().split('T')[0]; } },
                  ].map(p => (
                    <Button key={p.label} size="sm" variant="outline" onClick={() => { setDateFrom(p.from()); setDateTo(new Date().toISOString().split('T')[0]); }}>{p.label}</Button>
                  ))}
                </div>
                <Button size="sm" variant="outline" onClick={() => { setDateFrom(''); setDateTo(''); setCompanyFilter(''); }}>مسح</Button>
              </>
            )}
            <div className="mr-auto flex items-center gap-2">
              <button onClick={() => setCompareMode(!compareMode)}
                className={`flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg border transition-colors ${compareMode ? 'bg-primary-50 border-primary-300 text-primary-700' : 'border-gray-300 text-gray-600 hover:bg-gray-50'}`}>
                <ArrowLeftRight className="w-3.5 h-3.5" />
                مقارنة
              </button>
              {compareMode && (
                <select value={comparePeriod} onChange={e => setComparePeriod(e.target.value as any)}
                  className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 bg-white">
                  <option value="prev_month">الشهر السابق</option>
                  <option value="prev_quarter">الربع السابق</option>
                  <option value="prev_year">السنة السابقة</option>
                </select>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: 'الموظفين النشطين', value: stats?.total_employees || 0, icon: Users, color: 'text-blue-600', bg: 'bg-blue-50' },
              { label: 'حضور اليوم', value: stats?.today_attendance || 0, icon: CalendarCheck, color: 'text-green-600', bg: 'bg-green-50' },
              { label: 'رواتب معلقة', value: stats?.pending_salaries || 0, icon: DollarSign, color: 'text-amber-600', bg: 'bg-amber-50' },
              { label: 'خطط العمل', value: stats?.work_plans_total || 0, icon: ClipboardList, color: 'text-purple-600', bg: 'bg-purple-50' },
            ].map((stat) => {
              const Icon = stat.icon;
              return (
                <Card key={stat.label} className="hover:shadow-md transition-shadow">
                  <CardContent className="p-5">
                    <div className="flex items-center justify-between mb-3">
                      <div className={`w-10 h-10 rounded-xl ${stat.bg} flex items-center justify-center`}>
                        <Icon className={`w-5 h-5 ${stat.color}`} />
                      </div>
                    </div>
                    <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                    <p className="text-sm text-gray-500 mt-1">{stat.label}</p>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardContent className="p-6">
                <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <Building2 className="w-5 h-5 text-primary-500" />
                  توزيع الموظفين حسب الشركة
                </h3>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={employees?.by_company || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip formatter={(value: any) => [value, 'الموظفين']} />
                    <Bar dataKey="count" fill="#10b981" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <CalendarCheck className="w-5 h-5 text-green-500" />
                  ملخص الحضور (آخر 30 يوم)
                </h3>
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie data={[
                      { name: 'حاضر', value: attendance?.summary?.present || 0 },
                      { name: 'متأخر', value: attendance?.summary?.late || 0 },
                      { name: 'غائب', value: attendance?.summary?.absent || 0 },
                      { name: 'مرضي', value: attendance?.summary?.sick || 0 },
                      { name: 'إجازة', value: attendance?.summary?.annual_leave || 0 },
                    ].filter(d => d.value > 0)} cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={3} dataKey="value">
                    </Pie>
                    <Tooltip formatter={(value: any) => [value, 'يوم']} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardContent className="p-6">
                <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <ClipboardList className="w-5 h-5 text-purple-500" />
                  حالة خطط العمل
                </h3>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie data={workPlanPieData} cx="50%" cy="50%" innerRadius={55} outerRadius={90} paddingAngle={3} dataKey="value">
                      {workPlanPieData.map((_, i) => <Cell key={i} fill={COLORS[i]} />)}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <DollarSign className="w-5 h-5 text-emerald-500" />
                  الملخص المالي الشهري
                </h3>
                <ResponsiveContainer width="100%" height={250}>
                  <AreaChart data={financial?.monthly || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(value: any) => [formatNum(value) + ' ر.ي', '']} />
                    <Area type="monotone" dataKey="income" stroke="#10b981" fill="#10b98133" name="الإيرادات" />
                    <Area type="monotone" dataKey="expense" stroke="#ef4444" fill="#ef444433" name="المصروفات" />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Employees Tab */}
      {activeTab === 'employees' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardContent className="p-6">
                <h3 className="font-bold text-gray-900 mb-4">الموظفين حسب الشركة</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={employees?.by_company || []} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis type="number" tick={{ fontSize: 12 }} />
                    <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={100} />
                    <Tooltip formatter={(value: any) => [value, 'موظف']} />
                    <Bar dataKey="count" fill="#6366f1" radius={[0, 6, 6, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-6">
                <h3 className="font-bold text-gray-900 mb-4">إجمالي أعداد الرواتب</h3>
                <div className="text-center py-8">
                  <p className="text-4xl font-bold text-primary-600">{formatNum(employees?.total_salary)}</p>
                  <p className="text-gray-500 mt-2">ر.ي إجمالي الرواتب الشهرية</p>
                  <p className="text-sm text-gray-400 mt-1">{employees?.total || 0} موظف نشط</p>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardContent className="p-0">
              <div className="p-4 bg-primary-50 border-b flex items-center justify-between">
                <h3 className="font-bold text-primary-800">قائمة الموظفين ({employees?.employees?.length || 0})</h3>
                <Button size="sm" onClick={() => {
                  const csv = employees?.employees?.map((e: any) => `${e.name},${e.job_title},${e.company_name},${e.salary}`).join('\n') || '';
                  const blob = new Blob(['الاسم,الوظيفة,الشركة,الراتب\n' + csv], { type: 'text/csv;charset=utf-8;' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a'); a.href = url; a.download = 'employees_report.csv'; a.click();
                }}><Download className="w-3.5 h-3.5" /> تصدير CSV</Button>
              </div>
              <div className="overflow-x-auto max-h-96">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-gray-50"><tr>
                    <th className="px-4 py-3 text-right font-semibold">الاسم</th>
                    <th className="px-4 py-3 text-right font-semibold">الوظيفة</th>
                    <th className="px-4 py-3 text-right font-semibold">الشركة</th>
                    <th className="px-4 py-3 text-right font-semibold">الراتب</th>
                  </tr></thead>
                  <tbody>
                    {employees?.employees?.map((e: any) => (
                      <tr key={e.id} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="px-4 py-3 font-medium">{e.name}</td>
                        <td className="px-4 py-3 text-gray-600">{e.job_title || '—'}</td>
                        <td className="px-4 py-3"><Badge variant="default">{e.company_name || 'غير محدد'}</Badge></td>
                        <td className="px-4 py-3 font-bold">{formatNum(e.salary)} ر.ي</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Attendance Tab */}
      {activeTab === 'attendance' && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
            {[
              { label: 'حاضر', value: attendance?.summary?.present || 0, comp: attendanceComp?.summary?.present || 0, color: 'bg-green-500' },
              { label: 'متأخر', value: attendance?.summary?.late || 0, comp: attendanceComp?.summary?.late || 0, color: 'bg-yellow-500' },
              { label: 'غائب', value: attendance?.summary?.absent || 0, comp: attendanceComp?.summary?.absent || 0, color: 'bg-red-500' },
              { label: 'مرضي', value: attendance?.summary?.sick || 0, comp: attendanceComp?.summary?.sick || 0, color: 'bg-blue-500' },
              { label: 'إجازة', value: attendance?.summary?.annual_leave || 0, comp: attendanceComp?.summary?.annual_leave || 0, color: 'bg-purple-500' },
            ].map((item) => (
              <Card key={item.label}>
                <CardContent className="p-4 text-center">
                  <div className={`w-3 h-3 rounded-full ${item.color} mx-auto mb-2`} />
                  <p className="text-2xl font-bold">{item.value}</p>
                  <p className="text-xs text-gray-500">{item.label}</p>
                  {compareMode && item.comp > 0 && (
                    <p className={`text-xs mt-1 font-medium ${item.value >= item.comp ? 'text-green-600' : 'text-red-600'}`}>
                      {item.value >= item.comp ? '↑' : '↓'} {Math.abs(Math.round((item.value - item.comp) / item.comp * 100))}%
                    </p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>

          {compareMode && (
            <Card className="bg-primary-50 border-primary-200">
              <CardContent className="p-4">
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-center">
                  <div>
                    <p className="text-xs text-gray-500">الفترة الحالية</p>
                    <p className="font-bold text-primary-700">{attendance?.start_date || ''} ~ {attendance?.end_date || ''}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">نسبة الحضور</p>
                    <p className="font-bold text-green-700">{attendance?.attendance_rate || 0}%</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">الفترة المقارنة</p>
                    <p className="font-bold text-gray-600">{attendanceComp?.start_date || '—'} ~ {attendanceComp?.end_date || '—'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">نسبة الحضور (مقارنة)</p>
                    <p className="font-bold text-gray-600">{attendanceComp?.attendance_rate || 0}%</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardContent className="p-6">
              <h3 className="font-bold text-gray-900 mb-4">الحضور اليومي ({attendance?.period || 'آخر 30 يوم'})</h3>
              <ResponsiveContainer width="100%" height={350}>
                <BarChart data={attendance?.daily || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="present" fill="#10b981" name="حاضر" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="late" fill="#f59e0b" name="متأخر" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="absent" fill="#ef4444" name="غائب" radius={[4, 4, 0, 0]} />
                  {compareMode && <Bar dataKey="sick" fill="#3b82f6" name="مرضي" radius={[4, 4, 0, 0]} />}
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardContent className="p-6">
                <h3 className="font-bold text-gray-900 mb-4">نسبة الحضور — الفترة الحالية</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie data={[
                      { name: 'حاضر', value: attendance?.summary?.present || 0 },
                      { name: 'متأخر', value: attendance?.summary?.late || 0 },
                      { name: 'غائب', value: attendance?.summary?.absent || 0 },
                      { name: 'مرضي', value: attendance?.summary?.sick || 0 },
                      { name: 'إجازة', value: attendance?.summary?.annual_leave || 0 },
                    ].filter(d => d.value > 0)} cx="50%" cy="50%" innerRadius={70} outerRadius={110} paddingAngle={4} dataKey="value" label={({ name, percent }: any) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}>
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
            {compareMode && attendanceComp && (
              <Card>
                <CardContent className="p-6">
                  <h3 className="font-bold text-gray-900 mb-4">نسبة الحضور — الفترة المقارنة</h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie data={[
                        { name: 'حاضر', value: attendanceComp?.summary?.present || 0 },
                        { name: 'متأخر', value: attendanceComp?.summary?.late || 0 },
                        { name: 'غائب', value: attendanceComp?.summary?.absent || 0 },
                        { name: 'مرضي', value: attendanceComp?.summary?.sick || 0 },
                        { name: 'إجازة', value: attendanceComp?.summary?.annual_leave || 0 },
                      ].filter(d => d.value > 0)} cx="50%" cy="50%" innerRadius={70} outerRadius={110} paddingAngle={4} dataKey="value" label={({ name, percent }: any) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}>
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      )}

      {/* Work Plans Tab */}
      {activeTab === 'workplans' && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: 'إجمالي الخطط', value: stats?.work_plans_total || 0, color: 'text-gray-700', bg: 'bg-gray-50' },
              { label: 'قيد الانتظار', value: stats?.work_plans_pending || 0, color: 'text-yellow-600', bg: 'bg-yellow-50' },
              { label: 'قيد التنفيذ', value: stats?.work_plans_in_progress || 0, color: 'text-blue-600', bg: 'bg-blue-50' },
              { label: 'مكتملة', value: stats?.work_plans_completed || 0, color: 'text-green-600', bg: 'bg-green-50' },
            ].map(item => (
              <Card key={item.label}>
                <CardContent className="p-4 text-center">
                  <p className={`text-3xl font-bold ${item.color}`}>{item.value}</p>
                  <p className="text-xs text-gray-500 mt-1">{item.label}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardContent className="p-6">
                <h3 className="font-bold text-gray-900 mb-4">حالة الخطط</h3>
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie data={workPlanPieData} cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={3} dataKey="value">
                      {workPlanPieData.map((_, i) => <Cell key={i} fill={COLORS[i]} />)}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <h3 className="font-bold text-gray-900 mb-4">الخطط حسب النوع</h3>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={workPlanTypeData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#8b5cf6" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          {/* Tasks Progress */}
          <Card>
            <CardContent className="p-6">
              <h3 className="font-bold text-gray-900 mb-4">تقدم المهام الإجمالي</h3>
              <div className="grid grid-cols-3 gap-4 mb-4">
                <div className="text-center">
                  <p className="text-3xl font-bold text-gray-900">{stats?.work_plan_tasks_total || 0}</p>
                  <p className="text-xs text-gray-500">إجمالي المهام</p>
                </div>
                <div className="text-center">
                  <p className="text-3xl font-bold text-green-600">{stats?.work_plan_tasks_completed || 0}</p>
                  <p className="text-xs text-gray-500">مهام مكتملة</p>
                </div>
                <div className="text-center">
                  <p className="text-3xl font-bold text-amber-600">{(stats?.work_plan_tasks_total || 0) - (stats?.work_plan_tasks_completed || 0)}</p>
                  <p className="text-xs text-gray-500">مهام متبقية</p>
                </div>
              </div>
              <div className="w-full h-4 bg-gray-200 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-l from-purple-500 to-primary-500 rounded-full transition-all"
                  style={{ width: `${stats?.work_plan_tasks_total ? Math.round((stats.work_plan_tasks_completed / stats.work_plan_tasks_total) * 100) : 0}%` }} />
              </div>
              <p className="text-center text-sm text-gray-500 mt-2">
                نسبة الإنجاز: {stats?.work_plan_tasks_total ? Math.round((stats.work_plan_tasks_completed / stats.work_plan_tasks_total) * 100) : 0}%
              </p>
            </CardContent>
          </Card>

          {/* Plans List */}
          <Card>
            <CardContent className="p-0">
              <div className="p-4 bg-purple-50 border-b">
                <h3 className="font-bold text-purple-800">قائمة الخطط ({workPlans.length})</h3>
              </div>
              <div className="overflow-x-auto max-h-96">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-gray-50"><tr>
                    <th className="px-4 py-3 text-right font-semibold">الخطة</th>
                    <th className="px-4 py-3 text-right font-semibold">النوع</th>
                    <th className="px-4 py-3 text-right font-semibold">الحالة</th>
                    <th className="px-4 py-3 text-right font-semibold">المهام</th>
                    <th className="px-4 py-3 text-right font-semibold">التقدم</th>
                  </tr></thead>
                  <tbody>
                    {workPlans.map((plan) => (
                      <tr key={plan.id} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="px-4 py-3 font-medium">{plan.title}</td>
                        <td className="px-4 py-3"><Badge variant="default">{plan.plan_type_name}</Badge></td>
                        <td className="px-4 py-3">
                          <Badge variant={plan.status === 'completed' ? 'success' : plan.status === 'in_progress' ? 'warning' : 'default'}>
                            {plan.status_name}
                          </Badge>
                        </td>
                        <td className="px-4 py-3">{plan.completed_tasks}/{plan.tasks_count}</td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <div className="w-20 h-2 bg-gray-200 rounded-full overflow-hidden">
                              <div className="h-full bg-primary-500 rounded-full" style={{ width: `${plan.progress}%` }} />
                            </div>
                            <span className="text-xs font-bold">{plan.progress}%</span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Evaluations Tab */}
      {activeTab === 'evaluations' && (
        <div className="space-y-6">
          {!evaluations ? (
            <div className="text-center py-12">
              <div className="w-12 h-12 border-4 border-primary-500/20 border-t-primary-500 rounded-full animate-spin mx-auto" />
              <p className="text-gray-400 mt-4 text-sm">جاري تحميل بيانات التقييمات...</p>
            </div>
          ) : evaluations.total_evaluations === 0 ? (
            <div className="text-center py-12">
              <Star className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">لا توجد تقييمات مسجلة بعد</p>
              <p className="text-sm text-gray-400 mt-1">أضف تقييمات من صفحة التقييمات</p>
            </div>
          ) : (
            <>
              {/* KPI Cards */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="bg-gradient-to-br from-amber-50 to-orange-50 border-amber-200">
                  <CardContent className="p-5 text-center">
                    <Star className="w-8 h-8 text-amber-500 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-amber-700">{evaluations.total_evaluations}</p>
                    <p className="text-sm text-amber-600">إجمالي التقييمات</p>
                  </CardContent>
                </Card>
                <Card className="bg-gradient-to-br from-green-50 to-emerald-50 border-green-200">
                  <CardContent className="p-5 text-center">
                    <TrendingUp className="w-8 h-8 text-green-500 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-green-700">{evaluations.avg_score}/10</p>
                    <p className="text-sm text-green-600">المتوسط — {evaluations.avg_rating}</p>
                  </CardContent>
                </Card>
                <Card className="bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200">
                  <CardContent className="p-5 text-center">
                    <Award className="w-8 h-8 text-blue-500 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-blue-700">{evaluations.rating_distribution?.find((r: any) => r.name === 'ممتاز')?.value || 0}</p>
                    <p className="text-sm text-blue-600">تقييم "ممتاز"</p>
                  </CardContent>
                </Card>
                <Card className="bg-gradient-to-br from-red-50 to-pink-50 border-red-200">
                  <CardContent className="p-5 text-center">
                    <Target className="w-8 h-8 text-red-500 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-red-700">{evaluations.rating_distribution?.find((r: any) => r.name === 'ضعيف')?.value || 0}</p>
                    <p className="text-sm text-red-600">تقييم "ضعيف"</p>
                  </CardContent>
                </Card>
              </div>

              {/* Charts Row */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md transition-shadow">
                  <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <Star className="w-5 h-5 text-amber-500" />
                    توزيع التقييمات حسب التصنيف
                  </h3>
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={evaluations.rating_distribution || []} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                      <XAxis type="number" tick={{ fontSize: 11 }} />
                      <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={80} />
                      <Tooltip formatter={(value: any) => [value, 'عدد']} />
                      <Bar dataKey="value" radius={[0, 6, 6, 0]}>
                        {(evaluations.rating_distribution || []).map((_: any, idx: number) => (
                          <Cell key={idx} fill={['#10b981', '#3b82f6', '#f59e0b', '#f97316', '#ef4444'][idx] || '#ccc'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                <div className="bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md transition-shadow">
                  <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <Users className="w-5 h-5 text-blue-500" />
                    التقييمات حسب النوع
                  </h3>
                  <ResponsiveContainer width="100%" height={280}>
                    <PieChart>
                      <Pie data={evaluations.type_distribution || []} cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={5} dataKey="value" label={({ name, percent }: any) => `${name} (${((percent || 0) * 100).toFixed(0)}%)`}>
                        {(evaluations.type_distribution || []).map((_: any, idx: number) => (
                          <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Monthly Trend + Top Employees */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md transition-shadow">
                  <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-green-500" />
                    اتجاه التقييمات الشهرية
                  </h3>
                  <ResponsiveContainer width="100%" height={280}>
                    <AreaChart data={(evaluations.monthly_trend || []).reverse()}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                      <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip formatter={(value: any, name: any) => [value, name === 'avg' ? 'متوسط الدرجة' : 'عدد التقييمات']} />
                      <Legend />
                      <Area type="monotone" dataKey="avg" name="متوسط الدرجة" stroke="#10b981" fill="#10b98120" strokeWidth={2} />
                      <Area type="monotone" dataKey="count" name="عدد التقييمات" stroke="#6366f1" fill="#6366f120" strokeWidth={2} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>

                <div className="bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md transition-shadow">
                  <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <Award className="w-5 h-5 text-amber-500" />
                    أفضل 10 موظفين أداءً
                  </h3>
                  <div className="space-y-3 max-h-[280px] overflow-y-auto">
                    {(evaluations.top_employees || []).map((emp: any, idx: number) => (
                      <div key={emp.employee_id} className="flex items-center gap-3 p-3 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0 ${
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
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                            emp.rating === 'ممتاز' ? 'bg-green-100 text-green-700' :
                            emp.rating === 'جيد جداً' ? 'bg-blue-100 text-blue-700' :
                            emp.rating === 'جيد' ? 'bg-yellow-100 text-yellow-700' :
                            emp.rating === 'مقبول' ? 'bg-orange-100 text-orange-700' :
                            'bg-red-100 text-red-700'
                          }`}>
                            {emp.rating}
                          </span>
                          <div className="flex items-center gap-1">
                            <Star className="w-3.5 h-3.5 text-amber-500 fill-amber-500" />
                            <span className="text-sm font-bold text-amber-600">{emp.avg_score}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* All Employees Table */}
              {evaluations.all_employees && evaluations.all_employees.length > 0 && (
                <div className="bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md transition-shadow">
                  <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <Users className="w-5 h-5 text-primary-500" />
                    قائمة الموظفين بالتقييم
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-gray-50 text-right">
                          <th className="px-4 py-3 font-semibold text-gray-600">#</th>
                          <th className="px-4 py-3 font-semibold text-gray-600">الموظف</th>
                          <th className="px-4 py-3 font-semibold text-gray-600">الوظيفة</th>
                          <th className="px-4 py-3 font-semibold text-gray-600">عدد التقييمات</th>
                          <th className="px-4 py-3 font-semibold text-gray-600">متوسط الدرجة</th>
                          <th className="px-4 py-3 font-semibold text-gray-600">التصنيف</th>
                        </tr>
                      </thead>
                      <tbody>
                        {evaluations.all_employees.map((emp: any, idx: number) => (
                          <tr key={emp.employee_id} className="border-b border-gray-100 hover:bg-gray-50">
                            <td className="px-4 py-3 text-gray-500">{idx + 1}</td>
                            <td className="px-4 py-3 font-medium">{emp.name}</td>
                            <td className="px-4 py-3 text-gray-600">{emp.job_title}</td>
                            <td className="px-4 py-3 text-center">{emp.eval_count}</td>
                            <td className="px-4 py-3 text-center">
                              <span className={`font-bold ${
                                emp.avg_score >= 9 ? 'text-green-600' :
                                emp.avg_score >= 7 ? 'text-blue-600' :
                                emp.avg_score >= 5 ? 'text-yellow-600' :
                                emp.avg_score >= 3 ? 'text-orange-600' : 'text-red-600'
                              }`}>
                                {emp.avg_score}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-center">
                              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                                emp.rating === 'ممتاز' ? 'bg-green-100 text-green-700' :
                                emp.rating === 'جيد جداً' ? 'bg-blue-100 text-blue-700' :
                                emp.rating === 'جيد' ? 'bg-yellow-100 text-yellow-700' :
                                emp.rating === 'مقبول' ? 'bg-orange-100 text-orange-700' :
                                'bg-red-100 text-red-700'
                              }`}>
                                {emp.rating}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Financial Tab */}
      {activeTab === 'financial' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card className="bg-green-50 border-green-200">
              <CardContent className="p-6 text-center">
                <TrendingUp className="w-8 h-8 text-green-500 mx-auto mb-2" />
                <p className="text-sm text-green-600">إجمالي الإيرادات</p>
                <p className="text-3xl font-bold text-green-700">{formatNum(financial?.total_income)} ر.ي</p>
              </CardContent>
            </Card>
            <Card className="bg-red-50 border-red-200">
              <CardContent className="p-6 text-center">
                <TrendingDown className="w-8 h-8 text-red-500 mx-auto mb-2" />
                <p className="text-sm text-red-600">إجمالي المصروفات</p>
                <p className="text-3xl font-bold text-red-700">{formatNum(financial?.total_expense)} ر.ي</p>
              </CardContent>
            </Card>
            <Card className="bg-primary-50 border-primary-200">
              <CardContent className="p-6 text-center">
                <DollarSign className="w-8 h-8 text-primary-500 mx-auto mb-2" />
                <p className="text-sm text-primary-600">الصافي</p>
                <p className={`text-3xl font-bold ${(financial?.balance || 0) >= 0 ? 'text-green-700' : 'text-red-700'}`}>{formatNum(financial?.balance)} ر.ي</p>
              </CardContent>
            </Card>
          </div>

          {compareMode && attendanceComp && (
            <Card className="bg-primary-50 border-primary-200">
              <CardContent className="p-4">
                <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 text-center">
                  <div>
                    <p className="text-xs text-gray-500">إيرادات الفترة الحالية</p>
                    <p className="font-bold text-green-700">{formatNum(financial?.total_income)} ر.ي</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">مصروفات الفترة الحالية</p>
                    <p className="font-bold text-red-700">{formatNum(financial?.total_expense)} ر.ي</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">صافي الفترة الحالية</p>
                    <p className={`font-bold ${(financial?.balance || 0) >= 0 ? 'text-green-700' : 'text-red-700'}`}>{formatNum(financial?.balance)} ر.ي</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardContent className="p-6">
              <h3 className="font-bold text-gray-900 mb-4">التطور الشهري للإيرادات والمصروفات</h3>
              <ResponsiveContainer width="100%" height={350}>
                <BarChart data={financial?.monthly || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(value: any) => [formatNum(value) + ' ر.ي', '']} />
                  <Legend />
                  <Bar dataKey="income" fill="#10b981" name="الإيرادات" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="expense" fill="#ef4444" name="المصروفات" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <h3 className="font-bold text-gray-900 mb-4">توزيع المعاملات حسب النوع</h3>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie data={(financial?.by_type || []).map((t: any) => ({ name: ({ advance: 'سلفة', overtime: 'إضافي', deduction: 'خصم', penalty: 'جزاء', restaurant: 'مطعم', buffet: 'بوفية' } as any)[t.type] || t.type, value: t.total }))}
                    cx="50%" cy="50%" outerRadius={100} paddingAngle={4} dataKey="value" label={({ name, percent }: any) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}>
                    {(financial?.by_type || []).map((_: any, i: number) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={(value: any) => [formatNum(value) + ' ر.ي', '']} />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'contractor' && (
        <div className="space-y-6">
          <h2 className="text-xl font-bold">أرباح المتعهد - طلعت هائل</h2>
          
          {contractorProfit?.summary && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card>
                <CardContent className="p-4">
                  <div className="text-sm text-gray-500">إجمالي الإيرادات</div>
                  <div className="text-xl font-bold text-green-600">{formatNum(contractorProfit.summary.total_revenue)} ر.ي</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="text-sm text-gray-500">المدفوع للعمال</div>
                  <div className="text-xl font-bold text-blue-600">{formatNum((contractorProfit.summary.total_basic_paid || 0) + (contractorProfit.summary.total_resident_paid || 0))} ر.ي</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="text-sm text-gray-500">تكاليف صاحب العمل</div>
                  <div className="text-xl font-bold text-orange-600">{formatNum(contractorProfit.summary.total_employer_costs)} ر.ي</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="text-sm text-gray-500">صافي الربح</div>
                  <div className={`text-xl font-bold ${(contractorProfit.summary.total_profit || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {formatNum(contractorProfit.summary.total_profit)} ر.ي
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-right font-medium text-gray-600">العامل</th>
                      <th className="px-4 py-3 text-right font-medium text-gray-600">الشركة</th>
                      <th className="px-4 py-3 text-right font-medium text-gray-600">الراتب الشامل</th>
                      <th className="px-4 py-3 text-right font-medium text-gray-600">أيام الحضور</th>
                      <th className="px-4 py-3 text-right font-medium text-gray-600">الراتب الأساسي</th>
                      <th className="px-4 py-3 text-right font-medium text-gray-600">بدل الإقامة</th>
                      <th className="px-4 py-3 text-right font-medium text-gray-600">تكاليف صاحب العمل</th>
                      <th className="px-4 py-3 text-right font-medium text-gray-600">الربح</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {(contractorProfit?.employees || []).map((emp: any) => (
                      <tr key={emp.employee_id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 font-medium">{emp.employee_name}</td>
                        <td className="px-4 py-3 text-gray-600">{emp.company_name}</td>
                        <td className="px-4 py-3">{formatNum(emp.total_salary_revenue)} ر.ي</td>
                        <td className="px-4 py-3">{emp.present_days}/{emp.days_in_month}</td>
                        <td className="px-4 py-3">{formatNum(emp.basic_paid)} ر.ي</td>
                        <td className="px-4 py-3">{formatNum(emp.resident_paid)} ر.ي</td>
                        <td className="px-4 py-3">{formatNum(emp.total_employer_costs)} ر.ي</td>
                        <td className={`px-4 py-3 font-bold ${emp.profit >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatNum(emp.profit)} ر.ي
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
