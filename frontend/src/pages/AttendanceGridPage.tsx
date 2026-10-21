import { useState, useEffect, useMemo } from 'react';
import { CalendarCheck, Download, Building2, CalendarRange, RotateCcw, AlertTriangle } from 'lucide-react';
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

const toISO = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

const monthRange = (y: number, m: number) => ({
  start: toISO(new Date(y, m - 1, 1)),
  end: toISO(new Date(y, m, 0)),
});

export default function AttendanceGridPage() {
  const now = new Date();
  const defaultRange = monthRange(now.getFullYear(), now.getMonth() + 1);

  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [periodId, setPeriodId] = useState<string>('');
  const [startDate, setStartDate] = useState(defaultRange.start);
  const [endDate, setEndDate] = useState(defaultRange.end);
  const [companyId, setCompanyId] = useState<number | ''>('');
  const [data, setData] = useState<any>(null);
  const [companies, setCompanies] = useState<any[]>([]);
  const [periods, setPeriods] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get('/companies').then(r => setCompanies(r.data.data || [])).catch(() => {});
    api.get('/periods').then(r => setPeriods(r.data.data || [])).catch(() => {});
  }, []);

  useEffect(() => {
    if (!startDate || !endDate) return;
    setLoading(true);
    setError('');
    const params: any = { start_date: startDate, end_date: endDate };
    if (companyId) params.company_id = companyId;
    api.get('/reports/attendance-grid', { params })
      .then(r => setData(r.data.data))
      .catch((e: any) => {
        setData(null);
        setError(e.response?.data?.message || 'تعذر تحميل بيانات التحضير');
      })
      .finally(() => setLoading(false));
  }, [startDate, endDate, companyId]);

  const dates: any[] = data?.dates || [];

  const handlePeriodChange = (value: string) => {
    setPeriodId(value);
    if (!value) return;
    const p = periods.find(x => String(x.id) === value);
    if (p) {
      setStartDate(p.start_date);
      setEndDate(p.end_date);
      const d = new Date(p.start_date);
      setYear(d.getFullYear());
      setMonth(d.getMonth() + 1);
    }
  };

  const handleMonthJump = (y: number, m: number) => {
    setYear(y);
    setMonth(m);
    setPeriodId('');
    const r = monthRange(y, m);
    setStartDate(r.start);
    setEndDate(r.end);
  };

  const handleStartChange = (v: string) => {
    setStartDate(v);
    setPeriodId('');
  };

  const handleEndChange = (v: string) => {
    setEndDate(v);
    setPeriodId('');
  };

  const resetFilters = () => {
    const y = now.getFullYear();
    const m = now.getMonth() + 1;
    setYear(y);
    setMonth(m);
    setPeriodId('');
    setCompanyId('');
    const r = monthRange(y, m);
    setStartDate(r.start);
    setEndDate(r.end);
  };

  const rangeDays = useMemo(() => {
    const s = new Date(startDate);
    const e = new Date(endDate);
    if (isNaN(s.getTime()) || isNaN(e.getTime()) || e < s) return 0;
    return Math.round((e.getTime() - s.getTime()) / 86400000) + 1;
  }, [startDate, endDate]);

  const totalPresent = data?.employees?.reduce((s: number, e: any) => s + e.present_count, 0) || 0;
  const totalAbsent = data?.employees?.reduce((s: number, e: any) => s + e.absent_count, 0) || 0;
  const totalLate = data?.employees?.reduce((s: number, e: any) => s + e.late_count, 0) || 0;
  const totalLeave = data?.employees?.reduce((s: number, e: any) => s + e.leave_count, 0) || 0;

  const years = [];
  for (let y = now.getFullYear() + 1; y >= now.getFullYear() - 4; y--) years.push(y);

  const handleExport = () => {
    if (!data || !dates.length) return;
    const headers = ['الاسم', 'الكود', 'الشركة'];
    dates.forEach((d: any, idx: number) => {
      const prev = idx > 0 ? dates[idx - 1] : null;
      const newMonth = !prev || prev.month !== d.month;
      headers.push(newMonth ? `${d.day} ${MONTHS[d.month - 1]}` : String(d.day));
    });
    headers.push('حضور', 'غياب', 'تأخير', 'إجازات');

    const rows: string[][] = data.employees.map((emp: any) => {
      const row: string[] = [emp.employee_name, emp.employee_code, emp.company_name];
      dates.forEach((d: any) => row.push(STATUS_FULL_LABELS[emp.days[d.date]] || '—'));
      row.push(String(emp.present_count), String(emp.absent_count), String(emp.late_count), String(emp.leave_count));
      return row;
    });

    const title = `التحضير الشجري — ${startDate} إلى ${endDate}`;
    const ths = headers.map(h => `<th style="background:#059669;color:white;padding:6px 8px;border:1px solid #065f46;font-size:10px;text-align:center;direction:rtl;white-space:nowrap;">${h}</th>`).join('');
    const trs = rows.map((row: string[], i: number) => {
      const bg = i % 2 ? '#f0fdf4' : '#ffffff';
      const tds = row.map((c: string) => `<td style="padding:4px 6px;border:1px solid #d1d5db;font-size:10px;text-align:center;background:${bg};direction:rtl;white-space:nowrap;">${c}</td>`).join('');
      return `<tr>${tds}</tr>`;
    }).join('');
    const html = `<html dir="rtl"><head><meta charset="UTF-8"><style>table{border-collapse:collapse;}</style></head><body><table border="1" cellpadding="0" cellspacing="0"><tr><td colspan="${headers.length}" style="background:#065f46;color:white;padding:10px;font-size:14px;font-weight:bold;text-align:center;">${title}</td></tr><tr>${ths}</tr>${trs}</table></body></html>`;
    const blob = new Blob([html], { type: 'application/vnd.ms-excel;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `attendance-grid-${startDate}_${endDate}.xls`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const selectedPeriod = periods.find(p => String(p.id) === periodId);

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">التحضير اليومي الشجري</h1>
          <p className="text-gray-500 text-sm mt-1">جدول حضور وغياب الموظفين خلال الفترة المحددة</p>
        </div>
        <Button onClick={handleExport} variant="outline" className="gap-2" disabled={!dates.length}>
          <Download className="w-4 h-4" /> تصدير Excel
        </Button>
      </div>

      <Card className="p-4 space-y-3">
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500 flex items-center gap-1">
              <CalendarRange className="w-3.5 h-3.5" /> الفترة المالية
            </label>
            <select
              value={periodId}
              onChange={e => handlePeriodChange(e.target.value)}
              className="h-10 border-2 border-gray-200 rounded-lg px-3 text-sm focus:border-primary-500 outline-none min-w-[220px]"
            >
              <option value="">تحديد يدوي (من - إلى)</option>
              {periods.map(p => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.start_date} ← {p.end_date}) - {p.status_name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">من تاريخ</label>
            <input
              type="date"
              value={startDate}
              onChange={e => handleStartChange(e.target.value)}
              className="h-10 px-3 rounded-lg border-2 border-gray-200 text-sm focus:border-primary-500 outline-none"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">إلى تاريخ</label>
            <input
              type="date"
              value={endDate}
              onChange={e => handleEndChange(e.target.value)}
              className="h-10 px-3 rounded-lg border-2 border-gray-200 text-sm focus:border-primary-500 outline-none"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500 flex items-center gap-1">
              <Building2 className="w-3.5 h-3.5" /> الشركة
            </label>
            <select
              value={companyId}
              onChange={e => setCompanyId(e.target.value ? Number(e.target.value) : '')}
              className="h-10 border-2 border-gray-200 rounded-lg px-3 text-sm focus:border-primary-500 outline-none min-w-[170px]"
            >
              <option value="">كل الشركات</option>
              {companies.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500 flex items-center gap-1">
              <CalendarCheck className="w-3.5 h-3.5" /> الشهر
            </label>
            <div className="flex items-center gap-2">
              <select
                value={year}
                onChange={e => handleMonthJump(Number(e.target.value), month)}
                className="h-10 border-2 border-gray-200 rounded-lg px-3 text-sm focus:border-primary-500 outline-none"
              >
                {years.map(y => <option key={y} value={y}>{y}</option>)}
              </select>
              <select
                value={month}
                onChange={e => handleMonthJump(year, Number(e.target.value))}
                className="h-10 border-2 border-gray-200 rounded-lg px-3 text-sm focus:border-primary-500 outline-none"
              >
                {MONTHS.map((m, i) => <option key={i + 1} value={i + 1}>{m}</option>)}
              </select>
            </div>
          </div>

          <Button variant="ghost" onClick={resetFilters} className="gap-2 h-10">
            <RotateCcw className="w-4 h-4" /> إعادة تعيين
          </Button>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs text-gray-600 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
          <span className="font-medium text-gray-800">
            الفترة المعروضة: {startDate} إلى {endDate}
          </span>
          <span className="text-gray-400">|</span>
          <span>{rangeDays > 0 ? `${rangeDays} يوم` : 'مدة غير صالحة'}</span>
          {selectedPeriod ? (
            <>
              <span className="text-gray-400">|</span>
              <span className="text-primary-700 font-medium">
                الفترة المالية: {selectedPeriod.name} ({selectedPeriod.status_name})
              </span>
            </>
          ) : data?.period_label ? (
            <>
              <span className="text-gray-400">|</span>
              <span className="text-primary-700 font-medium">
                فترة مفتوحة تغطي المدى: {data.period_label}
              </span>
            </>
          ) : null}
        </div>
      </Card>

      {error && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">
          <AlertTriangle className="w-4 h-4" /> {error}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3 text-xs">
        {Object.entries(STATUS_COLORS).filter(([k]) => k !== 'absent').map(([k, cls]) => (
          <span key={k} className={`px-2 py-1 rounded-full font-medium ${cls}`}>{STATUS_FULL_LABELS[k] || k}</span>
        ))}
        <span className="px-2 py-1 rounded-full font-medium bg-red-500 text-white">غياب</span>
        <span className="px-2 py-1 rounded-full font-medium bg-gray-200 text-gray-500">عطلة (الجمعة)</span>
      </div>

      {data && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
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
          <Card className="p-3 text-center">
            <div className="text-2xl font-bold text-purple-600">{totalLeave}</div>
            <div className="text-xs text-gray-500">أيام الإجازات</div>
          </Card>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-40">
          <div className="w-8 h-8 border-3 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" />
        </div>
      ) : data && data.employees?.length > 0 && dates.length > 0 ? (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="bg-primary-600 text-white sticky top-0 z-10">
                  <th className="px-2 py-2 text-right font-semibold sticky right-0 bg-primary-600 z-20 min-w-[120px]">الاسم</th>
                  <th className="px-2 py-2 text-right font-semibold bg-primary-600">الكود</th>
                  <th className="px-2 py-2 text-right font-semibold bg-primary-600">الشركة</th>
                  {dates.map((d: any, idx: number) => {
                    const prev = idx > 0 ? dates[idx - 1] : null;
                    const newMonth = !prev || prev.month !== d.month;
                    return (
                      <th key={d.date} className={`px-1 py-2 text-center font-semibold min-w-[28px] ${d.is_holiday ? 'bg-primary-700' : ''}`}>
                        {newMonth && <div className="text-[8px] opacity-60">{MONTHS[d.month - 1]}</div>}
                        <div>{d.day}</div>
                        <div className="text-[9px] opacity-70">{d.weekday_short}</div>
                      </th>
                    );
                  })}
                  <th className="px-2 py-2 text-center font-semibold bg-primary-700">ح</th>
                  <th className="px-2 py-2 text-center font-semibold bg-primary-700">غ</th>
                  <th className="px-2 py-2 text-center font-semibold bg-primary-700">م</th>
                  <th className="px-2 py-2 text-center font-semibold bg-primary-700">إ</th>
                </tr>
              </thead>
              <tbody>
                {data.employees.map((emp: any) => (
                  <tr key={emp.employee_id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-2 py-1.5 font-medium text-gray-900 sticky right-0 bg-white z-10 whitespace-nowrap">{emp.employee_name}</td>
                    <td className="px-2 py-1.5 text-gray-500 font-mono">{emp.employee_code}</td>
                    <td className="px-2 py-1.5 text-gray-500 whitespace-nowrap">{emp.company_name}</td>
                    {dates.map((d: any) => {
                      const status = emp.days[d.date];
                      return (
                        <td key={d.date} className={`px-0.5 py-1 text-center ${d.is_holiday && !status ? 'bg-gray-100' : ''}`}>
                          {status ? (
                            <span className={`inline-flex items-center justify-center w-5 h-5 rounded text-[10px] font-bold ${STATUS_COLORS[status] || 'bg-gray-200'}`}>
                              {STATUS_LABELS[status] || '?'}
                            </span>
                          ) : d.is_holiday ? (
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
                    <td className="px-2 py-1.5 text-center font-bold text-purple-600 bg-purple-50">{emp.leave_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : (
        <Card className="p-12 text-center text-gray-400">
          <CalendarCheck className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>لا توجد بيانات تحضير في هذه الفترة</p>
        </Card>
      )}
    </div>
  );
}
