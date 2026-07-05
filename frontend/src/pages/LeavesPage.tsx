import { useState, useEffect } from 'react';
import api from '@/api/client';
import { formatNum } from '@/lib/utils';
import { Calendar, Check, X, Clock, Plus, Filter } from 'lucide-react';

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-700',
  approved: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700',
  cancelled: 'bg-gray-100 text-gray-700',
};

export default function LeavesPage() {
  const [leaves, setLeaves] = useState<any[]>([]);
  const [balances, setBalances] = useState<any[]>([]);
  const [leaveTypes, setLeaveTypes] = useState<any[]>([]);
  const [employees, setEmployees] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'requests' | 'balances'>('requests');
  const [filterStatus, setFilterStatus] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ employee_id: '', leave_type_id: '', start_date: '', end_date: '', total_days: '', reason: '' });
  const [creating, setCreating] = useState(false);
  const currentYear = new Date().getFullYear();

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [leavesRes, typesRes, empRes] = await Promise.all([
        api.get('/leave-requests' + (filterStatus ? `?status=${filterStatus}` : '')),
        api.get('/leave-types'),
        api.get('/employees'),
      ]);
      setLeaves(leavesRes.data.data || []);
      setLeaveTypes(typesRes.data.data || []);
      setEmployees(empRes.data.data || []);

      // Load balances for each employee
      const balRes = await api.get(`/leave-balances?year=${currentYear}`);
      setBalances(balRes.data.data || []);
    } catch {}
    setLoading(false);
  };

  useEffect(() => { loadData(); }, [filterStatus]);

  const handleCreate = async () => {
    if (!form.employee_id || !form.leave_type_id || !form.start_date || !form.end_date) return;
    setCreating(true);
    try {
      await api.post('/leave-requests', {
        ...form,
        employee_id: Number(form.employee_id),
        leave_type_id: Number(form.leave_type_id),
        total_days: Number(form.total_days),
      });
      setModalOpen(false);
      setForm({ employee_id: '', leave_type_id: '', start_date: '', end_date: '', total_days: '', reason: '' });
      loadData();
    } catch (e: any) {
      alert(e.response?.data?.message || 'خطأ في الإنشاء');
    }
    setCreating(false);
  };

  const handleApprove = async (id: number) => {
    if (!confirm('هل تريد الموافقة على هذا الطلب؟')) return;
    try {
      await api.post(`/leave-requests/${id}/approve`);
      loadData();
    } catch (e: any) {
      alert(e.response?.data?.message || 'خطأ');
    }
  };

  const handleReject = async (id: number) => {
    const reason = prompt('سبب الرفض (اختياري):');
    try {
      await api.post(`/leave-requests/${id}/reject`, { reason });
      loadData();
    } catch (e: any) {
      alert(e.response?.data?.message || 'خطأ');
    }
  };

  // Calculate days when dates change
  useEffect(() => {
    if (form.start_date && form.end_date) {
      const start = new Date(form.start_date);
      const end = new Date(form.end_date);
      const diff = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1;
      if (diff > 0) setForm(f => ({ ...f, total_days: String(diff) }));
    }
  }, [form.start_date, form.end_date]);

  // Group balances by employee
  const balancesByEmployee = balances.reduce((acc: any, b: any) => {
    if (!acc[b.employee_id]) acc[b.employee_id] = { name: b.employee_name, items: [] };
    acc[b.employee_id].items.push(b);
    return acc;
  }, {});

  return (
    <div className="p-4 lg:p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">إدارة الإجازات</h1>
          <p className="text-sm text-gray-500 mt-1">طلبات الإجازة وأرصدة الإجازات</p>
        </div>
        <button onClick={() => setModalOpen(true)} className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
          <Plus size={18} /> طلب إجازة جديد
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg mb-6 w-fit">
        <button onClick={() => setTab('requests')} className={`px-4 py-2 rounded-md text-sm font-medium transition ${tab === 'requests' ? 'bg-white shadow text-blue-600' : 'text-gray-600 hover:text-gray-800'}`}>
          طلبات الإجازة ({leaves.length})
        </button>
        <button onClick={() => setTab('balances')} className={`px-4 py-2 rounded-md text-sm font-medium transition ${tab === 'balances' ? 'bg-white shadow text-blue-600' : 'text-gray-600 hover:text-gray-800'}`}>
          أرصدة الإجازات
        </button>
      </div>

      {/* Requests Tab */}
      {tab === 'requests' && (
        <>
          <div className="flex gap-2 mb-4">
            <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} className="h-9 px-3 rounded-lg border border-gray-200 text-sm">
              <option value="">جميع الحالات</option>
              <option value="pending">قيد المراجعة</option>
              <option value="approved">تمت الموافقة</option>
              <option value="rejected">مرفوض</option>
            </select>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-100">
                    <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">الموظف</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">نوع الإجازة</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">من</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">إلى</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">الأيام</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">السبب</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">الحالة</th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">الإجراءات</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {loading ? (
                    <tr><td colSpan={8} className="text-center py-8 text-gray-400">جاري التحميل...</td></tr>
                  ) : leaves.length === 0 ? (
                    <tr><td colSpan={8} className="text-center py-8 text-gray-400">لا توجد طلبات</td></tr>
                  ) : leaves.map(l => (
                    <tr key={l.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-900">{l.employee_name}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{l.leave_type_name}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{l.start_date}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{l.end_date}</td>
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">{l.total_days}</td>
                      <td className="px-4 py-3 text-sm text-gray-500 max-w-[150px] truncate">{l.reason || '-'}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${statusColors[l.status]}`}>
                          {l.status === 'pending' && <Clock size={12} />}
                          {l.status === 'approved' && <Check size={12} />}
                          {l.status === 'rejected' && <X size={12} />}
                          {l.status_name}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {l.status === 'pending' && (
                          <div className="flex gap-2">
                            <button onClick={() => handleApprove(l.id)} className="text-xs text-green-600 hover:text-green-700 font-medium">موافقة</button>
                            <button onClick={() => handleReject(l.id)} className="text-xs text-red-600 hover:text-red-700 font-medium">رفض</button>
                          </div>
                        )}
                        {l.status === 'approved' && l.approver_name && (
                          <span className="text-xs text-gray-500">وافق: {l.approver_name}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* Balances Tab */}
      {tab === 'balances' && (
        <div className="space-y-4">
          {Object.keys(balancesByEmployee).length === 0 && !loading && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8 text-center">
              <Calendar size={48} className="mx-auto text-gray-300 mb-3" />
              <p className="text-gray-500">لا توجد أرصدة إجازات. قم بتهيئة الأرصدة أولاً.</p>
            </div>
          )}
          {Object.entries(balancesByEmployee).map(([empId, empData]: [string, any]) => (
            <div key={empId} className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
              <h3 className="font-bold text-gray-900 mb-3">{empData.name}</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {empData.items.filter((b: any) => !b.leave_type_name?.includes('أمومة')).map((b: any) => (
                  <div key={b.id} className="bg-gray-50 rounded-lg p-3">
                    <div className="text-sm font-medium text-gray-700 mb-2">{b.leave_type_name}</div>
                    {b.total_days >= 999 ? (
                      <div className="text-xs text-gray-500">غير محدود — مستخدم: {b.used_days} يوم</div>
                    ) : (
                      <>
                        <div className="flex justify-between text-xs text-gray-500 mb-1">
                          <span>المتبقي</span>
                          <span className="font-bold text-blue-600">{b.remaining_days} يوم</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-1.5">
                          <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${b.total_days > 0 ? (b.remaining_days / b.total_days) * 100 : 0}%` }} />
                        </div>
                        <div className="flex justify-between text-[10px] text-gray-400 mt-1">
                          <span>مستخدم: {b.used_days}</span>
                          <span>إجمالي: {b.total_days}</span>
                        </div>
                      </>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Modal */}
      {modalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
            <div className="p-6 border-b border-gray-100">
              <h2 className="text-lg font-bold text-gray-900">طلب إجازة جديد</h2>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">الموظف *</label>
                <select value={form.employee_id} onChange={e => setForm({...form, employee_id: e.target.value})} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
                  <option value="">اختر الموظف</option>
                  {employees.map((e: any) => <option key={e.id} value={e.id}>{e.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">نوع الإجازة *</label>
                <select value={form.leave_type_id} onChange={e => setForm({...form, leave_type_id: e.target.value})} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
                  <option value="">اختر النوع</option>
                  {leaveTypes.filter((t: any) => !t.name_ar?.includes('أمومة') && !t.name_ar?.includes('مرضية')).map((t: any) => <option key={t.id} value={t.id}>{t.name_ar} ({t.days_per_year > 0 ? `${t.days_per_year} يوم` : 'بدون حد'})</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">من تاريخ *</label>
                  <input type="date" value={form.start_date} onChange={e => setForm({...form, start_date: e.target.value})} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">إلى تاريخ *</label>
                  <input type="date" value={form.end_date} onChange={e => setForm({...form, end_date: e.target.value})} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">عدد الأيام</label>
                <input type="number" value={form.total_days} onChange={e => setForm({...form, total_days: e.target.value})} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm bg-gray-50" readOnly />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">سبب الإجازة</label>
                <textarea value={form.reason} onChange={e => setForm({...form, reason: e.target.value})} className="w-full h-20 px-3 py-2 rounded-lg border-2 border-gray-200 text-sm resize-none" placeholder="اختياري..." />
              </div>
            </div>
            <div className="p-6 border-t border-gray-100 flex gap-3 justify-end">
              <button onClick={() => setModalOpen(false)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">إلغاء</button>
              <button onClick={handleCreate} disabled={creating || !form.employee_id || !form.leave_type_id || !form.start_date || !form.end_date} className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
                {creating ? 'جاري الإرسال...' : 'إرسال الطلب'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
