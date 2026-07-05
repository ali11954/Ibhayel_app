import { useState, useEffect } from 'react';
import { Plus, CalendarCheck, Users, Clock, AlertTriangle, ClipboardCheck } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Modal } from '@/components/ui/modal';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
import api from '@/api/client';

const STATUS_OPTIONS = [
  { value: 'present', label: 'حاضر', color: 'bg-green-500' },
  { value: 'late', label: 'متأخر', color: 'bg-yellow-500' },
  { value: 'absent', label: 'غائب', color: 'bg-red-500' },
  { value: 'sick', label: 'إجازة مرضية', color: 'bg-blue-500' },
  { value: 'annual_leave', label: 'إجازة مدفوعة الأجر', color: 'bg-purple-500' },
  { value: 'unpaid_leave', label: 'إجازة بدون أجر', color: 'bg-gray-500' },
];

const BADGE_VARIANT: Record<string, string> = {
  present: 'success', late: 'warning', absent: 'danger',
  sick: 'info', annual_leave: 'default', unpaid_leave: 'secondary',
};

export default function AttendancePage() {
  const [records, setRecords] = useState<any[]>([]);
  const [employees, setEmployees] = useState<any[]>([]);
  const [attendanceReport, setAttendanceReport] = useState<any>(null);
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ employee_id: '', attendance_status: 'present', notes: '', time_in: '', time_out: '' });
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<'list' | 'charts' | 'group'>('list');

  // Group preparation state
  const [groupData, setGroupData] = useState<Record<number, { status: string; notes: string }>>({});
  const [savingCompany, setSavingCompany] = useState<string | null>(null);

  const loadData = () => {
    setLoading(true);
    Promise.all([
      api.get('/attendance', { params: { date } }),
      api.get('/employees'),
      api.get('/reports/attendance'),
    ]).then(([aRes, eRes, rRes]) => {
      setRecords(aRes.data.data || []);
      setEmployees(eRes.data.data || []);
      setAttendanceReport(rRes.data.data);
      // Initialize group data for employees not yet present today
      const presentEmpIds = new Set((aRes.data.data || []).map((r: any) => r.employee_id));
      const initial: Record<number, { status: string; notes: string }> = {};
      (eRes.data.data || []).forEach((emp: any) => {
        if (!presentEmpIds.has(emp.id)) {
          initial[emp.id] = { status: 'absent', notes: '' };
        }
      });
      setGroupData(initial);
    }).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, [date]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.post('/attendance', { ...form, date, employee_id: Number(form.employee_id) });
      setModalOpen(false);
      setForm({ employee_id: '', attendance_status: 'present', notes: '', time_in: '', time_out: '' });
      loadData();
    } catch (err: any) {
      alert(err.response?.data?.message || 'حدث خطأ');
    } finally {
      setSaving(false);
    }
  };

  const handleCompanySave = async (company: string, empIds: number[]) => {
    setSavingCompany(company);
    try {
      const recordsArr = empIds
        .filter(id => groupData[id])
        .map(id => ({
          employee_id: id,
          attendance_status: groupData[id].status,
          notes: groupData[id].notes,
        }));
      await api.post('/attendance/bulk', { date, records: recordsArr });
      loadData();
    } catch (err: any) {
      alert(err.response?.data?.message || 'حدث خطأ');
    } finally {
      setSavingCompany(null);
    }
  };

  const setGroupStatus = (empId: number, status: string) => {
    setGroupData(prev => ({ ...prev, [empId]: { ...prev[empId], status } }));
  };

  const filtered = records.filter(e => e.employee_name?.includes(search));
  const present = records.filter(r => r.attendance_status === 'present').length;
  const late = records.filter(r => r.attendance_status === 'late').length;
  const absent = records.filter(r => r.attendance_status === 'absent').length;

  const statusMap: Record<string, string> = {
    present: 'حاضر', late: 'متأخر', absent: 'غائب',
    sick: 'مرضي', annual_leave: 'إجازة', unpaid_leave: 'إجازة بدون أجر',
  };

  const filteredEmployees = employees.filter(e => e.name?.includes(search));
  const groupEntries = Object.entries(groupData).filter(([id]) =>
    filteredEmployees.some((e: any) => e.id === Number(id))
  );

  const groupStats = Object.values(groupData).reduce(
    (acc, d) => { acc[d.status] = (acc[d.status] || 0) + 1; return acc; },
    {} as Record<string, number>
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">الحضور والغياب</h1>
          <p className="text-gray-500 text-sm mt-1">{records.length} سجل لليوم</p>
        </div>
        <div className="flex gap-2">
          <Button variant={activeTab === 'list' ? 'default' : 'outline'} onClick={() => setActiveTab('list')}>القائمة</Button>
          <Button variant={activeTab === 'group' ? 'default' : 'outline'} onClick={() => setActiveTab('group')}>
            <ClipboardCheck className="w-4 h-4" /> تحضير جماعي
          </Button>
          <Button variant={activeTab === 'charts' ? 'default' : 'outline'} onClick={() => setActiveTab('charts')}>الرسوم</Button>
          <Button onClick={() => setModalOpen(true)}><Plus className="w-4 h-4" /> تسجيل حضور</Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="p-4 text-center">
            <div className="w-10 h-10 bg-green-500 rounded-xl flex items-center justify-center mx-auto mb-2">
              <Users className="w-5 h-5 text-white" />
            </div>
            <p className="text-2xl font-bold text-green-600">{present}</p>
            <p className="text-xs text-gray-500">حاضر</p>
          </CardContent>
        </Card>
        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="p-4 text-center">
            <div className="w-10 h-10 bg-yellow-500 rounded-xl flex items-center justify-center mx-auto mb-2">
              <Clock className="w-5 h-5 text-white" />
            </div>
            <p className="text-2xl font-bold text-yellow-600">{late}</p>
            <p className="text-xs text-gray-500">متأخر</p>
          </CardContent>
        </Card>
        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="p-4 text-center">
            <div className="w-10 h-10 bg-red-500 rounded-xl flex items-center justify-center mx-auto mb-2">
              <AlertTriangle className="w-5 h-5 text-white" />
            </div>
            <p className="text-2xl font-bold text-red-600">{absent}</p>
            <p className="text-xs text-gray-500">غائب</p>
          </CardContent>
        </Card>
        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="p-4 text-center">
            <div className="w-10 h-10 bg-primary-500 rounded-xl flex items-center justify-center mx-auto mb-2">
              <CalendarCheck className="w-5 h-5 text-white" />
            </div>
            <p className="text-2xl font-bold text-primary-600">{records.length}</p>
            <p className="text-xs text-gray-500">الإجمالي</p>
          </CardContent>
        </Card>
      </div>

      {/* Date + Search */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="بحث بالاسم..." className="w-full h-10 px-4 rounded-lg border-2 border-gray-200 text-sm focus:border-primary-500 outline-none" />
            </div>
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="h-10 px-4 rounded-lg border-2 border-gray-200 text-sm" />
          </div>
        </CardContent>
      </Card>

      {/* Charts Tab */}
      {activeTab === 'charts' && attendanceReport && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardContent className="p-6">
                <h3 className="font-bold text-gray-900 mb-4">الحضور اليومي (آخر 30 يوم)</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={attendanceReport.daily || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="date" tick={{ fontSize: 9 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="present" fill="#10b981" name="حاضر" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="late" fill="#f59e0b" name="متأخر" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="absent" fill="#ef4444" name="غائب" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <h3 className="font-bold text-gray-900 mb-4">نسبة الحضور (آخر 30 يوم)</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie data={[
                      { name: 'حاضر', value: attendanceReport.summary?.present || 0 },
                      { name: 'متأخر', value: attendanceReport.summary?.late || 0 },
                      { name: 'غائب', value: attendanceReport.summary?.absent || 0 },
                      { name: 'مرضي', value: attendanceReport.summary?.sick || 0 },
                      { name: 'إجازة', value: attendanceReport.summary?.annual_leave || 0 },
                    ].filter((d: any) => d.value > 0)} cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={4} dataKey="value"
                      label={({ name, percent }: any) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}>
                    </Pie>
                    <Tooltip formatter={(value: any) => [value, 'يوم']} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Group Preparation Tab */}
      {activeTab === 'group' && (
        <div className="space-y-4">
          <Card>
            <div className="p-4 border-b bg-primary-50">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-gray-900">تحضير جماعي - {new Date(date).toLocaleDateString('ar-EG')}</h3>
                  <p className="text-sm text-gray-500 mt-1">
                    حدد حالة كل موظف ثم اضغط حفظ على كل شركة
                  </p>
                </div>
                <div className="flex gap-4 text-xs">
                  {STATUS_OPTIONS.map(opt => (
                    <span key={opt.value} className="flex items-center gap-1">
                      <span className={`w-2.5 h-2.5 rounded-full ${opt.color}`} />
                      {opt.label} {groupStats[opt.value] || 0}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </Card>

          {(() => {
            const grouped: Record<string, any[]> = {};
            filteredEmployees.forEach(emp => {
              const company = emp.company_name || 'بدون شركة';
              if (!grouped[company]) grouped[company] = [];
              if (groupData[emp.id]) grouped[company].push(emp);
            });
            let rowIdx = 0;
            return Object.entries(grouped).map(([company, emps]) => {
              const companyEmpIds = emps.map(e => e.id);
              const companyCount = companyEmpIds.length;
              return (
                <Card key={company}>
                  <div className="px-4 py-2.5 bg-primary-600 text-white flex items-center justify-between">
                    <span className="font-bold text-sm">{company}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-xs bg-white/20 px-2.5 py-0.5 rounded-full">{companyCount} موظف</span>
                      <Button
                        size="sm"
                        className="bg-white text-primary-700 hover:bg-primary-50 text-xs h-7"
                        disabled={savingCompany === company}
                        onClick={() => handleCompanySave(company, companyEmpIds)}
                      >
                        {savingCompany === company ? 'جاري الحفظ...' : 'حفظ'}
                      </Button>
                    </div>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-gray-50 text-right">
                          <th className="px-4 py-2 font-semibold text-gray-600 w-10">#</th>
                          <th className="px-4 py-2 font-semibold text-gray-600">الموظف</th>
                          <th className="px-4 py-2 font-semibold text-gray-600">الوظيفة</th>
                          <th className="px-4 py-2 font-semibold text-gray-600">الحالة</th>
                          <th className="px-4 py-2 font-semibold text-gray-600">ملاحظات</th>
                        </tr>
                      </thead>
                      <tbody>
                        {emps.map(emp => {
                          const data = groupData[emp.id];
                          rowIdx++;
                          return (
                            <tr key={emp.id} className="border-b border-gray-100 hover:bg-gray-50">
                              <td className="px-4 py-2 text-gray-400">{rowIdx}</td>
                              <td className="px-4 py-2">
                                <div className="flex items-center gap-2">
                                  <div className="w-7 h-7 rounded-full bg-primary-100 flex items-center justify-center text-primary-700 text-xs font-bold">
                                    {emp.name?.[0]}
                                  </div>
                                  <span className="font-medium">{emp.name}</span>
                                </div>
                              </td>
                              <td className="px-4 py-2 text-gray-500 text-xs">{emp.job_title || '—'}</td>
                              <td className="px-4 py-2">
                                <select
                                  value={data.status}
                                  onChange={(e) => setGroupStatus(emp.id, e.target.value)}
                                  className={`h-8 px-2 rounded-lg border text-xs font-medium ${
                                    data.status === 'present' ? 'border-green-300 bg-green-50 text-green-700' :
                                    data.status === 'late' ? 'border-yellow-300 bg-yellow-50 text-yellow-700' :
                                    data.status === 'sick' ? 'border-blue-300 bg-blue-50 text-blue-700' :
                                    data.status === 'annual_leave' ? 'border-purple-300 bg-purple-50 text-purple-700' :
                                    data.status === 'unpaid_leave' ? 'border-gray-300 bg-gray-50 text-gray-700' :
                                    'border-red-300 bg-red-50 text-red-700'
                                  }`}
                                >
                                  {STATUS_OPTIONS.map(opt => (
                                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                                  ))}
                                </select>
                              </td>
                              <td className="px-4 py-2">
                                <input
                                  type="text"
                                  value={data.notes}
                                  onChange={(e) => setGroupData(prev => ({ ...prev, [emp.id]: { ...prev[emp.id], notes: e.target.value } }))}
                                  placeholder="ملاحظة..."
                                  className="w-full h-8 px-2 rounded-lg border border-gray-200 text-xs"
                                />
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </Card>
              );
            });
          })()}
        </div>
      )}

      {/* List Tab */}
      {activeTab === 'list' && (
        <Card>
          <div className="overflow-x-auto">
            {loading ? (
              <div className="flex items-center justify-center h-32"><div className="w-8 h-8 border-3 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" /></div>
            ) : (
              <table className="w-full text-sm">
                <thead><tr className="bg-primary-600 text-white">
                  <th className="px-4 py-3 text-right font-semibold">الموظف</th>
                  <th className="px-4 py-3 text-right font-semibold">وقت الدخول</th>
                  <th className="px-4 py-3 text-right font-semibold">وقت الخروج</th>
                  <th className="px-4 py-3 text-right font-semibold">الحالة</th>
                  <th className="px-4 py-3 text-right font-semibold">ملاحظات</th>
                </tr></thead>
                <tbody>
                  {filtered.map((rec, i) => (
                    <tr key={rec.id || i} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="px-4 py-3"><div className="flex items-center gap-3"><div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center text-primary-700 text-sm font-bold">{rec.employee_name?.[0]}</div><span className="font-medium">{rec.employee_name}</span></div></td>
                      <td className="px-4 py-3">{rec.check_in_time || '—'}</td>
                      <td className="px-4 py-3">{rec.check_out_time || '—'}</td>
                      <td className="px-4 py-3">
                        <Badge variant={(BADGE_VARIANT[rec.attendance_status] || 'danger') as any}>
                          {statusMap[rec.attendance_status] || rec.attendance_status}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs">{rec.notes || '—'}</td>
                    </tr>
                  ))}
                  {filtered.length === 0 && <tr><td colSpan={5} className="text-center py-8 text-gray-400">لا توجد سجلات</td></tr>}
                </tbody>
              </table>
            )}
          </div>
        </Card>
      )}

      {/* Add Modal */}
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="تسجيل حضور">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">الموظف *</label>
            <select value={form.employee_id} onChange={(e) => setForm({ ...form, employee_id: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
              <option value="">اختر الموظف</option>
              {employees.map((e: any) => <option key={e.id} value={e.id}>{e.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">الحالة *</label>
            <select value={form.attendance_status} onChange={(e) => setForm({ ...form, attendance_status: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
              {STATUS_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium text-gray-700 mb-1">وقت الدخول</label><Input type="time" value={form.time_in} onChange={(e) => setForm({ ...form, time_in: e.target.value })} /></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">وقت الخروج</label><Input type="time" value={form.time_out} onChange={(e) => setForm({ ...form, time_out: e.target.value })} /></div>
          </div>
          <div><label className="block text-sm font-medium text-gray-700 mb-1">ملاحظات</label><Input value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} placeholder="ملاحظات إضافية" /></div>
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setModalOpen(false)}>إلغاء</Button>
            <Button onClick={handleSave} disabled={saving || !form.employee_id}>{saving ? 'جاري الحفظ...' : 'حفظ'}</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
