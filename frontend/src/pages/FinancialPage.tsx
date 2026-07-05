import { useState, useEffect } from 'react';
import { DollarSign, Plus, ArrowUpRight, ArrowDownLeft, TrendingUp, TrendingDown, Filter, Printer } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Modal } from '@/components/ui/modal';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
import api from '@/api/client';
import { formatNum } from '@/lib/utils';

const COLORS = ['#f59e0b', '#10b981', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899'];
const txTypeMap: Record<string, string> = { advance: 'سلفة', overtime: 'إضافي', deduction: 'خصم', penalty: 'جزاء', restaurant: 'مطعم', cafeteria: 'بوفية', buffet: 'بوفية' };
const txTypeVariant: Record<string, 'success' | 'danger' | 'warning' | 'default'> = { advance: 'warning', overtime: 'success', deduction: 'danger', penalty: 'danger', restaurant: 'default', cafeteria: 'default', buffet: 'default' };

export default function FinancialPage() {
  const [transactions, setTransactions] = useState<any[]>([]);
  const [employees, setEmployees] = useState<any[]>([]);
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [dashboard, setDashboard] = useState<any>(null);
  const [balances, setBalances] = useState({ cash: 0, bank: 0, total: 0 });
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [confirmModal, setConfirmModal] = useState(false);
  const [settleModal, setSettleModal] = useState(false);
  const [unsettledAdvances, setUnsettledAdvances] = useState<any[]>([]);
  const [settleForm, setSettleForm] = useState({ employee_id: '', amount: '', payment_method: 'cash' });
  const [form, setForm] = useState({ employee_id: '', description: '', amount: '', transaction_type: 'advance', date: new Date().toISOString().split('T')[0], payment_method: 'cash', supplier_id: '', monthly_installment: '' });
  const [saving, setSaving] = useState(false);

  const loadData = () => {
    Promise.all([api.get('/financial/transactions'), api.get('/financial/dashboard'), api.get('/employees'), api.get('/accounts/balance'), api.get('/suppliers')])
      .then(([txRes, dashRes, empRes, balRes, supRes]) => { setTransactions(txRes.data.data || []); setDashboard(dashRes.data.data); setEmployees(empRes.data.data || []); setBalances(balRes.data.data || { cash: 0, bank: 0, total: 0 }); setSuppliers(supRes.data.data || []); })
      .catch(console.error).finally(() => setLoading(false));
  };
  useEffect(() => { loadData(); }, []);

  const loadUnsettledAdvances = async () => {
    try {
      const res = await api.get('/financial/advances/unsettled');
      setUnsettledAdvances(res.data.data || []);
    } catch (err) { console.error(err); }
  };

  const handleSettleAdvance = async () => {
    if (!settleForm.employee_id || !settleForm.amount) {
      alert('يرجى تحديد الموظف والمبلغ');
      return;
    }
    const amt = Number(settleForm.amount);
    const method = settleForm.payment_method;
    const available = method === 'cash' ? balances.cash : balances.bank;
    if (amt > available) {
      alert(`الرصيد غير كافٍ. الرصيد الحالي: ${formatNum(available)} ر.ي`);
      return;
    }
    setSaving(true);
    try {
      await api.post('/financial/advances/settle', {
        employee_id: Number(settleForm.employee_id),
        amount: amt,
        payment_method: method,
      });
      setSettleModal(false);
      setSettleForm({ employee_id: '', amount: '', payment_method: 'cash' });
      loadData();
      alert('تم سداد السلفة بنجاح');
    } catch (err: any) {
      alert(err.response?.data?.message || 'حدث خطأ');
    } finally { setSaving(false); }
  };

  const validateBalance = () => {
    const amt = Number(form.amount);
    const method = form.payment_method;
    const available = method === 'cash' ? balances.cash : balances.bank;
    if (amt > available) {
      const accountName = method === 'cash' ? 'الصندوق' : 'البنك';
      alert(`الرصيد غير كافٍ في ${accountName}. الرصيد الحالي: ${formatNum(available)} ر.ي`);
      return false;
    }
    return true;
  };

  const handleSave = async () => {
    if (!validateBalance()) return;
    setSaving(true);
    try {
      const payload = { ...form, employee_id: Number(form.employee_id), amount: Number(form.amount), supplier_id: form.supplier_id ? Number(form.supplier_id) : null, monthly_installment: form.transaction_type === 'advance' ? Number(form.monthly_installment || 0) : 0 };
      await api.post('/financial/transactions', payload);
      setModalOpen(false); setForm({ employee_id: '', description: '', amount: '', transaction_type: 'advance', date: new Date().toISOString().split('T')[0], payment_method: 'cash', supplier_id: '', monthly_installment: '' }); loadData();
    } catch (err: any) { alert(err.response?.data?.message || 'حدث خطأ'); }
    finally { setSaving(false); }
  };

  const printVoucher = (tx: any) => {
    const win = window.open('', '_blank', 'width=800,height=600');
    if (!win) return;
    win.document.write(`<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><title>سند صرف</title>
      <style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Arial',sans-serif;padding:30px;color:#000}
      .voucher{border:2px solid #000;padding:20px;max-width:600px;margin:0 auto}
      .header{text-align:center;border-bottom:2px solid #000;padding-bottom:15px;margin-bottom:15px}
      .header h1{font-size:18px;margin-bottom:5px}.header h2{font-size:14px;color:#555}
      .row{display:flex;justify-content:space-between;margin:8px 0;font-size:14px}
      .row span{flex:1}.row .label{font-weight:bold;color:#555}.row .value{font-weight:bold;font-size:16px}
      .amount-box{border:2px solid #000;padding:12px;text-align:center;margin:15px 0;font-size:20px;font-weight:bold}
      .footer{margin-top:30px;display:flex;justify-content:space-between}
      .footer .sig{text-align:center;width:30%}.footer .line{border-bottom:1px solid #000;margin-top:40px;font-size:12px}
      .watermark{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%) rotate(-30deg);font-size:80px;color:rgba(0,0,0,0.03);font-weight:bold;pointer-events:none}
      @media print{body{padding:10px}.voucher{border-width:1px}}</style></head><body>
      <div class="voucher"><div class="watermark">سند صرف</div>
      <div class="header"><h1>سند صرف نقدي</h1><h2>طلعت هائل للخدمات والاستشارات الزراعية</h2></div>
      <div class="row"><span class="label">التاريخ:</span><span class="value">${tx.date || '—'}</span></div>
      <div class="row"><span class="label">رقم السند:</span><span class="value">#${tx.id || '—'}</span></div>
      <div class="row"><span class="label">اسم المستلم:</span><span class="value">${tx.employee_name || '—'}</span></div>
      <div class="row"><span class="label">طريقة الدفع:</span><span class="value">${tx.payment_method_name || 'نقداً'}</span></div>
      <div class="row"><span class="label">نوع المعاملة:</span><span class="value">${txTypeMap[tx.transaction_type] || tx.transaction_type}</span></div>
      <div class="row"><span class="label">البيان:</span><span class="value">${tx.description || '—'}</span></div>
      <div class="amount-box">${formatNum(tx.amount || 0)} ريال يمني</div>
      <div class="footer">
        <div class="sig"><div class="line">توقيع المستلم</div></div>
        <div class="sig"><div class="line">توقيع المحاسب</div></div>
        <div class="sig"><div class="line">توقيع مدير الموارد البشرية</div></div>
      </div></div>
      <script>window.onload=function(){window.print();window.close()}</script></body></html>`);
    win.document.close();
  };

  const filtered = transactions.filter(t => {
    const matchSearch = t.description?.includes(search) || t.employee_name?.includes(search);
    const matchType = typeFilter === 'all' || t.transaction_type === typeFilter;
    return matchSearch && matchType;
  });

  // Chart data
  const byType = transactions.reduce((acc: any, t: any) => {
    const type = t.transaction_type || 'other';
    acc[type] = (acc[type] || 0) + (t.amount || 0);
    return acc;
  }, {});
  const pieData = Object.entries(byType).map(([type, total]) => ({
    name: txTypeMap[type] || type,
    value: total as number,
  })).filter(d => d.value > 0);

  const byMonth: Record<string, { month: string; total: number; count: number }> = {};
  transactions.forEach((t: any) => {
    const key = t.date?.substring(0, 7) || 'غير محدد';
    if (!byMonth[key]) byMonth[key] = { month: key, total: 0, count: 0 };
    byMonth[key].total += t.amount || 0;
    byMonth[key].count += 1;
  });
  const barData = Object.values(byMonth).sort((a, b) => a.month.localeCompare(b.month));

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-3 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">المالية</h1>
          <p className="text-gray-500 text-sm mt-1">{transactions.length} معاملة مسجلة</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => { loadUnsettledAdvances(); setSettleModal(true); }} variant="outline"><DollarSign className="w-4 h-4" /> سداد سلفة</Button>
          <Button onClick={() => setModalOpen(true)}><Plus className="w-4 h-4" /> معاملة جديدة</Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-5 gap-4">
        <Card className="bg-green-50 border-green-200 hover:shadow-md transition-shadow">
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-green-500 flex items-center justify-center"><ArrowDownLeft className="w-6 h-6 text-white" /></div>
              <div><p className="text-sm text-green-600">الإيرادات (إضافي)</p><p className="text-2xl font-bold text-green-700">{formatNum(dashboard?.total_income || 0)} ر.ي</p></div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-red-50 border-red-200 hover:shadow-md transition-shadow">
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-red-500 flex items-center justify-center"><ArrowUpRight className="w-6 h-6 text-white" /></div>
              <div><p className="text-sm text-red-600">المصروفات</p><p className="text-2xl font-bold text-red-700">{formatNum(dashboard?.total_expense || 0)} ر.ي</p></div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-primary-50 border-primary-200 hover:shadow-md transition-shadow">
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-primary-500 flex items-center justify-center"><DollarSign className="w-6 h-6 text-white" /></div>
              <div><p className="text-sm text-primary-600">الصافي</p>
                <p className={`text-2xl font-bold ${(dashboard?.balance || 0) >= 0 ? 'text-green-700' : 'text-red-700'}`}>{formatNum(dashboard?.balance || 0)} ر.ي</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-amber-50 border-amber-200 hover:shadow-md transition-shadow">
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-amber-500 flex items-center justify-center"><DollarSign className="w-6 h-6 text-white" /></div>
              <div><p className="text-sm text-amber-600">الصندوق (نقدي)</p>
                <p className={`text-2xl font-bold ${balances.cash >= 0 ? 'text-green-700' : 'text-red-700'}`}>{formatNum(balances.cash)} ر.ي</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-blue-50 border-blue-200 hover:shadow-md transition-shadow">
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-blue-500 flex items-center justify-center"><DollarSign className="w-6 h-6 text-white" /></div>
              <div><p className="text-sm text-blue-600">البنك</p>
                <p className={`text-2xl font-bold ${balances.bank >= 0 ? 'text-green-700' : 'text-red-700'}`}>{formatNum(balances.bank)} ر.ي</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardContent className="p-6">
            <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-emerald-500" />
              التطور الشهري
            </h3>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={barData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip formatter={(value: any) => [formatNum(value) + ' ر.ي', '']} />
                <Bar dataKey="total" fill="#6366f1" name="المبلغ" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
              <DollarSign className="w-5 h-5 text-primary-500" />
              توزيع المعاملات حسب النوع
            </h3>
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={95} paddingAngle={4} dataKey="value" label={({ name, percent }: any) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}>
                  {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={(value: any) => [formatNum(value) + ' ر.ي', '']} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Filter & Table */}
      <Card>
        <CardContent className="p-4 border-b">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="بحث بالاسم أو الوصف..." className="w-full h-10 px-4 rounded-lg border-2 border-gray-200 text-sm focus:border-primary-500 outline-none" />
            </div>
            <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="h-10 px-4 rounded-lg border-2 border-gray-200 text-sm">
              <option value="all">الكل</option><option value="advance">سلفة</option><option value="overtime">إضافي</option><option value="deduction">خصم</option><option value="penalty">جزاء</option><option value="restaurant">مطعم</option><option value="buffet">بوفية</option>
            </select>
          </div>
        </CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="bg-gray-50">
              <th className="px-4 py-3 text-right font-semibold">التاريخ</th>
              <th className="px-4 py-3 text-right font-semibold">الموظف</th>
              <th className="px-4 py-3 text-right font-semibold">المورد</th>
              <th className="px-4 py-3 text-right font-semibold">الوصف</th>
              <th className="px-4 py-3 text-right font-semibold">النوع</th>
              <th className="px-4 py-3 text-right font-semibold">طريقة الدفع</th>
              <th className="px-4 py-3 text-right font-semibold">المبلغ</th>
              <th className="px-4 py-3 text-center font-semibold">سند الصرف</th>
            </tr></thead>
            <tbody>
              {filtered.map((tx) => (
                <tr key={tx.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-600">{tx.date}</td>
                  <td className="px-4 py-3 font-medium">{tx.employee_name || '—'}</td>
                  <td className="px-4 py-3 text-gray-600">{tx.supplier_name || '—'}</td>
                  <td className="px-4 py-3 text-gray-600">{tx.description}</td>
                  <td className="px-4 py-3"><Badge variant={txTypeVariant[tx.transaction_type] || 'default'}>{txTypeMap[tx.transaction_type] || tx.transaction_type}</Badge></td>
                  <td className="px-4 py-3"><Badge variant={tx.payment_method === 'bank' ? 'default' : 'success'}>{tx.payment_method_name || 'نقداً'}</Badge></td>
                  <td className="px-4 py-3 font-bold text-red-600">- {formatNum(tx.amount || 0)} ر.ي</td>
                  <td className="px-4 py-3 text-center"><Button variant="outline" size="sm" onClick={() => printVoucher(tx)}><Printer className="w-3 h-3" /></Button></td>
                </tr>
              ))}
              {filtered.length === 0 && <tr><td colSpan={8} className="text-center py-8 text-gray-400">لا توجد معاملات</td></tr>}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Add Modal */}
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="معاملة جديدة">
        <div className="space-y-4">
          <div><label className="block text-sm font-medium text-gray-700 mb-1">التاريخ *</label><Input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} /></div>
          <div><label className="block text-sm font-medium text-gray-700 mb-1">الموظف *</label>
            <select value={form.employee_id} onChange={(e) => setForm({ ...form, employee_id: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
              <option value="">اختر الموظف</option>{employees.map((e: any) => <option key={e.id} value={e.id}>{e.name}</option>)}
            </select>
          </div>
          <div><label className="block text-sm font-medium text-gray-700 mb-1">النوع *</label>
            <select value={form.transaction_type} onChange={(e) => setForm({ ...form, transaction_type: e.target.value, supplier_id: (e.target.value !== 'restaurant' && e.target.value !== 'cafeteria') ? '' : form.supplier_id })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
              <option value="advance">سلفة</option><option value="overtime">إضافي</option><option value="deduction">خصم</option><option value="penalty">جزاء</option><option value="restaurant">مطعم</option><option value="cafeteria">بوفية</option>
            </select>
          </div>
          {(form.transaction_type === 'restaurant' || form.transaction_type === 'cafeteria') && (
            <div><label className="block text-sm font-medium text-gray-700 mb-1">المورد *</label>
              <select value={form.supplier_id} onChange={(e) => setForm({ ...form, supplier_id: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
                <option value="">اختر المورد</option>{suppliers.filter((s: any) => form.transaction_type === 'restaurant' ? s.supplier_type === 'restaurant' : s.supplier_type === 'cafeteria').map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
          )}
          {form.transaction_type === 'advance' && (
            <>
              <div><label className="block text-sm font-medium text-gray-700 mb-1">طريقة الدفع *</label>
                <select value={form.payment_method} onChange={(e) => setForm({ ...form, payment_method: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
                  <option value="cash">نقدي (الصندوق) - الرصيد: {formatNum(balances.cash)} ر.ي</option>
                  <option value="bank">بنكي (البنك) - الرصيد: {formatNum(balances.bank)} ر.ي</option>
                </select>
              </div>
              <div><label className="block text-sm font-medium text-gray-700 mb-1">القسط الشهري للخصم (ر.ي) *</label>
                <Input type="number" value={form.monthly_installment || ''} onChange={(e) => setForm({ ...form, monthly_installment: e.target.value })} placeholder="مثال: 10000" />
                <p className="text-xs text-gray-500 mt-1">المبلغ الذي يُخصم من راتب العامل شهرياً حتى سداد السلفة كاملة</p>
              </div>
            </>
          )}
          {form.transaction_type !== 'advance' && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-700">
              {form.transaction_type === 'overtime' && 'يُحتسب الإضافي تلقائياً في الراتب (ساعات العمل × قيمة الساعة) ويُضاف للراتب الشامل'}
              {form.transaction_type === 'deduction' && 'يُخصم من الراتب الأساسي عند احتساب الرواتب'}
              {form.transaction_type === 'penalty' && 'يُخصم من الراتب الأساسي عند احتساب الرواتب'}
              {form.transaction_type === 'restaurant' && 'يُخصم من الراتب الأساسي ويُضاف للمورد عند احتساب الرواتب'}
              {form.transaction_type === 'cafeteria' && 'يُخصم من الراتب الأساسي ويُضاف للمورد عند احتساب الرواتب'}
            </div>
          )}
          <div><label className="block text-sm font-medium text-gray-700 mb-1">الوصف *</label><Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="وصف المعاملة" /></div>
          <div><label className="block text-sm font-medium text-gray-700 mb-1">المبلغ (ر.ي) *</label><Input type="number" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} placeholder="0" /></div>
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setModalOpen(false)}>إلغاء</Button>
            <Button onClick={handleSave} disabled={saving || !form.employee_id || !form.description || !form.amount || ((form.transaction_type === 'restaurant' || form.transaction_type === 'cafeteria') && !form.supplier_id)}>{saving ? 'جاري الحفظ...' : 'حفظ'}</Button>
          </div>
        </div>
      </Modal>

      {/* Settlement Modal */}
      <Modal open={settleModal} onClose={() => setSettleModal(false)} title="سداد سلفة">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">الموظف *</label>
            <select value={settleForm.employee_id} onChange={(e) => {
              const empId = e.target.value;
              const empAdvances = unsettledAdvances.find((a: any) => a.employee_id === Number(empId));
              setSettleForm({ ...settleForm, employee_id: empId, amount: empAdvances ? String(empAdvances.total_amount) : '' });
            }} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
              <option value="">اختر الموظف</option>
              {unsettledAdvances.map((a: any) => (
                <option key={a.employee_id} value={a.employee_id}>{a.employee_name} - متبقي: {formatNum(a.total_amount)} ر.ي</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">المبلغ (ر.ي) *</label>
            <Input type="number" value={settleForm.amount} onChange={(e) => setSettleForm({ ...settleForm, amount: e.target.value })} placeholder="0" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">طريقة السداد *</label>
            <select value={settleForm.payment_method} onChange={(e) => setSettleForm({ ...settleForm, payment_method: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
              <option value="cash">نقدي (الصندوق) - الرصيد: {formatNum(balances.cash)} ر.ي</option>
              <option value="bank">بنكي (البنك) - الرصيد: {formatNum(balances.bank)} ر.ي</option>
            </select>
          </div>
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-700">
            سيتم تسجيل القيد: مدين مستحق الرواتب + دائن الصندوق/البنك
          </div>
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setSettleModal(false)}>إلغاء</Button>
            <Button onClick={handleSettleAdvance} disabled={saving || !settleForm.employee_id || !settleForm.amount}>{saving ? 'جاري السداد...' : 'سداد'}</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
