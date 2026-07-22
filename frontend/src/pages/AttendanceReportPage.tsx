import { useState, useEffect, useMemo } from 'react';
import { Download, Search, Filter, ChevronDown, ChevronUp, FileText } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import api from '@/api/client';
import logoB64 from '@/lib/logoBase64';

function fmt(n: number) { return (n || 0).toLocaleString('en'); }

const STATUS_MAP: Record<string, string> = { present: 'حاضر', late: 'متأخر', absent: 'غائب', sick: 'مرضي', annual_leave: 'إجازة', unpaid_leave: 'إج. بدون راتب' };
const STATUS_COLORS: Record<string, string> = { present: 'bg-green-100 text-green-700', late: 'bg-yellow-100 text-yellow-700', absent: 'bg-red-100 text-red-700', sick: 'bg-blue-100 text-blue-700', annual_leave: 'bg-purple-100 text-purple-700', unpaid_leave: 'bg-gray-100 text-gray-700' };

function downloadExcel(filename: string, title: string, headers: string[], rows: string[][]) {
  const ths = headers.map(h => `<th style="background:#059669;color:white;padding:8px 12px;border:1px solid #065f46;font-weight:bold;font-size:11px;text-align:right;direction:rtl;">${h}</th>`).join('');
  const trs = rows.map((row, i) => {
    const bg = i % 2 ? '#f0fdf4' : '#ffffff';
    const tds = row.map(c => `<td style="padding:6px 10px;border:1px solid #d1d5db;font-size:11px;text-align:right;background:${bg};direction:rtl;white-space:nowrap;">${c}</td>`).join('');
    return `<tr>${tds}</tr>`;
  }).join('');
  const html = `<html dir="rtl" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel">
<head><meta charset="UTF-8">
<!--[if gte mso 9]><xml><x:ExcelWorkbook><x:ExcelWorksheets><x:ExcelWorksheet><x:Name>${title}</x:Name></x:ExcelWorksheet></x:ExcelWorksheets></x:ExcelWorkbook></xml><![endif]-->
<style>table{border-collapse:collapse;}</style></head>
<body><table border="1" cellpadding="0" cellspacing="0">
<tr><td colspan="${headers.length}" style="background:#065f46;color:white;padding:10px;font-size:14px;font-weight:bold;text-align:center;">${title}</td></tr>
<tr><td colspan="${headers.length}" style="padding:6px;font-size:10px;color:#666;text-align:center;">طلعت هائل للخدمات والاستشارات الزراعية — التاريخ: ${new Date().toLocaleDateString('ar-EG')} — عدد السجلات: ${rows.length}</td></tr>
<tr>${ths}</tr>${trs}
</table></body></html>`;
  const blob = new Blob([html], { type: 'application/vnd.ms-excel;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

function openPDF(title: string, headers: string[], rows: string[][], summaryItems?: { l: string; v: string; c?: string }[]) {
  const ths = headers.map(h => `<th style="padding:7px 8px;background:#ecfdf5;border:1px solid #d1d5db;font-size:10px;text-align:right;font-weight:bold;color:#374151;white-space:nowrap;">${h}</th>`).join('');
  const trs = rows.map((row, i) => {
    const bg = i % 2 ? '#f9fafb' : '#ffffff';
    const tds = row.map(c => `<td style="padding:5px 8px;border:1px solid #e5e7eb;font-size:10px;text-align:right;background:${bg};">${c}</td>`).join('');
    return `<tr>${tds}</tr>`;
  }).join('');
  let statsHtml = '';
  if (summaryItems?.length) {
    const cells = summaryItems.map(s => `<td style="text-align:center;padding:8px 6px;background:#ecfdf5;border:1px solid #d1fae5;border-radius:6px;"><div style="font-size:15px;font-weight:bold;color:${s.c || '#065f46'};">${s.v}</div><div style="font-size:9px;color:#6b7280;">${s.l}</div></td>`).join('');
    statsHtml = `<table width="100%" cellpadding="0" cellspacing="4" style="margin-bottom:15px;"><tr>${cells}</tr></table>`;
  }
  const html = `<!DOCTYPE html><html><head><meta charset="UTF-8"><title>${title}</title>
    <style>*{margin:0;padding:0;box-sizing:border-box;}@media print{.no-print{display:none!important;}body{margin:0;}}body{font-family:Arial,Tahoma,sans-serif;background:#f3f4f6;}.toolbar{position:fixed;top:0;left:0;right:0;z-index:9999;background:#1f2937;padding:8px 20px;display:flex;align-items:center;gap:10px;direction:rtl;}.toolbar button{padding:6px 16px;border:none;border-radius:6px;cursor:pointer;font-size:13px;color:white;}.btn-print{background:#059669;}.btn-close{background:#dc2626;}.toolbar span{color:white;font-size:12px;margin-right:auto;}.content{max-width:1200px;margin:55px auto 20px;background:white;padding:20px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.1);}</style></head><body>
    <div class="toolbar no-print"><button class="btn-print" onclick="window.print()">طباعة / حفظ PDF</button><button class="btn-close" onclick="window.close()">اغلاق</button><span>${title}</span></div>
    <div class="content">
      <div style="direction:rtl;text-align:center;margin-bottom:15px;border-bottom:3px solid #059669;padding-bottom:12px;">
        <img src="${logoB64}" style="width:65px;height:65px;border-radius:14px;margin-bottom:6px;" />
        <div style="font-size:22px;font-weight:bold;color:#065f46;">طلعت هائل للخدمات والاستشارات الزراعية</div>
        <div style="font-size:11px;color:#9ca3af;">TALAAT HAIL FOR AGRICULTURAL SERVICES AND CONSULTATIONS</div>
        <div style="font-size:16px;font-weight:bold;color:#111827;margin-top:10px;">${title}</div>
        <div style="font-size:11px;color:#6b7280;margin-top:3px;">التاريخ: ${new Date().toLocaleDateString('ar-EG')} | عدد السجلات: ${rows.length}</div>
      </div>
      ${statsHtml}
      <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;direction:rtl;font-family:Arial,Tahoma,sans-serif;">
        <thead><tr>${ths}</tr></thead><tbody>${trs}</tbody>
      </table>
      <div style="direction:rtl;text-align:center;margin-top:15px;border-top:1px solid #e5e7eb;padding-top:8px;">
        <span style="font-size:9px;color:#9ca3af;">طلعت هائل للخدمات والاستشارات الزراعية | نظام إدارة الخدمات الزراعية | ${new Date().toLocaleString('ar-EG')}</span>
      </div>
    </div></body></html>`;
  const win = window.open('', '_blank');
  if (win) { win.document.write(html); win.document.close(); }
}

export default function AttendanceReportPage() {
  const [loading, setLoading] = useState(true);
  const [companies, setCompanies] = useState<any[]>([]);
  const [employees, setEmployees] = useState<any[]>([]);
  const [data, setData] = useState<any>(null);
  const [view, setView] = useState<'summary' | 'detail'>('summary');
  const [expandedEmp, setExpandedEmp] = useState<number | null>(null);

  const [filters, setFilters] = useState({
    company_id: '',
    employee_id: '',
    date_from: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0],
    date_to: new Date().toISOString().split('T')[0],
  });

  const loadData = () => {
    setLoading(true);
    const params: any = {};
    if (filters.company_id) params.company_id = filters.company_id;
    if (filters.employee_id) params.employee_id = filters.employee_id;
    params.date_from = filters.date_from;
    params.date_to = filters.date_to;

    Promise.all([
      api.get('/companies').catch(() => ({ data: { data: [] } })),
      api.get('/employees').catch(() => ({ data: { data: [] } })),
      api.get('/reports/attendance-detail', { params }).catch(() => ({ data: { data: null } })),
    ]).then(([cRes, eRes, aRes]) => {
      setCompanies(cRes.data.data || []);
      setEmployees(eRes.data.data || []);
      setData(aRes.data.data);
    }).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, []);

  const filteredEmployees = useMemo(() => {
    if (!data?.employees_summary) return [];
    let emps = data.employees_summary;
    if (filters.company_id) emps = emps.filter((e: any) => e.company_id === Number(filters.company_id));
    return emps;
  }, [data, filters.company_id]);

  const filteredRecords = useMemo(() => {
    if (!data?.records) return [];
    let recs = data.records;
    if (filters.employee_id) recs = recs.filter((r: any) => r.employee_id === Number(filters.employee_id));
    return recs;
  }, [data, filters.employee_id]);

  const empDetailRecords = (empId: number) => filteredRecords.filter((r: any) => r.employee_id === empId);

  const exportExcel = () => {
    const title = view === 'summary' ? 'ملخص الحضور حسب الموظف' : 'تفاصيل الحضور اليومية';
    const filename = view === 'summary'
      ? `attendance_summary_${filters.date_from}_${filters.date_to}.xls`
      : `attendance_detail_${filters.date_from}_${filters.date_to}.xls`;

    if (view === 'summary') {
      const headers = ['#', 'الاسم', 'الكود', 'الشركة', 'أيام العمل', 'حضور', 'تأخر', 'إجازة', 'غياب', 'نسبة الحضور'];
      const rows = filteredEmployees.map((e: any, i: number) => {
        const rate = e.working_days > 0 ? Math.round((e.present + e.late) / e.working_days * 100) : 0;
        return [String(i + 1), e.employee_name, e.employee_code, e.company_name,
          String(e.working_days), String(e.present), String(e.late), String(e.leave), String(e.absent), `${rate}%`];
      });
      downloadExcel(filename, title, headers, rows);
    } else {
      const headers = ['#', 'الموظف', 'الكود', 'الشركة', 'التاريخ', 'الحالة', 'الفترة', 'وقت الحضور', 'وقت الانصراف', 'ملاحظات'];
      const rows = filteredRecords.map((rec: any, i: number) => [
        String(i + 1), rec.employee_name, rec.employee_code, rec.company_name,
        rec.date, STATUS_MAP[rec.status] || rec.status,
        rec.shift_type === 'morning' ? 'صباحي' : rec.shift_type === 'evening' ? 'مسائي' : rec.shift_type || '—',
        rec.check_in || '—', rec.check_out || '—', rec.notes || '',
      ]);
      downloadExcel(filename, title, headers, rows);
    }
  };

  const exportPDF = () => {
    const title = view === 'summary' ? 'ملخص الحضور حسب الموظف' : 'تفاصيل الحضور اليومية';

    if (view === 'summary') {
      const headers = ['#', 'الاسم', 'الكود', 'الشركة', 'أيام العمل', 'حضور', 'تأخر', 'إجازة', 'غياب', 'النسبة'];
      const rows = filteredEmployees.map((e: any, i: number) => {
        const rate = e.working_days > 0 ? Math.round((e.present + e.late) / e.working_days * 100) : 0;
        return [String(i + 1), e.employee_name, e.employee_code, e.company_name,
          String(e.working_days), String(e.present), String(e.late), String(e.leave), String(e.absent), `${rate}%`];
      });
      const summaryItems = [
        { l: 'أيام العمل', v: String(data?.working_days || 0), c: '#6b7280' },
        { l: 'الحضور', v: fmt(filteredEmployees.reduce((s: number, e: any) => s + e.present, 0)), c: '#059669' },
        { l: 'التأخر', v: fmt(filteredEmployees.reduce((s: number, e: any) => s + e.late, 0)), c: '#d97706' },
        { l: 'الغياب', v: fmt(filteredEmployees.reduce((s: number, e: any) => s + e.absent, 0)), c: '#dc2626' },
        { l: 'الإجازات', v: fmt(filteredEmployees.reduce((s: number, e: any) => s + e.leave, 0)), c: '#7c3aed' },
        { l: 'نسبة الحضور', v: `${data?.summary?.attendance_rate || 0}%`, c: '#2563eb' },
      ];
      openPDF(`تقرير ${title} — ${filters.date_from} إلى ${filters.date_to}`, headers, rows, summaryItems);
    } else {
      const headers = ['#', 'الموظف', 'الكود', 'الشركة', 'التاريخ', 'الحالة', 'الفترة', 'وقت الحضور', 'وقت الانصراف', 'ملاحظات'];
      const rows = filteredRecords.map((rec: any, i: number) => [
        String(i + 1), rec.employee_name, rec.employee_code, rec.company_name,
        rec.date, STATUS_MAP[rec.status] || rec.status,
        rec.shift_type === 'morning' ? 'صباحي' : rec.shift_type === 'evening' ? 'مسائي' : rec.shift_type || '—',
        rec.check_in || '—', rec.check_out || '—', rec.notes || '',
      ]);
      openPDF(`تقرير ${title} — ${filters.date_from} إلى ${filters.date_to}`, headers, rows);
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-3 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">تقرير سحب الحضور</h1>
          <p className="text-gray-500 text-sm mt-1">تقرير تفصيلي للحضور والغياب حسب الشركة والفترة والموظف</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={exportExcel}><Download className="w-4 h-4" /> تصدير Excel</Button>
          <Button variant="outline" onClick={exportPDF}><FileText className="w-4 h-4" /> تصدير PDF</Button>
        </div>
      </div>

      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex items-center gap-2"><Filter className="w-4 h-4 text-gray-500" /><span className="text-sm font-medium text-gray-700">الفلاتر:</span></div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">الشركة</label>
              <select value={filters.company_id} onChange={e => setFilters({ ...filters, company_id: e.target.value, employee_id: '' })}
                className="h-9 px-3 rounded-lg border border-gray-300 text-sm bg-white">
                <option value="">جميع الشركات</option>
                {companies.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">الموظف</label>
              <select value={filters.employee_id} onChange={e => setFilters({ ...filters, employee_id: e.target.value })}
                className="h-9 px-3 rounded-lg border border-gray-300 text-sm bg-white min-w-[180px]">
                <option value="">جميع الموظفين</option>
                {employees.filter((e: any) => !filters.company_id || e.company_id === Number(filters.company_id)).map((e: any) => (
                  <option key={e.id} value={e.id}>{e.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">من تاريخ</label>
              <input type="date" value={filters.date_from} onChange={e => setFilters({ ...filters, date_from: e.target.value })}
                className="h-9 px-3 rounded-lg border border-gray-300 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">إلى تاريخ</label>
              <input type="date" value={filters.date_to} onChange={e => setFilters({ ...filters, date_to: e.target.value })}
                className="h-9 px-3 rounded-lg border border-gray-300 text-sm" />
            </div>
            <Button onClick={loadData} className="h-9"><Search className="w-4 h-4" /> بحث</Button>
          </div>
        </CardContent>
      </Card>

      {data && (
        <div className="grid grid-cols-3 lg:grid-cols-6 gap-3">
          <Card className="bg-gray-50 border-gray-200"><CardContent className="p-3 text-center"><p className="text-xl font-bold text-gray-700">{data.working_days || 0}</p><p className="text-xs text-gray-500">أيام العمل</p></CardContent></Card>
          <Card className="bg-green-50 border-green-200"><CardContent className="p-3 text-center"><p className="text-xl font-bold text-green-700">{fmt(data.summary?.total_present || 0)}</p><p className="text-xs text-green-600">الحضور</p></CardContent></Card>
          <Card className="bg-yellow-50 border-yellow-200"><CardContent className="p-3 text-center"><p className="text-xl font-bold text-yellow-700">{fmt(data.summary?.total_late || 0)}</p><p className="text-xs text-yellow-600">التأخر</p></CardContent></Card>
          <Card className="bg-red-50 border-red-200"><CardContent className="p-3 text-center"><p className="text-xl font-bold text-red-700">{fmt(data.summary?.total_absent || 0)}</p><p className="text-xs text-red-600">الغياب</p></CardContent></Card>
          <Card className="bg-purple-50 border-purple-200"><CardContent className="p-3 text-center"><p className="text-xl font-bold text-purple-700">{fmt(data.summary?.total_leave || 0)}</p><p className="text-xs text-purple-600">الإجازات</p></CardContent></Card>
          <Card className="bg-blue-50 border-blue-200"><CardContent className="p-3 text-center"><p className="text-xl font-bold text-blue-700">{data.summary?.attendance_rate || 0}%</p><p className="text-xs text-blue-600">نسبة الحضور</p></CardContent></Card>
        </div>
      )}

      <div className="flex gap-2">
        <button onClick={() => setView('summary')} className={`px-4 py-2 rounded-lg text-sm font-medium ${view === 'summary' ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600'}`}>ملخص حسب الموظف</button>
        <button onClick={() => setView('detail')} className={`px-4 py-2 rounded-lg text-sm font-medium ${view === 'detail' ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600'}`}>التفاصيل اليومية</button>
      </div>

      {view === 'summary' && (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-primary-600 text-white">
                  <th className="px-4 py-3 text-right font-semibold">#</th>
                  <th className="px-4 py-3 text-right font-semibold">الموظف</th>
                  <th className="px-4 py-3 text-right font-semibold">الكود</th>
                  <th className="px-4 py-3 text-right font-semibold">الشركة</th>
                  <th className="px-4 py-3 text-center font-semibold">أيام العمل</th>
                  <th className="px-4 py-3 text-center font-semibold">حضور</th>
                  <th className="px-4 py-3 text-center font-semibold">تأخر</th>
                  <th className="px-4 py-3 text-center font-semibold">إجازة</th>
                  <th className="px-4 py-3 text-center font-semibold">غياب</th>
                  <th className="px-4 py-3 text-center font-semibold">النسبة</th>
                  <th className="px-4 py-3 text-center font-semibold">تفاصيل</th>
                </tr>
              </thead>
              <tbody>
                {filteredEmployees.map((emp: any, i: number) => {
                  const rate = emp.working_days > 0 ? Math.round((emp.present + emp.late) / emp.working_days * 100) : 0;
                  const isExpanded = expandedEmp === emp.employee_id;
                  return (
                    <>
                      <tr key={emp.employee_id} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="px-4 py-3 text-gray-500">{i + 1}</td>
                        <td className="px-4 py-3 font-medium">{emp.employee_name}</td>
                        <td className="px-4 py-3 text-gray-600 text-xs">{emp.employee_code}</td>
                        <td className="px-4 py-3"><span className="px-2 py-1 rounded-full text-xs bg-gray-100 text-gray-700">{emp.company_name}</span></td>
                        <td className="px-4 py-3 text-center text-gray-600">{emp.working_days}</td>
                        <td className="px-4 py-3 text-center"><span className="font-bold text-green-600">{emp.present}</span></td>
                        <td className="px-4 py-3 text-center"><span className="font-bold text-yellow-600">{emp.late}</span></td>
                        <td className="px-4 py-3 text-center"><span className="font-bold text-purple-600">{emp.leave}</span></td>
                        <td className="px-4 py-3 text-center"><span className="font-bold text-red-600">{emp.absent}</span></td>
                        <td className="px-4 py-3 text-center">
                          <span className={`px-2 py-1 rounded-full text-xs font-bold ${rate >= 80 ? 'bg-green-100 text-green-700' : rate >= 50 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'}`}>
                            {rate}%
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <button onClick={() => setExpandedEmp(isExpanded ? null : emp.employee_id)} className="p-1 rounded-lg hover:bg-gray-100 text-gray-500">
                            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                          </button>
                        </td>
                      </tr>
                      {isExpanded && empDetailRecords(emp.employee_id).map((rec: any) => (
                        <tr key={`d-${rec.id}`} className="bg-gray-50 border-b border-gray-100">
                          <td className="px-4 py-2"></td>
                          <td colSpan={3} className="px-4 py-2 text-xs text-gray-500">{rec.date}</td>
                          <td colSpan={2} className="px-4 py-2 text-center">
                            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[rec.status] || 'bg-gray-100 text-gray-600'}`}>
                              {STATUS_MAP[rec.status] || rec.status}
                            </span>
                          </td>
                          <td className="px-4 py-2 text-xs text-gray-500">{rec.shift_type === 'morning' ? 'صباحي' : 'مسائي'}</td>
                          <td className="px-4 py-2 text-xs text-gray-500">{rec.check_in || '—'}</td>
                          <td className="px-4 py-2 text-xs text-gray-500">{rec.check_out || '—'}</td>
                          <td className="px-4 py-2 text-xs text-gray-400">{rec.notes || ''}</td>
                          <td></td>
                        </tr>
                      ))}
                    </>
                  );
                })}
                {filteredEmployees.length === 0 && (
                  <tr><td colSpan={10} className="text-center py-8 text-gray-400">لا توجد بيانات حضور</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {view === 'detail' && (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-primary-600 text-white">
                  <th className="px-4 py-3 text-right font-semibold">#</th>
                  <th className="px-4 py-3 text-right font-semibold">الموظف</th>
                  <th className="px-4 py-3 text-right font-semibold">الشركة</th>
                  <th className="px-4 py-3 text-right font-semibold">التاريخ</th>
                  <th className="px-4 py-3 text-center font-semibold">الحالة</th>
                  <th className="px-4 py-3 text-center font-semibold">الفترة</th>
                  <th className="px-4 py-3 text-center font-semibold">وقت الحضور</th>
                  <th className="px-4 py-3 text-center font-semibold">وقت الانصراف</th>
                  <th className="px-4 py-3 text-right font-semibold">ملاحظات</th>
                </tr>
              </thead>
              <tbody>
                {filteredRecords.map((rec: any, i: number) => (
                  <tr key={rec.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-500">{i + 1}</td>
                    <td className="px-4 py-3 font-medium">{rec.employee_name}</td>
                    <td className="px-4 py-3"><span className="px-2 py-1 rounded-full text-xs bg-gray-100 text-gray-700">{rec.company_name}</span></td>
                    <td className="px-4 py-3 text-gray-600">{rec.date}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[rec.status] || 'bg-gray-100 text-gray-600'}`}>
                        {STATUS_MAP[rec.status] || rec.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center text-xs text-gray-500">{rec.shift_type === 'morning' ? 'صباحي' : rec.shift_type === 'evening' ? 'مسائي' : rec.shift_type || '—'}</td>
                    <td className="px-4 py-3 text-center text-xs text-gray-500">{rec.check_in || '—'}</td>
                    <td className="px-4 py-3 text-center text-xs text-gray-500">{rec.check_out || '—'}</td>
                    <td className="px-4 py-3 text-xs text-gray-400">{rec.notes || ''}</td>
                  </tr>
                ))}
                {filteredRecords.length === 0 && (
                  <tr><td colSpan={9} className="text-center py-8 text-gray-400">لا توجد سجلات حضور</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
