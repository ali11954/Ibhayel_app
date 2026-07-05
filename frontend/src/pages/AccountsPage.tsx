import { useState, useEffect, useRef } from 'react';
import { Search, Plus, Trash2, BookOpen, FileText, BarChart3, DollarSign, TrendingUp, TrendingDown, Edit, Printer, Download } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Modal } from '@/components/ui/modal';
import { formatNum } from '@/lib/utils';
import api from '@/api/client';

type Tab = 'chart' | 'journal' | 'trial' | 'income' | 'balance' | 'statement';

export default function AccountsPage() {
  const [tab, setTab] = useState<Tab>('chart');
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">النظام المحاسبي</h1>
          <p className="text-gray-500 text-sm mt-1">دليل الحسابات والقيود والتقارير المالية</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 flex-wrap">
        {([
          { key: 'chart' as Tab, label: 'دليل الحسابات', icon: BookOpen },
          { key: 'journal' as Tab, label: 'القيود اليومية', icon: FileText },
          { key: 'trial' as Tab, label: 'ميزان المراجعة', icon: BarChart3 },
          { key: 'income' as Tab, label: 'قائمة الدخل', icon: TrendingUp },
          { key: 'balance' as Tab, label: 'الميزانية العمومية', icon: DollarSign },
          { key: 'statement' as Tab, label: 'كشف حساب', icon: FileText },
        ]).map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${tab === t.key ? 'bg-primary-600 text-white shadow-sm' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
            <t.icon className="w-4 h-4" />
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'chart' && <ChartOfAccounts />}
      {tab === 'journal' && <JournalEntries />}
      {tab === 'trial' && <TrialBalance />}
      {tab === 'income' && <IncomeStatement />}
      {tab === 'balance' && <BalanceSheet />}
      {tab === 'statement' && <AccountStatement />}
    </div>
  );
}

function ChartOfAccounts() {
  const [accounts, setAccounts] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editItem, setEditItem] = useState<any>(null);
  const [form, setForm] = useState({ code: '', name_ar: '', account_type: 'asset', nature: 'debit', parent_id: '' });
  const [saving, setSaving] = useState(false);

  const loadData = () => {
    api.get('/accounts/chart').then(res => setAccounts(res.data.data || [])).catch(console.error).finally(() => setLoading(false));
  };
  useEffect(() => { loadData(); }, []);

  const openAdd = () => { setEditItem(null); setForm({ code: '', name_ar: '', account_type: 'asset', nature: 'debit', parent_id: '' }); setModalOpen(true); };
  const openEdit = (a: any) => { setEditItem(a); setForm({ code: a.code, name_ar: a.name_ar || a.name, account_type: a.account_type, nature: a.nature || 'debit', parent_id: a.parent_id || '' }); setModalOpen(true); };

  const handleSave = async () => {
    if (!form.code || !form.name_ar) return;
    setSaving(true);
    try {
      const payload = { ...form, name: form.name_ar, parent_id: form.parent_id ? Number(form.parent_id) : null };
      if (editItem) { await api.put(`/accounts/${editItem.id}`, payload); }
      else { await api.post('/accounts', payload); }
      setModalOpen(false); loadData();
    } catch (err: any) { alert(err.response?.data?.message || 'حدث خطأ'); }
    finally { setSaving(false); }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('هل أنت متأكد من حذف هذا الحساب؟')) return;
    await api.delete(`/accounts/${id}`);
    loadData();
  };

  const typeColors: Record<string, string> = {
    asset: 'bg-blue-100 text-blue-700',
    liability: 'bg-red-100 text-red-700',
    equity: 'bg-purple-100 text-purple-700',
    revenue: 'bg-green-100 text-green-700',
    expense: 'bg-amber-100 text-amber-700',
    cost: 'bg-orange-100 text-orange-700',
  };
  const typeNames: Record<string, string> = {
    asset: 'أصول', liability: 'خصوم', equity: 'حقوق ملكية', revenue: 'إيرادات', expense: 'مصروفات', cost: 'تكاليف',
  };

  const filtered = accounts.filter(a => (a.name_ar || a.name)?.includes(search) || a.code?.includes(search));
  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-3 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" /></div>;

  return (
    <>
      <div className="flex flex-col sm:flex-row gap-3">
        <Card className="flex-1"><CardContent className="p-4">
          <div className="relative">
            <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="بحث بالاسم أو الكود..." className="w-full h-10 pr-10 pl-4 rounded-lg border-2 border-gray-200 text-sm focus:border-primary-500 outline-none" />
          </div>
        </CardContent></Card>
        <Button onClick={openAdd}><Plus className="w-4 h-4" /> حساب جديد</Button>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {Object.entries(typeNames).map(([key, label]) => {
          const count = accounts.filter(a => a.account_type === key).length;
          return (
            <Card key={key}><CardContent className="p-3 text-center">
              <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium mb-1 ${typeColors[key]}`}>{label}</span>
              <p className="text-lg font-bold">{count}</p>
            </CardContent></Card>
          );
        })}
      </div>

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="bg-primary-600 text-white">
              <th className="px-4 py-3 text-right font-semibold">الكود</th>
              <th className="px-4 py-3 text-right font-semibold">اسم الحساب</th>
              <th className="px-4 py-3 text-right font-semibold">النوع</th>
              <th className="px-4 py-3 text-right font-semibold">النوع الفرعي</th>
              <th className="px-4 py-3 text-right font-semibold">الرصيد</th>
              <th className="px-4 py-3 text-right font-semibold">إجراءات</th>
            </tr></thead>
            <tbody>
              {filtered.map((acc) => (
                <tr key={acc.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-3"><span className="font-mono text-primary-600 font-medium">{acc.code}</span></td>
                  <td className="px-4 py-3 font-medium">{acc.name_ar || acc.name}</td>
                  <td className="px-4 py-3"><span className={`px-2 py-0.5 rounded-full text-xs font-medium ${typeColors[acc.account_type] || ''}`}>{typeNames[acc.account_type] || acc.account_type}</span></td>
                  <td className="px-4 py-3 text-gray-500">{acc.nature_name || acc.nature}</td>
                  <td className={`px-4 py-3 font-bold ${(acc.balance || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>{formatNum(acc.balance || 0)} ر.ي</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <button onClick={() => openEdit(acc)} className="p-1.5 rounded-lg hover:bg-blue-50 text-blue-500"><Edit className="w-4 h-4" /></button>
                      <button onClick={() => handleDelete(acc.id)} className="p-1.5 rounded-lg hover:bg-red-50 text-red-500"><Trash2 className="w-4 h-4" /></button>
                    </div>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && <tr><td colSpan={6} className="text-center py-8 text-gray-400">لا توجد حسابات</td></tr>}
            </tbody>
          </table>
        </div>
      </Card>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editItem ? 'تعديل حساب' : 'حساب جديد'}>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">كود الحساب *</label>
            <Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} placeholder="مثال: 1001" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">اسم الحساب (عربي) *</label>
            <Input value={form.name_ar} onChange={(e) => setForm({ ...form, name_ar: e.target.value })} placeholder="اسم الحساب" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">نوع الحساب *</label>
              <select value={form.account_type} onChange={(e) => setForm({ ...form, account_type: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
                <option value="asset">أصول</option>
                <option value="liability">خصوم</option>
                <option value="equity">حقوق ملكية</option>
                <option value="revenue">إيرادات</option>
                <option value="expense">مصروفات</option>
                <option value="cost">تكاليف</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">النوع الفرعي *</label>
              <select value={form.nature} onChange={(e) => setForm({ ...form, nature: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
                <option value="debit">مدين</option>
                <option value="credit">دائن</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">الحساب الأب</label>
            <select value={form.parent_id} onChange={(e) => setForm({ ...form, parent_id: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
              <option value="">بدون حساب أب</option>
              {accounts.filter(a => a.id !== editItem?.id).map(a => <option key={a.id} value={a.id}>{a.code} — {a.name_ar || a.name}</option>)}
            </select>
          </div>
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setModalOpen(false)}>إلغاء</Button>
            <Button onClick={handleSave} disabled={saving || !form.code || !form.name_ar}>{saving ? 'جاري الحفظ...' : 'حفظ'}</Button>
          </div>
        </div>
      </Modal>
    </>
  );
}

function JournalEntries() {
  const [entries, setEntries] = useState<any[]>([]);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    date: new Date().toISOString().split('T')[0],
    description: '',
    details: [
      { account_id: '', debit: '', credit: '', description: '' },
      { account_id: '', debit: '', credit: '', description: '' },
    ],
  });

  const loadData = () => {
    Promise.all([api.get('/accounts/journal'), api.get('/accounts')])
      .then(([jRes, aRes]) => { setEntries(jRes.data.data || []); setAccounts(aRes.data.data || []); })
      .catch(console.error).finally(() => setLoading(false));
  };
  useEffect(() => { loadData(); }, []);

  const addRow = () => setForm({ ...form, details: [...form.details, { account_id: '', debit: '', credit: '', description: '' }] });
  const removeRow = (idx: number) => { if (form.details.length <= 2) return; setForm({ ...form, details: form.details.filter((_, i) => i !== idx) }); };
  const updateRow = (idx: number, field: string, value: string) => {
    const d = [...form.details];
    (d[idx] as any)[field] = value;
    setForm({ ...form, details: d });
  };

  const totalDebit = form.details.reduce((s, d) => s + (Number(d.debit) || 0), 0);
  const totalCredit = form.details.reduce((s, d) => s + (Number(d.credit) || 0), 0);
  const isBalanced = Math.abs(totalDebit - totalCredit) < 0.01 && totalDebit > 0;

  const handleSave = async () => {
    if (!isBalanced) return alert('المدين لا يساوي الدائن');
    setSaving(true);
    try {
      await api.post('/accounts/journal', {
        date: form.date,
        description: form.description,
        details: form.details.filter(d => d.account_id).map(d => ({
          account_id: Number(d.account_id),
          debit: Number(d.debit) || 0,
          credit: Number(d.credit) || 0,
          description: d.description,
        })),
      });
      setModalOpen(false);
      setForm({ date: new Date().toISOString().split('T')[0], description: '', details: [
        { account_id: '', debit: '', credit: '', description: '' },
        { account_id: '', debit: '', credit: '', description: '' },
      ]});
      loadData();
    } catch (err: any) { alert(err.response?.data?.message || 'حدث خطأ'); }
    finally { setSaving(false); }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('هل أنت متأكد من حذف هذا القيد؟')) return;
    await api.delete(`/accounts/journal/${id}`);
    loadData();
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-3 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" /></div>;

  return (
    <>
      <div className="flex justify-end">
        <Button onClick={() => setModalOpen(true)}><Plus className="w-4 h-4" /> قيد جديد</Button>
      </div>

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="bg-primary-600 text-white">
              <th className="px-4 py-3 text-right font-semibold">رقم القيد</th>
              <th className="px-4 py-3 text-right font-semibold">التاريخ</th>
              <th className="px-4 py-3 text-right font-semibold">الوصف</th>
              <th className="px-4 py-3 text-right font-semibold">المدين</th>
              <th className="px-4 py-3 text-right font-semibold">الدائن</th>
              <th className="px-4 py-3 text-right font-semibold">إجراءات</th>
            </tr></thead>
            <tbody>
              {entries.map((entry) => (
                <>
                  <tr key={entry.id} className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer" onClick={() => setExpandedId(expandedId === entry.id ? null : entry.id)}>
                    <td className="px-4 py-3 font-mono text-primary-600">{entry.entry_number}</td>
                    <td className="px-4 py-3 text-gray-600">{entry.date}</td>
                    <td className="px-4 py-3 font-medium">{entry.description}</td>
                    <td className="px-4 py-3 font-bold text-green-600">{formatNum(entry.total_debit || 0)} ر.ي</td>
                    <td className="px-4 py-3 font-bold text-blue-600">{formatNum(entry.total_credit || 0)} ر.ي</td>
                    <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                      <button onClick={() => handleDelete(entry.id)} className="p-1.5 rounded-lg hover:bg-red-50 text-red-500"><Trash2 className="w-4 h-4" /></button>
                    </td>
                  </tr>
                  {expandedId === entry.id && entry.details && (
                    <tr key={`${entry.id}-d`}>
                      <td colSpan={6} className="px-6 py-3 bg-gray-50">
                        <table className="w-full text-xs">
                          <thead><tr className="text-gray-500">
                            <th className="text-right py-1">الحساب</th>
                            <th className="text-right py-1">الوصف</th>
                            <th className="text-right py-1">مدين</th>
                            <th className="text-right py-1">دائن</th>
                          </tr></thead>
                          <tbody>
                            {entry.details.map((d: any) => (
                              <tr key={d.id} className="border-t border-gray-200">
                                <td className="py-1.5">{d.account_code} — {d.account_name}</td>
                                <td className="py-1.5 text-gray-500">{d.description || '—'}</td>
                                <td className="py-1.5 font-bold text-green-600">{d.debit ? formatNum(d.debit) : '—'}</td>
                                <td className="py-1.5 font-bold text-blue-600">{d.credit ? formatNum(d.credit) : '—'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </td>
                    </tr>
                  )}
                </>
              ))}
              {entries.length === 0 && <tr><td colSpan={6} className="text-center py-8 text-gray-400">لا توجد قيود يومية</td></tr>}
            </tbody>
          </table>
        </div>
      </Card>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="قيد يومي جديد" size="lg">
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">التاريخ *</label>
              <Input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">الوصف *</label>
              <Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="وصف القيد" />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-medium text-sm">تفاصيل القيد</h4>
              <button onClick={addRow} className="text-xs text-primary-600 hover:underline">+ إضافة سطر</button>
            </div>
            <div className="space-y-2">
              {form.details.map((d, idx) => (
                <div key={idx} className="grid grid-cols-12 gap-2 items-end">
                  <div className="col-span-4">
                    {idx === 0 && <label className="block text-xs text-gray-500 mb-1">الحساب</label>}
                    <select value={d.account_id} onChange={(e) => updateRow(idx, 'account_id', e.target.value)} className="w-full h-9 px-2 rounded-lg border-2 border-gray-200 text-xs">
                      <option value="">اختر الحساب</option>
                      {accounts.map((a) => <option key={a.id} value={a.id}>{a.code} — {a.name_ar || a.name}</option>)}
                    </select>
                  </div>
                  <div className="col-span-3">
                    {idx === 0 && <label className="block text-xs text-gray-500 mb-1">مدين</label>}
                    <Input type="number" value={d.debit} onChange={(e) => updateRow(idx, 'debit', e.target.value)} placeholder="0" className="h-9 text-xs" />
                  </div>
                  <div className="col-span-3">
                    {idx === 0 && <label className="block text-xs text-gray-500 mb-1">دائن</label>}
                    <Input type="number" value={d.credit} onChange={(e) => updateRow(idx, 'credit', e.target.value)} placeholder="0" className="h-9 text-xs" />
                  </div>
                  <div className="col-span-1">
                    {form.details.length > 2 && <button onClick={() => removeRow(idx)} className="p-2 text-red-500 hover:bg-red-50 rounded-lg"><Trash2 className="w-3 h-3" /></button>}
                  </div>
                </div>
              ))}
            </div>
            <div className="flex justify-between mt-3 pt-2 border-t text-sm">
              <span>المدين: <strong className="text-green-600">{formatNum(totalDebit)}</strong></span>
              <span>الدائن: <strong className="text-blue-600">{formatNum(totalCredit)}</strong></span>
              <span className={isBalanced ? 'text-green-600 font-bold' : 'text-red-600 font-bold'}>
                {isBalanced ? 'متوازن ✓' : 'غير متوازن ✗'}
              </span>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setModalOpen(false)}>إلغاء</Button>
            <Button onClick={handleSave} disabled={saving || !isBalanced || !form.description}>{saving ? 'جاري الحفظ...' : 'حفظ القيد'}</Button>
          </div>
        </div>
      </Modal>
    </>
  );
}

function TrialBalance() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { api.get('/accounts/trial-balance').then(r => setData(r.data.data)).catch(console.error).finally(() => setLoading(false)); }, []);

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-3 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" /></div>;
  if (!data) return <p className="text-center text-gray-400 py-8">لا توجد بيانات</p>;

  return (
    <>
      <Card>
        <CardContent className="p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">ميزان المراجعة</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="bg-gray-100">
                <th className="px-4 py-2 text-right font-semibold">الكود</th>
                <th className="px-4 py-2 text-right font-semibold">اسم الحساب</th>
                <th className="px-4 py-2 text-right font-semibold">مدين</th>
                <th className="px-4 py-2 text-right font-semibold">دائن</th>
              </tr></thead>
              <tbody>
                {data.accounts.map((a: any, i: number) => (
                  <tr key={i} className="border-b border-gray-100">
                    <td className="px-4 py-2 font-mono text-primary-600">{a.code}</td>
                    <td className="px-4 py-2 font-medium">{a.name_ar || a.name}</td>
                    <td className="px-4 py-2 font-bold text-green-600">{a.debit > 0 ? formatNum(a.debit) : '—'}</td>
                    <td className="px-4 py-2 font-bold text-blue-600">{a.credit > 0 ? formatNum(a.credit) : '—'}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot><tr className="bg-primary-50 font-bold">
                <td colSpan={2} className="px-4 py-3 text-right">الإجمالي</td>
                <td className="px-4 py-3 text-green-600">{formatNum(data.total_debit)} ر.ي</td>
                <td className="px-4 py-3 text-blue-600">{formatNum(data.total_credit)} ر.ي</td>
              </tr></tfoot>
            </table>
          </div>
        </CardContent>
      </Card>
    </>
  );
}

function AccountStatement() {
  const [accounts, setAccounts] = useState<any[]>([]);
  const [selectedAccount, setSelectedAccount] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [search, setSearch] = useState('');
  const [statement, setStatement] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const printRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.get('/accounts/statement').then(res => setAccounts(res.data.data || [])).catch(console.error);
  }, []);

  const loadStatement = () => {
    if (!selectedAccount) return;
    setLoading(true);
    const params: any = { account_id: selectedAccount };
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    api.get('/accounts/statement', { params }).then(res => setStatement(res.data.data)).catch(console.error).finally(() => setLoading(false));
  };

  const filteredAccounts = accounts.filter(a =>
    !search || a.code.includes(search) || (a.name && a.name.includes(search))
  );

  const printStatement = () => {
    if (!statement) return;
    const win = window.open('', '_blank', 'width=900,height=600');
    if (!win) return;

    let rows = '';
    statement.transactions.forEach((t: any, i: number) => {
      rows += `<tr style="border-bottom:1px solid #eee">
        <td style="padding:8px">${i + 1}</td>
        <td style="padding:8px">${t.date}</td>
        <td style="padding:8px">${t.entry_number}</td>
        <td style="padding:8px">${t.description}</td>
        <td style="padding:8px;text-align:left">${t.debit > 0 ? formatNum(t.debit) : ''}</td>
        <td style="padding:8px;text-align:left">${t.credit > 0 ? formatNum(t.credit) : ''}</td>
        <td style="padding:8px;text-align:left;font-weight:bold">${formatNum(t.balance)}</td>
      </tr>`;
    });

    win.document.write(`<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><title>كشف حساب - ${statement.account.name}</title>
      <style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Arial',sans-serif;padding:30px;color:#000}
      .header{text-align:center;border-bottom:2px solid #10b981;padding-bottom:15px;margin-bottom:15px}
      .header h1{font-size:22px;color:#10b981;margin-bottom:5px}
      .header h2{font-size:14px;color:#555}
      .info{display:flex;gap:20px;margin:15px 0;font-size:13px}
      .info div{background:#f9fafb;padding:10px 15px;border-radius:6px;border:1px solid #e5e7eb}
      .info .label{color:#6b7280;font-size:11px}.info .value{font-weight:bold;font-size:14px}
      table{width:100%;border-collapse:collapse;margin:15px 0}
      th{background:#10b981;color:white;padding:10px;text-align:right;font-size:12px}
      td{padding:8px;font-size:13px;border-bottom:1px solid #eee}
      .total-row{background:#f0fdf4;font-weight:bold;border-top:2px solid #10b981}
      .footer{margin-top:30px;text-align:center;color:#6b7280;font-size:11px}
      @media print{body{padding:15px}}</style></head><body>
      <div class="header"><h1>طلعت هائل للخدمات والاستشارات الزراعية</h1><h2>كشف حساب</h2></div>
      <div class="info">
        <div><span class="label">رقم الحساب</span><br><span class="value">${statement.account.code}</span></div>
        <div><span class="label">اسم الحساب</span><br><span class="value">${statement.account.name}</span></div>
        <div><span class="label">من تاريخ</span><br><span class="value">${dateFrom || 'البداية'}</span></div>
        <div><span class="label"> الى تاريخ</span><br><span class="value">${dateTo || 'الآن'}</span></div>
      </div>
      <table>
        <thead><tr><th>#</th><th>التاريخ</th><th>رقم القيد</th><th>البيان</th><th style="text-align:left">مدين</th><th style="text-align:left">دائن</th><th style="text-align:left">الرصيد</th></tr></thead>
        <tbody>${rows}
        <tr class="total-row">
          <td colspan="4" style="padding:10px;text-align:center">الإجمالي</td>
          <td style="padding:10px;text-align:left">${formatNum(statement.total_debit)}</td>
          <td style="padding:10px;text-align:left">${formatNum(statement.total_credit)}</td>
          <td style="padding:10px;text-align:left;font-size:14px">${formatNum(statement.final_balance)}</td>
        </tr></tbody>
      </table>
      <div class="footer">طلعت هائل للخدمات والاستشارات الزراعية - كشف حساب</div>
      <script>window.onload=function(){window.print();window.close()}</script></body></html>`);
    win.document.close();
  };

  const exportCSV = () => {
    if (!statement) return;
    const headers = ['التاريخ','رقم القيد','البيان','مدين','دائن','الرصيد'];
    const rows = statement.transactions.map((t: any) => [t.date, t.entry_number, t.description, t.debit, t.credit, t.balance]);
    rows.push(['الإجمالي', '', '', statement.total_debit, statement.total_credit, statement.final_balance]);
    const csv = [headers, ...rows].map(r => r.join(',')).join('\n');
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `statement_${statement.account.code}.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">بحث عن حساب</label>
              <div className="relative">
                <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input value={search} onChange={(e) => { setSearch(e.target.value); setSelectedAccount(''); setStatement(null); }} placeholder="كود أو اسم الحساب" className="w-full h-10 pr-10 pl-3 rounded-lg border-2 border-gray-200 text-sm" />
              </div>
              {search && !selectedAccount && (
                <div className="absolute z-10 mt-1 w-full bg-white border rounded-lg shadow-lg max-h-48 overflow-auto">
                  {filteredAccounts.map(a => (
                    <button key={a.id} onClick={() => { setSelectedAccount(String(a.id)); setSearch(`${a.code} - ${a.name}`); }}
                      className="w-full text-right px-3 py-2 hover:bg-gray-50 text-sm border-b last:border-0">
                      <span className="font-mono text-primary-600">{a.code}</span> - {a.name}
                      <span className="text-xs text-gray-400 mr-2">{formatNum(a.balance)} ر.ي</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">من تاريخ</label>
              <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">الى تاريخ</label>
              <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
            </div>
            <div className="flex items-end gap-2">
              <Button onClick={loadStatement} disabled={!selectedAccount || loading} className="flex-1">{loading ? 'جاري التحميل...' : 'عرض كشف الحساب'}</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {statement && (
        <>
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-bold">{statement.account.code} - {statement.account.name}</h3>
                  <p className="text-sm text-gray-500">{dateFrom || 'البداية'} الى {dateTo || 'الآن'} - {statement.transactions.length} حركة</p>
                </div>
                <div className="flex gap-2">
                  <Button onClick={printStatement} variant="outline"><Printer className="w-4 h-4" /> طباعة</Button>
                  <Button onClick={exportCSV} variant="outline"><Download className="w-4 h-4" /> تصدير</Button>
                </div>
              </div>

              <div ref={printRef} className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="bg-gray-50">
                    <th className="px-3 py-2 text-right">#</th>
                    <th className="px-3 py-2 text-right">التاريخ</th>
                    <th className="px-3 py-2 text-right">رقم القيد</th>
                    <th className="px-3 py-2 text-right">البيان</th>
                    <th className="px-3 py-2 text-left">مدين</th>
                    <th className="px-3 py-2 text-left">دائن</th>
                    <th className="px-3 py-2 text-left">الرصيد</th>
                  </tr></thead>
                  <tbody>
                    {statement.transactions.map((t: any, i: number) => (
                      <tr key={i} className="border-b hover:bg-gray-50">
                        <td className="px-3 py-2">{i + 1}</td>
                        <td className="px-3 py-2">{t.date}</td>
                        <td className="px-3 py-2 font-mono text-xs">{t.entry_number}</td>
                        <td className="px-3 py-2">{t.description}</td>
                        <td className="px-3 py-2 text-left font-medium">{t.debit > 0 ? formatNum(t.debit) : ''}</td>
                        <td className="px-3 py-2 text-left font-medium text-green-600">{t.credit > 0 ? formatNum(t.credit) : ''}</td>
                        <td className="px-3 py-2 text-left font-bold">{formatNum(t.balance)}</td>
                      </tr>
                    ))}
              <tr className="bg-primary-50 font-bold">
                <td colSpan={2} className="px-4 py-3 text-right">الإجمالي</td>
                <td className="px-4 py-3 text-green-600">{formatNum(statement.total_debit)} ر.ي</td>
                <td className="px-4 py-3 text-blue-600">{formatNum(statement.total_credit)} ر.ي</td>
              </tr>
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

function IncomeStatement() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { api.get('/accounts/income-statement').then(r => setData(r.data.data)).catch(console.error).finally(() => setLoading(false)); }, []);

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-3 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" /></div>;
  if (!data) return <p className="text-center text-gray-400 py-8">لا توجد بيانات</p>;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-green-600" />
            <h2 className="text-lg font-bold text-gray-900">الإيرادات</h2>
          </div>
          <div className="space-y-2">
            {data.revenue.map((r: any, i: number) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm text-gray-600">{r.name_ar || r.name}</span>
                <span className="font-bold text-green-600">{formatNum(r.balance)} ر.ي</span>
              </div>
            ))}
            <div className="flex items-center justify-between pt-3 font-bold text-lg">
              <span>إجمالي الإيرادات</span>
              <span className="text-green-600">{formatNum(data.total_revenue)} ر.ي</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <TrendingDown className="w-5 h-5 text-red-600" />
            <h2 className="text-lg font-bold text-gray-900">المصروفات</h2>
          </div>
          <div className="space-y-2">
            {data.expense.map((e: any, i: number) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm text-gray-600">{e.name_ar || e.name}</span>
                <span className="font-bold text-red-600">{formatNum(e.balance)} ر.ي</span>
              </div>
            ))}
            <div className="flex items-center justify-between pt-3 font-bold text-lg">
              <span>إجمالي المصروفات</span>
              <span className="text-red-600">{formatNum(data.total_expense)} ر.ي</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="lg:col-span-2">
        <CardContent className="p-6">
          <div className="text-center">
            <h3 className="text-lg font-bold text-gray-900 mb-2">صافي الربح / الخسارة</h3>
            <p className={`text-3xl font-bold ${data.net_income >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {formatNum(data.net_income)} ر.ي
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function BalanceSheet() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { api.get('/accounts/balance-sheet').then(r => setData(r.data.data)).catch(console.error).finally(() => setLoading(false)); }, []);

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-3 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" /></div>;
  if (!data) return <p className="text-center text-gray-400 py-8">لا توجد بيانات</p>;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Card>
        <CardContent className="p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">الأصول</h2>
          <div className="space-y-2">
            {data.assets.map((a: any, i: number) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm text-gray-600">{a.name_ar || a.name}</span>
                <span className="font-bold">{formatNum(a.balance)} ر.ي</span>
              </div>
            ))}
            <div className="flex items-center justify-between pt-3 font-bold text-lg border-t-2">
              <span>إجمالي الأصول</span>
              <span className="text-primary-600">{formatNum(data.total_assets)} ر.ي</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">الخصوم وحقوق الملكية</h2>
          <div className="space-y-2">
            {data.liabilities.map((l: any, i: number) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm text-gray-600">{l.name_ar || l.name}</span>
                <span className="font-bold text-red-600">{formatNum(l.balance)} ر.ي</span>
              </div>
            ))}
            {data.equity.map((e: any, i: number) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm text-gray-600">{e.name_ar || e.name}</span>
                <span className="font-bold text-purple-600">{formatNum(e.balance)} ر.ي</span>
              </div>
            ))}
            <div className="flex items-center justify-between py-2 border-b border-gray-100">
              <span className="text-sm text-gray-600">صافي الربح / الخسارة</span>
              <span className={`font-bold ${data.net_income >= 0 ? 'text-green-600' : 'text-red-600'}`}>{formatNum(data.net_income)} ر.ي</span>
            </div>
            <div className="flex items-center justify-between pt-3 font-bold text-lg border-t-2">
              <span>إجمالي الخصوم وحقوق الملكية</span>
              <span className="text-primary-600">{formatNum(data.total_liabilities + data.total_equity + data.net_income)} ر.ي</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="lg:col-span-2">
        <CardContent className="p-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div>
              <p className="text-sm text-gray-500 mb-1">إجمالي الأصول</p>
              <p className="text-2xl font-bold text-primary-600">{formatNum(data.total_assets)}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500 mb-1">إجمالي الخصوم</p>
              <p className="text-2xl font-bold text-red-600">{formatNum(data.total_liabilities)}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500 mb-1">حقوق الملكية</p>
              <p className="text-2xl font-bold text-purple-600">{formatNum(data.total_equity)}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500 mb-1">صافي الربح</p>
              <p className={`text-2xl font-bold ${data.net_income >= 0 ? 'text-green-600' : 'text-red-600'}`}>{formatNum(data.net_income)}</p>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t text-center">
            <p className="text-sm text-gray-500 mb-1">الميزانية متوازنة؟</p>
            <p className={`text-xl font-bold ${Math.abs(data.total_assets - (data.total_liabilities + data.total_equity + data.net_income)) < 0.01 ? 'text-green-600' : 'text-red-600'}`}>
              {Math.abs(data.total_assets - (data.total_liabilities + data.total_equity + data.net_income)) < 0.01 ? 'نعم، متوازنة' : 'غير متوازنة'}
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
