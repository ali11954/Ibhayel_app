import { useState, useEffect } from 'react';
import { Plus, Edit, Trash2, User, Lock, Eye, EyeOff, Check } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Modal } from '@/components/ui/modal';
import api from '@/api/client';

const roleLabels: Record<string, string> = {
  admin: 'مدير النظام', supervisor: 'مشرف', accountant: 'محاسب',
  viewer: 'مشاهد', employee: 'موظف',
};

const employeePages = [
  { key: 'my-portal', label: 'بوابة الموظف' },
  { key: 'attendance', label: 'الحضور' },
  { key: 'salaries', label: 'الرواتب' },
  { key: 'leaves', label: 'الإجازات' },
];

export default function UsersPage() {
  const [users, setUsers] = useState<any[]>([]);
  const [employees, setEmployees] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editItem, setEditItem] = useState<any>(null);
  const [form, setForm] = useState<any>({ username: '', full_name: '', password: '', role: 'viewer', employee_code: '', employee_id: null, allowed_pages: ['my-portal'] });
  const [saving, setSaving] = useState(false);
  const [codeSearch, setCodeSearch] = useState('');
  const [codeResults, setCodeResults] = useState<any[]>([]);
  const [showPassword, setShowPassword] = useState(false);

  const loadData = () => {
    api.get('/users').then(res => setUsers(res.data.data || [])).catch(() => {});
    api.get('/employees').then(res => setEmployees(res.data.data || [])).finally(() => setLoading(false));
  };
  useEffect(() => { loadData(); }, []);

  const openAdd = () => {
    setEditItem(null);
    setForm({ username: '', full_name: '', password: '', role: 'viewer', employee_code: '', employee_id: null, allowed_pages: ['my-portal'] });
    setCodeSearch('');
    setModalOpen(true);
  };

  const openEdit = (u: any) => {
    setEditItem(u);
    const emp = employees.find((e: any) => e.id === u.employee_id);
    setForm({
      username: u.username, full_name: u.full_name, password: '', role: u.role,
      employee_code: emp?.code || '', employee_id: u.employee_id || null,
      allowed_pages: u.allowed_pages || ['my-portal'],
    });
    setCodeSearch(emp?.code || '');
    setModalOpen(true);
  };

  const searchEmployee = (code: string) => {
    setCodeSearch(code);
    if (code.length < 2) { setCodeResults([]); return; }
    const results = employees.filter((e: any) =>
      e.code?.toLowerCase().includes(code.toLowerCase()) ||
      e.name?.toLowerCase().includes(code.toLowerCase())
    );
    setCodeResults(results.slice(0, 5));
  };

  const selectEmployee = (emp: any) => {
    setForm({ ...form, employee_id: emp.id, employee_code: emp.code, full_name: emp.name, username: emp.code });
    setCodeSearch(emp.code);
    setCodeResults([]);
  };

  const togglePage = (pageKey: string) => {
    const current = form.allowed_pages || [];
    if (current.includes(pageKey)) {
      setForm({ ...form, allowed_pages: current.filter((p: string) => p !== pageKey) });
    } else {
      setForm({ ...form, allowed_pages: [...current, pageKey] });
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload: any = {
        username: form.username, full_name: form.full_name, role: form.role,
        employee_id: form.employee_id, allowed_pages: form.allowed_pages,
      };
      if (form.password) payload.password = form.password;
      if (editItem) { await api.put(`/users/${editItem.id}`, payload); }
      else { await api.post('/users', payload); }
      setModalOpen(false); loadData();
    } catch (err: any) { alert(err.response?.data?.message || 'حدث خطأ'); }
    finally { setSaving(false); }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('هل أنت متأكد؟')) return;
    try { await api.delete(`/users/${id}`); setUsers(prev => prev.filter(u => u.id !== id)); }
    catch (err: any) { alert(err.response?.data?.message || 'خطأ'); }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-3 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div><h1 className="text-2xl font-bold text-gray-900">المستخدمين</h1><p className="text-gray-500 text-sm mt-1">{users.length} مستخدم</p></div>
        <Button onClick={openAdd}><Plus className="w-4 h-4" /> إضافة مستخدم</Button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <Card><CardContent className="p-4 text-center"><p className="text-xs text-gray-500">الإجمالي</p><p className="text-xl font-bold">{users.length}</p></CardContent></Card>
        <Card><CardContent className="p-4 text-center"><p className="text-xs text-gray-500">مدراء</p><p className="text-xl font-bold text-blue-600">{users.filter(u => u.role === 'admin').length}</p></CardContent></Card>
        <Card><CardContent className="p-4 text-center"><p className="text-xs text-gray-500">مشرفين</p><p className="text-xl font-bold text-green-600">{users.filter(u => u.role === 'supervisor').length}</p></CardContent></Card>
        <Card><CardContent className="p-4 text-center"><p className="text-xs text-gray-500">محاسبين</p><p className="text-xl font-bold text-purple-600">{users.filter(u => u.role === 'accountant').length}</p></CardContent></Card>
        <Card><CardContent className="p-4 text-center"><p className="text-xs text-gray-500">موظفين</p><p className="text-xl font-bold text-orange-600">{users.filter(u => u.role === 'employee').length}</p></CardContent></Card>
      </div>

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="bg-primary-600 text-white">
              <th className="px-4 py-3 text-right font-semibold">المستخدم</th>
              <th className="px-4 py-3 text-right font-semibold">الاسم الكامل</th>
              <th className="px-4 py-3 text-right font-semibold">الصلاحية</th>
              <th className="px-4 py-3 text-right font-semibold">الموظف المرتبط</th>
              <th className="px-4 py-3 text-right font-semibold">إجراءات</th>
            </tr></thead>
            <tbody>
              {users.map((user) => {
                const emp = employees.find((e: any) => e.id === user.employee_id);
                return (
                  <tr key={user.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center text-primary-700"><User className="w-4 h-4" /></div>
                        <span className="font-medium">{user.username}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{user.full_name}</td>
                    <td className="px-4 py-3">
                      <Badge variant={user.role === 'admin' ? 'danger' : user.role === 'employee' ? 'warning' : user.role === 'supervisor' ? 'info' : 'default'}>
                        {roleLabels[user.role] || user.role}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{emp ? `${emp.name} (${emp.code})` : '-'}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <button onClick={() => openEdit(user)} className="p-1.5 rounded-lg hover:bg-blue-50 text-blue-500"><Edit className="w-4 h-4" /></button>
                        <button onClick={() => handleDelete(user.id)} className="p-1.5 rounded-lg hover:bg-red-50 text-red-500"><Trash2 className="w-4 h-4" /></button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editItem ? 'تعديل مستخدم' : 'إضافة مستخدم جديد'}>
        <div className="space-y-4">
          {/* Role */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">نوع المستخدم *</label>
            <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
              <option value="admin">مدير النظام</option>
              <option value="supervisor">مشرف</option>
              <option value="accountant">محاسب</option>
              <option value="viewer">مشاهد</option>
              <option value="employee">موظف</option>
            </select>
          </div>

          {/* Employee Code (only for employee role) */}
          {form.role === 'employee' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">رقم كود الموظف *</label>
              <div className="relative">
                <Input
                  value={codeSearch}
                  onChange={(e) => searchEmployee(e.target.value)}
                  placeholder="ابحث برقم الكود أو الاسم..."
                  disabled={!!editItem}
                />
                {codeResults.length > 0 && (
                  <div className="absolute z-10 w-full bg-white border border-gray-200 rounded-lg shadow-lg mt-1 max-h-48 overflow-y-auto">
                    {codeResults.map((emp: any) => (
                      <button key={emp.id} onClick={() => selectEmployee(emp)}
                        className="w-full text-right px-4 py-2 hover:bg-blue-50 flex items-center justify-between text-sm">
                        <span className="font-medium">{emp.code}</span>
                        <span className="text-gray-500">{emp.name}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              {form.employee_id && (
                <div className="mt-2 p-2 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700 flex items-center gap-2">
                  <Check size={16} /> تم ربط الموظف بنجاح
                </div>
              )}
            </div>
          )}

          {/* Username */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">اسم المستخدم *</label>
            <Input
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              placeholder={form.role === 'employee' ? 'يُولّد تلقائياً من الكود' : 'اسم المستخدم'}
              disabled={!!editItem}
            />
          </div>

          {/* Full Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">الاسم الكامل *</label>
            <Input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} placeholder="الاسم الكامل" />
          </div>

          {/* Password */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{editItem ? 'كلمة المرور الجديدة (اتركها فارغة للإبقاء)' : 'كلمة المرور *'}</label>
            <div className="relative">
              <Input
                type={showPassword ? 'text' : 'password'}
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder="كلمة المرور"
              />
              <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          {/* Allowed Pages (only for employee role) */}
          {form.role === 'employee' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">الصفحات المتاحة للموظف</label>
              <div className="space-y-2">
                {employeePages.map((page) => (
                  <label key={page.key} className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={(form.allowed_pages || []).includes(page.key)}
                      onChange={() => togglePage(page.key)}
                      className="w-4 h-4 text-blue-600 rounded"
                    />
                    <span className="text-sm">{page.label}</span>
                  </label>
                ))}
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setModalOpen(false)}>إلغاء</Button>
            <Button onClick={handleSave} disabled={saving || !form.username || !form.full_name || (!editItem && !form.password)}>
              {saving ? 'جاري الحفظ...' : 'حفظ'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
