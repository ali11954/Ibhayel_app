import { useState, useEffect } from 'react';
import { Plus, Edit, Trash2, Users, User, Building2, ChevronDown, ChevronUp, UserCheck, UserX, ArrowRight, Star, Calendar, DollarSign, Clock, FileText, Eye, X, Download } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Modal } from '@/components/ui/modal';
import { formatNum } from '@/lib/utils';
import { openEmployeeProfilePDF } from '@/lib/pdfExport';
import api from '@/api/client';

const emptyEmployee = {
  name: '', card_number: '', code: '', phone: '', job_title: '', region: '', region_id: '',
  company_id: '', supervisor_id: '', salary: '', total_salary: '', basic_salary: '', daily_allowance: '',
  is_active: true, is_resident: false, employee_type: 'worker', worker_type: 'permanent',
  clothing_allowance: '', health_card_allowance: '', monthly_insurance: '',
};

type Tab = 'table' | 'grouped' | 'structure' | 'detail';

function BankInfoTab({ employeeId, employeeName }: { employeeId: number; employeeName: string }) {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editItem, setEditItem] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ bank_name: '', account_number: '', iban: '', swift_code: '', branch_name: '', account_type: 'current', currency: 'YER', is_primary: true, notes: '' });

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/employees/${employeeId}/bank-info`);
      setItems(res.data?.data || []);
    } catch { setItems([]); }
    setLoading(false);
  };
  useEffect(() => { load(); }, [employeeId]);

  const openAdd = () => { setEditItem(null); setForm({ bank_name: '', account_number: '', iban: '', swift_code: '', branch_name: '', account_type: 'current', currency: 'YER', is_primary: items.length === 0, notes: '' }); setShowForm(true); };
  const openEdit = (item: any) => { setEditItem(item); setForm({ bank_name: item.bank_name, account_number: item.account_number, iban: item.iban || '', swift_code: item.swift_code || '', branch_name: item.branch_name || '', account_type: item.account_type || 'current', currency: item.currency || 'YER', is_primary: item.is_primary, notes: item.notes || '' }); setShowForm(true); };

  const handleSave = async () => {
    if (!form.bank_name || !form.account_number) return;
    setSaving(true);
    try {
      if (editItem) {
        await api.put(`/bank-info/${editItem.id}`, form);
      } else {
        await api.post(`/employees/${employeeId}/bank-info`, form);
      }
      setShowForm(false);
      load();
    } catch (e: any) { alert(e?.response?.data?.message || 'خطأ'); }
    setSaving(false);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('هل أنت متأكد من الحذف؟')) return;
    await api.delete(`/bank-info/${id}`);
    load();
  };

  const bankTypes: Record<string, string> = { current: 'حساب جاري', savings: 'حساب توفير', salary: 'حساب راتب' };

  return (
    <Card>
      <div className="p-4 border-b flex items-center justify-between">
        <h3 className="font-bold text-gray-900">المعلومات البنكية — {employeeName}</h3>
        <Button onClick={openAdd} className="text-xs"><Plus className="w-3.5 h-3.5" /> إضافة</Button>
      </div>
      {loading ? (
        <div className="flex items-center justify-center h-32"><div className="w-6 h-6 border-2 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" /></div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <Building2 className="w-10 h-10 mx-auto mb-2 opacity-30" />
          <p className="text-sm">لا توجد معلومات بنكية</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="bg-gray-50 border-b">
              <th className="px-3 py-3 text-right font-semibold text-xs">البنك</th>
              <th className="px-3 py-3 text-right font-semibold text-xs">رقم الحساب</th>
              <th className="px-3 py-3 text-right font-semibold text-xs">الآيبان</th>
              <th className="px-3 py-3 text-right font-semibold text-xs">الفرع</th>
              <th className="px-3 py-3 text-right font-semibold text-xs">النوع</th>
              <th className="px-3 py-3 text-right font-semibold text-xs">العملة</th>
              <th className="px-3 py-3 text-right font-semibold text-xs">الأساسي</th>
              <th className="px-3 py-3 text-right font-semibold text-xs">إجراءات</th>
            </tr></thead>
            <tbody>
              {items.map((item: any) => (
                <tr key={item.id} className="border-b hover:bg-gray-50">
                  <td className="px-3 py-3 font-medium">{item.bank_name}</td>
                  <td className="px-3 py-3 font-mono text-xs">{item.account_number}</td>
                  <td className="px-3 py-3 font-mono text-xs">{item.iban || '—'}</td>
                  <td className="px-3 py-3 text-xs">{item.branch_name || '—'}</td>
                  <td className="px-3 py-3"><span className="px-2 py-0.5 rounded-full text-xs bg-blue-100 text-blue-700">{bankTypes[item.account_type] || item.account_type}</span></td>
                  <td className="px-3 py-3 text-xs">{item.currency}</td>
                  <td className="px-3 py-3">{item.is_primary ? <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">أساسي</span> : '—'}</td>
                  <td className="px-3 py-3">
                    <div className="flex gap-1">
                      <button onClick={() => openEdit(item)} className="p-1 hover:bg-blue-50 rounded"><Edit className="w-3.5 h-3.5 text-blue-600" /></button>
                      <button onClick={() => handleDelete(item.id)} className="p-1 hover:bg-red-50 rounded"><Trash2 className="w-3.5 h-3.5 text-red-600" /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal open={showForm} onClose={() => setShowForm(false)} title={editItem ? 'تعديل معلومات بنكية' : 'إضافة معلومات بنكية'}>
        <div className="space-y-3 p-1">
          <div><label className="text-xs font-medium text-gray-600 mb-1 block">اسم البنك *</label><Input value={form.bank_name} onChange={(e) => setForm({ ...form, bank_name: e.target.value })} placeholder="مثال: بنك اليمن والخليج" /></div>
          <div><label className="text-xs font-medium text-gray-600 mb-1 block">رقم الحساب *</label><Input value={form.account_number} onChange={(e) => setForm({ ...form, account_number: e.target.value })} placeholder="رقم الحساب" /></div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="text-xs font-medium text-gray-600 mb-1 block">الآيبان (IBAN)</label><Input value={form.iban} onChange={(e) => setForm({ ...form, iban: e.target.value })} placeholder="YE..." /></div>
            <div><label className="text-xs font-medium text-gray-600 mb-1 block">SWIFT Code</label><Input value={form.swift_code} onChange={(e) => setForm({ ...form, swift_code: e.target.value })} placeholder="BOBYEAA" /></div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="text-xs font-medium text-gray-600 mb-1 block">اسم الفرع</label><Input value={form.branch_name} onChange={(e) => setForm({ ...form, branch_name: e.target.value })} placeholder="الفرع" /></div>
            <div><label className="text-xs font-medium text-gray-600 mb-1 block">العملة</label><Input value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })} placeholder="YER" /></div>
          </div>
          <div><label className="text-xs font-medium text-gray-600 mb-1 block">نوع الحساب</label>
            <select value={form.account_type} onChange={(e) => setForm({ ...form, account_type: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm">
              <option value="current">حساب جاري</option>
              <option value="savings">حساب توفير</option>
              <option value="salary">حساب راتب</option>
            </select>
          </div>
          <div><label className="text-xs font-medium text-gray-600 mb-1 block">ملاحظات</label><Input value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} placeholder="ملاحظات إضافية" /></div>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={form.is_primary} onChange={(e) => setForm({ ...form, is_primary: e.target.checked })} className="w-4 h-4 rounded" />
            <span className="text-sm font-medium text-gray-700">حساب أساسي</span>
          </label>
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setShowForm(false)}>إلغاء</Button>
            <Button onClick={handleSave} disabled={saving || !form.bank_name || !form.account_number}>
              {saving ? 'جاري الحفظ...' : editItem ? 'تحديث' : 'حفظ'}
            </Button>
          </div>
        </div>
      </Modal>
    </Card>
  );
}

export default function EmployeesPage() {
  const [employees, setEmployees] = useState<any[]>([]);
  const [companies, setCompanies] = useState<any[]>([]);
  const [regions, setRegions] = useState<any[]>([]);
  const [jobTitles, setJobTitles] = useState<string[]>([]);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');
  const [tab, setTab] = useState<Tab>('table');
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editItem, setEditItem] = useState<any>(null);
  const [form, setForm] = useState<any>(emptyEmployee);
  const [saving, setSaving] = useState(false);
  const [useNewJobTitle, setUseNewJobTitle] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState<any>(null);
  const [detailData, setDetailData] = useState<any>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailTab, setDetailTab] = useState<'profile' | 'salary' | 'attendance' | 'evaluations' | 'transactions' | 'leaves' | 'bank'>('profile');
  const [bankItems, setBankItems] = useState<any[]>([]);

  const loadData = () => {
    Promise.all([api.get('/employees'), api.get('/companies'), api.get('/regions'), api.get('/evaluation-criteria/job-titles')])
      .then(([eRes, cRes, rRes, jtRes]) => {
        setEmployees(eRes.data.data || []);
        setCompanies(cRes.data.data || []);
        setRegions(rRes.data.data || []);
        setJobTitles(jtRes.data.data || []);
      }).catch(console.error).finally(() => setLoading(false));
  };
  useEffect(() => { loadData(); }, []);

  const openAdd = () => { setEditItem(null); setForm(emptyEmployee); setModalOpen(true); };
  const openEdit = (emp: any) => {
    setEditItem(emp);
    setForm({
      ...emp,
      company_id: emp.company_id || '',
      supervisor_id: emp.supervisor_id || '',
      salary: emp.salary || '',
      total_salary: emp.total_salary || '',
      basic_salary: emp.basic_salary || '',
      daily_allowance: emp.daily_allowance || '',
      region_id: emp.region_id || '',
      clothing_allowance: emp.clothing_allowance || '',
      health_card_allowance: emp.health_card_allowance || '',
      monthly_insurance: emp.monthly_insurance || '',
    });
    setModalOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const selectedRegion = regions.find((r) => r.id === Number(form.region_id));
      const payload = {
        ...form,
        code: form.code || form.card_number,
        salary: form.salary ? Number(form.salary) : 0,
        total_salary: form.total_salary ? Number(form.total_salary) : 0,
        basic_salary: form.basic_salary ? Number(form.basic_salary) : 0,
        daily_allowance: form.daily_allowance ? Number(form.daily_allowance) : 0,
        clothing_allowance: form.clothing_allowance ? Number(form.clothing_allowance) : 0,
        health_card_allowance: form.health_card_allowance ? Number(form.health_card_allowance) : 0,
        monthly_insurance: form.monthly_insurance ? Number(form.monthly_insurance) : 0,
        company_id: form.company_id ? Number(form.company_id) : null,
        region_id: form.region_id ? Number(form.region_id) : null,
        supervisor_id: form.supervisor_id ? Number(form.supervisor_id) : null,
        region: selectedRegion ? selectedRegion.name : form.region || '',
      };
      if (editItem) {
        await api.put(`/employees/${editItem.id}`, payload);
      } else {
        await api.post('/employees', payload);
      }
      setModalOpen(false);
      loadData();
    } catch (err: any) {
      alert(err.response?.data?.message || 'حدث خطأ');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('هل أنت متأكد من حذف هذا الموظف؟')) return;
    await api.delete(`/employees/${id}`);
    loadData();
  };

  const loadEmployeeDetail = async (emp: any) => {
    setSelectedEmployee(emp);
    setDetailTab('profile');
    setDetailLoading(true);
    setTab('detail');
    try {
      const [salRes, attRes, evalRes, txRes, leaveRes, bankRes] = await Promise.all([
        api.get(`/financial/salaries?employee_id=${emp.id}`).catch(() => ({ data: { data: [] } })),
        api.get(`/attendance?employee_id=${emp.id}`).catch(() => ({ data: { data: [] } })),
        api.get('/evaluations').catch(() => ({ data: { data: [] } })),
        api.get(`/financial/transactions?employee_id=${emp.id}`).catch(() => ({ data: { data: [] } })),
        api.get(`/leave-requests?employee_id=${emp.id}`).catch(() => ({ data: { data: [] } })),
        api.get(`/employees/${emp.id}/bank-info`).catch(() => ({ data: { data: [] } })),
      ]);
      const allEvals = evalRes.data.data || [];
      const allLeaves = leaveRes.data.data || [];
      setDetailData({
        salaries: salRes.data.data || [],
        attendance: attRes.data.data || [],
        evaluations: allEvals.filter((e: any) => e.employee_id === emp.id),
        transactions: txRes.data.data || [],
        leaves: allLeaves.filter((l: any) => l.employee_id === emp.id),
      });
      setBankItems(bankRes.data?.data || []);
    } catch {
      setDetailData({ salaries: [], attendance: [], evaluations: [], transactions: [], leaves: [] });
    } finally {
      setDetailLoading(false);
    }
  };

  const filtered = employees.filter((e) => {
    const matchSearch = e.name?.includes(search) || e.card_number?.includes(search) || e.code?.includes(search);
    const matchFilter = filter === 'all' || (filter === 'active' && e.is_active) || (filter === 'inactive' && !e.is_active);
    return matchSearch && matchFilter;
  });

  const supervisors = employees.filter(e => e.employee_type === 'supervisor' && e.is_active);
  const groupedByCompany = companies.map(c => ({
    ...c,
    employees: filtered.filter(e => e.company_id === c.id),
    supervisors: supervisors.filter(e => e.company_id === c.id),
  })).filter(g => g.employees.length > 0);
  const ungrouped = filtered.filter(e => !e.company_id);

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-3 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">الموظفين</h1>
          <p className="text-gray-500 text-sm mt-1">{employees.length} موظف — {companies.length} شركة — {supervisors.length} مشرف</p>
        </div>
        <Button onClick={openAdd}><Plus className="w-4 h-4" /> إضافة موظف</Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card><CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary-100 flex items-center justify-center"><Users className="w-5 h-5 text-primary-600" /></div>
            <div><p className="text-2xl font-bold">{employees.length}</p><p className="text-xs text-gray-500">الإجمالي</p></div>
          </div>
        </CardContent></Card>
        <Card><CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-green-100 flex items-center justify-center"><UserCheck className="w-5 h-5 text-green-600" /></div>
            <div><p className="text-2xl font-bold text-green-600">{employees.filter(e => e.is_active).length}</p><p className="text-xs text-gray-500">نشط</p></div>
          </div>
        </CardContent></Card>
        <Card><CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-red-100 flex items-center justify-center"><UserX className="w-5 h-5 text-red-600" /></div>
            <div><p className="text-2xl font-bold text-red-600">{employees.filter(e => !e.is_active).length}</p><p className="text-xs text-gray-500">غير نشط</p></div>
          </div>
        </CardContent></Card>
        <Card><CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center"><Building2 className="w-5 h-5 text-amber-600" /></div>
            <div><p className="text-2xl font-bold text-amber-600">{companies.length}</p><p className="text-xs text-gray-500">الشركات</p></div>
          </div>
        </CardContent></Card>
      </div>

      {/* Search + Tab Toggle */}
      {tab !== 'detail' && (
        <div className="flex flex-col sm:flex-row gap-3">
          <Card className="flex-1"><CardContent className="p-3">
            <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="بحث بالاسم أو رقم البطاقة أو الكود..." className="w-full h-10 px-4 rounded-lg border-2 border-gray-200 text-sm focus:border-primary-500 outline-none" />
          </CardContent></Card>
          <select value={filter} onChange={(e) => setFilter(e.target.value)} className="h-10 px-4 rounded-lg border-2 border-gray-200 text-sm">
            <option value="all">الكل</option>
            <option value="active">نشط</option>
            <option value="inactive">غير نشط</option>
          </select>
          <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
            {([
              ['table', 'جدول'],
              ['grouped', 'حسب الشركة'],
              ['structure', 'هيكل'],
            ] as [Tab, string][]).map(([key, label]) => (
              <button key={key} onClick={() => setTab(key)} className={`px-3 py-1.5 rounded-md text-xs font-medium ${tab === key ? 'bg-white shadow-sm text-primary-700' : 'text-gray-500'}`}>{label}</button>
            ))}
          </div>
        </div>
      )}

      {/* Back button for detail view */}
      {tab === 'detail' && (
        <button onClick={() => { setTab('table'); setSelectedEmployee(null); setDetailData(null); }} className="flex items-center gap-2 text-sm text-gray-600 hover:text-primary-600 transition">
          <ArrowRight className="w-4 h-4" /> العودة لقائمة الموظفين
        </button>
      )}

      {/* ========== DETAIL VIEW ========== */}
      {tab === 'detail' && selectedEmployee && (
        <div className="space-y-4">
          <Card>
            <CardContent className="p-5">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-2xl bg-primary-100 flex items-center justify-center text-primary-700 text-2xl font-bold">
                  {selectedEmployee.name?.[0]}
                </div>
                <div className="flex-1">
                  <h2 className="text-xl font-bold text-gray-900">{selectedEmployee.name}</h2>
                  <div className="flex flex-wrap gap-2 mt-1">
                    <Badge variant="info">{selectedEmployee.code}</Badge>
                    <Badge variant={selectedEmployee.is_active ? 'success' : 'danger'}>{selectedEmployee.is_active ? 'نشط' : 'غير نشط'}</Badge>
                    <Badge variant={selectedEmployee.is_resident ? 'success' : 'warning'}>{selectedEmployee.is_resident ? 'ساكن' : 'غير ساكن'}</Badge>
                    {selectedEmployee.job_title && <Badge>{selectedEmployee.job_title}</Badge>}
                  </div>
                </div>
                <div className="text-left">
                  <p className="text-lg font-bold text-primary-600">{formatNum(selectedEmployee.total_salary || selectedEmployee.salary || 0)} ر.ي</p>
                  <p className="text-xs text-gray-400">الراتب الشامل</p>
                </div>
                <button
                  onClick={() => openEmployeeProfilePDF(selectedEmployee, detailData, bankItems)}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium bg-green-50 text-green-700 hover:bg-green-100 border border-green-200 transition"
                  title="تصدير ملف الموظف كـ PDF"
                >
                  <Download className="w-4 h-4" />
                  <span className="hidden sm:inline">تصدير PDF</span>
                </button>
              </div>
            </CardContent>
          </Card>

          <div className="flex gap-2 overflow-x-auto pb-1">
            {([
              ['profile', User, 'الملف الشخصي'],
              ['salary', DollarSign, 'الرواتب'],
              ['attendance', Calendar, 'الحضور'],
              ['evaluations', Star, 'التقييمات'],
              ['transactions', FileText, 'المعاملات'],
              ['leaves', Clock, 'الإجازات'],
              ['bank', Building2, 'المعلومات البنكية'],
            ] as const).map(([key, Icon, label]) => (
              <button key={key} onClick={() => setDetailTab(key)} className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium whitespace-nowrap ${detailTab === key ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                <Icon className="w-3.5 h-3.5" /> {label}
              </button>
            ))}
          </div>

          {detailLoading ? (
            <div className="flex items-center justify-center h-32"><div className="w-6 h-6 border-2 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" /></div>
          ) : detailData && (
            <>
              {/* Profile Tab */}
              {detailTab === 'profile' && (
                <Card><CardContent className="p-5">
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                    {[
                      ['الكود', selectedEmployee.code],
                      ['رقم البطاقة', selectedEmployee.card_number],
                      ['الهاتف', selectedEmployee.phone || '—'],
                      ['الوظيفة', selectedEmployee.job_title || '—'],
                      ['الشركة', selectedEmployee.company_name || '—'],
                      ['المنطقة', selectedEmployee.region_name || selectedEmployee.region || '—'],
                      ['الراتب الأساسي', `${formatNum(selectedEmployee.basic_salary || 0)} ر.ي`],
                      ['الراتب النقدي', `${formatNum(selectedEmployee.salary || 0)} ر.ي`],
                      ['الراتب الشامل', `${formatNum(selectedEmployee.total_salary || 0)} ر.ي`],
                      ['البدل اليومي', `${formatNum(selectedEmployee.daily_allowance || 0)} ر.ي`],
                      ['بدل الملابس', `${formatNum(selectedEmployee.clothing_allowance || 0)} ر.ي`],
                      ['البطاقة الصحية', `${formatNum(selectedEmployee.health_card_allowance || 0)} ر.ي`],
                      ['التأمين', `${formatNum(selectedEmployee.monthly_insurance || 0)} ر.ي`],
                      ['النوع', selectedEmployee.employee_type === 'supervisor' ? 'مشرف' : selectedEmployee.employee_type === 'admin' ? 'إداري' : 'عامل'],
                      ['نوع العامل', selectedEmployee.worker_type === 'permanent' ? 'دائم' : selectedEmployee.worker_type === 'daily' ? 'يومي' : 'تعاقد'],
                      ['المشرف', employees.find((e: any) => e.id === selectedEmployee.supervisor_id)?.name || '—'],
                    ].map(([label, value]) => (
                      <div key={label} className="bg-gray-50 rounded-lg p-3">
                        <p className="text-xs text-gray-400 mb-1">{label}</p>
                        <p className="text-sm font-medium text-gray-900">{value}</p>
                      </div>
                    ))}
                  </div>
                </CardContent></Card>
              )}

              {/* Salary Tab */}
              {detailTab === 'salary' && (
                <Card>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead><tr className="bg-gray-50 border-b">
                        <th className="px-3 py-3 text-right font-semibold text-xs">الشهر</th>
                        <th className="px-3 py-3 text-right font-semibold text-xs">الراتب الأساسي</th>
                        <th className="px-3 py-3 text-right font-semibold text-xs">الإضافي</th>
                        <th className="px-3 py-3 text-right font-semibold text-xs">الخصومات</th>
                        <th className="px-3 py-3 text-right font-semibold text-xs">الصافي</th>
                      </tr></thead>
                      <tbody>
                        {detailData.salaries.length === 0 ? (
                          <tr><td colSpan={5} className="text-center py-8 text-gray-400">لا توجد رواتب</td></tr>
                        ) : detailData.salaries.map((s: any) => (
                          <tr key={s.id} className="border-b hover:bg-gray-50">
                            <td className="px-3 py-3 font-medium">{s.month_year}</td>
                            <td className="px-3 py-3 text-blue-600">{formatNum(s.basic_payout || 0)}</td>
                            <td className="px-3 py-3 text-green-600">{formatNum(s.overtime_payout || 0)}</td>
                            <td className="px-3 py-3 text-red-600">{formatNum(s.total_deductions || 0)}</td>
                            <td className="px-3 py-3 font-bold text-primary-600">{formatNum(s.net_salary || 0)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              )}

              {/* Attendance Tab */}
              {detailTab === 'attendance' && (
                <Card>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead><tr className="bg-gray-50 border-b">
                        <th className="px-3 py-3 text-right font-semibold text-xs">التاريخ</th>
                        <th className="px-3 py-3 text-right font-semibold text-xs">الحالة</th>
                        <th className="px-3 py-3 text-right font-semibold text-xs">المنطقة</th>
                        <th className="px-3 py-3 text-right font-semibold text-xs">الموقع</th>
                      </tr></thead>
                      <tbody>
                        {detailData.attendance.length === 0 ? (
                          <tr><td colSpan={4} className="text-center py-8 text-gray-400">لا يوجد حضور</td></tr>
                        ) : detailData.attendance.map((a: any) => (
                          <tr key={a.id} className="border-b hover:bg-gray-50">
                            <td className="px-3 py-3">{a.date}</td>
                            <td className="px-3 py-3">
                              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${(a.attendance_status || a.status) === 'present' ? 'bg-green-100 text-green-700' : (a.attendance_status || a.status) === 'absent' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'}`}>
                                {(a.attendance_status || a.status) === 'present' ? 'حاضر' : (a.attendance_status || a.status) === 'absent' ? 'غائب' : (a.attendance_status || a.status)}
                              </span>
                            </td>
                            <td className="px-3 py-3 text-gray-500 text-xs">{a.region_name || '—'}</td>
                            <td className="px-3 py-3 text-gray-500 text-xs">{a.location || '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              )}

              {/* Evaluations Tab */}
              {detailTab === 'evaluations' && (
                <Card>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead><tr className="bg-gray-50 border-b">
                        <th className="px-3 py-3 text-right font-semibold text-xs">التاريخ</th>
                        <th className="px-3 py-3 text-right font-semibold text-xs">المُقيّم</th>
                        <th className="px-3 py-3 text-right font-semibold text-xs">النوع</th>
                        <th className="px-3 py-3 text-right font-semibold text-xs">التقييم</th>
                        <th className="px-3 py-3 text-right font-semibold text-xs">ملاحظات</th>
                      </tr></thead>
                      <tbody>
                        {detailData.evaluations.length === 0 ? (
                          <tr><td colSpan={5} className="text-center py-8 text-gray-400">لا توجد تقييمات</td></tr>
                        ) : detailData.evaluations.map((e: any) => (
                          <tr key={e.id} className="border-b hover:bg-gray-50">
                            <td className="px-3 py-3">{e.date}</td>
                            <td className="px-3 py-3 text-gray-500">{e.evaluator_name || '—'}</td>
                            <td className="px-3 py-3 text-xs">{e.evaluation_type === 'supervisor' ? 'مشرف' : 'متعهد'}</td>
                            <td className="px-3 py-3">
                              <span className={`inline-flex px-2.5 py-1 rounded-full text-xs font-bold ${e.score >= 80 ? 'bg-green-100 text-green-700' : e.score >= 60 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'}`}>
                                {e.score}
                              </span>
                            </td>
                            <td className="px-3 py-3 text-xs text-gray-500 max-w-[200px] truncate">{e.comments || '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              )}

              {/* Transactions Tab */}
              {detailTab === 'transactions' && (
                <Card>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead><tr className="bg-gray-50 border-b">
                        <th className="px-3 py-3 text-right font-semibold text-xs">التاريخ</th>
                        <th className="px-3 py-3 text-right font-semibold text-xs">النوع</th>
                        <th className="px-3 py-3 text-right font-semibold text-xs">المبلغ</th>
                        <th className="px-3 py-3 text-right font-semibold text-xs">القسط الشهري</th>
                        <th className="px-3 py-3 text-right font-semibold text-xs">البيان</th>
                      </tr></thead>
                      <tbody>
                        {detailData.transactions.length === 0 ? (
                          <tr><td colSpan={5} className="text-center py-8 text-gray-400">لا توجد معاملات</td></tr>
                        ) : detailData.transactions.map((t: any) => {
                          const typeLabels: Record<string, string> = { advance: 'سلفة', deduction: 'خصم', overtime: 'إضافي', penalty: 'غرامة', restaurant: 'مطعم', cafeteria: 'كافتيريا' };
                          const typeColors: Record<string, string> = { advance: 'text-blue-600', deduction: 'text-red-600', overtime: 'text-green-600', penalty: 'text-red-700', restaurant: 'text-orange-600', cafeteria: 'text-orange-600' };
                          return (
                            <tr key={t.id} className="border-b hover:bg-gray-50">
                              <td className="px-3 py-3">{t.date}</td>
                              <td className="px-3 py-3"><span className={`text-xs font-medium ${typeColors[t.transaction_type] || ''}`}>{typeLabels[t.transaction_type] || t.transaction_type}</span></td>
                              <td className="px-3 py-3 font-bold">{formatNum(t.amount)} ر.ي</td>
                              <td className="px-3 py-3 text-gray-500 text-xs">{t.monthly_installment ? `${formatNum(t.monthly_installment)} ر.ي` : '—'}</td>
                              <td className="px-3 py-3 text-gray-500 text-xs">{t.description || '—'}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </Card>
              )}

              {/* Leaves Tab */}
              {detailTab === 'leaves' && (
                <Card>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead><tr className="bg-gray-50 border-b">
                        <th className="px-3 py-3 text-right font-semibold text-xs">من</th>
                        <th className="px-3 py-3 text-right font-semibold text-xs">إلى</th>
                        <th className="px-3 py-3 text-right font-semibold text-xs">النوع</th>
                        <th className="px-3 py-3 text-right font-semibold text-xs">الأيام</th>
                        <th className="px-3 py-3 text-right font-semibold text-xs">الحالة</th>
                        <th className="px-3 py-3 text-right font-semibold text-xs">السبب</th>
                      </tr></thead>
                      <tbody>
                        {detailData.leaves.length === 0 ? (
                          <tr><td colSpan={6} className="text-center py-8 text-gray-400">لا توجد إجازات</td></tr>
                        ) : detailData.leaves.map((l: any) => (
                          <tr key={l.id} className="border-b hover:bg-gray-50">
                            <td className="px-3 py-3 text-xs">{l.start_date}</td>
                            <td className="px-3 py-3 text-xs">{l.end_date}</td>
                            <td className="px-3 py-3 text-xs">{l.leave_type_name || l.leave_type || '—'}</td>
                            <td className="px-3 py-3 font-medium">{l.total_days}</td>
                            <td className="px-3 py-3">
                              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${l.status === 'approved' ? 'bg-green-100 text-green-700' : l.status === 'rejected' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'}`}>
                                {l.status === 'approved' ? 'معتمدة' : l.status === 'rejected' ? 'مرفوضة' : 'قيد المراجعة'}
                              </span>
                            </td>
                            <td className="px-3 py-3 text-xs text-gray-500 max-w-[150px] truncate">{l.reason || '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              )}

              {/* Bank Info Tab */}
              {detailTab === 'bank' && (
                <BankInfoTab employeeId={selectedEmployee.id} employeeName={selectedEmployee.name} />
              )}
            </>
          )}
        </div>
      )}

      {/* ========== TABLE VIEW ========== */}
      {tab === 'table' && (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-primary-600 text-white">
                  <th className="px-3 py-3 text-right font-semibold">الكود</th>
                  <th className="px-3 py-3 text-right font-semibold">الاسم</th>
                  <th className="px-3 py-3 text-right font-semibold">رقم البطاقة</th>
                  <th className="px-3 py-3 text-right font-semibold">الوظيفة</th>
                  <th className="px-3 py-3 text-right font-semibold">الشركة</th>
                  <th className="px-3 py-3 text-right font-semibold">المشرف</th>
                  <th className="px-3 py-3 text-right font-semibold">الراتب الأساسي</th>
                  <th className="px-3 py-3 text-right font-semibold">الراتب الشامل</th>
                  <th className="px-3 py-3 text-right font-semibold">الحالة</th>
                  <th className="px-3 py-3 text-right font-semibold">إجراءات</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((emp) => {
                  const supName = employees.find((e: any) => e.id === emp.supervisor_id)?.name;
                  return (
                    <tr key={emp.id} className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer" onClick={() => loadEmployeeDetail(emp)}>
                      <td className="px-3 py-3"><span className="font-mono text-primary-600 font-bold text-xs">{emp.code}</span></td>
                      <td className="px-3 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-7 h-7 rounded-full bg-primary-100 flex items-center justify-center text-primary-700 text-xs font-bold">{emp.name?.[0]}</div>
                          <div>
                            <span className="font-medium">{emp.name}</span>
                            {emp.phone && <span className="block text-xs text-gray-400">{emp.phone}</span>}
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-3 text-gray-600 text-xs font-mono">{emp.card_number}</td>
                      <td className="px-3 py-3 text-gray-600">{emp.job_title || '—'}</td>
                      <td className="px-3 py-3"><span className="text-xs bg-gray-100 px-2 py-0.5 rounded-full">{emp.company_name || '—'}</span></td>
                      <td className="px-3 py-3 text-xs text-gray-500">{supName || '—'}</td>
                      <td className="px-3 py-3 font-medium text-blue-600">{formatNum(emp.basic_salary || 0)}</td>
                      <td className="px-3 py-3 font-bold text-primary-600">{formatNum(emp.total_salary || emp.salary || 0)}</td>
                      <td className="px-3 py-3"><Badge variant={emp.is_active ? 'success' : 'danger'}>{emp.is_active ? 'نشط' : 'غير نشط'}</Badge></td>
                      <td className="px-3 py-3">
                        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                          <button onClick={() => loadEmployeeDetail(emp)} className="p-1.5 rounded-lg hover:bg-green-50 text-green-500"><Eye className="w-4 h-4" /></button>
                          <button onClick={() => openEdit(emp)} className="p-1.5 rounded-lg hover:bg-blue-50 text-blue-500"><Edit className="w-4 h-4" /></button>
                          <button onClick={() => handleDelete(emp.id)} className="p-1.5 rounded-lg hover:bg-red-50 text-red-500"><Trash2 className="w-4 h-4" /></button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {filtered.length === 0 && <tr><td colSpan={10} className="text-center py-8 text-gray-400">لا توجد بيانات</td></tr>}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* ========== GROUPED VIEW ========== */}
      {tab === 'grouped' && (
        <div className="space-y-4">
          {groupedByCompany.map((group) => (
            <Card key={group.id}>
              <CardContent className="p-5">
                <div className="flex items-center gap-3 mb-4 pb-3 border-b">
                  <div className="w-10 h-10 rounded-xl bg-primary-100 flex items-center justify-center"><Building2 className="w-5 h-5 text-primary-600" /></div>
                  <div>
                    <h3 className="font-bold text-gray-900">{group.name}</h3>
                    <p className="text-xs text-gray-400">{group.employees.length} موظف — {group.supervisors.length} مشرف</p>
                  </div>
                  <div className="mr-auto text-sm font-bold text-primary-600">
                    إجمالي الرواتب: {formatNum(group.employees.reduce((s: number, e: any) => s + (e.total_salary || e.salary || 0), 0))} ر.ي
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead><tr className="bg-gray-50 text-gray-500">
                      <th className="px-2 py-2 text-right">الكود</th>
                      <th className="px-2 py-2 text-right">الاسم</th>
                      <th className="px-2 py-2 text-right">الوظيفة</th>
                      <th className="px-2 py-2 text-right">المشرف</th>
                      <th className="px-2 py-2 text-right">الراتب الشامل</th>
                      <th className="px-2 py-2 text-right">إجراءات</th>
                    </tr></thead>
                    <tbody>
                      {group.employees.map((emp: any) => {
                        const supName = employees.find((e: any) => e.id === emp.supervisor_id)?.name;
                        return (
                          <tr key={emp.id} className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer" onClick={() => loadEmployeeDetail(emp)}>
                            <td className="px-2 py-2 font-mono text-primary-600 font-bold">{emp.code}</td>
                            <td className="px-2 py-2 font-medium">{emp.name}</td>
                            <td className="px-2 py-2 text-gray-600">{emp.job_title || '—'}</td>
                            <td className="px-2 py-2 text-gray-500">{supName || '—'}</td>
                            <td className="px-2 py-2 font-bold text-primary-600">{formatNum(emp.total_salary || emp.salary || 0)}</td>
                            <td className="px-2 py-2" onClick={(e) => e.stopPropagation()}>
                              <div className="flex items-center gap-1">
                                <button onClick={() => loadEmployeeDetail(emp)} className="p-1 rounded hover:bg-green-50 text-green-500"><Eye className="w-3 h-3" /></button>
                                <button onClick={() => openEdit(emp)} className="p-1 rounded hover:bg-blue-50 text-blue-500"><Edit className="w-3 h-3" /></button>
                                <button onClick={() => handleDelete(emp.id)} className="p-1 rounded hover:bg-red-50 text-red-500"><Trash2 className="w-3 h-3" /></button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          ))}
          {ungrouped.length > 0 && (
            <Card>
              <CardContent className="p-5">
                <h3 className="font-bold text-gray-900 mb-3">غير مرتبطين بشركة ({ungrouped.length})</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead><tr className="bg-gray-50 text-gray-500">
                      <th className="px-2 py-2 text-right">الكود</th>
                      <th className="px-2 py-2 text-right">الاسم</th>
                      <th className="px-2 py-2 text-right">الوظيفة</th>
                      <th className="px-2 py-2 text-right">الراتب الشامل</th>
                      <th className="px-2 py-2 text-right">إجراءات</th>
                    </tr></thead>
                    <tbody>
                      {ungrouped.map((emp) => (
                        <tr key={emp.id} className="border-b border-gray-100 cursor-pointer" onClick={() => loadEmployeeDetail(emp)}>
                          <td className="px-2 py-2 font-mono text-primary-600 font-bold">{emp.code}</td>
                          <td className="px-2 py-2 font-medium">{emp.name}</td>
                          <td className="px-2 py-2 text-gray-600">{emp.job_title || '—'}</td>
                          <td className="px-2 py-2 font-bold">{formatNum(emp.total_salary || emp.salary || 0)}</td>
                          <td className="px-2 py-2">
                            <button onClick={() => openEdit(emp)} className="p-1 rounded hover:bg-blue-50 text-blue-500"><Edit className="w-3 h-3" /></button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* ========== STRUCTURE VIEW ========== */}
      {tab === 'structure' && (
        <div className="space-y-4">
          {groupedByCompany.map((group) => (
            <Card key={group.id}>
              <CardContent className="p-5">
                <div className="flex items-center gap-3 mb-4 pb-3 border-b">
                  <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center"><Building2 className="w-5 h-5 text-amber-600" /></div>
                  <div>
                    <h3 className="font-bold text-gray-900">{group.name}</h3>
                    <p className="text-xs text-gray-400">{group.employees.length} موظف</p>
                  </div>
                </div>
                {group.supervisors.length > 0 ? (
                  group.supervisors.map((sup: any) => {
                    const workers = group.employees.filter((e: any) => e.supervisor_id === sup.id);
                    const unassigned = group.employees.filter((e: any) => e.supervisor_id !== sup.id && e.employee_type !== 'supervisor');
                    return (
                      <div key={sup.id} className="mb-4 last:mb-0">
                        <div className="flex items-center gap-3 mb-2 p-3 bg-primary-50 rounded-xl">
                          <div className="w-9 h-9 rounded-full bg-primary-600 flex items-center justify-center text-white text-sm font-bold">{sup.name?.[0]}</div>
                          <div>
                            <p className="font-bold text-primary-900 text-sm">{sup.name}</p>
                            <p className="text-xs text-primary-600">{sup.job_title || 'مشرف'} — {workers.length} عامل</p>
                          </div>
                        </div>
                        {workers.length > 0 ? (
                          <div className="mr-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                            {workers.map((w: any) => (
                              <div key={w.id} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer transition" onClick={() => loadEmployeeDetail(w)}>
                                <div className="w-7 h-7 rounded-full bg-gray-200 flex items-center justify-center text-gray-600 text-xs font-bold">{w.name?.[0]}</div>
                                <div className="flex-1 min-w-0">
                                  <p className="text-sm font-medium text-gray-900 truncate">{w.name}</p>
                                  <p className="text-xs text-gray-400">{w.job_title || '—'} — {formatNum(w.total_salary || w.salary || 0)} ر.ي</p>
                                </div>
                                <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${w.is_resident ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700'}`}>
                                  {w.is_resident ? 'ساكن' : 'مقيم'}
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="mr-6 text-xs text-gray-400 py-2">لا يوجد عمال مرتبطين</p>
                        )}
                        {unassigned.length > 0 && (
                          <div className="mt-2">
                            <p className="text-xs text-gray-400 mb-1 mr-6">عمال غير مرتبطين بمشرف:</p>
                            <div className="mr-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                              {unassigned.map((w: any) => (
                                <div key={w.id} className="flex items-center gap-3 p-3 bg-yellow-50 rounded-lg border border-yellow-200 cursor-pointer hover:bg-yellow-100 transition" onClick={() => loadEmployeeDetail(w)}>
                                  <div className="w-7 h-7 rounded-full bg-yellow-200 flex items-center justify-center text-yellow-700 text-xs font-bold">{w.name?.[0]}</div>
                                  <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium text-gray-900 truncate">{w.name}</p>
                                    <p className="text-xs text-gray-400">{w.job_title || '—'}</p>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })
                ) : (
                  <div className="space-y-2">
                    {group.employees.map((emp: any) => (
                      <div key={emp.id} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer transition" onClick={() => loadEmployeeDetail(emp)}>
                        <div className="w-7 h-7 rounded-full bg-gray-200 flex items-center justify-center text-gray-600 text-xs font-bold">{emp.name?.[0]}</div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">{emp.name}</p>
                          <p className="text-xs text-gray-400">{emp.job_title || '—'} — {formatNum(emp.total_salary || emp.salary || 0)} ر.ي</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* ========== ADD/EDIT MODAL ========== */}
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editItem ? 'تعديل موظف' : 'إضافة موظف جديد'} size="lg">
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">الاسم الكامل *</label>
              <Input value={form.name || ''} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="الاسم الكامل" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">كود الموظف *</label>
              <Input value={form.code || ''} onChange={(e) => setForm({ ...form, code: e.target.value })} placeholder="كود الموظف (يدوي)" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">رقم البطاقة *</label>
              <Input value={form.card_number || ''} onChange={(e) => setForm({ ...form, card_number: e.target.value })} placeholder="رقم البطاقة" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">رقم الهاتف</label>
              <Input value={form.phone || ''} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="رقم الهاتف" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">الوظيفة</label>
              {useNewJobTitle ? (
                <Input value={form.job_title || ''} onChange={(e) => setForm({ ...form, job_title: e.target.value })} placeholder="أدخل المسمى الوظيفي" />
              ) : (
                <select value={form.job_title || ''} onChange={(e) => setForm({ ...form, job_title: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm focus:border-primary-500 outline-none">
                  <option value="">اختر الوظيفة</option>
                  {jobTitles.map((jt) => <option key={jt} value={jt}>{jt}</option>)}
                </select>
              )}
              <button type="button" onClick={() => setUseNewJobTitle(!useNewJobTitle)} className="mt-1 text-xs text-primary-600 hover:underline">
                {useNewJobTitle ? 'اختيار من القائمة' : 'إضافة وظيفة جديدة'}
              </button>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">الشركة</label>
              <select value={form.company_id || ''} onChange={(e) => setForm({ ...form, company_id: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm focus:border-primary-500 outline-none">
                <option value="">اختر الشركة</option>
                {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">المنطقة</label>
              <select value={form.region_id || ''} onChange={(e) => setForm({ ...form, region_id: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm focus:border-primary-500 outline-none">
                <option value="">اختر المنطقة</option>
                {regions.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
              </select>
            </div>
            {form.employee_type === 'worker' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">المشرف</label>
                <select value={form.supervisor_id || ''} onChange={(e) => setForm({ ...form, supervisor_id: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm focus:border-primary-500 outline-none">
                  <option value="">اختر المشرف</option>
                  {supervisors.filter(s => !form.company_id || s.company_id === Number(form.company_id)).map((s) => (
                    <option key={s.id} value={s.id}>{s.name} ({s.company_name || 'بدون شركة'})</option>
                  ))}
                </select>
              </div>
            )}

            {/* Salaries */}
            <div className="col-span-2 border-t pt-4">
              <h4 className="font-medium text-sm text-gray-700 mb-3">الرواتب والمستحقات</h4>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">الراتب الأساسي (ر.ي)</label>
              <Input type="number" value={form.basic_salary || ''} onChange={(e) => setForm({ ...form, basic_salary: e.target.value })} placeholder="0" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">الراتب الشامل (ر.ي)</label>
              <Input type="number" value={form.total_salary || ''} onChange={(e) => setForm({ ...form, total_salary: e.target.value })} placeholder="0" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">الراتب النقدي (ر.ي)</label>
              <Input type="number" value={form.salary || ''} onChange={(e) => setForm({ ...form, salary: e.target.value })} placeholder="0" />
            </div>
            {form.is_resident && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">البدل اليومي (ر.ي)</label>
                <Input type="number" value={form.daily_allowance || ''} onChange={(e) => setForm({ ...form, daily_allowance: e.target.value })} placeholder="0" />
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">بدل الملابس (ر.ي)</label>
              <Input type="number" value={form.clothing_allowance || ''} onChange={(e) => setForm({ ...form, clothing_allowance: e.target.value })} placeholder="0" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">بدل البطاقة الصحية (ر.ي)</label>
              <Input type="number" value={form.health_card_allowance || ''} onChange={(e) => setForm({ ...form, health_card_allowance: e.target.value })} placeholder="0" />
            </div>

            {/* Status */}
            <div className="col-span-2 border-t pt-4">
              <h4 className="font-medium text-sm text-gray-700 mb-3">الحالة</h4>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">النوع</label>
              <select value={form.employee_type || 'worker'} onChange={(e) => setForm({ ...form, employee_type: e.target.value, supervisor_id: e.target.value !== 'worker' ? '' : form.supervisor_id })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
                <option value="worker">عامل</option>
                <option value="supervisor">مشرف</option>
                <option value="admin">إداري</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">نوع العامل</label>
              <select value={form.worker_type || 'permanent'} onChange={(e) => setForm({ ...form, worker_type: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
                <option value="permanent">دائم</option>
                <option value="daily">يومي</option>
                <option value="contract">تعاقد</option>
              </select>
            </div>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={form.is_active !== false} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} className="w-4 h-4 rounded" />
                <span className="text-sm font-medium text-gray-700">نشط</span>
              </label>
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={form.is_resident === true} onChange={(e) => setForm({ ...form, is_resident: e.target.checked })} className="w-4 h-4 rounded" />
                <span className="text-sm font-medium text-gray-700">ساكن</span>
              </label>
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setModalOpen(false)}>إلغاء</Button>
            <Button onClick={handleSave} disabled={saving || !form.name || !form.card_number}>
              {saving ? 'جاري الحفظ...' : editItem ? 'تحديث' : 'حفظ'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
