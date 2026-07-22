import { useState, useEffect } from 'react';
import {
  User, Mail, Phone, Lock, Shield, Calendar, Edit3,
  Save, Loader2, Eye, EyeOff, Briefcase, DollarSign,
  CheckCircle2, AlertCircle, CalendarDays,
  BadgeCheck, Key
} from 'lucide-react';
import api from '@/api/client';

const roleColors: Record<string, string> = {
  admin: 'bg-rose-100 text-rose-700 border-rose-200',
  supervisor: 'bg-blue-100 text-blue-700 border-blue-200',
  accountant: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  viewer: 'bg-gray-100 text-gray-700 border-gray-200',
  employee: 'bg-violet-100 text-violet-700 border-violet-200',
};

const roleNames: Record<string, string> = {
  admin: 'مدير النظام',
  supervisor: 'مشرف',
  accountant: 'محاسب',
  viewer: 'مشاهد',
  employee: 'موظف',
};

interface ProfileData {
  id: number;
  username: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
  employee_id: number | null;
}

interface StatsData {
  employee: {
    code: string;
    job_title: string;
    company_name: string;
    salary: number;
    total_salary: number;
    daily_allowance: number;
    worker_type: string;
    is_resident: boolean;
  } | null;
  attendance: {
    total_days: number;
    present_days: number;
    late_days: number;
    absent_days: number;
    sick_days: number;
    leave_days: number;
  } | null;
  evaluations: {
    latest_score: number | null;
    latest_date: string | null;
    average_score: number;
    total_evaluations: number;
  } | null;
  salary: {
    total_paid: number;
    base_salary: number;
    total_salary: number;
  } | null;
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [stats, setStats] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [editMode, setEditMode] = useState(false);
  const [editForm, setEditForm] = useState({ full_name: '', phone: '' });
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');

  const [pwForm, setPwForm] = useState({ old_password: '', new_password: '', confirm: '' });
  const [showOldPw, setShowOldPw] = useState(false);
  const [showNewPw, setShowNewPw] = useState(false);
  const [pwSaving, setPwSaving] = useState(false);
  const [pwMsg, setPwMsg] = useState('');
  const [pwError, setPwError] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [profileRes, statsRes] = await Promise.all([
        api.get('/auth/me'),
        api.get('/reports/dashboard'),
      ]);
      const userData = profileRes.data.data;
      setProfile(userData);
      setStats(statsRes.data.data);
      setEditForm({
        full_name: userData.full_name || '',
        phone: '',
      });
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleEditSave = async () => {
    setSaving(true);
    setSaveMsg('');
    try {
      await api.put('/auth/me', { full_name: editForm.full_name, phone: editForm.phone });
      setSaveMsg('تم حفظ التغييرات بنجاح');
      setEditMode(false);
      loadData();
      setTimeout(() => setSaveMsg(''), 3000);
    } catch (err: any) {
      setSaveMsg(err.response?.data?.message || 'حدث خطأ أثناء الحفظ');
    } finally {
      setSaving(false);
    }
  };

  const handlePasswordChange = async () => {
    setPwError('');
    setPwMsg('');

    if (pwForm.new_password !== pwForm.confirm) {
      setPwError('كلمتا المرور غير متطابقتين');
      return;
    }
    if (pwForm.new_password.length < 6) {
      setPwError('كلمة المرور يجب أن تكون 6 أحرف على الأقل');
      return;
    }

    setPwSaving(true);
    try {
      await api.put('/auth/change-password', {
        old_password: pwForm.old_password,
        new_password: pwForm.new_password,
      });
      setPwMsg('تم تغيير كلمة المرور بنجاح');
      setPwForm({ old_password: '', new_password: '', confirm: '' });
      setTimeout(() => setPwMsg(''), 3000);
    } catch (err: any) {
      setPwError(err.response?.data?.message || 'حدث خطأ أثناء تغيير كلمة المرور');
    } finally {
      setPwSaving(false);
    }
  };

  const getPasswordStrength = (pw: string): { level: number; label: string; color: string } => {
    if (!pw) return { level: 0, label: '', color: 'bg-gray-100' };
    let score = 0;
    if (pw.length >= 6) score++;
    if (pw.length >= 10) score++;
    if (/[A-Z]/.test(pw)) score++;
    if (/[0-9]/.test(pw)) score++;
    if (/[^A-Za-z0-9]/.test(pw)) score++;

    if (score <= 2) return { level: 1, label: 'ضعيفة', color: 'bg-rose-500' };
    if (score <= 3) return { level: 2, label: 'متوسطة', color: 'bg-amber-500' };
    if (score <= 4) return { level: 3, label: 'جيدة', color: 'bg-blue-500' };
    return { level: 4, label: 'قوية', color: 'bg-emerald-500' };
  };

  const pwStrength = getPasswordStrength(pwForm.new_password);

  const getInitials = (name: string) => {
    if (!name) return '?';
    const parts = name.split(' ').filter(Boolean);
    if (parts.length >= 2) return parts[0][0] + parts[1][0];
    return parts[0]?.[0] || '?';
  };

  const formatDate = (d: string | null) => {
    if (!d) return '—';
    const date = new Date(d);
    return date.toLocaleDateString('ar-SA', { year: 'numeric', month: 'long', day: 'numeric' });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="text-center py-20">
        <AlertCircle className="w-12 h-12 text-gray-300 mx-auto mb-4" />
        <p className="text-gray-500">لم يتم العثور على بيانات الملف الشخصي</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="h-24 bg-gradient-to-l from-primary-500 to-blue-600" />
        <div className="px-6 pb-6">
          <div className="flex flex-col sm:flex-row items-start gap-5 -mt-10">
            <div className="w-20 h-20 rounded-2xl bg-white border-4 border-white shadow-lg flex items-center justify-center flex-shrink-0">
              <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center text-white font-bold text-xl">
                {getInitials(profile.full_name)}
              </div>
            </div>
            <div className="flex-1 pt-3">
              <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
                <h1 className="text-xl font-bold text-gray-900">{profile.full_name}</h1>
                <span className={`inline-flex items-center px-3 py-0.5 rounded-full text-xs font-medium border ${roleColors[profile.role] || 'bg-gray-100 text-gray-600'}`}>
                  {roleNames[profile.role] || profile.role}
                </span>
                <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${profile.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>
                  {profile.is_active ? <BadgeCheck className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}
                  {profile.is_active ? 'نشط' : 'غير نشط'}
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-4 mt-2 text-sm text-gray-500">
                <span className="flex items-center gap-1.5">
                  <User className="w-4 h-4 text-gray-400" />
                  @{profile.username}
                </span>
                {profile.created_at && (
                  <span className="flex items-center gap-1.5">
                    <Calendar className="w-4 h-4 text-gray-400" />
                    عضو منذ {formatDate(profile.created_at)}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {saveMsg && (
        <div className={`flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-medium ${saveMsg.includes('خطأ') ? 'bg-rose-50 text-rose-700 border border-rose-200' : 'bg-emerald-50 text-emerald-700 border border-emerald-200'}`}>
          {saveMsg.includes('خطأ') ? <AlertCircle className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
          {saveMsg}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <Edit3 className="w-5 h-5 text-primary-500" />
                المعلومات الشخصية
              </h2>
              {!editMode && (
                <button onClick={() => setEditMode(true)} className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary-50 text-primary-600 text-sm font-medium hover:bg-primary-100 transition-colors">
                  <Edit3 className="w-4 h-4" /> تعديل
                </button>
              )}
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1.5">الاسم الكامل</label>
                {editMode ? (
                  <input type="text" value={editForm.full_name} onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })}
                    className="w-full h-11 px-4 rounded-xl border border-gray-200 text-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 outline-none transition-all" />
                ) : (
                  <p className="text-sm text-gray-900 bg-gray-50 rounded-xl px-4 py-3">{profile.full_name}</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1.5">رقم الهاتف</label>
                {editMode ? (
                  <input type="tel" value={editForm.phone} onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })} placeholder="أدخل رقم الهاتف"
                    className="w-full h-11 px-4 rounded-xl border border-gray-200 text-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 outline-none transition-all" />
                ) : (
                  <p className="text-sm text-gray-900 bg-gray-50 rounded-xl px-4 py-3 flex items-center gap-2">
                    <Phone className="w-4 h-4 text-gray-400" /> غير محدد
                  </p>
                )}
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-600 mb-1.5">اسم المستخدم</label>
                  <p className="text-sm text-gray-900 bg-gray-50 rounded-xl px-4 py-3 flex items-center gap-2">
                    <User className="w-4 h-4 text-gray-400" /> {profile.username}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-600 mb-1.5">الدور</label>
                  <p className="text-sm text-gray-900 bg-gray-50 rounded-xl px-4 py-3 flex items-center gap-2">
                    <Shield className="w-4 h-4 text-gray-400" /> {roleNames[profile.role] || profile.role}
                  </p>
                </div>
              </div>
              {editMode && (
                <div className="flex justify-end gap-3 pt-2">
                  <button onClick={() => { setEditMode(false); setEditForm({ full_name: profile.full_name, phone: '' }); }}
                    className="px-5 py-2.5 rounded-xl text-sm font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 transition-colors">إلغاء</button>
                  <button onClick={handleEditSave} disabled={saving}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50 transition-colors">
                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} حفظ التغييرات
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
            <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2 mb-6">
              <Key className="w-5 h-5 text-primary-500" /> تغيير كلمة المرور
            </h2>
            {pwMsg && (
              <div className="flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 mb-4">
                <CheckCircle2 className="w-4 h-4" /> {pwMsg}
              </div>
            )}
            {pwError && (
              <div className="flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-medium bg-rose-50 text-rose-700 border border-rose-200 mb-4">
                <AlertCircle className="w-4 h-4" /> {pwError}
              </div>
            )}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1.5">كلمة المرور الحالية</label>
                <div className="relative">
                  <input type={showOldPw ? 'text' : 'password'} value={pwForm.old_password} onChange={(e) => setPwForm({ ...pwForm, old_password: e.target.value })}
                    className="w-full h-11 px-4 pl-11 rounded-xl border border-gray-200 text-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 outline-none transition-all"
                    placeholder="أدخل كلمة المرور الحالية" />
                  <button type="button" onClick={() => setShowOldPw(!showOldPw)} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                    {showOldPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1.5">كلمة المرور الجديدة</label>
                <div className="relative">
                  <input type={showNewPw ? 'text' : 'password'} value={pwForm.new_password} onChange={(e) => setPwForm({ ...pwForm, new_password: e.target.value })}
                    className="w-full h-11 px-4 pl-11 rounded-xl border border-gray-200 text-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 outline-none transition-all"
                    placeholder="أدخل كلمة المرور الجديدة" />
                  <button type="button" onClick={() => setShowNewPw(!showNewPw)} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                    {showNewPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {pwForm.new_password && (
                  <div className="mt-2">
                    <div className="flex gap-1.5">
                      {[1, 2, 3, 4].map((i) => (
                        <div key={i} className={`h-1 flex-1 rounded-full transition-all ${pwStrength.level >= i ? pwStrength.color : 'bg-gray-100'}`} />
                      ))}
                    </div>
                    <p className="text-xs mt-1 text-gray-500">{pwStrength.label}</p>
                  </div>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1.5">تأكيد كلمة المرور</label>
                <input type="password" value={pwForm.confirm} onChange={(e) => setPwForm({ ...pwForm, confirm: e.target.value })}
                  className="w-full h-11 px-4 rounded-xl border border-gray-200 text-sm focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 outline-none transition-all"
                  placeholder="أعد إدخال كلمة المرور الجديدة" />
              </div>
              <div className="flex justify-end pt-2">
                <button onClick={handlePasswordChange} disabled={pwSaving || !pwForm.old_password || !pwForm.new_password || !pwForm.confirm}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50 transition-colors">
                  {pwSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Lock className="w-4 h-4" />} تغيير كلمة المرور
                </button>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
            <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2 mb-4">
              <Shield className="w-5 h-5 text-primary-500" /> معلومات الحساب
            </h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between py-2 border-b border-gray-50">
                <span className="text-sm text-gray-500">تاريخ الإنشاء</span>
                <span className="text-sm font-medium text-gray-900">{formatDate(profile.created_at)}</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-gray-50">
                <span className="text-sm text-gray-500">اسم المستخدم</span>
                <span className="text-sm font-medium text-gray-900">@{profile.username}</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-gray-50">
                <span className="text-sm text-gray-500">الدور</span>
                <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${roleColors[profile.role] || 'bg-gray-100 text-gray-600'}`}>
                  {roleNames[profile.role] || profile.role}
                </span>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-sm text-gray-500">الحالة</span>
                <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${profile.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>
                  {profile.is_active ? 'نشط' : 'غير نشط'}
                </span>
              </div>
            </div>
          </div>

          {stats?.employee && (
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
              <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2 mb-4">
                <Briefcase className="w-5 h-5 text-primary-500" /> بيانات الموظف
              </h2>
              <div className="space-y-3">
                <div className="flex items-center justify-between py-2 border-b border-gray-50">
                  <span className="text-sm text-gray-500">المنصب</span>
                  <span className="text-sm font-medium text-gray-900">{stats.employee.job_title || '—'}</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-gray-50">
                  <span className="text-sm text-gray-500">الشركة</span>
                  <span className="text-sm font-medium text-gray-900">{stats.employee.company_name || '—'}</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-gray-50">
                  <span className="text-sm text-gray-500">الراتب الأساسي</span>
                  <span className="text-sm font-medium text-gray-900">{(stats.employee.salary || 0).toLocaleString('en')}</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-gray-50">
                  <span className="text-sm text-gray-500">الراتب الإجمالي</span>
                  <span className="text-sm font-medium text-primary-600">{(stats.employee.total_salary || 0).toLocaleString('en')}</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-gray-50">
                  <span className="text-sm text-gray-500">البدل اليومي</span>
                  <span className="text-sm font-medium text-gray-900">{(stats.employee.daily_allowance || 0).toLocaleString('en')}</span>
                </div>
                <div className="flex items-center justify-between py-2">
                  <span className="text-sm text-gray-500">نوع العامل</span>
                  <span className="text-sm font-medium text-gray-900">{stats.employee.worker_type === 'permanent' ? 'دائم' : 'مؤقت'}</span>
                </div>
              </div>
            </div>
          )}

          {stats?.attendance && (
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
              <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2 mb-4">
                <CalendarDays className="w-5 h-5 text-primary-500" /> إحصائيات الحضور
              </h2>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-blue-50 rounded-xl p-3 text-center">
                  <div className="text-2xl font-bold text-blue-600">{stats.attendance.present_days}</div>
                  <div className="text-xs text-blue-500 mt-1">أيام الحضور</div>
                </div>
                <div className="bg-amber-50 rounded-xl p-3 text-center">
                  <div className="text-2xl font-bold text-amber-600">{stats.attendance.late_days}</div>
                  <div className="text-xs text-amber-500 mt-1">أيام التأخر</div>
                </div>
                <div className="bg-rose-50 rounded-xl p-3 text-center">
                  <div className="text-2xl font-bold text-rose-600">{stats.attendance.absent_days}</div>
                  <div className="text-xs text-rose-500 mt-1">أيام الغياب</div>
                </div>
                <div className="bg-emerald-50 rounded-xl p-3 text-center">
                  <div className="text-2xl font-bold text-emerald-600">{stats.attendance.leave_days}</div>
                  <div className="text-xs text-emerald-500 mt-1">أيام الإجازة</div>
                </div>
              </div>
            </div>
          )}

          {stats?.salary && (
            <div className="bg-gradient-to-br from-primary-500 to-blue-600 rounded-2xl shadow-sm p-6 text-white">
              <h2 className="text-lg font-bold flex items-center gap-2 mb-4">
                <DollarSign className="w-5 h-5" /> إحصائيات الراتب
              </h2>
              <div className="space-y-3">
                <div className="flex items-center justify-between py-2 border-b border-white/20">
                  <span className="text-sm text-white/70">إجمالي المدفوعات</span>
                  <span className="text-lg font-bold">{(stats.salary.total_paid || 0).toLocaleString('en')}</span>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-white/20">
                  <span className="text-sm text-white/70">الراتب الأساسي</span>
                  <span className="text-sm font-medium">{(stats.salary.base_salary || 0).toLocaleString('en')}</span>
                </div>
                <div className="flex items-center justify-between py-2">
                  <span className="text-sm text-white/70">الراتب الإجمالي</span>
                  <span className="text-sm font-medium">{(stats.salary.total_salary || 0).toLocaleString('en')}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
