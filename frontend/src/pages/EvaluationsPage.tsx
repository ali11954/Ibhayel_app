import { useState, useEffect } from 'react';
import { Search, Plus, Trash2, Star, ChevronDown, ChevronUp, Settings, CheckCircle, Edit } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Modal } from '@/components/ui/modal';
import api from '@/api/client';

function StarRating({ value, onChange, max = 5 }: { value: number; onChange?: (v: number) => void; max?: number }) {
  const [hover, setHover] = useState(0);
  return (
    <div className="flex gap-1" dir="ltr">
      {Array.from({ length: max }, (_, i) => i + 1).map((s) => (
        <button key={s} type="button" disabled={!onChange}
          onClick={() => onChange?.(s)} onMouseEnter={() => setHover(s)} onMouseLeave={() => setHover(0)}
          className="focus:outline-none transition-transform hover:scale-110">
          <Star className={`w-7 h-7 transition-colors ${s <= (hover || value) ? 'fill-amber-400 text-amber-400' : 'fill-gray-200 text-gray-200'}`} />
        </button>
      ))}
    </div>
  );
}

export default function EvaluationsPage() {
  const [tab, setTab] = useState<'list' | 'criteria'>('list');
  const [evaluations, setEvaluations] = useState<any[]>([]);
  const [employees, setEmployees] = useState<any[]>([]);
  const [regions, setRegions] = useState<any[]>([]);
  const [locations, setLocations] = useState<any[]>([]);
  const [jobTitles, setJobTitles] = useState<string[]>([]);
  const [criteria, setCriteria] = useState<any[]>([]);
  const [allCriteria, setAllCriteria] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<any>({
    employee_id: '', evaluation_type: 'supervisor', comments: '',
    region_id: '', location_id: '', criteria: [],
  });

  const loadData = () => {
    Promise.all([
      api.get('/evaluations'),
      api.get('/employees'),
      api.get('/regions'),
      api.get('/locations'),
      api.get('/evaluation-criteria/job-titles'),
      api.get('/evaluation-criteria'),
    ]).then(([eRes, empRes, regRes, locRes, jtRes, crRes]) => {
      setEvaluations(eRes.data.data || []);
      setEmployees(empRes.data.data || []);
      setRegions(regRes.data.data || []);
      setLocations(locRes.data.data || []);
      setJobTitles(jtRes.data.data || []);
      setAllCriteria(crRes.data.data || []);
    }).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, []);

  const loadCriteria = (jobTitle: string) => {
    if (!jobTitle) { setCriteria([]); return; }
    api.get(`/evaluation-criteria?job_title=${encodeURIComponent(jobTitle)}`)
      .then((r) => {
        const c = r.data.data || [];
        setCriteria(c);
        setForm((f: any) => ({
          ...f,
          criteria: c.map((cr: any) => ({ criterion_id: cr.id, score: 0, notes: '' })),
        }));
      });
  };

  const handleEmployeeSelect = (empId: string) => {
    const emp = employees.find((e: any) => e.id === Number(empId));
    setForm((f: any) => ({ ...f, employee_id: empId, criteria: [] }));
    if (emp?.job_title) loadCriteria(emp.job_title);
  };

  const updateCriterionScore = (criterionId: number, score: number) => {
    setForm((f: any) => ({
      ...f,
      criteria: f.criteria.map((c: any) => c.criterion_id === criterionId ? { ...c, score } : c),
    }));
  };

  const allCriteriaScored = criteria.length > 0 && form.criteria.every((c: any) => c.score > 0);

  const calcAvgScore = () => {
    const scores = form.criteria.filter((c: any) => c.score > 0).map((c: any) => c.score);
    if (scores.length === 0) return 0;
    return Math.round((scores.reduce((a: number, b: number) => a + b, 0) / scores.length) * 20);
  };

  const handleSave = async () => {
    if (!allCriteriaScored) return alert('يجب تقييم جميع المعايير بالنجوم');
    setSaving(true);
    try {
      const payload = {
        ...form,
        employee_id: Number(form.employee_id),
        score: calcAvgScore(),
        date: new Date().toISOString().split('T')[0],
        region_id: form.region_id ? Number(form.region_id) : null,
        location_id: form.location_id ? Number(form.location_id) : null,
        criteria: form.criteria.filter((c: any) => c.score > 0),
      };
      await api.post('/evaluations', payload);
      setModalOpen(false);
      setForm({ employee_id: '', evaluation_type: 'supervisor', comments: '', region_id: '', location_id: '', criteria: [] });
      setCriteria([]);
      loadData();
    } catch (err: any) { alert(err.response?.data?.message || 'حدث خطأ'); }
    finally { setSaving(false); }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('هل أنت متأكد من حذف هذا التقييم؟')) return;
    await api.delete(`/evaluations/${id}`);
    setEvaluations(prev => prev.filter(e => e.id !== id));
  };

  const filtered = evaluations.filter(e => e.employee_name?.includes(search));

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-8 h-8 border-3 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">التقييمات ومعايير العمل</h1>
          <p className="text-gray-500 text-sm mt-1">{evaluations.length} تقييم — {jobTitles.length} وظيفة — {allCriteria.length} معيار</p>
        </div>
        <Button onClick={() => { setTab('criteria'); }} variant="outline"><Settings className="w-4 h-4" /> معايير التقييم</Button>
      </div>

      {/* Tab Switcher */}
      <div className="flex gap-2">
        <button onClick={() => setTab('list')} className={`px-4 py-2 rounded-lg text-sm font-medium ${tab === 'list' ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600'}`}>التقييمات</button>
        <button onClick={() => setTab('criteria')} className={`px-4 py-2 rounded-lg text-sm font-medium ${tab === 'criteria' ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600'}`}>معايير التقييم</button>
      </div>

      {tab === 'list' && (
        <>
          <div className="flex flex-col sm:flex-row gap-3">
            <Card className="flex-1"><CardContent className="p-4">
              <div className="relative">
                <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="بحث بالاسم..." className="w-full h-10 pr-10 pl-4 rounded-lg border-2 border-gray-200 text-sm focus:border-primary-500 outline-none" />
              </div>
            </CardContent></Card>
            <Button onClick={() => setModalOpen(true)} className="h-10"><Plus className="w-4 h-4" /> تقييم جديد</Button>
          </div>

          <Card>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-primary-600 text-white">
                    <th className="px-4 py-3 text-right font-semibold">الموظف</th>
                    <th className="px-4 py-3 text-right font-semibold">التاريخ</th>
                    <th className="px-4 py-3 text-right font-semibold">النوع</th>
                    <th className="px-4 py-3 text-right font-semibold">التقييم</th>
                    <th className="px-4 py-3 text-right font-semibold">المنطقة</th>
                    <th className="px-4 py-3 text-right font-semibold">إجراءات</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((ev) => (
                    <tr key={ev.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center text-primary-700 text-sm font-bold">{ev.employee_name?.[0]}</div>
                          <div>
                            <span className="font-medium">{ev.employee_name}</span>
                            {ev.employee_job && <span className="block text-xs text-gray-400">{ev.employee_job}</span>}
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-gray-600">{ev.date}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded-full text-xs ${ev.evaluation_type === 'supervisor' ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'}`}>
                          {ev.evaluation_type === 'supervisor' ? 'تقييم مشرف' : 'تقييم متعهد'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <StarRating value={Math.round((ev.score || 0) / 20)} />
                          <span className="font-bold text-sm text-gray-600">{ev.score}/100</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs">{ev.region_name || '—'}</td>
                      <td className="px-4 py-3 flex gap-1">
                        <button onClick={() => setExpandedId(expandedId === ev.id ? null : ev.id)} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500">
                          {expandedId === ev.id ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </button>
                        <button onClick={() => handleDelete(ev.id)} className="p-1.5 rounded-lg hover:bg-red-50 text-red-500"><Trash2 className="w-4 h-4" /></button>
                      </td>
                    </tr>
                  ))}
                  {filtered.length === 0 && (
                    <tr><td colSpan={6} className="text-center py-8 text-gray-400">لا توجد تقييمات</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>

          {filtered.filter(ev => expandedId === ev.id).map((ev) => (
            <Card key={`detail-${ev.id}`}>
              <CardContent className="p-6">
                <h3 className="font-bold text-gray-900 mb-4">تفاصيل تقييم {ev.employee_name}</h3>
                {ev.details && ev.details.length > 0 ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {ev.details.map((d: any) => (
                      <div key={d.id} className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium text-sm">{d.criterion_name}</span>
                          <StarRating value={d.score} />
                        </div>
                        {d.criterion_description && <p className="text-xs text-gray-500">{d.criterion_description}</p>}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-400 text-sm">لا توجد تفاصيل معايير</p>
                )}
                {ev.comments && <p className="mt-4 text-sm text-gray-600"><strong>ملاحظات:</strong> {ev.comments}</p>}
              </CardContent>
            </Card>
          ))}
        </>
      )}

      {tab === 'criteria' && (
        <CriteriaTab jobTitles={jobTitles} allCriteria={allCriteria} loadData={loadData} />
      )}

      {/* Add Evaluation Modal */}
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="تقييم جديد" size="lg">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">الموظف *</label>
            <select value={form.employee_id} onChange={(e) => handleEmployeeSelect(e.target.value)} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
              <option value="">اختر الموظف</option>
              {employees.map((e: any) => <option key={e.id} value={e.id}>{e.name} — {e.job_title || 'بدون وظيفة'}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">نوع التقييم *</label>
              <select value={form.evaluation_type} onChange={(e) => setForm({ ...form, evaluation_type: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
                <option value="supervisor">تقييم مشرف</option>
                <option value="contractor">تقييم متعهد</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">المنطقة</label>
              <select value={form.region_id} onChange={(e) => setForm({ ...form, region_id: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
                <option value="">اختر المنطقة</option>
                {regions.map((r: any) => <option key={r.id} value={r.id}>{r.name}</option>)}
              </select>
            </div>
          </div>
          {form.region_id && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">الموقع</label>
              <select value={form.location_id} onChange={(e) => setForm({ ...form, location_id: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
                <option value="">اختر الموقع</option>
                {locations.filter((l: any) => l.region_id === Number(form.region_id)).map((l: any) => <option key={l.id} value={l.id}>{l.name}</option>)}
              </select>
            </div>
          )}

          {criteria.length > 0 && (
            <div className="border-t pt-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-medium text-gray-900">
                  معايير التقييم — {form.employee_id && employees.find((e: any) => e.id === Number(form.employee_id))?.job_title}
                </h3>
                <div className="flex items-center gap-3">
                  <div className={`flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${allCriteriaScored ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
                    {allCriteriaScored ? <CheckCircle className="w-4 h-4" /> : <Star className="w-4 h-4" />}
                    {form.criteria.filter((c: any) => c.score > 0).length}/{criteria.length} معايير
                  </div>
                  <span className="font-bold text-lg">{calcAvgScore()}</span>
                  <span className="text-xs text-gray-400">/100</span>
                </div>
              </div>
              <div className="space-y-3 max-h-80 overflow-y-auto">
                {criteria.map((cr: any) => {
                  const detail = form.criteria.find((c: any) => c.criterion_id === cr.id);
                  return (
                    <div key={cr.id} className={`bg-gray-50 rounded-lg p-4 border-2 transition-colors ${detail?.score > 0 ? 'border-green-200 bg-green-50/50' : 'border-gray-200'}`}>
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <span className="font-medium text-sm">{cr.name}</span>
                          {cr.description && <span className="block text-xs text-gray-500 mt-0.5">{cr.description}</span>}
                        </div>
                        <StarRating value={detail?.score || 0} onChange={(v) => updateCriterionScore(cr.id, v)} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">ملاحظات</label>
            <textarea value={form.comments} onChange={(e) => setForm({ ...form, comments: e.target.value })} className="w-full h-20 px-3 py-2 rounded-lg border-2 border-gray-200 text-sm focus:border-primary-500 outline-none resize-none" placeholder="ملاحظات التقييم" />
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setModalOpen(false)}>إلغاء</Button>
            <Button onClick={handleSave} disabled={saving || !form.employee_id || !allCriteriaScored}>
              {saving ? 'جاري الحفظ...' : !allCriteriaScored ? 'أكمل تقييم جميع المعايير' : 'حفظ التقييم'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

function CriteriaTab({ jobTitles, allCriteria, loadData }: { jobTitles: string[]; allCriteria: any[]; loadData: () => void }) {
  const [critForm, setCritForm] = useState({ job_title: '', name: '', description: '', max_score: 5 });
  const [useExisting, setUseExisting] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editModal, setEditModal] = useState<any>(null);
  const [editForm, setEditForm] = useState({ job_title: '', name: '', description: '' });

  const handleAddCriterion = async () => {
    if (!critForm.job_title || !critForm.name) return alert('أدخل الوظيفة والمعيار');
    setSaving(true);
    try {
      await api.post('/evaluation-criteria', { ...critForm, max_score: 5 });
      setCritForm({ job_title: '', name: '', description: '', max_score: 5 });
      loadData();
    } catch (err: any) { alert(err.response?.data?.message || 'حدث خطأ'); }
    finally { setSaving(false); }
  };

  const handleDeleteCriterion = async (id: number) => {
    if (!confirm('هل أنت متأكد من حذف هذا المعيار؟')) return;
    await api.delete(`/evaluation-criteria/${id}`);
    loadData();
  };

  const openEdit = (cr: any) => {
    setEditModal(cr);
    setEditForm({ job_title: cr.job_title, name: cr.name, description: cr.description || '' });
  };

  const handleEditCriterion = async () => {
    if (!editForm.job_title || !editForm.name) return alert('أدخل الوظيفة والمعيار');
    setSaving(true);
    try {
      await api.put(`/evaluation-criteria/${editModal.id}`, editForm);
      setEditModal(null);
      loadData();
    } catch (err: any) { alert(err.response?.data?.message || 'حدث خطأ'); }
    finally { setSaving(false); }
  };

  const groupedCriteria = jobTitles.map(jt => ({
    job_title: jt,
    criteria: allCriteria.filter(c => c.job_title === jt),
  }));

  return (
    <div className="space-y-6">
      <div className="flex gap-2">
        <button onClick={() => {}} className="px-4 py-2 rounded-lg text-sm font-medium bg-primary-600 text-white">التقييمات</button>
        <button onClick={() => {}} className="px-4 py-2 rounded-lg text-sm font-medium bg-primary-600 text-white">معايير التقييم</button>
      </div>

      {/* Grouped criteria by job title */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {groupedCriteria.map((group) => (
          <Card key={group.job_title} className="hover:shadow-md transition-shadow">
            <CardContent className="p-5">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-primary-100 flex items-center justify-center">
                  <Star className="w-5 h-5 text-primary-600" />
                </div>
                <div>
                  <h3 className="font-bold text-gray-900">{group.job_title}</h3>
                  <p className="text-xs text-gray-400">{group.criteria.length} معيار</p>
                </div>
              </div>
              <div className="space-y-2">
                {group.criteria.map((cr) => (
                  <div key={cr.id} className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2">
                    <div className="flex items-center gap-2">
                      <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                      <div>
                        <span className="text-sm font-medium">{cr.name}</span>
                        {cr.description && <span className="block text-xs text-gray-400">{cr.description}</span>}
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <button onClick={() => openEdit(cr)} className="p-1 rounded hover:bg-blue-100 text-blue-500">
                        <Edit className="w-3 h-3" />
                      </button>
                      <button onClick={() => handleDeleteCriterion(cr.id)} className="p-1 rounded hover:bg-red-100 text-red-500">
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                ))}
                {group.criteria.length === 0 && <p className="text-xs text-gray-400">لا توجد معايير</p>}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Add New Criterion */}
      <Card>
        <CardContent className="p-6">
          <h3 className="font-bold text-gray-900 mb-4">إضافة معيار تقييم جديد</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">الوظيفة *</label>
              <div className="flex gap-2">
                {useExisting ? (
                  <select value={critForm.job_title} onChange={(e) => setCritForm({ ...critForm, job_title: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
                    <option value="">اختر وظيفة</option>
                    {jobTitles.map(jt => <option key={jt} value={jt}>{jt}</option>)}
                  </select>
                ) : (
                  <Input value={critForm.job_title} onChange={(e) => setCritForm({ ...critForm, job_title: e.target.value })} placeholder="أدخل الوظيفة" />
                )}
              </div>
              <button onClick={() => setUseExisting(!useExisting)} className="mt-1 text-xs text-primary-600 hover:underline">
                {useExisting ? 'كتابة وظيفة جديدة' : 'اختيار من القائمة'}
              </button>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">اسم المعيار *</label>
              <Input value={critForm.name} onChange={(e) => setCritForm({ ...critForm, name: e.target.value })} placeholder="مثال: ري النخل" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">الوصف</label>
              <Input value={critForm.description} onChange={(e) => setCritForm({ ...critForm, description: e.target.value })} placeholder="وصف المعيار (اختياري)" />
            </div>
          </div>
          <Button onClick={handleAddCriterion} className="mt-4" disabled={saving || !critForm.job_title || !critForm.name}>
            <Plus className="w-4 h-4" /> {saving ? 'جاري الإضافة...' : 'إضافة المعيار'}
          </Button>
        </CardContent>
      </Card>

      {/* Edit Criterion Modal */}
      <Modal open={!!editModal} onClose={() => setEditModal(null)} title="تعديل المعيار">
        {editModal && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">الوظيفة *</label>
              <select value={editForm.job_title} onChange={(e) => setEditForm({ ...editForm, job_title: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
                <option value="">اختر وظيفة</option>
                {jobTitles.map(jt => <option key={jt} value={jt}>{jt}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">اسم المعيار *</label>
              <Input value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} placeholder="مثال: ري النخل" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">الوصف</label>
              <Input value={editForm.description} onChange={(e) => setEditForm({ ...editForm, description: e.target.value })} placeholder="وصف المعيار (اختياري)" />
            </div>
            <div className="flex justify-end gap-2 pt-4 border-t">
              <Button variant="outline" onClick={() => setEditModal(null)}>إلغاء</Button>
              <Button onClick={handleEditCriterion} disabled={saving || !editForm.job_title || !editForm.name}>
                {saving ? 'جاري الحفظ...' : 'حفظ التعديلات'}
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
