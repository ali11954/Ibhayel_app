import logoB64 from './logoBase64';

function getArabicMonth(monthStr: string) {
  const [y, m] = monthStr.split('-').map(Number);
  const names = ['يناير','فبراير','مارس','أبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر'];
  return `${names[m - 1]} ${y}`;
}

function fmt(n: number) { return (n || 0).toLocaleString('en'); }
const F = 'Arial,Tahoma,Helvetica,sans-serif';

// ===== Column definitions =====

export interface ColDef { key: string; label: string; width?: number; default?: boolean; sum?: boolean }

export const contractorColumns: ColDef[] = [
  { key: 'employee_name', label: 'العامل', default: true },
  { key: 'company_name', label: 'الشركة', default: true },
  { key: 'total_salary_revenue', label: 'الراتب الشامل', default: true, sum: true },
  { key: 'base_salary', label: 'الراتب الأساسي', default: true, sum: true },
  { key: 'present_days', label: 'أيام الحضور', default: true },
  { key: 'basic_paid', label: 'المبلغ المستحق', default: true, sum: true },
  { key: 'resident_paid', label: 'بدل الإقامة', default: true, sum: true },
  { key: 'overtime_amount', label: 'بدل الإضافي', default: true, sum: true },
  { key: 'insurance_cost', label: 'التأمين', default: true, sum: true },
  { key: 'health_cost', label: 'صندوق صحي', default: true, sum: true },
  { key: 'clothing_cost', label: 'بدل الملابس', default: true, sum: true },
  { key: 'profit', label: 'الربح', default: true, sum: true },
];

export const attendanceColumns: ColDef[] = [
  { key: 'date', label: 'التاريخ', default: true },
  { key: 'present', label: 'حاضر', default: true, sum: true },
  { key: 'late', label: 'متأخر', default: true, sum: true },
  { key: 'absent', label: 'غائب', default: true, sum: true },
  { key: 'sick', label: 'مرضي', default: true, sum: true },
  { key: 'annual_leave', label: 'إجازة', default: true, sum: true },
];

export const employeesColumns: ColDef[] = [
  { key: 'num', label: '#', default: true },
  { key: 'name', label: 'الاسم', default: true },
  { key: 'job_title', label: 'المسمى الوظيفي', default: true },
  { key: 'company', label: 'الشركة', default: true },
  { key: 'nationality', label: 'الجنسية', default: true },
  { key: 'salary', label: 'الراتب', default: true },
  { key: 'total_salary', label: 'الراتب الشامل', default: true },
  { key: 'phone', label: 'الهاتف', default: false },
  { key: 'card_number', label: 'رقم البطاقة', default: false },
  { key: 'hire_date', label: 'تاريخ التعيين', default: false },
];

export const financialColumns: ColDef[] = [
  { key: 'type', label: 'النوع', default: true },
  { key: 'count', label: 'العدد', default: true, sum: true },
  { key: 'total', label: 'المبلغ', default: true, sum: true },
];

export const evaluationsColumns: ColDef[] = [
  { key: 'name', label: 'الاسم', default: true },
  { key: 'job_title', label: 'المسمى', default: true },
  { key: 'eval_count', label: 'عدد التقييمات', default: true, sum: true },
  { key: 'avg_score', label: 'متوسط الدرجة', default: true },
  { key: 'rating', label: 'التقييم', default: true },
];

export const overviewColumns: ColDef[] = [
  { key: 'company', label: 'الشركة', default: true },
  { key: 'count', label: 'عدد الموظفين', default: true, sum: true },
];

export const workPlansColumns: ColDef[] = [
  { key: 'title', label: 'العنوان', default: true },
  { key: 'plan_type', label: 'النوع', default: true },
  { key: 'status', label: 'الحالة', default: true },
  { key: 'creator', label: 'أنشأه', default: true },
  { key: 'date', label: 'التاريخ', default: true },
];

// ===== Row extractors =====

const TN: Record<string,string> = { advance:'سلفة', overtime:'عمل إضافي', deduction:'خصم', penalty:'غرامة', income:'دخل', expense:'مصروف', buffet:'بوفيه', restaurant:'مطعم', cafeteria:'كافتيريا', advance_settlement:'تسوية سلفة' };
const PT: Record<string,string> = { daily:'يومي', monthly:'شهري', yearly:'سنوي' };
const SN: Record<string,string> = { completed:'مكتمل', in_progress:'قيد التنفيذ', pending:'قيد الانتظار' };

export function contractorRow(e: any): Record<string, string> {
  return {
    employee_name: e.employee_name||'', company_name: e.company_name||'',
    total_salary_revenue: fmt(e.total_salary_revenue), base_salary: fmt(e.base_salary),
    present_days: `${e.present_days}/${e.days_in_month}`, basic_paid: fmt(e.basic_paid),
    resident_paid: fmt(e.resident_paid), overtime_amount: fmt(e.overtime_amount||0),
    insurance_cost: fmt(e.insurance_cost), health_cost: fmt(e.health_cost),
    clothing_cost: fmt(e.clothing_cost),
    profit: `<span style="color:${(e.profit||0)>=0?'#059669':'#dc2626'};font-weight:bold;">${fmt(e.profit)}</span>`,
    _profit_num: e.profit || 0,
  } as any;
}

export function attendanceRow(d: any): Record<string, string> {
  return { date: d.date||'', present: String(d.present||0), late: String(d.late||0), absent: String(d.absent||0), sick: String(d.sick||0), annual_leave: String(d.annual_leave||0) };
}

export function employeesRow(e: any, i: number): Record<string, string> {
  return { num: String(i+1), name: e.employee_name||e.name||'', job_title: e.job_title||'', company: e.company_name||e.company||'', nationality: e.nationality||'', salary: e.salary?f(e.salary):'', total_salary: e.total_salary?f(e.total_salary):'', phone: e.phone||'', card_number: e.card_number||'', hire_date: e.hire_date||'' };
}

export function financialRow(t: any): Record<string, string> {
  return { type: TN[t.type]||t.type, count: String(t.count||0), total: fmt(t.total) };
}

export function evaluationsRow(e: any): Record<string, string> {
  return { name: e.name||'', job_title: e.job_title||'', eval_count: String(e.eval_count||0), avg_score: String(e.avg_score||0), rating: e.rating||'' };
}

export function overviewRow(c: any): Record<string, string> {
  return { company: c.name||'', count: String(c.count||0) };
}

export function workPlansRow(p: any): Record<string, string> {
  return { title: p.title||'', plan_type: PT[p.plan_type]||p.plan_type||'', status: SN[p.status]||p.status||'', creator: p.creator_name||'', date: p.created_at||'' };
}

// ===== Print window =====

export function openPrintWindow(title: string, monthStr: string, columns: ColDef[], data: Record<string, string>[], summaryItems?: {l:string;v:string;c?:string}[]) {
  const date = new Date().toLocaleDateString('ar-EG');

  // Calculate totals for sum columns
  const sumCols = columns.filter(c => c.sum);
  const hasTotals = sumCols.length > 0 && data.length > 0;

  // Build header row
  const ths = columns.map(c => `<th style="padding:7px 8px;background:#ecfdf5;border:1px solid #d1d5db;font-size:10px;text-align:right;font-weight:bold;color:#374151;white-space:nowrap;">${c.label}</th>`).join('');

  // Build data rows
  const trs = data.map((row, i) => {
    const bg = i % 2 ? '#f9fafb' : '#ffffff';
    const tds = columns.map(c => `<td style="padding:5px 8px;border:1px solid #e5e7eb;font-size:10px;text-align:right;background:${bg};">${row[c.key]||''}</td>`).join('');
    return `<tr>${tds}</tr>`;
  }).join('');

  // Build totals row
  let totalsRow = '';
  if (hasTotals) {
    const tds = columns.map(c => {
      if (c.sum) {
        let total = 0;
        data.forEach(row => {
          const val = parseFloat(String(row[c.key]).replace(/[^0-9.-]/g, ''));
          if (!isNaN(val)) total += val;
        });
        const isProfit = c.key === 'profit';
        const color = isProfit ? (total >= 0 ? '#059669' : '#dc2626') : '#111827';
        return `<td style="padding:6px 8px;border:2px solid #059669;background:#d1fae5;font-size:11px;font-weight:bold;text-align:right;color:${color};">إجمالي: ${fmt(total)}</td>`;
      }
      if (c.key === columns.find(cc => cc.sum === undefined || cc.sum === false)?.key) {
        const firstSumIdx = columns.findIndex(cc => cc.sum);
        if (columns.indexOf(c) < firstSumIdx) {
          return `<td style="padding:6px 8px;border:2px solid #059669;background:#d1fae5;font-size:11px;font-weight:bold;text-align:right;color:#065f46;">الإجمالي</td>`;
        }
      }
      return `<td style="padding:6px 8px;border:2px solid #059669;background:#d1fae5;"></td>`;
    }).join('');
    totalsRow = `<tr>${tds}</tr>`;
  }

  // Summary cards
  let statsHtml = '';
  if (summaryItems && summaryItems.length) {
    const cells = summaryItems.map(s => `<td style="text-align:center;padding:8px 6px;background:#ecfdf5;border:1px solid #d1fae5;border-radius:6px;">
      <div style="font-size:15px;font-weight:bold;color:${s.c||'#065f46'};">${s.v}</div>
      <div style="font-size:9px;color:#6b7280;">${s.l}</div>
    </td>`).join('');
    statsHtml = `<table width="100%" cellpadding="0" cellspacing="4" style="margin-bottom:15px;"><tr>${cells}</tr></table>`;
  }

  const html = `<!DOCTYPE html><html><head><meta charset="UTF-8"><title>${title}</title>
    <style>
      *{margin:0;padding:0;box-sizing:border-box;}
      @media print{.no-print{display:none!important;}body{margin:0;}}
      body{font-family:${F};background:#f3f4f6;}
      .toolbar{position:fixed;top:0;left:0;right:0;z-index:9999;background:#1f2937;padding:8px 20px;display:flex;align-items:center;gap:10px;direction:rtl;}
      .toolbar button{padding:6px 16px;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-family:${F};color:white;}
      .btn-print{background:#059669;}.btn-close{background:#dc2626;}
      .toolbar span{color:white;font-size:12px;margin-right:auto;}
      .content{max-width:1100px;margin:55px auto 20px;background:white;padding:20px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.1);}
    </style></head><body>
    <div class="toolbar no-print">
      <button class="btn-print" onclick="window.print()">🖨️ طباعة / حفظ PDF</button>
      <button class="btn-close" onclick="window.close()">✖ إغلاق</button>
      <span>${title} — ${getArabicMonth(monthStr)}</span>
    </div>
    <div class="content">
      <div style="direction:rtl;text-align:center;margin-bottom:15px;border-bottom:3px solid #059669;padding-bottom:12px;">
        <img src="${logoB64}" style="width:65px;height:65px;border-radius:14px;margin-bottom:6px;" />
        <div style="font-size:22px;font-weight:bold;color:#065f46;">طلعت هائل للخدمات والاستشارات الزراعية</div>
        <div style="font-size:11px;color:#9ca3af;">TALAAT HAIL FOR AGRICULTURAL SERVICES AND CONSULTATIONS</div>
        <div style="font-size:16px;font-weight:bold;color:#111827;margin-top:10px;">${title}</div>
        <div style="font-size:11px;color:#6b7280;margin-top:3px;">التاريخ: ${date} | الفترة: ${getArabicMonth(monthStr)} | عدد السجلات: ${data.length}</div>
      </div>
      ${statsHtml}
      <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;direction:rtl;font-family:${F};">
        <thead><tr>${ths}</tr></thead>
        <tbody>${trs}${totalsRow}</tbody>
      </table>
      <div style="direction:rtl;text-align:center;margin-top:15px;border-top:1px solid #e5e7eb;padding-top:8px;">
        <span style="font-size:9px;color:#9ca3af;">طلعت هائل للخدمات والاستشارات الزراعية | نظام إدارة الموارد البشرية | ${new Date().toLocaleString('ar-EG')}</span>
      </div>
    </div></body></html>`;

  const win = window.open('', '_blank');
  if (win) { win.document.write(html); win.document.close(); }
}

export function openEmployeeProfilePDF(emp: any, detailData: any, bankItems: any[]) {
  const date = new Date().toLocaleDateString('ar-EG');
  const sal = detailData?.salaries || [];
  const att = detailData?.attendance || [];
  const evals = detailData?.evaluations || [];
  const txs = detailData?.transactions || [];
  const leaves = detailData?.leaves || [];

  const totalSalaryPaid = sal.reduce((s: number, r: any) => s + (r.net_salary || 0), 0);
  const totalPaid = sal.filter((r: any) => r.is_paid).reduce((s: number, r: any) => s + (r.net_salary || 0), 0);
  const totalOvertime = txs.filter((t: any) => t.transaction_type === 'overtime').reduce((s: number, t: any) => s + (t.amount || 0), 0);
  const totalDeductions = txs.filter((t: any) => t.transaction_type === 'deduction' || t.transaction_type === 'penalty').reduce((s: number, t: any) => s + (t.amount || 0), 0);
  const totalAdvances = txs.filter((t: any) => t.transaction_type === 'advance').reduce((s: number, t: any) => s + (t.amount || 0), 0);
  const totalCafeteria = txs.filter((t: any) => t.transaction_type === 'cafeteria').reduce((s: number, t: any) => s + (t.amount || 0), 0);
  const totalRestaurant = txs.filter((t: any) => t.transaction_type === 'restaurant').reduce((s: number, t: any) => s + (t.amount || 0), 0);

  function miniTable(rows: string[][], headers: string[]) {
    const ths = headers.map(h => `<th style="padding:6px 8px;background:#ecfdf5;border:1px solid #d1d5db;font-size:10px;text-align:right;font-weight:bold;color:#374151;">${h}</th>`).join('');
    const trs = rows.map((row, i) => {
      const bg = i % 2 ? '#f9fafb' : '#ffffff';
      return `<tr>${row.map(c => `<td style="padding:5px 8px;border:1px solid #e5e7eb;font-size:10px;text-align:right;background:${bg};">${c}</td>`).join('')}</tr>`;
    }).join('');
    return `<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;direction:rtl;font-family:${F};"><thead><tr>${ths}</tr></thead><tbody>${trs}</tbody></table>`;
  }

  const statsHtml = `
    <table width="100%" cellpadding="0" cellspacing="4" style="margin-bottom:15px;"><tr>
      <td style="text-align:center;padding:10px 6px;background:#ecfdf5;border:1px solid #d1fae5;border-radius:6px;">
        <div style="font-size:16px;font-weight:bold;color:#065f46;">${fmt(emp.total_salary || emp.salary || 0)}</div>
        <div style="font-size:9px;color:#6b7280;">الراتب الشامل</div>
      </td>
      <td style="text-align:center;padding:10px 6px;background:#ecfdf5;border:1px solid #d1fae5;border-radius:6px;">
        <div style="font-size:16px;font-weight:bold;color:#065f46;">${fmt(emp.basic_salary || 0)}</div>
        <div style="font-size:9px;color:#6b7280;">الراتب الأساسي</div>
      </td>
      <td style="text-align:center;padding:10px 6px;background:#ecfdf5;border:1px solid #d1fae5;border-radius:6px;">
        <div style="font-size:16px;font-weight:bold;color:#065f46;">${fmt(totalPaid)}</div>
        <div style="font-size:9px;color:#6b7280;">إجمالي المدفوعات</div>
      </td>
      <td style="text-align:center;padding:10px 6px;background:#fef2f2;border:1px solid #fecaca;border-radius:6px;">
        <div style="font-size:16px;font-weight:bold;color:#dc2626;">${fmt(totalDeductions)}</div>
        <div style="font-size:9px;color:#6b7280;">الخصومات</div>
      </td>
    </tr></table>`;

  // Profile section
  const profileInfo = [
    ['الكود', emp.code || '—', 'رقم البطاقة', emp.card_number || '—'],
    ['الاسم', emp.name || '—', 'الهاتف', emp.phone || '—'],
    ['المسمى الوظيفي', emp.job_title || '—', 'النوع', emp.employee_type === 'supervisor' ? 'مشرف' : emp.employee_type === 'accountant' ? 'محاسب' : 'عامل'],
    ['الشركة', emp.company_name || '—', 'المنطقة', emp.region || '—'],
    ['تاريخ التعيين', emp.hire_date || '—', 'الحالة', emp.is_active ? 'نشط' : 'غير نشط'],
    ['ساكن', emp.is_resident ? 'نعم' : 'لا', 'المشرف', emp.supervisor_name || '—'],
  ];
  const profileHtml = `<div style="margin-bottom:20px;">
    <h3 style="font-size:14px;font-weight:bold;color:#065f46;border-bottom:2px solid #059669;padding-bottom:6px;margin-bottom:10px;">الملف الشخصي</h3>
    <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;direction:rtl;font-family:${F};">
      ${profileInfo.map(row => `<tr>
        <td style="padding:6px 10px;border:1px solid #e5e7eb;font-size:10px;font-weight:bold;background:#f9fafb;width:20%;text-align:right;">${row[0]}</td>
        <td style="padding:6px 10px;border:1px solid #e5e7eb;font-size:10px;width:30%;text-align:right;">${row[1]}</td>
        <td style="padding:6px 10px;border:1px solid #e5e7eb;font-size:10px;font-weight:bold;background:#f9fafb;width:20%;text-align:right;">${row[2]}</td>
        <td style="padding:6px 10px;border:1px solid #e5e7eb;font-size:10px;width:30%;text-align:right;">${row[3]}</td>
      </tr>`).join('')}
    </table>
  </div>`;

  // Salaries section
  const salariesHtml = sal.length > 0 ? `<div style="margin-bottom:20px;">
    <h3 style="font-size:14px;font-weight:bold;color:#065f46;border-bottom:2px solid #059669;padding-bottom:6px;margin-bottom:10px;">الرواتب (${sal.length})</h3>
    ${miniTable(sal.map((s: any) => [
      s.month_year || '—', fmt(s.basic_salary || 0), fmt(s.resident_allowance || 0), fmt(s.overtime || 0),
      fmt(s.deductions || 0), fmt(s.penalties || 0), fmt(s.cafeteria || 0), fmt(s.restaurant || 0),
      fmt(s.advances || 0), fmt(s.net_salary || 0), s.is_paid ? 'مدفوع' : 'معلق'
    ]), ['الشهر', 'الأساسي', 'الإقامة', 'الإضافي', 'الخصومات', 'الغرامات', 'الكافتيريا', 'المطعم', 'السلف', 'الصافي', 'الحالة'])}
  </div>` : '';

  // Attendance section
  const attHtml = att.length > 0 ? `<div style="margin-bottom:20px;">
    <h3 style="font-size:14px;font-weight:bold;color:#065f46;border-bottom:2px solid #059669;padding-bottom:6px;margin-bottom:10px;">الحضور والغياب</h3>
    ${miniTable(att.slice(0, 30).map((a: any) => [
      a.date || '—', a.status === 'present' ? 'حاضر' : a.status === 'absent' ? 'غائب' : a.status === 'late' ? 'متأخر' : a.status,
      a.check_in || '—', a.check_out || '—', a.notes || '—'
    ]), ['التاريخ', 'الحالة', 'وقت الحضور', 'وقت الانصراف', 'ملاحظات'])}
  </div>` : '';

  // Evaluations section
  const evalsHtml = evals.length > 0 ? `<div style="margin-bottom:20px;">
    <h3 style="font-size:14px;font-weight:bold;color:#065f46;border-bottom:2px solid #059669;padding-bottom:6px;margin-bottom:10px;">التقييمات (${evals.length})</h3>
    ${miniTable(evals.map((e: any) => [
      e.evaluation_date || e.date || '—', e.rating || '—', fmt(e.total_score || e.score || 0),
      e.evaluator_name || e.supervisor_name || '—', e.notes || '—'
    ]), ['التاريخ', 'التقييم', 'الدرجة', 'المقيّم', 'ملاحظات'])}
  </div>` : '';

  // Transactions section
  const txNames: Record<string, string> = { advance: 'سلفة', overtime: 'عمل إضافي', deduction: 'خصم', penalty: 'غرامة', income: 'دخل', expense: 'مصروف', restaurant: 'مطعم', cafeteria: 'كافتيريا', advance_settlement: 'تسوية سلفة' };
  const txHtml = txs.length > 0 ? `<div style="margin-bottom:20px;">
    <h3 style="font-size:14px;font-weight:bold;color:#065f46;border-bottom:2px solid #059669;padding-bottom:6px;margin-bottom:10px;">المعاملات المالية (${txs.length})</h3>
    ${miniTable(txs.slice(0, 30).map((t: any) => [
      t.date || t.created_at?.split('T')[0] || '—', txNames[t.transaction_type] || t.transaction_type || '—',
      fmt(t.amount || 0), t.description || '—', t.payment_method || '—'
    ]), ['التاريخ', 'النوع', 'المبلغ', 'الوصف', 'طريقة الدفع'])}
  </div>` : '';

  // Leaves section
  const leavesHtml = leaves.length > 0 ? `<div style="margin-bottom:20px;">
    <h3 style="font-size:14px;font-weight:bold;color:#065f46;border-bottom:2px solid #059669;padding-bottom:6px;margin-bottom:10px;">الإجازات (${leaves.length})</h3>
    ${miniTable(leaves.map((l: any) => [
      l.start_date || '—', l.end_date || '—', l.leave_type_name || l.leave_type || '—',
      `${l.total_days || 0} يوم`, l.status === 'approved' ? 'معتمدة' : l.status === 'rejected' ? 'مرفوضة' : 'قيد المراجعة',
      l.reason || '—'
    ]), ['من', 'إلى', 'النوع', 'الأيام', 'الحالة', 'السبب'])}
  </div>` : '';

  // Bank section
  const bankHtml = bankItems.length > 0 ? `<div style="margin-bottom:20px;">
    <h3 style="font-size:14px;font-weight:bold;color:#065f46;border-bottom:2px solid #059669;padding-bottom:6px;margin-bottom:10px;">المعلومات البنكية</h3>
    ${miniTable(bankItems.map((b: any) => [
      b.bank_name || '—', b.account_number || '—', b.iban || '—',
      b.branch_name || '—', b.account_type_name || b.account_type || '—', b.currency || '—',
      b.is_primary ? 'أساسي' : '—'
    ]), ['البنك', 'رقم الحساب', 'الآيبان', 'الفرع', 'النوع', 'العملة', 'الأساسي'])}
  </div>` : '';

  const html = `<!DOCTYPE html><html><head><meta charset="UTF-8"><title>ملف الموظف — ${emp.name}</title>
    <style>
      *{margin:0;padding:0;box-sizing:border-box;}
      @media print{.no-print{display:none!important;}body{margin:0;}@page{size:A4 portrait;margin:15mm;}}
      body{font-family:${F};background:#f3f4f6;}
      .toolbar{position:fixed;top:0;left:0;right:0;z-index:9999;background:#1f2937;padding:8px 20px;display:flex;align-items:center;gap:10px;direction:rtl;}
      .toolbar button{padding:6px 16px;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-family:${F};color:white;}
      .btn-print{background:#059669;}.btn-close{background:#dc2626;}
      .toolbar span{color:white;font-size:12px;margin-right:auto;}
      .content{max-width:1100px;margin:55px auto 20px;background:white;padding:20px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.1);}
    </style></head><body>
    <div class="toolbar no-print">
      <button class="btn-print" onclick="window.print()">🖨️ طباعة / حفظ PDF</button>
      <button class="btn-close" onclick="window.close()">✖ إغلاق</button>
      <span>ملف الموظف — ${emp.name}</span>
    </div>
    <div class="content">
      <div style="direction:rtl;text-align:center;margin-bottom:15px;border-bottom:3px solid #059669;padding-bottom:12px;">
        <img src="${logoB64}" style="width:65px;height:65px;border-radius:14px;margin-bottom:6px;" />
        <div style="font-size:22px;font-weight:bold;color:#065f46;">طلعت هائل للخدمات والاستشارات الزراعية</div>
        <div style="font-size:11px;color:#9ca3af;">TALAAT HAIL FOR AGRICULTURAL SERVICES AND CONSULTATIONS</div>
        <div style="font-size:16px;font-weight:bold;color:#111827;margin-top:10px;">ملف الموظف — ${emp.name}</div>
        <div style="font-size:11px;color:#6b7280;margin-top:3px;">التاريخ: ${date} | الكود: ${emp.code || '—'} | الوظيفة: ${emp.job_title || '—'}</div>
      </div>
      ${statsHtml}
      ${profileHtml}
      ${salariesHtml}
      ${attHtml}
      ${evalsHtml}
      ${txHtml}
      ${leavesHtml}
      ${bankHtml}
      <div style="direction:rtl;text-align:center;margin-top:15px;border-top:1px solid #e5e7eb;padding-top:8px;">
        <span style="font-size:9px;color:#9ca3af;">طلعت هائل للخدمات والاستشارات الزراعية | نظام إدارة الموارد البشرية | ${new Date().toLocaleString('ar-EG')}</span>
      </div>
    </div></body></html>`;

  const win = window.open('', '_blank');
  if (win) { win.document.write(html); win.document.close(); }
}
