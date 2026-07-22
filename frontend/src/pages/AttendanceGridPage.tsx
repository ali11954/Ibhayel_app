import { useState, useEffect } from 'react';
import { CalendarCheck, Download, Building2 } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import api from '@/api/client';

const STATUS_COLORS: Record<string, string> = {
  present: 'bg-green-500 text-white',
  late: 'bg-yellow-400 text-white',
  sick: 'bg-blue-400 text-white',
  annual_leave: 'bg-purple-400 text-white',
  unpaid_leave: 'bg-gray-400 text-white',
  absent: 'bg-red-500 text-white',
};

const STATUS_LABELS: Record<string, string> = {
  present: 'ح',
  late: 'م',
  sick: 'ض',
  annual_leave: 'إ',
  unpaid_leave: 'غ',
  absent: 'غ',
};

const STATUS_FULL_LABELS: Record<string, string> = {
  present: 'حاضر',
  late: 'متأخر',
  sick: 'مرضية',
  annual_leave: 'إجازة مدفوعة',
  unpaid_leave: 'إجازة بدون أجر',
};

const MONTHS = [
  'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
  'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر',
];

const DAYS_WEEK = ['سب', 'أح', 'إث', 'ثل', 'أر', 'خم', 'جم'];

export default function AttendanceGridPage() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [companyId, setCompanyId] = useState<number | ''>('');
  const [data, setData] = useState<any>(null);
  const [companies, setCompanies] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const daysInMonth = data?.days_in_month || 30;

  useEffect(() => {
    api.get('/companies').then(r => setCompanies(r.data.data || [])).catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    const params: any = { year, month };
    if (companyId) params.company_id = companyId;
    api.get('/reports/attendance-grid', { params })
      .then(r => setData(r.data.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [year, month, companyId]);

  const getDayOfWeek = (day: number): string => {
    const date = new Date(year, month - 1, day);
    return DAYS_WEEK[date.getDay() === 6 ? 0 : date.getDay() + 1] || '';
  };

  const isWeekend = (day: number): boolean => {
    const date = new Date(year, month - 1, day);
    const dow = date.getDay();
    return dow === 5;
  };

  const handleExport = () => {
    if (!data) return;
    const headers = ['الاسم', 'الكود', 'الشركة'];
    for (let d = 1; d <= daysInMonth; d++) headers.push(String(d));
    headers.push('حضور', 'غياب', 'تأخير', 'إجازات');

    const rows = data.employees.map((emp: any) => {
      const row: string[] = [emp.employee_name, emp.employee_code, emp.company_name];
      for (let d = 1; d <= daysInMonth; d++) row.push(STATUS_FULL_LABELS[emp.days[d]] || '—');
      row.push(String(emp.present_count), String(emp.absent_count), String(emp.late_count), String(emp.leave_count));
      return row;
    });

    const ths = headers.map(h => `<th style="background:#059669;color:white;padding:6px 8px;border:1px solid #065f46;font-size:10px;text-align:center;direction:rtl;white-space:nowrap;">${h}</th>`).join('');
    const trs = rows.map((row, i) => {
      const bg = i % 2 ? '#f0fdf4' : '#ffffff';
      const tds = row.map(c => `<td style="padding:4px 6px;border:1px solid #d1d5db;font-size:10px;text-align:center;background:${bg};direction:rtl;white-space:nowrap;">${c}</td>`).join('');
      return `<tr>${tds}</tr>`;
    }).join('');
    const html = `<html dir="rtl"><head><meta charset="UTF-8"><style>table{border-collapse:collapse;}</style></head><body><table border="1" cellpadding="0" cellspacing="0"><tr><td colspan="${headers.length}" style="background:#065f46;color:white;padding:10px;font-size:14px;font-weight:bold;text-align:center;">التحضير الشجري — ${year}/${month}</td></tr><tr>${ths}</tr>${trs}</table></body></html>`;
    const blob = new Blob([html], { type: 'application/vnd.ms-excel;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `attendance-grid-${year}-${month}.xls`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const totalPresent = data?.employees?.reduce((s: number, e: any) => s + e.present_count, 0) || 0;
  const totalAbsent = data?.employees?.reduce((s: number, e: any) => s + e.absent_count, 0) || 0;
  const totalLate = data?.employees?.reduce((s: number, e: any) => s + e.late_count, 0) || 0;

  const years = [];
  for (let y = now.getFullYear(); y >= now.getFullYear() - 3; y--) years.push(y);

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">التحضير اليومي الشجري</h1>
          <p className="text-gray-500 text-sm mt-1">جدول حضور وغياب الموظفين خلال الشهر</p>
        </div>
        <Button onClick={handleExport} variant="outline" className="gap-2">
          <Download className="w-4 h-4" /> تصدير CSV
        </Button>
      </div>

      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <CalendarCheck className="w-4 h-4 text-gray-400" />
            <select value={year} onChange={e => setYear(Number(e.target.value))} className="border-2 border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:border-primary-500 outline-none">
              {years.map(y => <option key={y} value={y}>{y}</option>)}
            </select>
            <select value={month} onChange={e => setMonth(Number(e.target.value))} className="border-2 border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:border-primary-500 outline-none">
              {MONTHS.map((m, i) => <option key={i + 1} value={i + 1}>{m}</option>)}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <Building2 className="w-4 h-4 text-gray-400" />
            <select value={companyId} onChange={e => setCompanyId(e.target.value ? Number(e.target.value) : '')} className="border-2 border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:border-primary-500 outline-none">
              <option value="">كل الشركات</option>
              {companies.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
        </div>
      </Card>

      <div className="flex flex-wrap items-center gap-3 text-xs">
        {Object.entries(STATUS_COLORS).filter(([k]) => k !== 'absent').map(([k, cls]) => (
          <span key={k} className={`px-2 py-1 rounded-full font-medium ${cls}`}>{STATUS_FULL_LABELS[k] || k}</span>
        ))}
        <span className="px-2 py-1 rounded-full font-medium bg-red-500 text-white">غياب</span>
        <span className="px-2 py-1 rounded-full font-medium bg-gray-200 text-gray-500">عطلة</span>
      </div>

      {data && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Card className="p-3 text-center">
            <div className="text-2xl font-bold text-primary-600">{data.employees?.length || 0}</div>
            <div className="text-xs text-gray-500">الموظفين</div>
          </Card>
          <Card className="p-3 text-center">
            <div className="text-2xl font-bold text-green-600">{totalPresent}</div>
            <div className="text-xs text-gray-500">أيام الحضور</div>
          </Card>
          <Card className="p-3 text-center">
            <div className="text-2xl font-bold text-red-600">{totalAbsent}</div>
            <div className="text-xs text-gray-500">أيام الغياب</div>
          </Card>
          <Card className="p-3 text-center">
            <div className="text-2xl font-bold text-yellow-600">{totalLate}</div>
            <div className="text-xs text-gray-500">أيام التأخير</div>
          </Card>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-40">
          <div className="w-8 h-8 border-3 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" />
        </div>
      ) : data && data.employees?.length > 0 ? (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="bg-primary-600 text-white sticky top-0 z-10">
                  <th className="px-2 py-2 text-right font-semibold sticky right-0 bg-primary-600 z-20 min-w-[120px]">الاسم</th>
                  <th className="px-2 py-2 text-right font-semibold bg-primary-600">الكود</th>
                  <th className="px-2 py-2 text-right font-semibold bg-primary-600">الشركة</th>
                  {Array.from({ length: daysInMonth }, (_, i) => i + 1).map(d => (
                    <th key={d} className={`px-1 py-2 text-center font-semibold min-w-[28px] ${isWeekend(d) ? 'bg-primary-700' : ''}`}>
                      <div>{d}</div>
                      <div className="text-[9px] opacity-70">{getDayOfWeek(d)}</div>
                    </th>
                  ))}
                  <th className="px-2 py-2 text-center font-semibold bg-primary-700">ح</th>
                  <th className="px-2 py-2 text-center font-semibold bg-primary-700">غ</th>
                  <th className="px-2 py-2 text-center font-semibold bg-primary-700">م</th>
                </tr>
              </thead>
              <tbody>
                {data.employees.map((emp: any) => (
                  <tr key={emp.employee_id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-2 py-1.5 font-medium text-gray-900 sticky right-0 bg-white z-10 whitespace-nowrap">{emp.employee_name}</td>
                    <td className="px-2 py-1.5 text-gray-500 font-mono">{emp.employee_code}</td>
                    <td className="px-2 py-1.5 text-gray-500 whitespace-nowrap">{emp.company_name}</td>
                    {Array.from({ length: daysInMonth }, (_, i) => i + 1).map(d => {
                      const status = emp.days[d];
                      const weekend = isWeekend(d);
                      return (
                        <td key={d} className={`px-0.5 py-1 text-center ${weekend && !status ? 'bg-gray-100' : ''}`}>
                          {status ? (
                            <span className={`inline-flex items-center justify-center w-5 h-5 rounded text-[10px] font-bold ${STATUS_COLORS[status] || 'bg-gray-200'}`}>
                              {STATUS_LABELS[status] || '?'}
                            </span>
                          ) : weekend ? (
                            <span className="inline-flex items-center justify-center w-5 h-5 rounded text-[10px] text-gray-300">—</span>
                          ) : (
                            <span className="inline-flex items-center justify-center w-5 h-5 rounded text-[10px] font-bold bg-red-500 text-white">غ</span>
                          )}
                        </td>
                      );
                    })}
                    <td className="px-2 py-1.5 text-center font-bold text-green-600 bg-green-50">{emp.present_count}</td>
                    <td className="px-2 py-1.5 text-center font-bold text-red-600 bg-red-50">{emp.absent_count}</td>
                    <td className="px-2 py-1.5 text-center font-bold text-yellow-600 bg-yellow-50">{emp.late_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : (
        <Card className="p-12 text-center text-gray-400">
          <CalendarCheck className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>لا توجد بيانات تحضير لهذا الشهر</p>
        </Card>
      )}
    </div>
  );
}
