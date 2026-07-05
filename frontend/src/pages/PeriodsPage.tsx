import { useState, useEffect } from 'react';
import api from '@/api/client';
import { Calendar, Lock, Unlock, CheckCircle, Plus, AlertTriangle } from 'lucide-react';

const statusColors: Record<string, string> = {
  open: 'bg-green-100 text-green-700',
  closed: 'bg-yellow-100 text-yellow-700',
  locked: 'bg-red-100 text-red-700',
};

const statusIcons: Record<string, any> = {
  open: Unlock,
  closed: CheckCircle,
  locked: Lock,
};

export default function PeriodsPage() {
  const [periods, setPeriods] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ name: '', start_date: '', end_date: '', notes: '' });
  const [creating, setCreating] = useState(false);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const r = await api.get('/periods');
      setPeriods(r.data.data || []);
    } catch {}
    setLoading(false);
  };

  const handleCreate = async () => {
    if (!form.name || !form.start_date || !form.end_date) return;
    setCreating(true);
    try {
      await api.post('/periods', form);
      setModalOpen(false);
      setForm({ name: '', start_date: '', end_date: '', notes: '' });
      loadData();
    } catch (e: any) {
      alert(e.response?.data?.message || 'خطأ في الإنشاء');
    }
    setCreating(false);
  };

  const handleClose = async (id: number) => {
    if (!confirm('هل تريد إغلاق هذه الفترة؟ لن يتمكن من إنشاء معاملات جديدة')) return;
    try {
      await api.post(`/periods/${id}/close`);
      loadData();
    } catch (e: any) {
      alert(e.response?.data?.message || 'خطأ');
    }
  };

  const handleReopen = async (id: number) => {
    if (!confirm('هل تريد إعادة فتح هذه الفترة؟')) return;
    try {
      await api.post(`/periods/${id}/reopen`);
      loadData();
    } catch (e: any) {
      alert(e.response?.data?.message || 'خطأ');
    }
  };

  const openPeriod = periods.find(p => p.status === 'open');

  return (
    <div className="p-4 lg:p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">الفترات المالية</h1>
          <p className="text-sm text-gray-500 mt-1">إدارة وإغلاق الفترات المالية الشهرية</p>
        </div>
        <button onClick={() => setModalOpen(true)} className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
          <Plus size={18} /> فترة جديدة
        </button>
      </div>

      {/* Period Status Banner */}
      {openPeriod ? (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 mb-6 flex items-center gap-3">
          <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
            <Unlock size={20} className="text-green-600" />
          </div>
          <div>
            <div className="font-semibold text-green-800">فترة مفتوحة: {openPeriod.name}</div>
            <div className="text-sm text-green-600">{openPeriod.start_date} إلى {openPeriod.end_date}</div>
          </div>
        </div>
      ) : (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 flex items-center gap-3">
          <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
            <AlertTriangle size={20} className="text-red-600" />
          </div>
          <div>
            <div className="font-semibold text-red-800">لا توجد فترة مفتوحة</div>
            <div className="text-sm text-red-600">لا يمكن إنشاء معاملات مالية أو احتساب رواتب بدون فترة مفتوحة</div>
          </div>
        </div>
      )}

      {/* Periods Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-100">
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">الاسم</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">النوع</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">تاريخ البداية</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">تاريخ النهاية</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">الحالة</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase">الإجراءات</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                <tr><td colSpan={6} className="text-center py-8 text-gray-400">جاري التحميل...</td></tr>
              ) : periods.length === 0 ? (
                <tr><td colSpan={6} className="text-center py-8 text-gray-400">لا توجد فترات</td></tr>
              ) : periods.map(p => {
                const StatusIcon = statusIcons[p.status] || Unlock;
                return (
                  <tr key={p.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{p.name}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{p.period_type === 'monthly' ? 'شهرية' : 'سنوية'}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{p.start_date}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{p.end_date}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${statusColors[p.status] || ''}`}>
                        <StatusIcon size={14} />
                        {p.status_name}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {p.status === 'open' && (
                        <button onClick={() => handleClose(p.id)} className="text-sm text-red-600 hover:text-red-700 font-medium">إغلاق</button>
                      )}
                      {p.status === 'closed' && (
                        <button onClick={() => handleReopen(p.id)} className="text-sm text-blue-600 hover:text-blue-700 font-medium">إعادة فتح</button>
                      )}
                      {p.status === 'locked' && (
                        <span className="text-sm text-gray-400">مقفلة نهائياً</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Modal */}
      {modalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
            <div className="p-6 border-b border-gray-100">
              <h2 className="text-lg font-bold text-gray-900">إنشاء فترة مالية جديدة</h2>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">اسم الفترة *</label>
                <input type="text" value={form.name} onChange={e => setForm({...form, name: e.target.value})} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm" placeholder="مثال: يوليو 2026" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">تاريخ البداية *</label>
                  <input type="date" value={form.start_date} onChange={e => setForm({...form, start_date: e.target.value})} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">تاريخ النهاية *</label>
                  <input type="date" value={form.end_date} onChange={e => setForm({...form, end_date: e.target.value})} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">ملاحظات</label>
                <textarea value={form.notes} onChange={e => setForm({...form, notes: e.target.value})} className="w-full h-20 px-3 py-2 rounded-lg border-2 border-gray-200 text-sm resize-none" />
              </div>
            </div>
            <div className="p-6 border-t border-gray-100 flex gap-3 justify-end">
              <button onClick={() => setModalOpen(false)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">إلغاء</button>
              <button onClick={handleCreate} disabled={creating || !form.name || !form.start_date || !form.end_date} className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
                {creating ? 'جاري الإنشاء...' : 'إنشاء'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
