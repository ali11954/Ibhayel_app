import { useState, useEffect } from 'react';
import { Plus, DollarSign, Trash2, Printer, Filter } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Modal } from '@/components/ui/modal';
import { formatNum } from '@/lib/utils';
import api from '@/api/client';

export default function SupplierInvoicesPage() {
  const [invoices, setInvoices] = useState<any[]>([]);
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSupplier, setSelectedSupplier] = useState<string>('');
  const [modalOpen, setModalOpen] = useState(false);
  const [payModal, setPayModal] = useState<any>(null);
  const [payForm, setPayForm] = useState({ payment_method: 'cash' });
  const [form, setForm] = useState({ supplier_id: '', invoice_number: '', amount: '', date: new Date().toISOString().split('T')[0] });
  const [saving, setSaving] = useState(false);

  const loadData = () => {
    setLoading(true);
    const params: any = {};
    if (selectedSupplier) params.supplier_id = selectedSupplier;
    Promise.all([api.get('/supplier-invoices', { params }), api.get('/suppliers')])
      .then(([iRes, sRes]) => { setInvoices(iRes.data.data || []); setSuppliers(sRes.data.data || []); })
      .catch(console.error).finally(() => setLoading(false));
  };
  useEffect(() => { loadData(); }, [selectedSupplier]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.post('/supplier-invoices', {
        supplier_id: parseInt(form.supplier_id),
        invoice_number: form.invoice_number,
        amount: parseFloat(form.amount),
        date: form.date,
      });
      setModalOpen(false);
      setForm({ supplier_id: '', invoice_number: '', amount: '', date: new Date().toISOString().split('T')[0] });
      loadData();
    } catch (err: any) { alert(err.response?.data?.message || 'حدث خطأ أثناء الحفظ'); }
    finally { setSaving(false); }
  };

  const handlePay = async () => {
    if (!payModal) return;
    try {
      if (payModal.source === 'salary_deduction_group') {
        await api.post('/salary-deduction/pay', {
          salary_ids: payModal.salary_ids,
          deduction_type: payModal.deduction_type,
          payment_method: payForm.payment_method,
        });
      } else {
        const realId = String(payModal.id).replace('inv_', '');
        await api.post(`/supplier-invoices/${realId}/pay`, {
          amount: payModal.amount,
          payment_method: payForm.payment_method,
        });
      }
      setPayModal(null);
      setPayForm({ payment_method: 'cash' });
      loadData();
    } catch (err: any) {
      alert(err.response?.data?.message || 'حدث خطأ أثناء الدفع');
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('هل أنت متأكد من حذف هذه الفاتورة؟')) return;
    try {
      if (String(id).startsWith('sal_group_')) return;
      const realId = String(id).replace('inv_', '');
      await api.post(`/supplier-invoices/${realId}/delete`);
      loadData();
    } catch (err: any) {
      alert(err.response?.data?.message || 'حدث خطأ أثناء الحذف');
    }
  };

  const printVoucher = async (item: any) => {
    if (item.source === 'salary_deduction_group') {
      try {
        const res = await api.post('/salary-deduction/voucher', {
          salary_ids: item.salary_ids,
          deduction_type: item.deduction_type,
        });
        const v = res.data.data;
        const win = window.open('', '_blank', 'width=800,height=600');
        if (!win) return;

        let detailsHtml = '';
        v.details.forEach((d: any, i: number) => {
          detailsHtml += `<tr style="border-bottom:1px solid #eee">
            <td style="padding:8px">${i + 1}</td>
            <td style="padding:8px">${d.employee_name}</td>
            <td style="padding:8px">${d.employee_code}</td>
            <td style="padding:8px;text-align:left;font-weight:bold">${formatNum(d.amount)} ر.ي</td>
          </tr>`;
        });

        win.document.write(`<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><title>سند صرف - ${v.type}</title>
          <style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Arial',sans-serif;padding:30px;color:#000}
          .voucher{border:2px solid #000;padding:20px;max-width:700px;margin:0 auto}
          .header{text-align:center;border-bottom:2px solid #000;padding-bottom:15px;margin-bottom:15px}
          .header h1{font-size:22px;margin-bottom:5px}.header h2{font-size:14px;color:#555}
          .row{display:flex;justify-content:space-between;margin:6px 0;font-size:13px}
          .row .label{font-weight:bold;color:#555;flex:1}.row .value{font-weight:bold;flex:1;text-align:left}
          .amount-box{border:2px solid #000;padding:12px;text-align:center;margin:15px 0;font-size:20px;font-weight:bold;background:#f9f9f9}
          table{width:100%;border-collapse:collapse;margin:15px 0}
          th{background:#f3f4f6;padding:8px;text-align:right;font-size:12px;border-bottom:2px solid #ddd}
          td{padding:8px;font-size:13px}
          .total-row{background:#f0fdf4;font-weight:bold;border-top:2px solid #000}
          .footer{margin-top:30px;display:flex;justify-content:space-between}
          .footer .sig{text-align:center;width:30%}.footer .line{border-bottom:1px solid #000;margin-top:40px;font-size:11px}
          @media print{body{padding:10px}.voucher{border-width:1px}}</style></head><body>
          <div class="voucher">
          <div class="header"><h1>سند صرف - ${v.type}</h1><h2>طلعت هائل للخدمات والاستشارات الزراعية</h2></div>
          <div class="row"><span class="label">الشهر:</span><span class="value">${v.month_year}</span></div>
          <div class="row"><span class="label">المورد:</span><span class="value">${v.supplier_name}</span></div>
          <div class="row"><span class="label">عدد الموظفين:</span><span class="value">${v.employee_count}</span></div>
          
          <table>
            <thead><tr><th>#</th><th>اسم الموظف</th><th>الكود</th><th style="text-align:left">المبلغ</th></tr></thead>
            <tbody>${detailsHtml}
            <tr class="total-row"><td colspan="3" style="padding:10px;text-align:center;font-size:14px">المجموع</td><td style="padding:10px;text-align:left;font-size:16px">${formatNum(v.total)} ر.ي</td></tr>
            </tbody>
          </table>
          
          <div class="amount-box">${formatNum(v.total)} ريال يمني فقط</div>
          <div class="footer">
            <div class="sig"><div class="line">توقيع المستلم</div></div>
            <div class="sig"><div class="line">توقيع المحاسب</div></div>
            <div class="sig"><div class="line">توقيع المدير</div></div>
          </div></div>
          <script>window.onload=function(){window.print();window.close()}</script></body></html>`);
        win.document.close();
      } catch { alert('خطأ في تحميل بيانات السند'); }
    } else {
      // فاتورة مورد عادية
      try {
        const res = await api.get(`/supplier-invoices/${item.id}/voucher`);
        const v = res.data.data;
        const win = window.open('', '_blank', 'width=800,height=600');
        if (!win) return;

        let paymentsHtml = '';
        v.payments.forEach((p: any, i: number) => {
          const method = p.payment_method === 'bank' ? 'تحويل بنكي' : 'نقدي';
          paymentsHtml += `<tr style="border-bottom:1px solid #eee">
            <td style="padding:8px">${i + 1}</td>
            <td style="padding:8px">${p.payment_date}</td>
            <td style="padding:8px">${method}</td>
            <td style="padding:8px;text-align:left;font-weight:bold">${formatNum(p.amount)} ر.ي</td>
          </tr>`;
        });

        win.document.write(`<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><title>سند دفع فاتورة مورد - ${v.supplier.name}</title>
          <style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Arial',sans-serif;padding:30px;color:#000}
          .voucher{border:2px solid #000;padding:20px;max-width:700px;margin:0 auto}
          .header{text-align:center;border-bottom:2px solid #000;padding-bottom:15px;margin-bottom:15px}
          .header h1{font-size:22px;margin-bottom:5px}.header h2{font-size:14px;color:#555}
          .row{display:flex;justify-content:space-between;margin:6px 0;font-size:13px}
          .row .label{font-weight:bold;color:#555;flex:1}.row .value{font-weight:bold;flex:1;text-align:left}
          .amount-box{border:2px solid #000;padding:12px;text-align:center;margin:15px 0;font-size:20px;font-weight:bold;background:#f9f9f9}
          table{width:100%;border-collapse:collapse;margin:15px 0}
          th{background:#f3f4f6;padding:8px;text-align:right;font-size:12px;border-bottom:2px solid #ddd}
          td{padding:8px;font-size:13px}
          .total-row{background:#f0fdf4;font-weight:bold;border-top:2px solid #000}
          .footer{margin-top:30px;display:flex;justify-content:space-between}
          .footer .sig{text-align:center;width:30%}.footer .line{border-bottom:1px solid #000;margin-top:40px;font-size:11px}
          @media print{body{padding:10px}.voucher{border-width:1px}}</style></head><body>
          <div class="voucher">
          <div class="header"><h1>سند دفع فاتورة مورد</h1><h2>${v.company_name}</h2></div>
          <div class="row"><span class="label">رقم الفاتورة:</span><span class="value">${v.invoice.invoice_number}</span></div>
          <div class="row"><span class="label">المورد:</span><span class="value">${v.supplier.name}</span></div>
          <div class="row"><span class="label">هاتف المورد:</span><span class="value">${v.supplier.phone || '—'}</span></div>
          <div class="row"><span class="label">قيمة الفاتورة:</span><span class="value">${formatNum(v.invoice.amount)} ر.ي</span></div>
          <div class="row"><span class="label">المبلغ المدفوع:</span><span class="value" style="color:#10b981">${formatNum(v.invoice.paid_amount)} ر.ي</span></div>
          <div class="row"><span class="label">المتبقي:</span><span class="value" style="color:#ef4444">${formatNum(v.invoice.remaining_amount)} ر.ي</span></div>
          
          <h3 style="margin-top:20px;margin-bottom:10px;font-size:14px">تفاصيل الدفعات</h3>
          <table>
            <thead><tr><th>#</th><th>التاريخ</th><th>طريقة الدفع</th><th style="text-align:left">المبلغ</th></tr></thead>
            <tbody>${paymentsHtml}
            <tr class="total-row"><td colspan="3" style="padding:10px;text-align:center;font-size:14px">إجمالي المدفوع</td><td style="padding:10px;text-align:left;font-size:16px">${formatNum(v.invoice.paid_amount)} ر.ي</td></tr>
            </tbody>
          </table>
          
          <div class="amount-box">${formatNum(v.invoice.paid_amount)} ريال يمني فقط</div>
          <div class="footer">
            <div class="sig"><div class="line">توقيع المستلم</div></div>
            <div class="sig"><div class="line">توقيع المحاسب</div></div>
            <div class="sig"><div class="line">توقيع المدير</div></div>
          </div></div>
          <script>window.onload=function(){window.print();window.close()}</script></body></html>`);
        win.document.close();
      } catch { alert('خطأ في تحميل بيانات السند'); }
    }
  };

  const total = invoices.reduce((s, i) => s + (i.amount || 0), 0);
  const paid = invoices.reduce((s, i) => s + (i.paid_amount || 0), 0);
  const unpaid = total - paid;

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-3 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">فواتير الموردين</h1>
          <p className="text-gray-500 text-sm mt-1">{invoices.length} فاتورة مسجلة</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-white border rounded-lg px-3 py-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <select value={selectedSupplier} onChange={(e) => setSelectedSupplier(e.target.value)} className="text-sm border-0 bg-transparent focus:outline-none">
              <option value="">جميع الموردين</option>
              {suppliers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          <Button onClick={() => setModalOpen(true)}><Plus className="w-4 h-4" /> فاتورة جديدة</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="bg-blue-50 border-blue-200">
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-blue-500 flex items-center justify-center"><DollarSign className="w-6 h-6 text-white" /></div>
              <div><p className="text-sm text-blue-600">الإجمالي</p><p className="text-2xl font-bold text-blue-700">{formatNum(total)} ر.ي</p></div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-green-50 border-green-200">
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-green-500 flex items-center justify-center"><DollarSign className="w-6 h-6 text-white" /></div>
              <div><p className="text-sm text-green-600">المدفوع</p><p className="text-2xl font-bold text-green-700">{formatNum(paid)} ر.ي</p></div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-red-50 border-red-200">
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-red-500 flex items-center justify-center"><DollarSign className="w-6 h-6 text-white" /></div>
              <div><p className="text-sm text-red-600">المتبقي</p><p className="text-2xl font-bold text-red-700">{formatNum(unpaid)} ر.ي</p></div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="bg-primary-600 text-white">
              <th className="px-4 py-3 text-right font-semibold">النوع</th>
              <th className="px-4 py-3 text-right font-semibold">رقم الفاتورة / البيان</th>
              <th className="px-4 py-3 text-right font-semibold">المورد</th>
              <th className="px-4 py-3 text-right font-semibold">المبلغ</th>
              <th className="px-4 py-3 text-right font-semibold">المدفوع</th>
              <th className="px-4 py-3 text-right font-semibold">المتبقي</th>
              <th className="px-4 py-3 text-right font-semibold">الحالة</th>
              <th className="px-4 py-3 text-right font-semibold">إجراءات</th>
            </tr></thead>
            <tbody>
              {invoices.map((inv) => {
                const remaining = (inv.amount || 0) - (inv.paid_amount || 0);
                const isGroup = inv.source === 'salary_deduction_group';
                const status = inv.is_paid || remaining <= 0 ? 'paid' : (inv.paid_amount || 0) > 0 ? 'partial' : 'unpaid';
                return (
                  <tr key={inv.id} className={`border-b border-gray-100 hover:bg-gray-50 ${isGroup ? 'bg-amber-50/50' : ''}`}>
                    <td className="px-4 py-3">
                      <Badge variant={isGroup ? 'warning' : 'default'}>
                        {isGroup ? (inv.deduction_type === 'cafeteria' ? 'بوفية' : 'مطعم') : 'فاتورة'}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 font-medium">{inv.invoice_number}</td>
                    <td className="px-4 py-3 text-gray-600">{inv.supplier_name || '—'}</td>
                    <td className="px-4 py-3 font-bold">{formatNum(inv.amount || 0)} ر.ي</td>
                    <td className="px-4 py-3 text-green-600">{formatNum(inv.paid_amount || 0)} ر.ي</td>
                    <td className="px-4 py-3 text-red-600 font-bold">{formatNum(remaining > 0 ? remaining : 0)} ر.ي</td>
                    <td className="px-4 py-3">
                      <Badge variant={status === 'paid' ? 'success' : status === 'partial' ? 'warning' : 'danger'}>
                        {status === 'paid' ? 'مدفوعة' : status === 'partial' ? 'جزئي' : 'غير مدفوعة'}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        {status !== 'paid' && <button onClick={() => { setPayModal(inv); setPayForm({ payment_method: 'cash' }); }} className="p-1.5 rounded-lg hover:bg-green-50 text-green-500" title="دفع"><DollarSign className="w-4 h-4" /></button>}
                        {(isGroup || status === 'paid' || (inv.paid_amount || 0) > 0) && <button onClick={() => printVoucher(inv)} className="p-1.5 rounded-lg hover:bg-blue-50 text-blue-500" title="سند صرف"><Printer className="w-4 h-4" /></button>}
                        {!isGroup && <button onClick={() => handleDelete(inv.id)} className="p-1.5 rounded-lg hover:bg-red-50 text-red-500"><Trash2 className="w-4 h-4" /></button>}
                      </div>
                    </td>
                  </tr>
                );
              })}
              {invoices.length === 0 && <tr><td colSpan={8} className="text-center py-8 text-gray-400">لا توجد فواتير</td></tr>}
            </tbody>
          </table>
        </div>
      </Card>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="فاتورة مورد جديدة">
        <div className="space-y-4">
          <div><label className="block text-sm font-medium text-gray-700 mb-1">المورد *</label>
            <select value={form.supplier_id} onChange={(e) => setForm({ ...form, supplier_id: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
              <option value="">اختر المورد</option>{suppliers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          <div><label className="block text-sm font-medium text-gray-700 mb-1">رقم الفاتورة *</label><Input value={form.invoice_number} onChange={(e) => setForm({ ...form, invoice_number: e.target.value })} placeholder="رقم الفاتورة" /></div>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium text-gray-700 mb-1">المبلغ (ر.ي) *</label><Input type="number" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} placeholder="0" /></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">التاريخ</label><Input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} /></div>
          </div>
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setModalOpen(false)}>إلغاء</Button>
            <Button onClick={handleSave} disabled={saving || !form.supplier_id || !form.invoice_number || !form.amount}>{saving ? 'جاري الحفظ...' : 'حفظ'}</Button>
          </div>
        </div>
      </Modal>

      <Modal open={!!payModal} onClose={() => setPayModal(null)} title={payModal?.source === 'salary_deduction_group' ? 'دفع مخصصات الرواتب' : 'دفع فاتورة مورد'}>
        {payModal && (
          <div className="space-y-4">
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm text-gray-500">{payModal.invoice_number}</p>
              <p className="text-sm text-gray-500">المورد: {payModal.supplier_name}</p>
              <p className="text-sm font-bold text-lg text-primary-600">المبلغ: {formatNum(payModal.amount || 0)} ر.ي</p>
              {payModal.employee_count && <p className="text-sm text-gray-500">عدد الموظفين: {payModal.employee_count}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">طريقة الدفع</label>
              <select value={payForm.payment_method} onChange={(e) => setPayForm({ ...payForm, payment_method: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
                <option value="cash">نقدي (الصندوق)</option>
                <option value="bank">بنكي (البنك)</option>
              </select>
            </div>
            <div className="flex justify-end gap-2 pt-4 border-t">
              <Button variant="outline" onClick={() => setPayModal(null)}>إلغاء</Button>
              <Button onClick={handlePay} className="bg-green-600 hover:bg-green-700">دفع {formatNum(payModal.amount || 0)} ر.ي</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
