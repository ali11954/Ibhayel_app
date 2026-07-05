import { useState, useEffect } from 'react';
import { Truck, Search, Plus, Edit, Trash2, Phone, MapPin, BookOpen } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Modal } from '@/components/ui/modal';
import api from '@/api/client';
import { formatNum } from '@/lib/utils';

const typeColors: Record<string, string> = { restaurant: 'bg-orange-100 text-orange-700', cafeteria: 'bg-yellow-100 text-yellow-700', general: 'bg-gray-100 text-gray-700', utility: 'bg-blue-100 text-blue-700', rent: 'bg-purple-100 text-purple-700', office: 'bg-green-100 text-green-700', equipment: 'bg-red-100 text-red-700' };

export default function SuppliersPage() {
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editItem, setEditItem] = useState<any>(null);
  const [form, setForm] = useState({ name: '', name_ar: '', contact_person: '', phone: '', email: '', address: '', supplier_type: 'general' });
  const [saving, setSaving] = useState(false);

  const loadData = () => {
    Promise.all([api.get('/suppliers'), api.get('/accounts')])
      .then(([supRes, accRes]) => { setSuppliers(supRes.data.data || []); setAccounts(accRes.data.data || []); })
      .catch(console.error).finally(() => setLoading(false));
  };
  useEffect(() => { loadData(); }, []);

  const getAccountBalance = (supplier: any) => {
    if (!supplier.payable_account_id) return 0;
    const acc = accounts.find((a: any) => a.id === supplier.payable_account_id);
    return acc ? (acc.balance || 0) : 0;
  };

  const openAdd = () => { setEditItem(null); setForm({ name: '', name_ar: '', contact_person: '', phone: '', email: '', address: '', supplier_type: 'general' }); setModalOpen(true); };
  const openEdit = (s: any) => { setEditItem(s); setForm({ name: s.name, name_ar: s.name_ar || s.name, contact_person: s.contact_person || '', phone: s.phone || '', email: s.email || '', address: s.address || '', supplier_type: s.supplier_type || 'general' }); setModalOpen(true); };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (editItem) { await api.put(`/suppliers/${editItem.id}`, form); }
      else { await api.post('/suppliers', form); }
      setModalOpen(false); loadData();
    } catch (err: any) { alert(err.response?.data?.message || 'حدث خطأ'); }
    finally { setSaving(false); }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('هل أنت متأكد؟')) return;
    await api.delete(`/suppliers/${id}`);
    setSuppliers(prev => prev.filter(s => s.id !== id));
  };

  const filtered = suppliers.filter(s => s.name?.includes(search));
  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-3 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div><h1 className="text-2xl font-bold text-gray-900">الموردين</h1><p className="text-gray-500 text-sm mt-1">{suppliers.length} مورد</p></div>
        <Button onClick={openAdd}><Plus className="w-4 h-4" /> إضافة مورد</Button>
      </div>

      <Card><CardContent className="p-4"><div className="relative"><input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="بحث باسم المورد..." className="w-full h-10 px-4 rounded-lg border-2 border-gray-200 text-sm focus:border-primary-500 outline-none" /></div></CardContent></Card>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((supplier) => (
          <Card key={supplier.id} className="hover:shadow-md transition-shadow">
            <CardContent className="p-6">
              <div className="flex items-start justify-between">
                <div className="w-12 h-12 rounded-xl bg-primary-100 flex items-center justify-center"><Truck className="w-6 h-6 text-primary-600" /></div>
                <div className="flex items-center gap-1">
                  <button onClick={() => openEdit(supplier)} className="p-1.5 rounded-lg hover:bg-blue-50 text-blue-500"><Edit className="w-4 h-4" /></button>
                  <button onClick={() => handleDelete(supplier.id)} className="p-1.5 rounded-lg hover:bg-red-50 text-red-500"><Trash2 className="w-4 h-4" /></button>
                </div>
              </div>
              <div className="flex items-center gap-2 mt-4">
                <h3 className="text-lg font-bold text-gray-900">{supplier.name}</h3>
                <Badge variant={supplier.supplier_type === 'restaurant' ? 'warning' : supplier.supplier_type === 'cafeteria' ? 'success' : 'default'}>
                  {supplier.supplier_type_name || 'عام'}
                </Badge>
              </div>
              {supplier.contact_person && <p className="text-sm text-gray-500 mt-1">{supplier.contact_person}</p>}
              {supplier.phone && <div className="flex items-center gap-1 mt-2 text-gray-500 text-sm"><Phone className="w-3.5 h-3.5" />{supplier.phone}</div>}
              {supplier.address && <div className="flex items-center gap-1 mt-1 text-gray-500 text-sm"><MapPin className="w-3.5 h-3.5" />{supplier.address}</div>}
              <div className="mt-4 pt-4 border-t border-gray-100">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-gray-400 flex items-center gap-1"><BookOpen className="w-3 h-3" />الحساب</span>
                  <span className="text-xs text-gray-500 font-mono">{supplier.payable_account_code || 'غير مرتبط'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">الرصيد</span>
                  <span className={`font-bold ${getAccountBalance(supplier) >= 0 ? 'text-green-600' : 'text-red-600'}`}>{formatNum(getAccountBalance(supplier))} ر.ي</span>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
        {filtered.length === 0 && <p className="text-gray-400 text-center py-8 col-span-3">لا يوجد موردين</p>}
      </div>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editItem ? 'تعديل مورد' : 'إضافة مورد'}>
        <div className="space-y-4">
          <div><label className="block text-sm font-medium text-gray-700 mb-1">اسم المورد *</label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="اسم المورد" /></div>
          <div><label className="block text-sm font-medium text-gray-700 mb-1">الاسم بالعربي</label><Input value={form.name_ar} onChange={(e) => setForm({ ...form, name_ar: e.target.value })} placeholder="الاسم بالعربي" /></div>
          <div><label className="block text-sm font-medium text-gray-700 mb-1">نوع المورد *</label>
            <select value={form.supplier_type} onChange={(e) => setForm({ ...form, supplier_type: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
              <option value="general">عام</option>
              <option value="restaurant">مطعم</option>
              <option value="cafeteria">بوفية</option>
              <option value="utility">كهرباء وماء</option>
              <option value="rent">إيجار</option>
              <option value="office">مكتبية</option>
              <option value="equipment">معدات وأدوات</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium text-gray-700 mb-1">الهاتف</label><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="رقم الهاتف" /></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">جهة الاتصال</label><Input value={form.contact_person} onChange={(e) => setForm({ ...form, contact_person: e.target.value })} placeholder="اسم جهة الاتصال" /></div>
          </div>
          <div><label className="block text-sm font-medium text-gray-700 mb-1">البريد الإلكتروني</label><Input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="البريد" /></div>
          <div><label className="block text-sm font-medium text-gray-700 mb-1">العنوان</label><Input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} placeholder="العنوان" /></div>
          {editItem && editItem.payable_account_code && (
            <div className="p-3 bg-gray-50 rounded-lg text-sm">
              <span className="text-gray-500">الحساب المرتبط: </span>
              <span className="font-mono font-bold text-primary-600">{editItem.payable_account_code}</span>
              <span className="text-gray-400 mr-2">({editItem.payable_account_name || '—'})</span>
            </div>
          )}
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setModalOpen(false)}>إلغاء</Button>
            <Button onClick={handleSave} disabled={saving || !form.name}>{saving ? 'جاري الحفظ...' : 'حفظ'}</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
