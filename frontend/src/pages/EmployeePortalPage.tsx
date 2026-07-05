import { useState, useEffect } from 'react';
import api from '@/api/client';
import { User, Calendar, DollarSign, Clock, Check, X, Lock, Eye, EyeOff, Star } from 'lucide-react';

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-700',
  approved: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700',
  present: 'bg-green-100 text-green-700',
  late: 'bg-yellow-100 text-yellow-700',
  sick: 'bg-blue-100 text-blue-700',
  absent: 'bg-red-100 text-red-700',
  annual_leave: 'bg-purple-100 text-purple-700',
};

export default function EmployeePortalPage() {
  const [profile, setProfile] = useState<any>(null);
  const [attendance, setAttendance] = useState<any[]>([]);
  const [salaries, setSalaries] = useState<any[]>([]);
  const [leaves, setLeaves] = useState<any>({ balances: [], requests: [] });
  const [transactions, setTransactions] = useState<any[]>([]);
  const [evaluations, setEvaluations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'profile' | 'attendance' | 'salaries' | 'transactions' | 'evaluations' | 'leaves' | 'password'>('profile');
  const [leaveModalOpen, setLeaveModalOpen] = useState(false);
  const [leaveTypes, setLeaveTypes] = useState<any[]>([]);
  const [leaveForm, setLeaveForm] = useState({ leave_type_id: '', start_date: '', end_date: '', total_days: '', reason: '' });
  const [month, setMonth] = useState(String(new Date().getMonth() + 1));
  const [year, setYear] = useState(String(new Date().getFullYear()));
  const [pwForm, setPwForm] = useState({ old_password: '', new_password: '', confirm_password: '' });
  const [showPw, setShowPw] = useState(false);
  const [pwSaving, setPwSaving] = useState(false);
  const [txFilter, setTxFilter] = useState('');

  useEffect(() => { loadProfile(); }, []);

  const loadProfile = async () => {
    try {
      const r = await api.get('/employee/my-profile');
      setProfile(r.data.data);
    } catch {
      setLoading(false);
      return;
    }
    setLoading(false);
  };

  const loadAttendance = async () => {
    try {
      const r = await api.get(`/employee/my-attendance?month=${month}&year=${year}`);
      setAttendance(r.data.data || []);
    } catch {}
  };

  const loadSalaries = async () => {
    try {
      const r = await api.get('/employee/my-salaries');
      setSalaries(r.data.data || []);
    } catch {}
  };

  const loadLeaves = async () => {
    try {
      const [leavesRes, typesRes] = await Promise.all([
        api.get('/employee/my-leaves'),
        api.get('/leave-types'),
      ]);
      setLeaves(leavesRes.data.data || { balances: [], requests: [] });
      setLeaveTypes(typesRes.data.data || []);
    } catch {}
  };

  const loadTransactions = async () => {
    try {
      const r = await api.get('/employee/my-transactions');
      setTransactions(r.data.data || []);
    } catch {}
  };

  const loadEvaluations = async () => {
    try {
      const r = await api.get('/employee/my-evaluations');
      setEvaluations(r.data.data || []);
    } catch {}
  };

  useEffect(() => {
    if (tab === 'attendance') loadAttendance();
    if (tab === 'salaries') loadSalaries();
    if (tab === 'leaves') loadLeaves();
    if (tab === 'transactions') loadTransactions();
    if (tab === 'evaluations') loadEvaluations();
  }, [tab, month, year]);

  const handleLeaveRequest = async () => {
    if (!leaveForm.leave_type_id || !leaveForm.start_date || !leaveForm.end_date) return;
    try {
      await api.post('/leave-requests', {
        leave_type_id: Number(leaveForm.leave_type_id),
        start_date: leaveForm.start_date,
        end_date: leaveForm.end_date,
        total_days: Number(leaveForm.total_days),
        reason: leaveForm.reason,
      });
      setLeaveModalOpen(false);
      setLeaveForm({ leave_type_id: '', start_date: '', end_date: '', total_days: '', reason: '' });
      loadLeaves();
    } catch (e: any) {
      alert(e.response?.data?.message || 'خطأ');
    }
  };

  useEffect(() => {
    if (leaveForm.start_date && leaveForm.end_date) {
      const start = new Date(leaveForm.start_date);
      const end = new Date(leaveForm.end_date);
      const diff = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1;
      if (diff > 0) setLeaveForm(f => ({ ...f, total_days: String(diff) }));
    }
  }, [leaveForm.start_date, leaveForm.end_date]);

  if (loading) return <div className="p-8 text-center text-gray-400">جاري التحميل...</div>;
  if (!profile) return <div className="p-8 text-center text-gray-400">لم يتم ربط حسابك بموظف</div>;

  const tabs = [
    { key: 'profile', label: 'الملف الشخصي', icon: User },
    { key: 'attendance', label: 'الحضور', icon: Calendar },
    { key: 'salaries', label: 'الرواتب', icon: DollarSign },
    { key: 'transactions', label: 'المعاملات المالية', icon: DollarSign },
    { key: 'evaluations', label: 'التقييمات', icon: Star },
    { key: 'leaves', label: 'الإجازات', icon: Clock },
    { key: 'password', label: 'تغيير كلمة المرور', icon: Lock },
  ];

  const handleChangePassword = async () => {
    if (!pwForm.old_password || !pwForm.new_password) return alert('أدخل كلمة المرور القديمة والجديدة');
    if (pwForm.new_password !== pwForm.confirm_password) return alert('كلمتا المرور غير متطابقتين');
    if (pwForm.new_password.length < 4) return alert('كلمة المرور يجب أن تكون 4 أحرف على الأقل');
    setPwSaving(true);
    try {
      await api.post('/employee/change-password', { old_password: pwForm.old_password, new_password: pwForm.new_password });
      alert('تم تغيير كلمة المرور بنجاح');
      setPwForm({ old_password: '', new_password: '', confirm_password: '' });
    } catch (e: any) { alert(e.response?.data?.message || 'خطأ'); }
    setPwSaving(false);
  };

  return (
    <div className="p-4 lg:p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="bg-gradient-to-l from-blue-600 to-blue-700 rounded-2xl p-6 text-white mb-6">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center text-2xl font-bold">
            {profile.name?.charAt(0)}
          </div>
          <div>
            <h1 className="text-2xl font-bold">{profile.name}</h1>
            <p className="text-blue-100">{profile.job_title} - {profile.company_name}</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg mb-6 overflow-x-auto">
        {tabs.map(t => {
          const Icon = t.icon;
          return (
            <button key={t.key} onClick={() => setTab(t.key as any)} className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition whitespace-nowrap ${tab === t.key ? 'bg-white shadow text-blue-600' : 'text-gray-600 hover:text-gray-800'}`}>
              <Icon size={16} /> {t.label}
            </button>
          );
        })}
      </div>

      {/* Profile Tab */}
      {tab === 'profile' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
            <h3 className="font-bold text-gray-900 mb-3">المعلومات الأساسية</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-gray-500">الاسم</span><span className="font-medium">{profile.name}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">المسمى الوظيفي</span><span className="font-medium">{profile.job_title}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">الشركة</span><span className="font-medium">{profile.company_name}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">المنطقة</span><span className="font-medium">{profile.region}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">الهاتف</span><span className="font-medium">{profile.phone}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">مقيم</span><span className="font-medium">{profile.is_resident ? 'نعم' : 'لا'}</span></div>
            </div>
          </div>
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
            <h3 className="font-bold text-gray-900 mb-3">الراتب</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-gray-500">الراتب الأساسي</span><span className="font-medium">{profile.basic_salary?.toLocaleString()} ر.ي</span></div>
              <div className="flex justify-between"><span className="text-gray-500">الراتب الشامل</span><span className="font-medium">{profile.total_salary?.toLocaleString()} ر.ي</span></div>
            </div>
          </div>
        </div>
      )}

      {/* Attendance Tab */}
      {tab === 'attendance' && (
        <div>
          <div className="flex gap-3 mb-4">
            <select value={month} onChange={e => setMonth(e.target.value)} className="h-9 px-3 rounded-lg border border-gray-200 text-sm">
              {Array.from({length: 12}, (_, i) => <option key={i+1} value={String(i+1)}>{i+1}</option>)}
            </select>
            <select value={year} onChange={e => setYear(e.target.value)} className="h-9 px-3 rounded-lg border border-gray-200 text-sm">
              <option value="2026">2026</option>
              <option value="2025">2025</option>
            </select>
          </div>
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">التاريخ</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">الحالة</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">ملاحظات</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {attendance.length === 0 ? (
                  <tr><td colSpan={3} className="text-center py-8 text-gray-400">لا توجد سجلات</td></tr>
                ) : attendance.map(a => (
                  <tr key={a.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm">{a.date}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${statusColors[a.status] || ''}`}>
                        {a.status_name}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">{a.notes || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Salaries Tab */}
      {tab === 'salaries' && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-100">
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">الشهر</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">الأساسي</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">الإضافي</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">الخصومات</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">السلف</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">الصافي</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">الحالة</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {salaries.length === 0 ? (
                <tr><td colSpan={7} className="text-center py-8 text-gray-400">لا توجد رواتب</td></tr>
              ) : salaries.map(s => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-medium">{s.month_year}</td>
                  <td className="px-4 py-3 text-sm">{s.basic_salary_amount?.toLocaleString()}</td>
                  <td className="px-4 py-3 text-sm text-green-600">+{s.overtime_amount?.toLocaleString()}</td>
                  <td className="px-4 py-3 text-sm text-red-600">-{(s.deduction_amount + s.penalty_amount)?.toLocaleString()}</td>
                  <td className="px-4 py-3 text-sm text-red-600">-{s.advance_amount?.toLocaleString()}</td>
                  <td className="px-4 py-3 text-sm font-bold">{s.total_salary?.toLocaleString()}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${s.is_paid ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                      {s.is_paid ? 'مدفوع' : 'غير مدفوع'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Leaves Tab */}
      {tab === 'leaves' && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-bold text-gray-900">أرصدتي</h3>
            <button onClick={() => setLeaveModalOpen(true)} className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">
              <Calendar size={16} /> طلب إجازة
            </button>
          </div>

          {/* Balances */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
            {leaves.balances.filter((b: any) => !b.leave_type_name?.includes('أمومة')).map((b: any) => (
              <div key={b.id} className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                <div className="text-sm font-medium text-gray-700 mb-2">{b.leave_type_name}</div>
                {b.total_days >= 999 ? (
                  <>
                    <div className="text-2xl font-bold text-green-600">غير محدود</div>
                    <div className="text-xs text-gray-400 mt-1">مستخدم: {b.used_days} يوم</div>
                  </>
                ) : (
                  <>
                    <div className="text-2xl font-bold text-blue-600">{b.remaining_days}</div>
                    <div className="text-xs text-gray-400 mt-1">يوم متبقي من {b.total_days}</div>
                    <div className="w-full bg-gray-200 rounded-full h-1.5 mt-2">
                      <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${b.total_days > 0 ? (b.remaining_days / b.total_days) * 100 : 0}%` }} />
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>

          {/* Requests */}
          <h3 className="font-bold text-gray-900 mb-3">طلباتي</h3>
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">النوع</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">من</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">إلى</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">الأيام</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">الحالة</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {leaves.requests.length === 0 ? (
                  <tr><td colSpan={5} className="text-center py-8 text-gray-400">لا توجد طلبات</td></tr>
                ) : leaves.requests.map((r: any) => (
                  <tr key={r.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm">{r.leave_type_name}</td>
                    <td className="px-4 py-3 text-sm">{r.start_date}</td>
                    <td className="px-4 py-3 text-sm">{r.end_date}</td>
                    <td className="px-4 py-3 text-sm font-medium">{r.total_days}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${statusColors[r.status] || ''}`}>
                        {r.status === 'pending' && <Clock size={12} />}
                        {r.status === 'approved' && <Check size={12} />}
                        {r.status === 'rejected' && <X size={12} />}
                        {r.status_name}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Transactions Tab */}
      {tab === 'transactions' && (
        <div>
          <div className="flex gap-2 mb-4">
            <button onClick={() => setTxFilter('')} className={`px-3 py-1.5 rounded-lg text-xs font-medium ${!txFilter ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600'}`}>الكل</button>
            <button onClick={() => setTxFilter('advance')} className={`px-3 py-1.5 rounded-lg text-xs font-medium ${txFilter === 'advance' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600'}`}>سلف</button>
            <button onClick={() => setTxFilter('deduction')} className={`px-3 py-1.5 rounded-lg text-xs font-medium ${txFilter === 'deduction' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600'}`}>خصومات</button>
            <button onClick={() => setTxFilter('overtime')} className={`px-3 py-1.5 rounded-lg text-xs font-medium ${txFilter === 'overtime' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600'}`}>إضافي</button>
            <button onClick={() => setTxFilter('penalty')} className={`px-3 py-1.5 rounded-lg text-xs font-medium ${txFilter === 'penalty' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600'}`}>غرامات</button>
          </div>
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">التاريخ</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">النوع</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">المبلغ</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">القسط الشهري</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">البيان</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {transactions.filter((t: any) => !txFilter || t.transaction_type === txFilter).length === 0 ? (
                  <tr><td colSpan={5} className="text-center py-8 text-gray-400">لا توجد معاملات</td></tr>
                ) : transactions.filter((t: any) => !txFilter || t.transaction_type === txFilter).map((t: any) => {
                  const typeLabels: Record<string, string> = { advance: 'سلفة', deduction: 'خصم', overtime: 'إضافي', penalty: 'غرامة', restaurant: 'مطعم', cafeteria: 'كافتيريا' };
                  const typeColors: Record<string, string> = { advance: 'text-blue-600', deduction: 'text-red-600', overtime: 'text-green-600', penalty: 'text-red-700', restaurant: 'text-orange-600', cafeteria: 'text-orange-600' };
                  return (
                    <tr key={t.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm">{t.date}</td>
                      <td className="px-4 py-3"><span className={`text-sm font-medium ${typeColors[t.transaction_type] || ''}`}>{typeLabels[t.transaction_type] || t.transaction_type}</span></td>
                      <td className="px-4 py-3 text-sm font-bold">{t.amount?.toLocaleString()} ر.ي</td>
                      <td className="px-4 py-3 text-sm text-gray-500">{t.monthly_installment ? `${t.monthly_installment.toLocaleString()} ر.ي` : '-'}</td>
                      <td className="px-4 py-3 text-sm text-gray-500">{t.description || '-'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Evaluations Tab */}
      {tab === 'evaluations' && (
        <div>
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">التاريخ</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">المُقيّم</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">النوع</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">التقييم</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">ملاحظات</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {evaluations.length === 0 ? (
                  <tr><td colSpan={5} className="text-center py-8 text-gray-400">لا توجد تقييمات</td></tr>
                ) : evaluations.map((e: any) => (
                  <tr key={e.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm">{e.date}</td>
                    <td className="px-4 py-3 text-sm">{e.evaluator_name || '-'}</td>
                    <td className="px-4 py-3 text-sm">{e.evaluation_type === 'supervisor' ? 'مشرف' : 'متعهد'}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold ${e.score >= 80 ? 'bg-green-100 text-green-700' : e.score >= 60 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'}`}>
                        {e.score}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 max-w-[200px] truncate">{e.comments || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Password Tab */}
      {tab === 'password' && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 max-w-md">
          <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2"><Lock size={20} /> تغيير كلمة المرور</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">كلمة المرور الحالية *</label>
              <input type="password" value={pwForm.old_password} onChange={e => setPwForm({...pwForm, old_password: e.target.value})} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm" placeholder="أدخل كلمة المرور الحالية" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">كلمة المرور الجديدة *</label>
              <div className="relative">
                <input type={showPw ? 'text' : 'password'} value={pwForm.new_password} onChange={e => setPwForm({...pwForm, new_password: e.target.value})} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm" placeholder="كلمة المرور الجديدة" />
                <button type="button" onClick={() => setShowPw(!showPw)} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
                  {showPw ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">تأكيد كلمة المرور *</label>
              <input type="password" value={pwForm.confirm_password} onChange={e => setPwForm({...pwForm, confirm_password: e.target.value})} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm" placeholder="أعد إدخال كلمة المرور الجديدة" />
            </div>
            <button onClick={handleChangePassword} disabled={pwSaving || !pwForm.old_password || !pwForm.new_password || !pwForm.confirm_password} className="w-full py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
              {pwSaving ? 'جاري التغيير...' : 'تغيير كلمة المرور'}
            </button>
          </div>
        </div>
      )}

      {/* Leave Request Modal */}
      {leaveModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
            <div className="p-6 border-b border-gray-100">
              <h2 className="text-lg font-bold text-gray-900">طلب إجازة جديد</h2>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">نوع الإجازة *</label>
                <select value={leaveForm.leave_type_id} onChange={e => setLeaveForm({...leaveForm, leave_type_id: e.target.value})} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
                  <option value="">اختر النوع</option>
                  {leaveTypes.filter((t: any) => !t.name_ar?.includes('أمومة')).map((t: any) => <option key={t.id} value={t.id}>{t.name_ar}{t.days_per_year < 999 ? ` (${t.days_per_year} يوم)` : ''}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">من تاريخ *</label>
                  <input type="date" value={leaveForm.start_date} onChange={e => setLeaveForm({...leaveForm, start_date: e.target.value})} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">إلى تاريخ *</label>
                  <input type="date" value={leaveForm.end_date} onChange={e => setLeaveForm({...leaveForm, end_date: e.target.value})} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">عدد الأيام</label>
                <input type="number" value={leaveForm.total_days} readOnly className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm bg-gray-50" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">السبب</label>
                <textarea value={leaveForm.reason} onChange={e => setLeaveForm({...leaveForm, reason: e.target.value})} className="w-full h-20 px-3 py-2 rounded-lg border-2 border-gray-200 text-sm resize-none" placeholder="سبب الإجازة..." />
              </div>
            </div>
            <div className="p-6 border-t border-gray-100 flex gap-3 justify-end">
              <button onClick={() => setLeaveModalOpen(false)} className="px-4 py-2 text-sm text-gray-600">إلغاء</button>
              <button onClick={handleLeaveRequest} className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">إرسال</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
