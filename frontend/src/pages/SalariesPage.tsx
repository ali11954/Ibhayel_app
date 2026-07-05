import { useState, useEffect, Fragment } from 'react';
import { Calculator, CheckCircle, Clock, DollarSign, Trash2, Printer } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Modal } from '@/components/ui/modal';
import { formatNum } from '@/lib/utils';
import api from '@/api/client';

export default function SalariesPage() {
  const [salaries, setSalaries] = useState<any[]>([]);
  const [employees, setEmployees] = useState<any[]>([]);
  const [companies, setCompanies] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [calcModal, setCalcModal] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [monthYear, setMonthYear] = useState(new Date().toISOString().slice(0, 7));
  const [companyFilter, setCompanyFilter] = useState('');
  const [calculating, setCalculating] = useState(false);

  const loadData = () => {
    Promise.all([
      api.get(`/financial/salaries?month_year=${monthYear}`),
      api.get('/employees'),
      api.get('/companies'),
    ]).then(([sRes, eRes, cRes]) => {
      setSalaries(sRes.data.data || []);
      setEmployees(eRes.data.data || []);
      setCompanies(cRes.data.data || []);
    }).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, [monthYear]);

  const handleCalculate = async () => {
    setCalculating(true);
    try {
      const res = await api.post('/financial/salary-calculation', {
        month_year: monthYear,
        company_id: companyFilter ? Number(companyFilter) : null,
      });
      setCalcModal(false);
      loadData();
      alert(res.data.message);
    } catch (err: any) {
      alert(err.response?.data?.message || 'حدث خطأ');
    } finally {
      setCalculating(false);
    }
  };

  const handlePay = async (id: number) => {
    const method = prompt('اختر طريقة الدفع:\n1 - نقدي (الصندوق)\n2 - بنكي (البنك)\n\nأدخل 1 أو 2:', '1');
    if (!method || (method !== '1' && method !== '2')) return;
    const payment_method = method === '1' ? 'cash' : 'bank';
    try {
      await api.post(`/financial/salaries/${id}/pay`, { payment_method });
      loadData();
    } catch (err: any) {
      alert(err.response?.data?.message || 'حدث خطأ أثناء الدفع');
    }
  };

  const printVoucher = async (id: number) => {
    try {
      const res = await api.get(`/financial/salaries/${id}/voucher`);
      const v = res.data.data;
      const win = window.open('', '_blank', 'width=800,height=600');
      if (!win) return;
      win.document.write(`<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><title>سند صرف راتب</title>
        <style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Arial',sans-serif;padding:30px;color:#000}
        .voucher{border:2px solid #000;padding:20px;max-width:650px;margin:0 auto}
        .header{text-align:center;border-bottom:2px solid #000;padding-bottom:15px;margin-bottom:15px}
        .header h1{font-size:20px;margin-bottom:5px}.header h2{font-size:14px;color:#555}
        .row{display:flex;justify-content:space-between;margin:6px 0;font-size:13px}
        .row .label{font-weight:bold;color:#555;flex:1}.row .value{font-weight:bold;flex:1;text-align:left}
        .section{border:1px solid #ccc;padding:10px;margin:10px 0;border-radius:4px}
        .section h3{font-size:13px;margin-bottom:8px;color:#333;border-bottom:1px solid #eee;padding-bottom:5px}
        .amount-box{border:2px solid #000;padding:12px;text-align:center;margin:15px 0;font-size:22px;font-weight:bold;background:#f9f9f9}
        .footer{margin-top:30px;display:flex;justify-content:space-between}
        .footer .sig{text-align:center;width:30%}.footer .line{border-bottom:1px solid #000;margin-top:40px;font-size:11px}
        @media print{body{padding:10px}.voucher{border-width:1px}}</style></head><body>
        <div class="voucher">
        <div class="header"><h1>سند صرف راتب</h1><h2>طلعت هائل للخدمات والاستشارات الزراعية</h2></div>
        <div class="row"><span class="label">رقم السند:</span><span class="value">#${v.salary_id}</span></div>
        <div class="row"><span class="label">التاريخ:</span><span class="value">${v.paid_date || '—'}</span></div>
        <div class="row"><span class="label">الشهر:</span><span class="value">${v.month_year}</span></div>
        <div class="row"><span class="label">اسم الموظف:</span><span class="value">${v.employee_name}</span></div>
        <div class="row"><span class="label">الكود:</span><span class="value">${v.employee_code}</span></div>
        <div class="row"><span class="label">الشركة:</span><span class="value">${v.company_name}</span></div>
        <div class="row"><span class="label">طريقة الدفع:</span><span class="value">${v.payment_method_name}</span></div>
        
        <div class="section"><h3>تفاصيل الراتب</h3>
        <div class="row"><span class="label">الراتب الأساسي:</span><span class="value">${formatNum(v.basic_salary_amount)} ر.ي</span></div>
        <div class="row"><span class="label">بدل سكن:</span><span class="value">${formatNum(v.resident_allowance_amount)} ر.ي</span></div>
        <div class="row"><span class="label">الإضافي:</span><span class="value">${formatNum(v.overtime_amount)} ر.ي</span></div>
        </div>
        
        <div class="section"><h3>تكاليف صاحب العمل</h3>
        <div class="row"><span class="label">تأمينات:</span><span class="value">${formatNum(v.insurance_amount)} ر.ي</span></div>
        <div class="row"><span class="label">بطاقة صحية:</span><span class="value">${formatNum(v.health_card_amount)} ر.ي</span></div>
        <div class="row"><span class="label">بدل ملابس:</span><span class="value">${formatNum(v.clothing_allowance_amount)} ر.ي</span></div>
        </div>
        
        <div class="section"><h3>خصومات أخرى</h3>
        <div class="row"><span class="label">السلف:</span><span class="value">${formatNum(v.advance_amount)} ر.ي</span></div>
        <div class="row"><span class="label">الخصومات:</span><span class="value">${formatNum(v.deduction_amount)} ر.ي</span></div>
        <div class="row"><span class="label">الغرامات:</span><span class="value">${formatNum(v.penalty_amount)} ر.ي</span></div>
        ${v.cafeteria_deduction > 0 ? `<div class="row"><span class="label">بوفية (${v.cafeteria_supplier_name || ''}):</span><span class="value">${formatNum(v.cafeteria_deduction)} ر.ي</span></div>` : ''}
        ${v.restaurant_deduction > 0 ? `<div class="row"><span class="label">مطعم (${v.restaurant_supplier_name || ''}):</span><span class="value">${formatNum(v.restaurant_deduction)} ر.ي</span></div>` : ''}
        </div>
        
        <div class="amount-box">${formatNum(v.total_salary)} ريال يمني فقط</div>
        <div class="footer">
          <div class="sig"><div class="line">توقيع المستلم</div></div>
          <div class="sig"><div class="line">توقيع المحاسب</div></div>
          <div class="sig"><div class="line">توقيع مدير الموارد البشرية</div></div>
        </div></div>
        <script>window.onload=function(){window.print();window.close()}</script></body></html>`);
      win.document.close();
    } catch (err: any) { alert('خطأ في تحميل بيانات السند'); }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('هل أنت متأكد من حذف هذا الراتب؟')) return;
    await api.delete(`/financial/salaries/${id}`);
    loadData();
  };

  const filtered = salaries;
  const totalNet = filtered.reduce((s, sal) => s + (sal.total_salary || 0), 0);
  const totalPaid = filtered.filter(s => s.is_paid).reduce((s, sal) => s + (sal.total_salary || 0), 0);
  const totalUnpaid = filtered.filter(s => !s.is_paid).reduce((s, sal) => s + (sal.total_salary || 0), 0);

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-8 h-8 border-3 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">احتساب الرواتب</h1>
          <p className="text-gray-500 text-sm mt-1">حساب رواتب العمال حسب أيام الدوام والبدلات والخصومات</p>
        </div>
        <Button onClick={() => setCalcModal(true)}><Calculator className="w-4 h-4" /> احتساب الرواتب</Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card><CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary-100 flex items-center justify-center"><DollarSign className="w-5 h-5 text-primary-600" /></div>
            <div><p className="text-xl font-bold">{filtered.length}</p><p className="text-xs text-gray-500">الرواتب المحسوبة</p></div>
          </div>
        </CardContent></Card>
        <Card><CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-green-100 flex items-center justify-center"><CheckCircle className="w-5 h-5 text-green-600" /></div>
            <div><p className="text-xl font-bold text-green-600">{formatNum(totalPaid)}</p><p className="text-xs text-gray-500">مدفوع</p></div>
          </div>
        </CardContent></Card>
        <Card><CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center"><Clock className="w-5 h-5 text-amber-600" /></div>
            <div><p className="text-xl font-bold text-amber-600">{formatNum(totalUnpaid)}</p><p className="text-xs text-gray-500">غير مدفوع</p></div>
          </div>
        </CardContent></Card>
        <Card><CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center"><DollarSign className="w-5 h-5 text-blue-600" /></div>
            <div><p className="text-xl font-bold text-blue-600">{formatNum(totalNet)}</p><p className="text-xs text-gray-500">الإجمالي</p></div>
          </div>
        </CardContent></Card>
      </div>

      {/* Month Selector */}
      <div className="flex gap-3 items-center">
        <input type="month" value={monthYear} onChange={(e) => setMonthYear(e.target.value)}
          className="h-10 px-4 rounded-lg border-2 border-gray-200 text-sm focus:border-primary-500 outline-none" />
        <span className="text-sm text-gray-500">{salaries.length} راتب</span>
      </div>

      {/* Salaries Grouped by Company */}
      {(() => {
        const grouped: Record<string, any[]> = {};
        filtered.forEach((sal) => {
          const company = sal.company_name || 'بدون شركة';
          if (!grouped[company]) grouped[company] = [];
          grouped[company].push(sal);
        });
        return Object.entries(grouped).map(([company, companySalaries]) => {
          const companyTotal = companySalaries.reduce((s, sal) => s + (sal.total_salary || 0), 0);
          return (
            <div key={company} className="space-y-0">
              <Card>
                <div className="px-4 py-2.5 bg-primary-600 text-white flex items-center justify-between rounded-t-2xl">
                  <span className="font-bold text-sm">{company}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-xs bg-white/20 px-2.5 py-0.5 rounded-full">{companySalaries.length} موظف</span>
                    <span className="text-xs bg-white/20 px-2.5 py-0.5 rounded-full font-bold">{formatNum(companyTotal)} ر.ي</span>
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-gray-50 text-right">
                        <th className="px-3 py-2 font-semibold text-gray-600">الكود</th>
                        <th className="px-3 py-2 font-semibold text-gray-600">الموظف</th>
                        <th className="px-3 py-2 font-semibold text-gray-600">أيام الدوام</th>
                        <th className="px-3 py-2 font-semibold text-gray-600">الراتب الأساسي</th>
                        <th className="px-3 py-2 font-semibold text-gray-600">بدل الإقامة</th>
                        <th className="px-3 py-2 font-semibold text-gray-600">الإضافات</th>
                        <th className="px-3 py-2 font-semibold text-gray-600">الخصومات</th>
                        <th className="px-3 py-2 font-semibold text-gray-600">الصافي</th>
                        <th className="px-3 py-2 font-semibold text-gray-600">الحالة</th>
                        <th className="px-3 py-2 font-semibold text-gray-600">إجراءات</th>
                      </tr>
                    </thead>
                    <tbody>
                      {companySalaries.map((sal) => {
                        const totalExtras = sal.overtime_amount || 0;
                        const totalDeductions = (sal.advance_amount || 0) + (sal.deduction_amount || 0) + (sal.penalty_amount || 0) + (sal.cafeteria_deduction || 0) + (sal.restaurant_deduction || 0);
                        const isExpanded = expandedId === sal.id;
                        return (
                          <Fragment key={sal.id}>
                            <tr className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer" onClick={() => setExpandedId(isExpanded ? null : sal.id)}>
                              <td className="px-3 py-2.5 font-mono text-primary-600 font-bold text-xs">{sal.employee_code}</td>
                              <td className="px-3 py-2.5 font-medium">{sal.employee_name}</td>
                              <td className="px-3 py-2.5 text-center"><span className="bg-primary-100 text-primary-700 px-2 py-0.5 rounded-full text-xs font-bold">{sal.attendance_days}/30</span></td>
                              <td className="px-3 py-2.5 font-medium text-blue-600">{formatNum(sal.basic_salary_amount || 0)}</td>
                              <td className="px-3 py-2.5 text-green-600">{formatNum(sal.resident_allowance_amount || 0)}</td>
                              <td className="px-3 py-2.5 text-blue-500">{formatNum(totalExtras)}</td>
                              <td className="px-3 py-2.5 text-red-500">{formatNum(totalDeductions)}</td>
                              <td className="px-3 py-2.5 font-bold text-lg text-primary-600">{formatNum(sal.total_salary || 0)}</td>
                              <td className="px-3 py-2.5">
                                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${sal.is_paid ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
                                  {sal.is_paid ? 'مدفوع' : 'غير مدفوع'}
                                </span>
                              </td>
                              <td className="px-3 py-2.5" onClick={(e) => e.stopPropagation()}>
                                <div className="flex items-center gap-1">
                                  {!sal.is_paid && <button onClick={() => handlePay(sal.id)} className="p-1.5 rounded-lg hover:bg-green-50 text-green-500 text-xs">دفع</button>}
                                  {sal.is_paid && <button onClick={() => printVoucher(sal.id)} className="p-1.5 rounded-lg hover:bg-blue-50 text-blue-500" title="سند صرف"><Printer className="w-4 h-4" /></button>}
                                  <button onClick={() => handleDelete(sal.id)} className="p-1.5 rounded-lg hover:bg-red-50 text-red-500"><Trash2 className="w-4 h-4" /></button>
                                </div>
                              </td>
                            </tr>
                            {isExpanded && (
                              <tr key={`${sal.id}-detail`}>
                                <td colSpan={10} className="px-6 py-4 bg-gray-50">
                                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
                                    <div className="bg-white rounded-xl p-4 border border-gray-200">
                                      <h4 className="font-bold text-green-700 mb-3 text-sm">الإيرادات</h4>
                                      <div className="space-y-2 text-sm">
                                        <div className="flex justify-between"><span>الراتب الأساسي ({sal.attendance_days} يوم)</span><span className="font-bold">{formatNum(sal.basic_salary_amount || 0)}</span></div>
                                        {sal.resident_allowance_amount > 0 && <div className="flex justify-between"><span>بدل الإقامة</span><span className="font-bold text-green-600">{formatNum(sal.resident_allowance_amount)}</span></div>}
                                        {sal.overtime_amount > 0 && <div className="flex justify-between"><span>العمل الإضافي</span><span className="font-bold text-blue-600">{formatNum(sal.overtime_amount)}</span></div>}
                                        <div className="flex justify-between pt-2 border-t font-bold text-green-700">
                                          <span>إجمالي الإيرادات</span>
                                          <span>{formatNum(sal.total_earnings || 0)}</span>
                                        </div>
                                      </div>
                                    </div>
                                    <div className="bg-white rounded-xl p-4 border border-gray-200">
                                      <h4 className="font-bold text-red-700 mb-3 text-sm">الخصومات</h4>
                                      <div className="space-y-2 text-sm">
                                        {sal.advance_amount > 0 && <div className="flex justify-between"><span>السلف</span><span className="font-bold text-red-600">{formatNum(sal.advance_amount)}</span></div>}
                                        {sal.deduction_amount > 0 && <div className="flex justify-between"><span>خصومات أخرى</span><span className="font-bold text-red-600">{formatNum(sal.deduction_amount)}</span></div>}
                                        {sal.penalty_amount > 0 && <div className="flex justify-between"><span>الغرامات</span><span className="font-bold text-red-600">{formatNum(sal.penalty_amount)}</span></div>}
                                        {sal.cafeteria_deduction > 0 && <div className="flex justify-between"><span>البوفية</span><span className="font-bold text-red-600">{formatNum(sal.cafeteria_deduction)}</span></div>}
                                        {sal.restaurant_deduction > 0 && <div className="flex justify-between"><span>المطعم</span><span className="font-bold text-red-600">{formatNum(sal.restaurant_deduction)}</span></div>}
                                        {totalDeductions === 0 && <p className="text-gray-400 text-center py-4">لا توجد خصومات</p>}
                                        <div className="flex justify-between pt-2 border-t font-bold text-red-700">
                                          <span>إجمالي الخصومات</span>
                                          <span>{formatNum(totalDeductions)}</span>
                                        </div>
                                      </div>
                                    </div>
                                    <div className="bg-white rounded-xl p-4 border border-gray-200">
                                      <h4 className="font-bold text-blue-700 mb-3 text-sm">تكاليف صاحب العمل</h4>
                                      <div className="space-y-2 text-sm">
                                        {sal.insurance_amount > 0 && <div className="flex justify-between"><span>تأمينات</span><span className="font-bold text-blue-600">{formatNum(sal.insurance_amount)}</span></div>}
                                        {sal.health_card_amount > 0 && <div className="flex justify-between"><span>بطاقة صحية</span><span className="font-bold text-blue-600">{formatNum(sal.health_card_amount)}</span></div>}
                                        {sal.clothing_allowance_amount > 0 && <div className="flex justify-between"><span>بدل ملابس</span><span className="font-bold text-blue-600">{formatNum(sal.clothing_allowance_amount)}</span></div>}
                                        {(!sal.insurance_amount && !sal.health_card_amount && !sal.clothing_allowance_amount) && <p className="text-gray-400 text-center py-4">لا توجد تكاليف</p>}
                                      </div>
                                    </div>
                                    <div className="bg-primary-50 rounded-xl p-4 border border-primary-200">
                                      <h4 className="font-bold text-primary-700 mb-3 text-sm">الملخص</h4>
                                      <div className="space-y-3">
                                        <div className="bg-white rounded-lg p-3">
                                          <p className="text-xs text-gray-500">الراتب الأساسي الشامل</p>
                                          <p className="text-lg font-bold">{formatNum(sal.base_salary || 0)}</p>
                                        </div>
                                        <div className="bg-white rounded-lg p-3">
                                          <p className="text-xs text-gray-500">أيام الدوام الفعلية</p>
                                          <p className="text-lg font-bold">{sal.attendance_days} يوم من 30</p>
                                          <div className="w-full h-2 bg-gray-200 rounded-full mt-2 overflow-hidden">
                                            <div className="h-full bg-primary-500 rounded-full" style={{ width: `${Math.min(100, (sal.attendance_days / 30) * 100)}%` }} />
                                          </div>
                                        </div>
                                        <div className="flex justify-between items-center bg-green-100 rounded-lg p-3">
                                          <span className="font-bold text-green-700">الصافي</span>
                                          <span className="text-2xl font-bold text-green-700">{formatNum(sal.total_salary || 0)}</span>
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                </td>
                              </tr>
                            )}
                          </Fragment>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>
          );
        });
      })()}
      {filtered.length === 0 && (
        <Card>
          <div className="text-center py-12 text-gray-400">
            <Calculator className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p>لا توجد رواتب محسوبة لهذا الشهر</p>
            <p className="text-sm mt-1">اضغط "احتساب الرواتب" لبدء الحساب</p>
          </div>
        </Card>
      )}

      {/* Calculation Modal */}
      <Modal open={calcModal} onClose={() => setCalcModal(false)} title="احتساب الرواتب الشهرية">
        <div className="space-y-4">
          <div className="bg-blue-50 rounded-xl p-4 border border-blue-200">
            <h4 className="font-bold text-blue-800 mb-2 text-sm">طريقة الاحتساب</h4>
            <ul className="text-xs text-blue-700 space-y-1.5">
              <li>• الراتب اليومي = الراتب الأساسي ÷ 30 يوم</li>
              <li>• الراتب الأساسي = الراتب اليومي × أيام الحضور</li>
              <li>• بدل الإقامة = 500 ريال/يوم × أيام الحضور (للسكان فقط)</li>
              <li>• العمل الإضافي من المعاملات المالية</li>
              <li>• الخصومات = سلف + خصومات + غرامات + بوفية + مطعم</li>
              <li>• الصافي = الإيرادات − الخصومات</li>
            </ul>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">الشهر *</label>
            <input type="month" value={monthYear} onChange={(e) => setMonthYear(e.target.value)}
              className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">الشركة</label>
            <select value={companyFilter} onChange={(e) => setCompanyFilter(e.target.value)} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
              <option value="">جميع الشركات</option>
              {companies.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div className="bg-amber-50 rounded-lg p-3 border border-amber-200">
            <p className="text-xs text-amber-700">
              سيتم احتساب رواتب {companyFilter ? 'الموظفين في الشركة المحددة' : 'جميع الموظفين النشطين'}.
              إذا كان للموظف راتب محسوب سابقاً لنفس الشهر سيتم تخطيه.
            </p>
          </div>
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setCalcModal(false)}>إلغاء</Button>
            <Button onClick={handleCalculate} disabled={calculating}>
              {calculating ? 'جاري الاحتساب...' : 'احسب الرواتب'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
