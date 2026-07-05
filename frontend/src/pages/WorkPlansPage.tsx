import { useState, useEffect } from 'react';
import { Plus, Trash2, Calendar, CheckCircle, Clock, AlertCircle, ListTodo, ChevronDown, ChevronUp, Edit, Pencil } from 'lucide-react';
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
          className="focus:outline-none">
          <Star className={`w-5 h-5 transition-colors ${s <= (hover || value) ? 'fill-amber-400 text-amber-400' : 'fill-gray-200 text-gray-200'}`} />
        </button>
      ))}
    </div>
  );
}

function Star({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path fillRule="evenodd" d="M10.788 3.21c.448-1.077 1.976-1.077 2.424 0l2.082 5.006 5.404.434c1.164.093 1.636 1.545.749 2.305l-4.117 3.527 1.257 5.273c.271 1.136-.964 2.033-1.96 1.425L12 18.354 7.373 21.18c-.996.608-2.231-.29-1.96-1.425l1.257-5.273-4.117-3.527c-.887-.76-.415-2.212.749-2.305l5.404-.434 2.082-5.005Z" clipRule="evenodd" />
    </svg>
  );
}

export default function WorkPlansPage() {
  const [plans, setPlans] = useState<any[]>([]);
  const [employees, setEmployees] = useState<any[]>([]);
  const [companies, setCompanies] = useState<any[]>([]);
  const [regions, setRegions] = useState<any[]>([]);
  const [locations, setLocations] = useState<any[]>([]);
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editItem, setEditItem] = useState<any>(null);
  const [taskModal, setTaskModal] = useState<{ open: boolean; planId: number }>({ open: false, planId: 0 });
  const [editTaskModal, setEditTaskModal] = useState<any>(null);
  const [completeModal, setCompleteModal] = useState<{ open: boolean; taskId: number; score: number; notes: string }>({ open: false, taskId: 0, score: 0, notes: '' });
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    title: '', description: '', plan_type: 'daily', company_id: '', region_id: '',
    location_id: '', plan_date: new Date().toISOString().split('T')[0], assigned_to: '',
    tasks: [{ title: '', description: '', assigned_to: '', priority: 'normal' }],
  });
  const [taskForm, setTaskForm] = useState({ title: '', description: '', assigned_to: '', priority: 'normal' });

  const loadData = () => {
    Promise.all([
      api.get('/work-plans'),
      api.get('/employees'),
      api.get('/companies'),
      api.get('/regions'),
      api.get('/locations'),
    ]).then(([pRes, eRes, cRes, rRes, lRes]) => {
      setPlans(pRes.data.data || []);
      setEmployees(eRes.data.data || []);
      setCompanies(cRes.data.data || []);
      setRegions(rRes.data.data || []);
      setLocations(lRes.data.data || []);
    }).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, []);

  const openAdd = () => {
    setEditItem(null);
    setForm({
      title: '', description: '', plan_type: 'daily', company_id: '', region_id: '',
      location_id: '', plan_date: new Date().toISOString().split('T')[0], assigned_to: '',
      tasks: [{ title: '', description: '', assigned_to: '', priority: 'normal' }],
    });
    setModalOpen(true);
  };

  const openEdit = (plan: any) => {
    setEditItem(plan);
    setForm({
      title: plan.title, description: plan.description || '', plan_type: plan.plan_type,
      company_id: plan.company_id || '', region_id: plan.region_id || '',
      location_id: plan.location_id || '', plan_date: plan.plan_date || new Date().toISOString().split('T')[0],
      assigned_to: plan.assigned_to || '',
      tasks: plan.tasks?.length > 0 ? plan.tasks.map((t: any) => ({ title: t.title, description: t.description || '', assigned_to: t.assigned_to || '', priority: t.priority || 'normal' })) : [{ title: '', description: '', assigned_to: '', priority: 'normal' }],
    });
    setModalOpen(true);
  };

  const handleSave = async () => {
    if (!form.title) return alert('أدخل عنوان الخطة');
    setSaving(true);
    try {
      const payload = {
        ...form,
        company_id: form.company_id ? Number(form.company_id) : null,
        region_id: form.region_id ? Number(form.region_id) : null,
        location_id: form.location_id ? Number(form.location_id) : null,
        assigned_to: form.assigned_to ? Number(form.assigned_to) : null,
        tasks: form.tasks.filter(t => t.title.trim()).map(t => ({
          ...t,
          assigned_to: t.assigned_to ? Number(t.assigned_to) : null,
        })),
      };
      if (editItem) {
        await api.put(`/work-plans/${editItem.id}`, payload);
      } else {
        await api.post('/work-plans', payload);
      }
      setModalOpen(false);
      loadData();
    } catch (err: any) { alert(err.response?.data?.message || 'حدث خطأ'); }
    finally { setSaving(false); }
  };

  const handleAddTask = async () => {
    if (!taskForm.title) return;
    setSaving(true);
    try {
      await api.post(`/work-plans/${taskModal.planId}/tasks`, {
        ...taskForm,
        assigned_to: taskForm.assigned_to ? Number(taskForm.assigned_to) : null,
      });
      setTaskModal({ open: false, planId: 0 });
      setTaskForm({ title: '', description: '', assigned_to: '', priority: 'normal' });
      loadData();
    } catch (err: any) { alert(err.response?.data?.message || 'حدث خطأ'); }
    finally { setSaving(false); }
  };

  const handleEditTask = async () => {
    if (!editTaskModal?.title) return;
    setSaving(true);
    try {
      await api.put(`/work-plans/tasks/${editTaskModal.id}`, {
        title: editTaskModal.title,
        description: editTaskModal.description,
        assigned_to: editTaskModal.assigned_to ? Number(editTaskModal.assigned_to) : null,
        priority: editTaskModal.priority,
      });
      setEditTaskModal(null);
      loadData();
    } catch (err: any) { alert(err.response?.data?.message || 'حدث خطأ'); }
    finally { setSaving(false); }
  };

  const handleCompleteTask = async () => {
    setSaving(true);
    try {
      await api.post(`/work-plans/tasks/${completeModal.taskId}/complete`, {
        evaluation_score: completeModal.score,
        evaluation_notes: completeModal.notes,
      });
      setCompleteModal({ open: false, taskId: 0, score: 0, notes: '' });
      loadData();
    } catch (err: any) { alert(err.response?.data?.message || 'حدث خطأ'); }
    finally { setSaving(false); }
  };

  const handleDeletePlan = async (id: number) => {
    if (!confirm('هل أنت متأكد من حذف خطة العمل؟')) return;
    await api.delete(`/work-plans/${id}`);
    loadData();
  };

  const handleDeleteTask = async (id: number) => {
    if (!confirm('هل أنت متأكد من حذف المهمة؟')) return;
    await api.delete(`/work-plans/tasks/${id}`);
    loadData();
  };

  const filtered = plans.filter(p => filter === 'all' || p.plan_type === filter);

  const stats = {
    total: plans.length,
    pending: plans.filter(p => p.status === 'pending').length,
    in_progress: plans.filter(p => p.status === 'in_progress').length,
    completed: plans.filter(p => p.status === 'completed').length,
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-8 h-8 border-3 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">خطط العمل</h1>
          <p className="text-gray-500 text-sm mt-1">اليومية والشهرية والسنوية</p>
        </div>
        <Button onClick={openAdd}><Plus className="w-4 h-4" /> خطة جديدة</Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'الكل', value: stats.total, color: 'bg-gray-100 text-gray-700', icon: ListTodo },
          { label: 'قيد الانتظار', value: stats.pending, color: 'bg-amber-100 text-amber-700', icon: Clock },
          { label: 'قيد التنفيذ', value: stats.in_progress, color: 'bg-blue-100 text-blue-700', icon: AlertCircle },
          { label: 'مكتملة', value: stats.completed, color: 'bg-green-100 text-green-700', icon: CheckCircle },
        ].map((s) => (
          <Card key={s.label}><CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-xl ${s.color} flex items-center justify-center`}>
                <s.icon className="w-5 h-5" />
              </div>
              <div>
                <p className="text-2xl font-bold">{s.value}</p>
                <p className="text-xs text-gray-500">{s.label}</p>
              </div>
            </div>
          </CardContent></Card>
        ))}
      </div>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        {[
          { key: 'all', label: 'الكل' },
          { key: 'daily', label: 'يومي' },
          { key: 'monthly', label: 'شهري' },
          { key: 'yearly', label: 'سنوي' },
        ].map((f) => (
          <button key={f.key} onClick={() => setFilter(f.key)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${filter === f.key ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
            {f.label}
          </button>
        ))}
      </div>

      {/* Plans List */}
      <div className="space-y-4">
        {filtered.map((plan) => {
          const isExpanded = expandedId === plan.id;
          const tasks = plan.tasks || [];
          return (
            <Card key={plan.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-5">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="font-bold text-gray-900">{plan.title}</h3>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        plan.plan_type === 'daily' ? 'bg-blue-100 text-blue-700' :
                        plan.plan_type === 'monthly' ? 'bg-purple-100 text-purple-700' :
                        'bg-amber-100 text-amber-700'
                      }`}>{plan.plan_type_name}</span>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        plan.status === 'completed' ? 'bg-green-100 text-green-700' :
                        plan.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                        plan.status === 'cancelled' ? 'bg-red-100 text-red-700' :
                        'bg-gray-100 text-gray-600'
                      }`}>{plan.status_name}</span>
                    </div>
                    {plan.description && <p className="text-sm text-gray-500 mb-2">{plan.description}</p>}
                    <div className="flex items-center gap-4 text-xs text-gray-400">
                      <span className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5" /> {plan.plan_date}</span>
                      {plan.assignee_name && <span>المكلف: {plan.assignee_name}</span>}
                      {plan.company_name && <span>{plan.company_name}</span>}
                      {plan.region_name && <span>{plan.region_name}</span>}
                      {tasks.length > 0 && <span className="flex items-center gap-1"><ListTodo className="w-3.5 h-3.5" /> {plan.completed_tasks || 0}/{tasks.length} مهمة</span>}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="text-center">
                      <div className="w-12 h-12 rounded-full bg-primary-50 flex items-center justify-center">
                        <span className="text-lg font-bold text-primary-600">{plan.progress}%</span>
                      </div>
                    </div>
                    <button onClick={() => setExpandedId(isExpanded ? null : plan.id)} className="p-2 rounded-lg hover:bg-gray-100 text-gray-500">
                      {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                    </button>
                    <button onClick={() => { setTaskModal({ open: true, planId: plan.id }); }} className="p-2 rounded-lg hover:bg-blue-50 text-blue-500">
                      <Plus className="w-4 h-4" />
                    </button>
                    <button onClick={() => openEdit(plan)} className="p-2 rounded-lg hover:bg-amber-50 text-amber-500" title="تعديل">
                      <Pencil className="w-4 h-4" />
                    </button>
                    <button onClick={() => handleDeletePlan(plan.id)} className="p-2 rounded-lg hover:bg-red-50 text-red-500">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="mt-3 h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full transition-all ${
                    plan.progress >= 100 ? 'bg-green-500' : plan.progress > 0 ? 'bg-primary-500' : 'bg-gray-300'
                  }`} style={{ width: `${plan.progress}%` }} />
                </div>

                {/* Tasks */}
                {isExpanded && (
                  <div className="mt-4 space-y-2">
                    {tasks.length === 0 ? (
                      <p className="text-sm text-gray-400 text-center py-4">لا توجد مهام بعد — أضف مهمة جديدة</p>
                    ) : (
                      tasks.map((task: any) => (
                        <div key={task.id} className={`flex items-center gap-3 p-3 rounded-lg border ${
                          task.is_completed ? 'bg-green-50 border-green-200' : 'bg-white border-gray-200'
                        }`}>
                          <div className={`w-6 h-6 rounded-full flex items-center justify-center ${
                            task.is_completed ? 'bg-green-500 text-white' : 'bg-gray-200'
                          }`}>
                            {task.is_completed ? <CheckCircle className="w-4 h-4" /> : <span className="text-xs font-bold">{task.order + 1}</span>}
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className={`text-sm font-medium ${task.is_completed ? 'line-through text-gray-400' : ''}`}>{task.title}</span>
                              {task.priority && task.priority !== 'normal' && (
                                <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                  task.priority === 'urgent' ? 'bg-red-100 text-red-700' :
                                  task.priority === 'high' ? 'bg-orange-100 text-orange-700' :
                                  'bg-gray-100 text-gray-500'
                                }`}>
                                  {task.priority === 'urgent' ? 'عاجل' : task.priority === 'high' ? 'مهم' : task.priority === 'low' ? 'منخفض' : ''}
                                </span>
                              )}
                            </div>
                            {task.description && <p className="text-xs text-gray-400">{task.description}</p>}
                            {task.assignee_name && <p className="text-xs text-primary-600 mt-0.5">المسؤول: {task.assignee_name}</p>}
                            {task.is_completed && task.evaluation_score && (
                              <div className="flex items-center gap-1 mt-1">
                                <StarRating value={task.evaluation_score} />
                                {task.evaluation_notes && <span className="text-xs text-gray-400 mr-2">{task.evaluation_notes}</span>}
                              </div>
                            )}
                          </div>
                          <div className="flex items-center gap-1">
                            {!task.is_completed && (
                              <>
                                <button onClick={() => setEditTaskModal({ ...task, assigned_to: task.assigned_to || '', priority: task.priority || 'normal' })}
                                  className="p-1.5 rounded-lg hover:bg-blue-50 text-blue-500" title="تعديل المهمة">
                                  <Pencil className="w-4 h-4" />
                                </button>
                                <button onClick={() => setCompleteModal({ open: true, taskId: task.id, score: 0, notes: '' })}
                                  className="p-1.5 rounded-lg hover:bg-green-50 text-green-500" title="إتمام المهمة">
                                  <CheckCircle className="w-4 h-4" />
                                </button>
                              </>
                            )}
                            <button onClick={() => handleDeleteTask(task.id)} className="p-1.5 rounded-lg hover:bg-red-50 text-red-500">
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
        {filtered.length === 0 && <p className="text-gray-400 text-center py-12">لا توجد خطط عمل</p>}
      </div>

      {/* Add/Edit Plan Modal */}
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editItem ? 'تعديل خطة العمل' : 'خطة عمل جديدة'} size="lg">
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">عنوان الخطة *</label>
              <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="عنوان خطة العمل" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">نوع الخطة *</label>
              <select value={form.plan_type} onChange={(e) => setForm({ ...form, plan_type: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
                <option value="daily">يومي</option>
                <option value="monthly">شهري</option>
                <option value="yearly">سنوي</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">تاريخ الخطة *</label>
              <Input type="date" value={form.plan_date} onChange={(e) => setForm({ ...form, plan_date: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">الشركة</label>
              <select value={form.company_id} onChange={(e) => setForm({ ...form, company_id: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
                <option value="">اختر الشركة</option>
                {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">المنطقة</label>
              <select value={form.region_id} onChange={(e) => setForm({ ...form, region_id: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
                <option value="">اختر المنطقة</option>
                {regions.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">الموقع</label>
              <select value={form.location_id} onChange={(e) => setForm({ ...form, location_id: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
                <option value="">اختر الموقع</option>
                {locations.filter((l: any) => !form.region_id || l.region_id === Number(form.region_id)).map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">المكلف</label>
              <select value={form.assigned_to} onChange={(e) => setForm({ ...form, assigned_to: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
                <option value="">اختر الموظف</option>
                {employees.map((e) => <option key={e.id} value={e.id}>{e.name} — {e.job_title || ''}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">الوصف</label>
            <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="w-full h-20 px-3 py-2 rounded-lg border-2 border-gray-200 text-sm focus:border-primary-500 outline-none resize-none" placeholder="وصف خطة العمل" />
          </div>

          {/* Tasks */}
          <div className="border-t pt-4">
            <h4 className="font-medium text-sm mb-3">المهام الأولية (يمكن إضافة المزيد لاحقاً)</h4>
            <div className="space-y-2">
              {form.tasks.map((task, idx) => (
                <div key={idx} className="flex gap-2 items-start">
                  <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <Input value={task.title} onChange={(e) => {
                      const newTasks = [...form.tasks];
                      newTasks[idx].title = e.target.value;
                      setForm({ ...form, tasks: newTasks });
                    }} placeholder={`مهمة ${idx + 1}`} />
                    <select value={task.assigned_to || ''} onChange={(e) => {
                      const newTasks = [...form.tasks];
                      newTasks[idx].assigned_to = e.target.value;
                      setForm({ ...form, tasks: newTasks });
                    }} className="h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
                      <option value="">بدون مسؤول</option>
                      {employees.map((emp) => <option key={emp.id} value={emp.id}>{emp.name}</option>)}
                    </select>
                  </div>
                  {form.tasks.length > 1 && (
                    <button onClick={() => setForm({ ...form, tasks: form.tasks.filter((_, i) => i !== idx) })} className="p-2 text-red-500 hover:bg-red-50 rounded-lg mt-0">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
              <button onClick={() => setForm({ ...form, tasks: [...form.tasks, { title: '', description: '', assigned_to: '', priority: 'normal' }] })} className="text-sm text-primary-600 hover:underline flex items-center gap-1">
                <Plus className="w-4 h-4" /> إضافة مهمة
              </button>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setModalOpen(false)}>إلغاء</Button>
            <Button onClick={handleSave} disabled={saving || !form.title}>{saving ? 'جاري الحفظ...' : editItem ? 'تحديث الخطة' : 'حفظ الخطة'}</Button>
          </div>
        </div>
      </Modal>

      {/* Add Task Modal */}
      <Modal open={taskModal.open} onClose={() => setTaskModal({ open: false, planId: 0 })} title="إضافة مهمة">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">عنوان المهمة *</label>
            <Input value={taskForm.title} onChange={(e) => setTaskForm({ ...taskForm, title: e.target.value })} placeholder="عنوان المهمة" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">الوصف</label>
            <textarea value={taskForm.description} onChange={(e) => setTaskForm({ ...taskForm, description: e.target.value })} className="w-full h-20 px-3 py-2 rounded-lg border-2 border-gray-200 text-sm focus:border-primary-500 outline-none resize-none" placeholder="وصف المهمة" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">المسؤول</label>
              <select value={taskForm.assigned_to} onChange={(e) => setTaskForm({ ...taskForm, assigned_to: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
                <option value="">اختر المسؤول</option>
                {employees.map((emp) => <option key={emp.id} value={emp.id}>{emp.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">الأولوية</label>
              <select value={taskForm.priority} onChange={(e) => setTaskForm({ ...taskForm, priority: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
                <option value="low">منخفضة</option>
                <option value="normal">عادية</option>
                <option value="high">مهمة</option>
                <option value="urgent">عاجلة</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setTaskModal({ open: false, planId: 0 })}>إلغاء</Button>
            <Button onClick={handleAddTask} disabled={saving || !taskForm.title}>{saving ? 'جاري الإضافة...' : 'إضافة'}</Button>
          </div>
        </div>
      </Modal>

      {/* Edit Task Modal */}
      <Modal open={!!editTaskModal} onClose={() => setEditTaskModal(null)} title="تعديل المهمة">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">عنوان المهمة *</label>
            <Input value={editTaskModal?.title || ''} onChange={(e) => setEditTaskModal({ ...editTaskModal, title: e.target.value })} placeholder="عنوان المهمة" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">الوصف</label>
            <textarea value={editTaskModal?.description || ''} onChange={(e) => setEditTaskModal({ ...editTaskModal, description: e.target.value })} className="w-full h-20 px-3 py-2 rounded-lg border-2 border-gray-200 text-sm focus:border-primary-500 outline-none resize-none" placeholder="وصف المهمة" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">المسؤول</label>
              <select value={editTaskModal?.assigned_to || ''} onChange={(e) => setEditTaskModal({ ...editTaskModal, assigned_to: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
                <option value="">اختر المسؤول</option>
                {employees.map((emp) => <option key={emp.id} value={emp.id}>{emp.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">الأولوية</label>
              <select value={editTaskModal?.priority || 'normal'} onChange={(e) => setEditTaskModal({ ...editTaskModal, priority: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
                <option value="low">منخفضة</option>
                <option value="normal">عادية</option>
                <option value="high">مهمة</option>
                <option value="urgent">عاجلة</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setEditTaskModal(null)}>إلغاء</Button>
            <Button onClick={handleEditTask} disabled={saving}>{saving ? 'جاري الحفظ...' : 'حفظ التعديلات'}</Button>
          </div>
        </div>
      </Modal>

      {/* Complete Task Modal */}
      <Modal open={completeModal.open} onClose={() => setCompleteModal({ open: false, taskId: 0, score: 0, notes: '' })} title="إتمام المهمة وتقييمها">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">تقييم الأداء (0-5 نجوم)</label>
            <StarRating value={completeModal.score} onChange={(v) => setCompleteModal({ ...completeModal, score: v })} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">ملاحظات</label>
            <textarea value={completeModal.notes} onChange={(e) => setCompleteModal({ ...completeModal, notes: e.target.value })} className="w-full h-20 px-3 py-2 rounded-lg border-2 border-gray-200 text-sm focus:border-primary-500 outline-none resize-none" placeholder="ملاحظات على إتمام المهمة" />
          </div>
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setCompleteModal({ open: false, taskId: 0, score: 0, notes: '' })}>إلغاء</Button>
            <Button onClick={handleCompleteTask} disabled={saving || completeModal.score === 0}>{saving ? 'جاري الحفظ...' : 'إتمام وتقييم'}</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
