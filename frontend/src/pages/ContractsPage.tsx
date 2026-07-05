import { useState, useEffect } from 'react';
import { Plus, Edit, Trash2, FileText, DollarSign, Calendar } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Modal } from '@/components/ui/modal';
import { formatNum } from '@/lib/utils';
import api from '@/api/client';

export default function ContractsPage() {
  const [contracts, setContracts] = useState<any[]>([]);
  const [companies, setCompanies] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editItem, setEditItem] = useState<any>(null);
  const [form, setForm] = useState({ description: '', company_id: '', total_amount: '', start_date: '', end_date: '', contract_type: 'monthly' });
  const [saving, setSaving] = useState(false);

  const loadData = () => {
    Promise.all([api.get('/contracts'), api.get('/companies')])
      .then(([cRes, compRes]) => { setContracts(cRes.data.data || []); setCompanies(compRes.data.data || []); })
      .catch(console.error).finally(() => setLoading(false));
  };
  useEffect(() => { loadData(); }, []);

  const openAdd = () => { setEditItem(null); setForm({ description: '', company_id: '', total_amount: '', start_date: '', end_date: '', contract_type: 'monthly' }); setModalOpen(true); };
  const openEdit = (c: any) => { setEditItem(c); setForm({ description: c.notes || '', company_id: c.company_id || '', total_amount: c.contract_value || '', start_date: c.start_date || '', end_date: c.end_date || '', contract_type: c.contract_type || 'monthly' }); setModalOpen(true); };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = { ...form, total_amount: form.total_amount ? Number(form.total_amount) : 0, company_id: form.company_id ? Number(form.company_id) : null };
      if (editItem) { await api.put(`/contracts/${editItem.id}`, payload); }
      else { await api.post('/contracts', payload); }
      setModalOpen(false); loadData();
    } catch (err: any) { alert(err.response?.data?.message || 'حدث خطأ'); }
    finally { setSaving(false); }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('هل أنت متأكد؟')) return;
    await api.delete(`/contracts/${id}`);
    setContracts(prev => prev.filter(c => c.id !== id));
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-3 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div><h1 className="text-2xl font-bold text-gray-900">العقود</h1><p className="text-gray-500 text-sm mt-1">{contracts.length} عقد</p></div>
        <Button onClick={openAdd}><Plus className="w-4 h-4" /> عقد جديد</Button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card><CardContent className="p-6"><div className="flex items-center gap-3"><div className="w-12 h-12 rounded-xl bg-blue-500 flex items-center justify-center"><FileText className="w-6 h-6 text-white" /></div><div><p className="text-sm text-gray-500">العقود</p><p className="text-xl font-bold">{contracts.length}</p></div></div></CardContent></Card>
        <Card><CardContent className="p-6"><div className="flex items-center gap-3"><div className="w-12 h-12 rounded-xl bg-green-500 flex items-center justify-center"><DollarSign className="w-6 h-6 text-white" /></div><div><p className="text-sm text-gray-500">القيمة الإجمالية</p><p className="text-xl font-bold">{formatNum(contracts.reduce((s, c) => s + (c.contract_value || 0), 0))} ر.ي</p></div></div></CardContent></Card>
        <Card><CardContent className="p-6"><div className="flex items-center gap-3"><div className="w-12 h-12 rounded-xl bg-primary-500 flex items-center justify-center"><Calendar className="w-6 h-6 text-white" /></div><div><p className="text-sm text-gray-500">النشطة</p><p className="text-xl font-bold">{contracts.filter(c => c.status === 'active').length}</p></div></div></CardContent></Card>
      </div>

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="bg-primary-600 text-white">
              <th className="px-4 py-3 text-right font-semibold">الشركة</th><th className="px-4 py-3 text-right font-semibold">النوع</th><th className="px-4 py-3 text-right font-semibold">البداية</th><th className="px-4 py-3 text-right font-semibold">النهاية</th><th className="px-4 py-3 text-right font-semibold">القيمة</th><th className="px-4 py-3 text-right font-semibold">إجراءات</th>
            </tr></thead>
            <tbody>
              {contracts.map((c) => (
                <tr key={c.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{c.company_name}</td>
                  <td className="px-4 py-3"><Badge variant="default">{c.contract_type === 'annual' ? 'سنوي' : 'شهري'}</Badge></td>
                  <td className="px-4 py-3 text-gray-600">{c.start_date || '—'}</td>
                  <td className="px-4 py-3 text-gray-600">{c.end_date || '—'}</td>
                  <td className="px-4 py-3 font-bold">{formatNum(c.contract_value || 0)} ر.ي</td>
                  <td className="px-4 py-3"><div className="flex items-center gap-1">
                    <button onClick={() => openEdit(c)} className="p-1.5 rounded-lg hover:bg-blue-50 text-blue-500"><Edit className="w-4 h-4" /></button>
                    <button onClick={() => handleDelete(c.id)} className="p-1.5 rounded-lg hover:bg-red-50 text-red-500"><Trash2 className="w-4 h-4" /></button>
                  </div></td>
                </tr>
              ))}
              {contracts.length === 0 && <tr><td colSpan={7} className="text-center py-8 text-gray-400">لا توجد عقود</td></tr>}
            </tbody>
          </table>
        </div>
      </Card>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editItem ? 'تعديل عقد' : 'عقد جديد'} size="lg">
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium text-gray-700 mb-1">الشركة *</label>
              <select value={form.company_id} onChange={(e) => setForm({ ...form, company_id: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
                <option value="">اختر الشركة</option>{companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">نوع العقد</label>
              <select value={form.contract_type} onChange={(e) => setForm({ ...form, contract_type: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
                <option value="monthly">شهري</option><option value="annual">سنوي</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div><label className="block text-sm font-medium text-gray-700 mb-1">قيمة العقد (ر.ي) *</label><Input type="number" value={form.total_amount} onChange={(e) => setForm({ ...form, total_amount: e.target.value })} placeholder="0" /></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">تاريخ البداية *</label><Input type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} /></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">تاريخ النهاية</label><Input type="date" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} /></div>
          </div>
          <div><label className="block text-sm font-medium text-gray-700 mb-1">ملاحظات</label><textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="w-full h-20 px-3 py-2 rounded-lg border-2 border-gray-200 text-sm focus:border-primary-500 outline-none resize-none" placeholder="ملاحظات العقد" /></div>
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setModalOpen(false)}>إلغاء</Button>
            <Button onClick={handleSave} disabled={saving || !form.company_id || !form.total_amount}>{saving ? 'جاري الحفظ...' : 'حفظ'}</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
