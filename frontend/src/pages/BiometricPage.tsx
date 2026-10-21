import { useState, useEffect } from 'react';
import {
  Fingerprint, Plus, RefreshCw, Trash2, Settings as SettingsIcon,
  FileUp, Link2, Download, AlertTriangle, CheckCircle, Server, Search,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import api from '@/api/client';

const EMPTY_DEVICE = {
  id: 0, name: '', serial_number: '', ip_address: '', port: 4370,
  password: '', api_key: '', direction: 'pull', is_active: true,
};

type Tab = 'devices' | 'logs' | 'links' | 'settings' | 'import';

export default function BiometricPage() {
  const [tab, setTab] = useState<Tab>('devices');
  const [status, setStatus] = useState<any>(null);
  const [devices, setDevices] = useState<any[]>([]);
  const [logs, setLogs] = useState<any[]>([]);
  const [logsTotal, setLogsTotal] = useState(0);
  const [links, setLinks] = useState<any[]>([]);
  const [settings, setSettings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null);

  const [deviceModal, setDeviceModal] = useState(false);
  const [deviceForm, setDeviceForm] = useState<any>(EMPTY_DEVICE);
  const [busy, setBusy] = useState(false);

  const [logFilter, setLogFilter] = useState({ date_from: '', date_to: '', search: '', unprocessed: '' });
  const [linkSearch, setLinkSearch] = useState('');
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importDevice, setImportDevice] = useState('');

  const notify = (type: 'ok' | 'err', text: string) => {
    setMsg({ type, text });
    setTimeout(() => setMsg(null), 4000);
  };

  const loadAll = async () => {
    setLoading(true);
    try {
      const [st, dev, lg, stg] = await Promise.all([
        api.get('/biometric/status').catch(() => ({ data: { data: null } })),
        api.get('/biometric/devices').catch(() => ({ data: { data: [] } })),
        api.get('/biometric/logs', { params: { per_page: 100, ...logFilter } }).catch(() => ({ data: { data: null } })),
        api.get('/biometric/settings').catch(() => ({ data: { data: [] } })),
      ]);
      setStatus(st.data.data);
      setDevices(dev.data.data || []);
      if (lg.data.data) {
        setLogs(lg.data.data.logs || []);
        setLogsTotal(lg.data.data.total || 0);
      }
      setSettings(stg.data.data || []);
    } catch (e) {
      notify('err', 'تعذر تحميل البيانات');
    }
    setLoading(false);
  };

  useEffect(() => { loadAll(); }, []);

  const loadLinks = async (search = '') => {
    try {
      const r = await api.get('/biometric/employee-links', { params: { search } });
      setLinks(r.data.data || []);
    } catch { /* ignore */ }
  };

  useEffect(() => { if (tab === 'links') loadLinks(linkSearch); }, [tab]);

  const saveDevice = async () => {
    if (!deviceForm.name) { notify('err', 'اسم الجهاز مطلوب'); return; }
    setBusy(true);
    try {
      if (deviceForm.id) {
        await api.put(`/biometric/devices/${deviceForm.id}`, deviceForm);
        notify('ok', 'تم تحديث الجهاز');
      } else {
        await api.post('/biometric/devices', deviceForm);
        notify('ok', 'تمت إضافة الجهاز');
      }
      setDeviceModal(false);
      setDeviceForm(EMPTY_DEVICE);
      loadAll();
    } catch (e: any) {
      notify('err', e.response?.data?.message || 'خطأ في الحفظ');
    }
    setBusy(false);
  };

  const deleteDevice = async (id: number) => {
    if (!confirm('هل تريد حذف هذا الجهاز وسجلاته؟')) return;
    try {
      await api.delete(`/biometric/devices/${id}`);
      notify('ok', 'تم حذف الجهاز');
      loadAll();
    } catch (e: any) {
      notify('err', e.response?.data?.message || 'خطأ');
    }
  };

  const pullDevice = async (id: number) => {
    setBusy(true);
    try {
      const r = await api.post(`/biometric/devices/${id}/pull`);
      notify('ok', r.data.message || 'تم السحب');
      loadAll();
    } catch (e: any) {
      notify('err', e.response?.data?.message || 'تعذر السحب من الجهاز');
    }
    setBusy(false);
  };

  const processLogs = async () => {
    setBusy(true);
    try {
      const r = await api.post('/biometric/process', {});
      const d = r.data.data || {};
      notify('ok', `تمت معالجة ${d.processed_logs || 0} سجل - أُنشئ ${d.created_records || 0} سجل حضور`);
      loadAll();
    } catch (e: any) {
      notify('err', e.response?.data?.message || 'خطأ في المعالجة');
    }
    setBusy(false);
  };

  const markAbsent = async () => {
    const from = prompt('من تاريخ (YYYY-MM-DD):');
    if (!from) return;
    const to = prompt('إلى تاريخ (YYYY-MM-DD):', from);
    if (!to) return;
    if (!confirm(`سيتم إنشاء سجلات غياب لكل الموظفين في الفترة ${from} إلى ${to} (بدون بصمة وبدون إجازة). متابعة؟`)) return;
    setBusy(true);
    try {
      const r = await api.post('/biometric/mark-absent', { start_date: from, end_date: to });
      notify('ok', r.data.message || 'تم');
      loadAll();
    } catch (e: any) {
      notify('err', e.response?.data?.message || 'خطأ');
    }
    setBusy(false);
  };

  const saveLink = async (empId: number, pin: string) => {
    try {
      await api.put(`/biometric/employee-links/${empId}`, { biometric_pin: pin });
      notify('ok', 'تم حفظ رقم البصمة');
      loadLinks(linkSearch);
    } catch (e: any) {
      notify('err', e.response?.data?.message || 'خطأ');
    }
  };

  const saveSettings = async () => {
    setBusy(true);
    try {
      const payload: any = {};
      settings.forEach(s => { payload[s.key] = s.value; });
      await api.put('/biometric/settings', { settings: payload });
      notify('ok', 'تم حفظ الإعدادات');
      loadAll();
    } catch (e: any) {
      notify('err', e.response?.data?.message || 'خطأ');
    }
    setBusy(false);
  };

  const doImport = async () => {
    if (!importFile) { notify('err', 'اختر ملفاً أولاً'); return; }
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append('file', importFile);
      if (importDevice) fd.append('device_id', importDevice);
      const r = await api.post('/biometric/import', fd);
      notify('ok', r.data.message || 'تم الاستيراد');
      setImportFile(null);
      loadAll();
    } catch (e: any) {
      notify('err', e.response?.data?.message || 'خطأ في الاستيراد');
    }
    setBusy(false);
  };

  const tabs: { key: Tab; label: string; icon: any }[] = [
    { key: 'devices', label: 'الأجهزة', icon: Server },
    { key: 'logs', label: 'سجلات البصمة', icon: Fingerprint },
    { key: 'links', label: 'ربط الموظفين', icon: Link2 },
    { key: 'settings', label: 'الإعدادات', icon: SettingsIcon },
    { key: 'import', label: 'استيراد ملف', icon: FileUp },
  ];

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">أجهزة البصمة</h1>
          <p className="text-gray-500 text-sm mt-1">
            ربط أجهزة ZKTeco بسحب بصمات الموظفين وتحويلها إلى سجلات حضور تُحتسب منها الرواتب
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={loadAll} variant="outline" className="gap-2">
            <RefreshCw className="w-4 h-4" /> تحديث
          </Button>
          <Button
            onClick={() => { setDeviceForm(EMPTY_DEVICE); setDeviceModal(true); }}
            className="gap-2"
          >
            <Plus className="w-4 h-4" /> جهاز جديد
          </Button>
        </div>
      </div>

      {msg && (
        <div className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium ${
          msg.type === 'ok' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
          {msg.type === 'ok' ? <CheckCircle className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
          {msg.text}
        </div>
      )}

      {status && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Card className="p-3 text-center">
            <div className="text-2xl font-bold text-primary-600">{status.devices_count || 0}</div>
            <div className="text-xs text-gray-500">الأجهزة المسجلة</div>
          </Card>
          <Card className="p-3 text-center">
            <div className="text-2xl font-bold text-gray-700">{status.total_logs || 0}</div>
            <div className="text-xs text-gray-500">سجلات البصمة</div>
          </Card>
          <Card className="p-3 text-center">
            <div className="text-2xl font-bold text-amber-600">{status.unprocessed_logs || 0}</div>
            <div className="text-xs text-gray-500">بانتظار المعالجة</div>
          </Card>
          <Card className="p-3 text-center">
            <div className="text-2xl font-bold text-red-600">{status.unmapped_pins?.length || 0}</div>
            <div className="text-xs text-gray-500">أرقام غير مرتبطة</div>
          </Card>
        </div>
      )}

      <div className="flex flex-wrap gap-2 border-b border-gray-200 pb-2">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              tab === t.key ? 'bg-primary-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}
          >
            <t.icon className="w-4 h-4" /> {t.label}
          </button>
        ))}
      </div>

      {tab === 'devices' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2"><Server className="w-5 h-5" /> الأجهزة</span>
              <span className="text-xs font-normal text-gray-500">
                اسحب من الجهاز مباشرة (يتطلب وصول الخادم للجهاز) أو استخدم الوكيل المحلي أو الاستيراد
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center h-24">
                <div className="w-7 h-7 border-3 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" />
              </div>
            ) : devices.length === 0 ? (
              <p className="text-center text-gray-400 py-8 text-sm">
                لا توجد أجهزة مسجلة — أضف جهازك أو ابدأ باستيراد ملف بصمات
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200 text-xs text-gray-500">
                      <th className="text-right px-3 py-2">الاسم</th>
                      <th className="text-right px-3 py-2">الرقم التسلسلي</th>
                      <th className="text-right px-3 py-2">IP / المنفذ</th>
                      <th className="text-right px-3 py-2">النوع</th>
                      <th className="text-right px-3 py-2">آخر مزامنة</th>
                      <th className="text-right px-3 py-2">السجلات</th>
                      <th className="text-right px-3 py-2">إجراءات</th>
                    </tr>
                  </thead>
                  <tbody>
                    {devices.map(d => (
                      <tr key={d.id} className="border-b border-gray-100">
                        <td className="px-3 py-2 font-medium text-gray-900">{d.name}</td>
                        <td className="px-3 py-2 text-gray-600 font-mono text-xs">{d.serial_number || '—'}</td>
                        <td className="px-3 py-2 text-gray-600 font-mono text-xs">
                          {d.ip_address ? `${d.ip_address}:${d.port}` : '—'}
                        </td>
                        <td className="px-3 py-2 text-gray-600 text-xs">{d.direction_name}</td>
                        <td className="px-3 py-2 text-gray-600 text-xs">
                          {d.last_sync_at || '—'}
                          {d.last_sync_message && <div className="text-gray-400">{d.last_sync_message}</div>}
                        </td>
                        <td className="px-3 py-2 text-gray-600">{d.logs_count}</td>
                        <td className="px-3 py-2">
                          <div className="flex items-center gap-2">
                            <Button size="sm" variant="outline" onClick={() => pullDevice(d.id)} disabled={busy}>
                              سحب
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => { setDeviceForm(d); setDeviceModal(true); }}>
                              تعديل
                            </Button>
                            <Button size="sm" variant="ghost" onClick={() => deleteDevice(d.id)} className="text-red-600">
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-800 space-y-1">
              <div className="font-semibold">طرق ربط الجهاز:</div>
              <div>1) <b>الوكيل المحلي</b>: شغّل <code>tools/zk_sync_agent.py</code> على كمبيوتر المكتب (نفس شبكة الجهاز) وسيسحب السجلات ويرسلها للنظام تلقائياً.</div>
              <div>2) <b>دفع من الجهاز (ADMS)</b>: اضبط «Comm &gt; ADMS&gt; Server Address» على رابط الموقع: <code>{window.location.origin}/api/biometric/iclock/cdata</code></div>
              <div>3) <b>استيراد ملف</b>: صدّر سجلات الجهاز من برنامج ZKTimeWeb (CSV/Excel) وارفعها من تبويب «استيراد ملف».</div>
            </div>
          </CardContent>
        </Card>
      )}

      {tab === 'logs' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2"><Fingerprint className="w-5 h-5" /> سجلات البصمة</span>
              <div className="flex items-center gap-2">
                <Button size="sm" variant="outline" onClick={processLogs} disabled={busy} className="gap-1.5">
                  <RefreshCw className="w-3.5 h-3.5" /> معالجة وتحويل للحضور
                </Button>
                <Button size="sm" variant="ghost" onClick={markAbsent} disabled={busy}>
                  تسجيل غياب
                </Button>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-wrap items-end gap-2">
              <div>
                <label className="block text-xs text-gray-500 mb-1">من</label>
                <Input type="date" value={logFilter.date_from} onChange={e => setLogFilter({ ...logFilter, date_from: e.target.value })} className="h-9 w-40" />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">إلى</label>
                <Input type="date" value={logFilter.date_to} onChange={e => setLogFilter({ ...logFilter, date_to: e.target.value })} className="h-9 w-40" />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">بحث</label>
                <Input value={logFilter.search} onChange={e => setLogFilter({ ...logFilter, search: e.target.value })} placeholder="اسم أو كود أو رقم بصمة" className="h-9 w-56" />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">الحالة</label>
                <select
                  value={logFilter.unprocessed}
                  onChange={e => setLogFilter({ ...logFilter, unprocessed: e.target.value })}
                  className="h-9 px-2 border-2 border-gray-200 rounded-lg text-sm"
                >
                  <option value="">الكل</option>
                  <option value="1">غير المعالجة فقط</option>
                </select>
              </div>
              <Button size="sm" variant="outline" onClick={loadAll}>تطبيق</Button>
            </div>

            {status?.unmapped_pins?.length > 0 && (
              <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 text-amber-800 rounded-lg px-3 py-2 text-xs">
                <AlertTriangle className="w-4 h-4 mt-0.5" />
                <div>
                  أرقام بصمة غير مرتبطة بموظف: <b>{status.unmapped_pins.join('، ')}</b>
                  <div>اربطها من تبويب «ربط الموظفين» (الرقم في الجهاز = كود الموظف في النظام).</div>
                </div>
              </div>
            )}

            <div className="overflow-x-auto border border-gray-100 rounded-lg">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-gray-50 text-gray-500">
                    <th className="text-right px-3 py-2">الموظف</th>
                    <th className="text-right px-3 py-2">الرقم</th>
                    <th className="text-right px-3 py-2">الوقت</th>
                    <th className="text-right px-3 py-2">النوع</th>
                    <th className="text-right px-3 py-2">طريقة التحقق</th>
                    <th className="text-right px-3 py-2">الجهاز</th>
                    <th className="text-right px-3 py-2">الحالة</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.length === 0 ? (
                    <tr><td colSpan={7} className="text-center py-8 text-gray-400">لا توجد سجلات</td></tr>
                  ) : logs.map((l: any) => (
                    <tr key={l.id} className="border-t border-gray-100">
                      <td className="px-3 py-1.5 text-gray-800">{l.employee_name || <span className="text-red-500">غير مرتبط</span>}</td>
                      <td className="px-3 py-1.5 font-mono text-gray-600">{l.pin}</td>
                      <td className="px-3 py-1.5 text-gray-600">{l.log_time}</td>
                      <td className="px-3 py-1.5">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                          l.log_type === 'in' ? 'bg-green-100 text-green-700' :
                          l.log_type === 'out' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'}`}>
                          {l.log_type === 'in' ? 'دخول' : l.log_type === 'out' ? 'خروج' : 'غير محدد'}
                        </span>
                      </td>
                      <td className="px-3 py-1.5 text-gray-600">{l.verify_mode_name || '—'}</td>
                      <td className="px-3 py-1.5 text-gray-500">{l.device_name}</td>
                      <td className="px-3 py-1.5">
                        {l.is_processed
                          ? <span className="text-green-600">مُعالج</span>
                          : <span className="text-amber-600">بانتظار</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="text-xs text-gray-500">إجمالي السجلات: {logsTotal}</div>
          </CardContent>
        </Card>
      )}

      {tab === 'links' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Link2 className="w-5 h-5" /> ربط الموظفين بأرقام البصمة</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-xs text-gray-500">
              اكتب نفس الرقم المسجل في جهاز البصمة للموظف. إذا كان الرقم مساوياً لكود الموظف في النظام فسيتم الربط تلقائياً.
            </p>
            <div className="flex items-center gap-2">
              <Input
                value={linkSearch}
                onChange={e => setLinkSearch(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') loadLinks(linkSearch); }}
                placeholder="ابحث بالاسم أو الكود"
                className="max-w-xs"
              />
              <Button variant="outline" onClick={() => loadLinks(linkSearch)} className="gap-1.5">
                <Search className="w-4 h-4" /> بحث
              </Button>
            </div>
            <div className="overflow-x-auto border border-gray-100 rounded-lg max-h-[500px] overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-gray-50">
                  <tr className="text-xs text-gray-500">
                    <th className="text-right px-3 py-2">الموظف</th>
                    <th className="text-right px-3 py-2">الكود</th>
                    <th className="text-right px-3 py-2">رقم البصمة</th>
                    <th className="text-right px-3 py-2">حفظ</th>
                  </tr>
                </thead>
                <tbody>
                  {links.map((e: any) => (
                    <EmployeeLinkRow key={e.id} emp={e} onSave={saveLink} />
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {tab === 'settings' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2"><SettingsIcon className="w-5 h-5" /> إعدادات البصمة</span>
              <Button size="sm" onClick={saveSettings} disabled={busy}>حفظ</Button>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {settings.map(s => (
              <div key={s.key} className="grid grid-cols-1 sm:grid-cols-3 gap-2 items-center">
                <div>
                  <div className="text-sm font-medium text-gray-800">{s.name}</div>
                  <div className="text-[11px] text-gray-400">{s.description}</div>
                </div>
                <div className="sm:col-span-2">
                  {s.value_type === 'bool' ? (
                    <select
                      value={s.value}
                      onChange={e => setSettings(settings.map(x => x.key === s.key ? { ...x, value: e.target.value } : x))}
                      className="h-9 px-2 border-2 border-gray-200 rounded-lg text-sm w-full max-w-xs"
                    >
                      <option value="true">مفعّل</option>
                      <option value="false">معطّل</option>
                    </select>
                  ) : (
                    <Input
                      value={s.value}
                      onChange={e => setSettings(settings.map(x => x.key === s.key ? { ...x, value: e.target.value } : x))}
                      className="h-9 max-w-xs"
                    />
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {tab === 'import' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><FileUp className="w-5 h-5" /> استيراد سجلات بصمة من ملف</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-xs text-gray-500">
              يقبل الملف صيغة CSV أو Excel، ويجب أن يحتوي على عمود رقم الموظف/البصمة وعمود التاريخ،
              ويفضل أعمدة «وقت الدخول» و«وقت الخروج».
            </p>
            <div className="flex flex-wrap items-end gap-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">الملف</label>
                <input
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={e => setImportFile(e.target.files?.[0] || null)}
                  className="text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">الجهاز (اختياري)</label>
                <select value={importDevice} onChange={e => setImportDevice(e.target.value)} className="h-10 px-2 border-2 border-gray-200 rounded-lg text-sm">
                  <option value="">جهاز جديد (استيراد)</option>
                  {devices.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
              </div>
              <Button onClick={doImport} disabled={busy || !importFile} className="gap-2">
                <Download className="w-4 h-4" /> استيراد
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {deviceModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="p-5 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900">{deviceForm.id ? 'تعديل جهاز' : 'إضافة جهاز بصمة'}</h2>
              <button onClick={() => setDeviceModal(false)} className="text-gray-400 hover:text-gray-600">✕</button>
            </div>
            <div className="p-5 space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">اسم الجهاز *</label>
                <Input value={deviceForm.name} onChange={e => setDeviceForm({ ...deviceForm, name: e.target.value })} placeholder="مثال: جهاز البصمة الرئيسي" />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">الرقم التسلسلي (SN)</label>
                  <Input value={deviceForm.serial_number} onChange={e => setDeviceForm({ ...deviceForm, serial_number: e.target.value })} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">عنوان IP</label>
                  <Input value={deviceForm.ip_address} onChange={e => setDeviceForm({ ...deviceForm, ip_address: e.target.value })} placeholder="192.168.1.201" />
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">المنفذ</label>
                  <Input type="number" value={deviceForm.port} onChange={e => setDeviceForm({ ...deviceForm, port: Number(e.target.value) })} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">كلمة مرور الجهاز</label>
                  <Input value={deviceForm.password} onChange={e => setDeviceForm({ ...deviceForm, password: e.target.value })} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">نوع الربط</label>
                  <select value={deviceForm.direction} onChange={e => setDeviceForm({ ...deviceForm, direction: e.target.value })} className="h-10 px-2 border-2 border-gray-200 rounded-lg text-sm w-full">
                    <option value="pull">سحب من الجهاز</option>
                    <option value="push">دفع من الجهاز</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">مفتاح API (للوكيل المحلي / استقبال السجلات)</label>
                <Input value={deviceForm.api_key} onChange={e => setDeviceForm({ ...deviceForm, api_key: e.target.value })} />
              </div>
            </div>
            <div className="p-5 border-t border-gray-100 flex gap-3 justify-end">
              <button onClick={() => setDeviceModal(false)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">إلغاء</button>
              <Button onClick={saveDevice} disabled={busy}>{deviceForm.id ? 'حفظ التعديلات' : 'إضافة'}</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function EmployeeLinkRow({ emp, onSave }: { emp: any; onSave: (id: number, pin: string) => void }) {
  const [pin, setPin] = useState(emp.biometric_pin || '');
  useEffect(() => { setPin(emp.biometric_pin || ''); }, [emp.biometric_pin]);
  return (
    <tr className="border-t border-gray-100">
      <td className="px-3 py-1.5 text-gray-800">{emp.name}</td>
      <td className="px-3 py-1.5 font-mono text-gray-600">{emp.code}</td>
      <td className="px-3 py-1.5">
        <Input value={pin} onChange={e => setPin(e.target.value)} className="h-8 w-28" placeholder="PIN" />
      </td>
      <td className="px-3 py-1.5">
        <Button size="sm" variant="outline" onClick={() => onSave(emp.id, pin)}>حفظ</Button>
      </td>
    </tr>
  );
}
