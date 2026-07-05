import { useState } from 'react';
import { Settings as SettingsIcon, Save, Building2, Bell, Shield, CheckCircle } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import api from '@/api/client';

export default function SettingsPage() {
  const [company, setCompany] = useState({ name: 'طلعت هائل للخدمات والاستشارات الزراعية', email: 'info@taltahail.com', phone: '777123456', address: 'الحديدة، الجمهورية اليمنية' });
  const [password, setPassword] = useState({ current: '', new_pass: '', confirm: '' });
  const [notifications, setNotifications] = useState({ attendance: true, salary: true, invoices: true, system: false });
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState('');

  const handleSaveCompany = async () => {
    setSaving(true);
    try {
      await api.put('/settings', company);
      setMsg('تم حفظ الإعدادات بنجاح');
      setTimeout(() => setMsg(''), 3000);
    } catch (err: any) {
      alert(err.response?.data?.message || 'حدث خطأ');
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async () => {
    if (password.new_pass !== password.confirm) { alert('كلمتا المرور غير متطابقتين'); return; }
    if (!password.current || !password.new_pass) { alert('جميع الحقول مطلوبة'); return; }
    setSaving(true);
    try {
      await api.post('/settings/change-password', { current_password: password.current, new_password: password.new_pass });
      setMsg('تم تحديث كلمة المرور بنجاح');
      setPassword({ current: '', new_pass: '', confirm: '' });
      setTimeout(() => setMsg(''), 3000);
    } catch (err: any) {
      alert(err.response?.data?.message || 'حدث خطأ');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">الإعدادات</h1>
          <p className="text-gray-500 text-sm mt-1">إعدادات النظام والتكوين</p>
        </div>
        {msg && (
          <div className="flex items-center gap-2 bg-green-50 text-green-700 px-4 py-2 rounded-lg text-sm font-medium animate-pulse">
            <CheckCircle className="w-4 h-4" /> {msg}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* General Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building2 className="w-5 h-5" />
              إعدادات عامة
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">اسم الشركة</label>
              <Input value={company.name} onChange={(e) => setCompany({ ...company, name: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">البريد الإلكتروني</label>
              <Input value={company.email} onChange={(e) => setCompany({ ...company, email: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">الهاتف</label>
              <Input value={company.phone} onChange={(e) => setCompany({ ...company, phone: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">العنوان</label>
              <Input value={company.address} onChange={(e) => setCompany({ ...company, address: e.target.value })} />
            </div>
            <Button onClick={handleSaveCompany} disabled={saving}>
              <Save className="w-4 h-4" />
              {saving ? 'جاري الحفظ...' : 'حفظ التغييرات'}
            </Button>
          </CardContent>
        </Card>

        {/* Notification Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="w-5 h-5" />
              إعدادات الإشعارات
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {[
              { key: 'attendance' as const, label: 'إشعارات الحضور', desc: 'تنبيه عند تسجيل الحضور والغياب' },
              { key: 'salary' as const, label: 'إشعارات الرواتب', desc: 'تنبيه عند إعداد الرواتب' },
              { key: 'invoices' as const, label: 'إشعارات الفواتير', desc: 'تنبيه عند استلام فواتير جديدة' },
              { key: 'system' as const, label: 'تنبيهات النظام', desc: 'تنبيهات صيانة وتحديثات' },
            ].map((item) => (
              <div key={item.key} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div>
                  <p className="text-sm font-medium text-gray-900">{item.label}</p>
                  <p className="text-xs text-gray-500">{item.desc}</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" checked={notifications[item.key]} onChange={(e) => setNotifications({ ...notifications, [item.key]: e.target.checked })} className="sr-only peer" />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                </label>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Security Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5" />
              تغيير كلمة المرور
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">كلمة المرور الحالية</label>
              <Input type="password" value={password.current} onChange={(e) => setPassword({ ...password, current: e.target.value })} placeholder="أدخل كلمة المرور الحالية" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">كلمة المرور الجديدة</label>
              <Input type="password" value={password.new_pass} onChange={(e) => setPassword({ ...password, new_pass: e.target.value })} placeholder="أدخل كلمة المرور الجديدة" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">تأكيد كلمة المرور</label>
              <Input type="password" value={password.confirm} onChange={(e) => setPassword({ ...password, confirm: e.target.value })} placeholder="أكد كلمة المرور الجديدة" />
            </div>
            <Button onClick={handleChangePassword} disabled={saving}>
              <Save className="w-4 h-4" />
              {saving ? 'جاري التحديث...' : 'تحديث كلمة المرور'}
            </Button>
          </CardContent>
        </Card>

        {/* System Info */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <SettingsIcon className="w-5 h-5" />
              معلومات النظام
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[
                { label: 'إصدار النظام', value: '2.0.0' },
                { label: 'قاعدة البيانات', value: 'SQLite / PostgreSQL' },
                { label: 'تاريخ آخر تحديث', value: new Date().toLocaleDateString('ar-EG') },
                { label: 'حالة النظام', value: 'نشط', color: 'text-green-600' },
                { label: 'المطور', value: 'طلعت هائل' },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <span className="text-sm text-gray-600">{item.label}</span>
                  <span className={`text-sm font-medium ${item.color || 'text-gray-900'}`}>{item.value}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
