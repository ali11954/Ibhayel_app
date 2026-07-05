import { useState, useEffect, useRef } from 'react';
import { Plus, Trash2, Printer, Download, Eye, FileText, DollarSign, CheckCircle, Clock, AlertCircle } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Modal } from '@/components/ui/modal';
import { formatNum } from '@/lib/utils';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import api from '@/api/client';

export default function InvoicesPage() {
  const [invoices, setInvoices] = useState<any[]>([]);
  const [contracts, setContracts] = useState<any[]>([]);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [receiveModal, setReceiveModal] = useState<any>(null);
  const [receiveForm, setReceiveForm] = useState({ amount: '', payment_method: 'cash', notes: '' });
  const [previewInvoice, setPreviewInvoice] = useState<any>(null);
  const [form, setForm] = useState({ invoice_number: '', contract_id: '', amount: '', date: new Date().toISOString().split('T')[0] });
  const [saving, setSaving] = useState(false);
  const printRef = useRef<HTMLDivElement>(null);

  const loadData = () => {
    Promise.all([api.get('/invoices'), api.get('/contracts'), api.get('/accounts')])
      .then(([iRes, cRes, aRes]) => { setInvoices(iRes.data.data || []); setContracts(cRes.data.data || []); setAccounts(aRes.data.data || []); })
      .catch(console.error).finally(() => setLoading(false));
  };
  useEffect(() => { loadData(); }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.post('/invoices', { ...form, amount: Number(form.amount), contract_id: form.contract_id ? Number(form.contract_id) : null });
      setModalOpen(false); setForm({ invoice_number: '', contract_id: '', amount: '', date: new Date().toISOString().split('T')[0] }); loadData();
    } catch (err: any) { alert(err.response?.data?.message || 'حدث خطأ'); }
    finally { setSaving(false); }
  };

  const handleReceive = async () => {
    if (!receiveModal || !receiveForm.amount) return;
    try {
      await api.post(`/invoices/${receiveModal.id}/receive`, {
        amount: parseFloat(receiveForm.amount),
        payment_method: receiveForm.payment_method,
        notes: receiveForm.notes,
      });
      setReceiveModal(null);
      setReceiveForm({ amount: '', payment_method: 'cash', notes: '' });
      loadData();
    } catch (err: any) {
      alert(err.response?.data?.message || 'حدث خطأ أثناء التحصيل');
    }
  };

  const handlePrint = () => {
    const content = printRef.current;
    if (!content) return;
    const win = window.open('', '_blank', 'width=800,height=600');
    if (!win) return;
    win.document.write(`
      <html dir="rtl"><head><title>فاتورة</title>
      <style>
        body { font-family: 'Segoe UI', Tahoma, sans-serif; padding: 40px; color: #333; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #10b981; padding-bottom: 20px; margin-bottom: 30px; }
        .company-name { font-size: 24px; font-weight: bold; color: #10b981; }
        .invoice-title { font-size: 20px; font-weight: bold; color: #374151; }
        .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }
        .info-box { background: #f9fafb; padding: 15px; border-radius: 8px; border: 1px solid #e5e7eb; }
        .info-label { font-size: 12px; color: #6b7280; margin-bottom: 4px; }
        .info-value { font-size: 16px; font-weight: bold; color: #111827; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th { background: #10b981; color: white; padding: 12px; text-align: right; font-size: 14px; }
        td { padding: 12px; border-bottom: 1px solid #e5e7eb; font-size: 14px; }
        .total-row { background: #f0fdf4; font-weight: bold; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 2px solid #e5e7eb; text-align: center; color: #6b7280; font-size: 12px; }
        @media print { body { padding: 20px; } }
      </style></head><body>
      ${content.innerHTML}
      </body></html>
    `);
    win.document.close();
    setTimeout(() => { win.print(); }, 500);
  };

  const total = invoices.reduce((s, i) => s + (i.amount || 0), 0);
  const paid = invoices.reduce((s, i) => s + (i.paid_amount || 0), 0);
  const unpaid = total - paid;

  const statusData = [
    { name: 'مدفوعة', value: invoices.filter(i => (i.amount || 0) <= (i.paid_amount || 0)).length, color: '#10b981' },
    { name: 'جزئي', value: invoices.filter(i => (i.paid_amount || 0) > 0 && (i.amount || 0) > (i.paid_amount || 0)).length, color: '#f59e0b' },
    { name: 'غير مدفوعة', value: invoices.filter(i => !(i.paid_amount || 0)).length, color: '#ef4444' },
  ].filter(d => d.value > 0);

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-3 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">الفواتير</h1>
          <p className="text-gray-500 text-sm mt-1">{invoices.length} فاتورة مسجلة</p>
        </div>
        <Button onClick={() => setModalOpen(true)}><Plus className="w-4 h-4" /> فاتورة جديدة</Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="bg-blue-50 border-blue-200 hover:shadow-md transition-shadow">
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-blue-500 flex items-center justify-center"><DollarSign className="w-6 h-6 text-white" /></div>
              <div><p className="text-sm text-blue-600">الإجمالي</p><p className="text-2xl font-bold text-blue-700">{formatNum(total)} ر.ي</p></div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-green-50 border-green-200 hover:shadow-md transition-shadow">
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-green-500 flex items-center justify-center"><CheckCircle className="w-6 h-6 text-white" /></div>
              <div><p className="text-sm text-green-600">المدفوع</p><p className="text-2xl font-bold text-green-700">{formatNum(paid)} ر.ي</p></div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-red-50 border-red-200 hover:shadow-md transition-shadow">
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-red-500 flex items-center justify-center"><AlertCircle className="w-6 h-6 text-white" /></div>
              <div><p className="text-sm text-red-600">المتبقي</p><p className="text-2xl font-bold text-red-700">{formatNum(unpaid)} ر.ي</p></div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardContent className="p-6">
            <h3 className="font-bold text-gray-900 mb-4">حالة الفواتير</h3>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie data={statusData} cx="50%" cy="50%" innerRadius={50} outerRadius={90} paddingAngle={4} dataKey="value" label={({ name, percent }: any) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}>
                  {statusData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <h3 className="font-bold text-gray-900 mb-4">مقارنة المبالغ</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={[{ name: 'الإجمالي', value: total }, { name: 'المدفوع', value: paid }, { name: 'المتبقي', value: unpaid }]}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip formatter={(v: any) => formatNum(v) + ' ر.ي'} />
                <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                  {[{ fill: '#3b82f6' }, { fill: '#10b981' }, { fill: '#ef4444' }].map((s, i) => <Cell key={i} fill={s.fill} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Invoices Table */}
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="bg-primary-600 text-white">
              <th className="px-4 py-3 text-right font-semibold">رقم الفاتورة</th>
              <th className="px-4 py-3 text-right font-semibold">الشركة</th>
              <th className="px-4 py-3 text-right font-semibold">المبلغ</th>
              <th className="px-4 py-3 text-right font-semibold">المدفوع</th>
              <th className="px-4 py-3 text-right font-semibold">التاريخ</th>
              <th className="px-4 py-3 text-right font-semibold">الحالة</th>
              <th className="px-4 py-3 text-right font-semibold">إجراءات</th>
            </tr></thead>
            <tbody>
              {invoices.map((inv) => {
                const remaining = (inv.amount || 0) - (inv.paid_amount || 0);
                const status = remaining <= 0 ? 'paid' : (inv.paid_amount || 0) > 0 ? 'partial' : 'unpaid';
                return (
                  <tr key={inv.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-primary-600 font-medium">{inv.invoice_number}</td>
                    <td className="px-4 py-3 text-gray-600">{inv.company_name || '—'}</td>
                    <td className="px-4 py-3 font-bold">{formatNum(inv.amount || 0)} ر.ي</td>
                    <td className="px-4 py-3 text-green-600">{formatNum(inv.paid_amount || 0)} ر.ي</td>
                    <td className="px-4 py-3 text-gray-600">{inv.date || '—'}</td>
                    <td className="px-4 py-3">
                      <Badge variant={status === 'paid' ? 'success' : status === 'partial' ? 'warning' : 'danger'}>
                        {status === 'paid' ? 'مدفوعة' : status === 'partial' ? 'جزئي' : 'غير مدفوعة'}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        {status !== 'paid' && <button onClick={() => { setReceiveModal(inv); setReceiveForm({ amount: String(remaining > 0 ? remaining : inv.amount || 0), payment_method: 'cash', notes: '' }); }} className="p-1.5 rounded-lg hover:bg-green-50 text-green-500" title="تحصيل"><DollarSign className="w-4 h-4" /></button>}
                        <button onClick={() => setPreviewInvoice(inv)} className="p-1.5 rounded-lg hover:bg-blue-50 text-blue-500" title="معاينة"><Eye className="w-4 h-4" /></button>
                        <button onClick={() => { setPreviewInvoice(inv); setTimeout(handlePrint, 300); }} className="p-1.5 rounded-lg hover:bg-green-50 text-green-500" title="طباعة"><Printer className="w-4 h-4" /></button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {invoices.length === 0 && <tr><td colSpan={7} className="text-center py-8 text-gray-400">لا توجد فواتير</td></tr>}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Preview Modal */}
      <Modal open={!!previewInvoice} onClose={() => setPreviewInvoice(null)} title="معاينة الفاتورة" size="lg">
        {previewInvoice && (
          <div>
            <div ref={printRef}>
              <div className="header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '3px solid #10b981', paddingBottom: '20px', marginBottom: '30px' }}>
                <div>
                  <div style={{ fontSize: '22px', fontWeight: 'bold', color: '#10b981' }}>طلعت هائل للخدمات والاستشارات الزراعية</div>
                  <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>TALAAT HAIL FOR AGRICULTURAL SERVICES AND CONSULTATIONS</div>
                </div>
                <div style={{ textAlign: 'left' }}>
                  <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#374151' }}>فاتورة ضريبية</div>
                  <div style={{ fontSize: '12px', color: '#6b7280' }}>TAX INVOICE</div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px', marginBottom: '25px' }}>
                <div style={{ background: '#f9fafb', padding: '15px', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                  <div style={{ fontSize: '11px', color: '#6b7280', marginBottom: '3px' }}>رقم الفاتورة</div>
                  <div style={{ fontSize: '15px', fontWeight: 'bold' }}>{previewInvoice.invoice_number}</div>
                </div>
                <div style={{ background: '#f9fafb', padding: '15px', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                  <div style={{ fontSize: '11px', color: '#6b7280', marginBottom: '3px' }}>التاريخ</div>
                  <div style={{ fontSize: '15px', fontWeight: 'bold' }}>{previewInvoice.date}</div>
                </div>
                <div style={{ background: '#f9fafb', padding: '15px', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                  <div style={{ fontSize: '11px', color: '#6b7280', marginBottom: '3px' }}>الشركة</div>
                  <div style={{ fontSize: '15px', fontWeight: 'bold' }}>{previewInvoice.company_name || '—'}</div>
                </div>
                <div style={{ background: '#f9fafb', padding: '15px', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                  <div style={{ fontSize: '11px', color: '#6b7280', marginBottom: '3px' }}>الحالة</div>
                  <div style={{ fontSize: '15px', fontWeight: 'bold' }}>{previewInvoice.is_paid ? 'مدفوعة' : 'غير مدفوعة'}</div>
                </div>
              </div>

              <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '20px' }}>
                <thead>
                  <tr style={{ background: '#10b981', color: 'white' }}>
                    <th style={{ padding: '12px', textAlign: 'right', fontSize: '13px' }}>البيان</th>
                    <th style={{ padding: '12px', textAlign: 'right', fontSize: '13px' }}>المبلغ (ر.ي)</th>
                  </tr>
                </thead>
                <tbody>
                  <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
                    <td style={{ padding: '12px', fontSize: '14px' }}>قيمة الفاتورة</td>
                    <td style={{ padding: '12px', fontSize: '14px', fontWeight: 'bold' }}>{formatNum(previewInvoice.amount || 0)}</td>
                  </tr>
                  <tr style={{ borderBottom: '1px solid #e5e7eb', background: '#f0fdf4' }}>
                    <td style={{ padding: '12px', fontSize: '14px', fontWeight: 'bold' }}>المبلغ المدفوع</td>
                    <td style={{ padding: '12px', fontSize: '14px', fontWeight: 'bold', color: '#10b981' }}>{formatNum(previewInvoice.paid_amount || 0)}</td>
                  </tr>
                  <tr style={{ background: '#fef2f2', fontWeight: 'bold' }}>
                    <td style={{ padding: '12px', fontSize: '14px' }}>المبلغ المتبقي</td>
                    <td style={{ padding: '12px', fontSize: '14px', color: '#ef4444' }}>{formatNum((previewInvoice.amount || 0) - (previewInvoice.paid_amount || 0))}</td>
                  </tr>
                </tbody>
              </table>

              <div style={{ marginTop: '40px', paddingTop: '20px', borderTop: '2px solid #e5e7eb', textAlign: 'center', color: '#6b7280', fontSize: '11px' }}>
                <p>طلعت هائل للخدمات والاستشارات الزراعية - فاتورة ضريبية</p>
                <p style={{ marginTop: '4px' }}>TALAAT HAIL FOR AGRICULTURAL SERVICES AND CONSULTATIONS</p>
              </div>
            </div>

            <div className="flex justify-end gap-2 mt-4 pt-4 border-t">
              <Button variant="outline" onClick={() => setPreviewInvoice(null)}>إغلاق</Button>
              <Button onClick={handlePrint} className="bg-green-600 hover:bg-green-700"><Printer className="w-4 h-4" /> طباعة</Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Add Invoice Modal */}
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="فاتورة جديدة">
        <div className="space-y-4">
          <div><label className="block text-sm font-medium text-gray-700 mb-1">رقم الفاتورة *</label><Input value={form.invoice_number} onChange={(e) => setForm({ ...form, invoice_number: e.target.value })} placeholder="رقم الفاتورة" /></div>
          <div><label className="block text-sm font-medium text-gray-700 mb-1">العقد</label>
            <select value={form.contract_id} onChange={(e) => setForm({ ...form, contract_id: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
              <option value="">اختر العقد</option>{contracts.map((c) => <option key={c.id} value={c.id}>{c.company_name} - {c.contract_type === 'annual' ? 'سنوي' : 'شهري'}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium text-gray-700 mb-1">المبلغ (ر.ي) *</label><Input type="number" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} placeholder="0" /></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">التاريخ</label><Input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} /></div>
          </div>
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setModalOpen(false)}>إلغاء</Button>
            <Button onClick={handleSave} disabled={saving || !form.invoice_number || !form.amount}>{saving ? 'جاري الحفظ...' : 'حفظ'}</Button>
          </div>
        </div>
      </Modal>

      {/* Receive Payment Modal */}
      <Modal open={!!receiveModal} onClose={() => setReceiveModal(null)} title="تحصيل مبلغ من الفاتورة">
        {receiveModal && (
          <div className="space-y-4">
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm text-gray-500">الفاتورة: {receiveModal.invoice_number}</p>
              <p className="text-sm text-gray-500">الشركة: {receiveModal.company_name}</p>
              <p className="text-sm text-gray-500">المبلغ: {formatNum(receiveModal.amount || 0)} ر.ي</p>
              <p className="text-sm text-gray-500">المدفوع: {formatNum(receiveModal.paid_amount || 0)} ر.ي</p>
              <p className="text-sm font-bold text-red-600">المتبقي: {formatNum((receiveModal.amount || 0) - (receiveModal.paid_amount || 0))} ر.ي</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">المبلغ المدفوع *</label>
              <Input type="number" value={receiveForm.amount} onChange={(e) => setReceiveForm({ ...receiveForm, amount: e.target.value })} placeholder="0" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">طريقة الدفع</label>
              <select value={receiveForm.payment_method} onChange={(e) => setReceiveForm({ ...receiveForm, payment_method: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
                <option value="cash">نقدي (الصندوق)</option>
                <option value="bank">بنكي (البنك)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">ملاحظات</label>
              <Input value={receiveForm.notes} onChange={(e) => setReceiveForm({ ...receiveForm, notes: e.target.value })} placeholder="ملاحظات" />
            </div>
            <div className="flex justify-end gap-2 pt-4 border-t">
              <Button variant="outline" onClick={() => setReceiveModal(null)}>إلغاء</Button>
              <Button onClick={handleReceive} disabled={!receiveForm.amount || parseFloat(receiveForm.amount) <= 0} className="bg-green-600 hover:bg-green-700">تحصيل</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
