import { useState, useEffect } from 'react';
import { Plus, Trash2, Calendar, CheckCircle, Clock, AlertCircle, ListTodo, ChevronDown, ChevronUp, Edit, Pencil, Lock, FileText, X, ClipboardList, BarChart3 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Modal } from '@/components/ui/modal';
import { MobileSelect } from '@/components/ui/select';
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

  const [logModal, setLogModal] = useState<{ open: boolean; taskId: number }>({ open: false, taskId: 0 });
  const [logForm, setLogForm] = useState({ log_date: new Date().toISOString().split('T')[0], completed_work: '', progress_percent: 0, notes: '', employee_id: '' });
  const [taskLogsModal, setTaskLogsModal] = useState<{ open: boolean; task: any }>({ open: false, task: null });
  const [taskLogs, setTaskLogs] = useState<any[]>([]);
  const [closeModal, setCloseModal] = useState<{ open: boolean; planId: number }>({ open: false, planId: 0 });
  const [closeNotes, setCloseNotes] = useState('');
  const [evalModal, setEvalModal] = useState<{ open: boolean; data: any }>({ open: false, data: null });

  const [form, setForm] = useState({
    title: '', description: '', plan_type: 'daily', company_id: '', region_id: '',
    location_id: '', plan_date: new Date().toISOString().split('T')[0], assigned_to: '',
    tasks: [{ title: '', description: '', assigned_to: '', priority: 'normal', start_date: '', end_date: '', region_id: '' }],
  });
  const [taskForm, setTaskForm] = useState({ title: '', description: '', assigned_to: '', priority: 'normal', start_date: '', end_date: '', region_id: '' });

  const loadData = async () => {
    setLoading(true);
    try {
      const [pRes, eRes, cRes, rRes, lRes] = await Promise.allSettled([
        api.get('/work-plans'),
        api.get('/employees'),
        api.get('/companies'),
        api.get('/regions'),
        api.get('/locations'),
      ]);
      if (pRes.status === 'fulfilled') setPlans(pRes.value.data.data || []);
      if (eRes.status === 'fulfilled') setEmployees(eRes.value.data.data || []);
      if (cRes.status === 'fulfilled') setCompanies(cRes.value.data.data || []);
      if (rRes.status === 'fulfilled') setRegions(rRes.value.data.data || []);
      if (lRes.status === 'fulfilled') setLocations(lRes.value.data.data || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { loadData(); }, []);

  const openAdd = () => {
    setEditItem(null);
    setForm({
      title: '', description: '', plan_type: 'daily', company_id: '', region_id: '',
      location_id: '', plan_date: new Date().toISOString().split('T')[0], assigned_to: '',
      tasks: [{ title: '', description: '', assigned_to: '', priority: 'normal', start_date: '', end_date: '', region_id: '' }],
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
      tasks: plan.tasks?.length > 0 ? plan.tasks.map((t: any) => ({
        title: t.title, description: t.description || '', assigned_to: t.assigned_to || '', priority: t.priority || 'normal',
        start_date: t.start_date || '', end_date: t.end_date || '', region_id: t.region_id || '',
      })) : [{ title: '', description: '', assigned_to: '', priority: 'normal', start_date: '', end_date: '', region_id: '' }],
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
          region_id: t.region_id ? Number(t.region_id) : null,
          start_date: t.start_date || null,
          end_date: t.end_date || null,
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
        region_id: taskForm.region_id ? Number(taskForm.region_id) : null,
      });
      setTaskModal({ open: false, planId: 0 });
      setTaskForm({ title: '', description: '', assigned_to: '', priority: 'normal', start_date: '', end_date: '', region_id: '' });
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
        start_date: editTaskModal.start_date || null,
        end_date: editTaskModal.end_date || null,
        region_id: editTaskModal.region_id ? Number(editTaskModal.region_id) : null,
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

  const handleAddLog = async () => {
    if (!logForm.completed_work.trim()) return alert('أدخل الأعمال المنجزة');
    setSaving(true);
    try {
      await api.post(`/work-plans/tasks/${logModal.taskId}/logs`, {
        ...logForm,
        progress_percent: Number(logForm.progress_percent),
        employee_id: logForm.employee_id ? Number(logForm.employee_id) : null,
      });
      setLogModal({ open: false, taskId: 0 });
      setLogForm({ log_date: new Date().toISOString().split('T')[0], completed_work: '', progress_percent: 0, notes: '', employee_id: '' });
      loadData();
    } catch (err: any) { alert(err.response?.data?.message || 'حدث خطأ'); }
    finally { setSaving(false); }
  };

  const loadTaskLogs = async (task: any) => {
    try {
      const res = await api.get(`/work-plans/tasks/${task.id}/logs`);
      setTaskLogs(res.data.data || []);
      setTaskLogsModal({ open: true, task });
    } catch (err) { alert('خطأ في تحميل السجلات'); }
  };

  const handleDeleteLog = async (logId: number) => {
    if (!confirm('هل أنت متأكد من حذف السجل؟')) return;
    await api.delete(`/work-plans/tasks/logs/${logId}`);
    setTaskLogs(taskLogs.filter((l: any) => l.id !== logId));
  };

  const handleClosePlan = async () => {
    setSaving(true);
    try {
      await api.post(`/work-plans/${closeModal.planId}/close`, { close_notes: closeNotes });
      setCloseModal({ open: false, planId: 0 });
      setCloseNotes('');
      loadData();
    } catch (err: any) { alert(err.response?.data?.message || 'حدث خطأ'); }
    finally { setSaving(false); }
  };

  const loadEvaluation = async (planId: number) => {
    try {
      const res = await api.get(`/work-plans/${planId}/evaluation`);
      setEvalModal({ open: true, data: res.data.data });
    } catch (err) { alert('خطأ في تحميل التقييم'); }
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
    closed: plans.filter(p => p.status === 'closed').length,
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
          <p className="text-gray-500 text-sm mt-1">اليومية والشهرية والسنوية — تسجيل الأعمال اليومية والتقييم</p>
        </div>
        <Button onClick={openAdd}><Plus className="w-4 h-4" /> خطة جديدة</Button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {[
          { label: 'الكل', value: stats.total, color: 'bg-gray-100 text-gray-700', icon: ListTodo },
          { label: 'قيد الانتظار', value: stats.pending, color: 'bg-amber-100 text-amber-700', icon: Clock },
          { label: 'قيد التنفيذ', value: stats.in_progress, color: 'bg-blue-100 text-blue-700', icon: AlertCircle },
          { label: 'مكتملة', value: stats.completed, color: 'bg-green-100 text-green-700', icon: CheckCircle },
          { label: 'مغلقة', value: stats.closed, color: 'bg-purple-100 text-purple-700', icon: Lock },
        ].map((s) => (
          <Card key={s.label}><CardContent className="p-3">
            <div className="flex items-center gap-2">
              <div className={`w-9 h-9 rounded-xl ${s.color} flex items-center justify-center`}>
                <s.icon className="w-4 h-4" />
              </div>
              <div>
                <p className="text-xl font-bold">{s.value}</p>
                <p className="text-[10px] text-gray-500">{s.label}</p>
              </div>
            </div>
          </CardContent></Card>
        ))}
      </div>

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

      <div className="space-y-4">
        {filtered.map((plan) => {
          const isExpanded = expandedId === plan.id;
          const tasks = plan.tasks || [];
          const isLocked = plan.is_locked || plan.status === 'closed';
          return (
            <Card key={plan.id} className={`hover:shadow-md transition-shadow ${isLocked ? 'border-purple-200 bg-purple-50/30' : ''}`}>
              <CardContent className="p-5">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-2">
                      <h3 className="font-bold text-gray-900">{plan.title}</h3>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        plan.plan_type === 'daily' ? 'bg-blue-100 text-blue-700' :
                        plan.plan_type === 'monthly' ? 'bg-purple-100 text-purple-700' :
                        'bg-amber-100 text-amber-700'
                      }`}>{plan.plan_type_name}</span>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        plan.status === 'completed' ? 'bg-green-100 text-green-700' :
                        plan.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                        plan.status === 'closed' ? 'bg-purple-100 text-purple-700' :
                        plan.status === 'cancelled' ? 'bg-red-100 text-red-700' :
                        'bg-gray-100 text-gray-600'
                      }`}>{plan.status_name}</span>
                      {isLocked && <Lock className="w-3.5 h-3.5 text-purple-500" />}
                    </div>
                    {plan.description && <p className="text-sm text-gray-500 mb-2">{plan.description}</p>}
                    <div className="flex items-center gap-3 text-xs text-gray-400 flex-wrap">
                      <span className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5" /> {plan.plan_date}</span>
                      {plan.due_date && <span>الإنجاز: {plan.due_date}</span>}
                      {plan.assignee_name && <span>المكلف: {plan.assignee_name}</span>}
                      {plan.company_name && <span>{plan.company_name}</span>}
                      {plan.region_name && <span>{plan.region_name}</span>}
                      {tasks.length > 0 && <span className="flex items-center gap-1"><ListTodo className="w-3.5 h-3.5" /> {plan.completed_tasks || 0}/{tasks.length}</span>}
                    </div>
                    {isLocked && plan.close_notes && <p className="text-xs text-purple-600 mt-1">ملاحظات الإغلاق: {plan.close_notes}</p>}
                  </div>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    <div className="text-center">
                      <div className={`w-11 h-11 rounded-full flex items-center justify-center ${
                        plan.progress >= 100 ? 'bg-green-100' : plan.progress > 0 ? 'bg-primary-50' : 'bg-gray-100'
                      }`}>
                        <span className={`text-sm font-bold ${plan.progress >= 100 ? 'text-green-600' : plan.progress > 0 ? 'text-primary-600' : 'text-gray-400'}`}>{plan.progress}%</span>
                      </div>
                    </div>
                    <button onClick={() => setExpandedId(isExpanded ? null : plan.id)} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500">
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                    {!isLocked && (
                      <>
                        <button onClick={() => setTaskModal({ open: true, planId: plan.id })} className="p-1.5 rounded-lg hover:bg-blue-50 text-blue-500" title="إضافة مهمة">
                          <Plus className="w-4 h-4" />
                        </button>
                        <button onClick={() => openEdit(plan)} className="p-1.5 rounded-lg hover:bg-amber-50 text-amber-500" title="تعديل">
                          <Pencil className="w-4 h-4" />
                        </button>
                      </>
                    )}
                    <button onClick={() => loadEvaluation(plan.id)} className="p-1.5 rounded-lg hover:bg-indigo-50 text-indigo-500" title="تقييم">
                      <BarChart3 className="w-4 h-4" />
                    </button>
                    {!isLocked && plan.status !== 'completed' && (
                      <button onClick={() => setCloseModal({ open: true, planId: plan.id })} className="p-1.5 rounded-lg hover:bg-purple-50 text-purple-500" title="إغلاق الخطة">
                        <Lock className="w-4 h-4" />
                      </button>
                    )}
                    {!isLocked && (
                      <button onClick={() => handleDeletePlan(plan.id)} className="p-1.5 rounded-lg hover:bg-red-50 text-red-500" title="حذف">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>

                <div className="mt-3 h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full transition-all ${
                    plan.progress >= 100 ? 'bg-green-500' : plan.progress > 0 ? 'bg-primary-500' : 'bg-gray-300'
                  }`} style={{ width: `${plan.progress}%` }} />
                </div>

                {isExpanded && (
                  <div className="mt-4 space-y-2">
                    {tasks.length === 0 ? (
                      <p className="text-sm text-gray-400 text-center py-4">لا توجد مهام بعد</p>
                    ) : (
                      tasks.map((task: any) => (
                        <div key={task.id} className={`p-3 rounded-lg border ${
                          task.is_completed ? 'bg-green-50 border-green-200' : 'bg-white border-gray-200'
                        }`}>
                          <div className="flex items-start gap-3">
                            <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${
                              task.is_completed ? 'bg-green-500 text-white' : 'bg-gray-200'
                            }`}>
                              {task.is_completed ? <CheckCircle className="w-4 h-4" /> : <span className="text-xs font-bold">{task.order + 1}</span>}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className={`text-sm font-medium ${task.is_completed ? 'line-through text-gray-400' : ''}`}>{task.title}</span>
                                {task.priority && task.priority !== 'normal' && (
                                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                    task.priority === 'urgent' ? 'bg-red-100 text-red-700' :
                                    task.priority === 'high' ? 'bg-orange-100 text-orange-700' :
                                    'bg-gray-100 text-gray-500'
                                  }`}>
                                    {task.priority === 'urgent' ? 'عاجل' : task.priority === 'high' ? 'مهم' : 'منخفض'}
                                  </span>
                                )}
                              </div>
                              {task.description && <p className="text-xs text-gray-400 mt-0.5">{task.description}</p>}
                              <div className="flex items-center gap-3 text-[11px] text-gray-400 mt-1 flex-wrap">
                                {task.assignee_name && <span>المسؤول: {task.assignee_name}</span>}
                                {task.region_name && <span>المنطقة: {task.region_name}</span>}
                                {task.start_date && task.end_date && <span>{task.start_date} ← {task.end_date}</span>}
                                {task.progress_percent > 0 && <span className="font-medium text-primary-600">{task.progress_percent}%</span>}
                              </div>
                              {task.is_completed && task.evaluation_score && (
                                <div className="flex items-center gap-1 mt-1">
                                  <StarRating value={task.evaluation_score} />
                                  {task.evaluation_notes && <span className="text-xs text-gray-400 mr-2">{task.evaluation_notes}</span>}
                                </div>
                              )}
                              {task.logs_count > 0 && (
                                <span className="text-[11px] text-blue-500 mt-1 block">{task.logs_count} سجل عمل</span>
                              )}
                            </div>
                            <div className="flex items-center gap-1 flex-shrink-0">
                              {!isLocked && !task.is_completed && (
                                <>
                                  <button onClick={() => setEditTaskModal({ ...task, assigned_to: task.assigned_to || '', priority: task.priority || 'normal', region_id: task.region_id || '' })}
                                    className="p-1.5 rounded-lg hover:bg-blue-50 text-blue-500" title="تعديل">
                                    <Pencil className="w-4 h-4" />
                                  </button>
                                  <button onClick={() => setLogModal({ open: true, taskId: task.id })} className="p-1.5 rounded-lg hover:bg-amber-50 text-amber-500" title="تسجيل عمل يومي">
                                    <ClipboardList className="w-4 h-4" />
                                  </button>
                                  <button onClick={() => setCompleteModal({ open: true, taskId: task.id, score: 0, notes: '' })} className="p-1.5 rounded-lg hover:bg-green-50 text-green-500" title="إتمام وتقييم">
                                    <CheckCircle className="w-4 h-4" />
                                  </button>
                                </>
                              )}
                              <button onClick={() => loadTaskLogs(task)} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500" title="السجلات">
                                <FileText className="w-4 h-4" />
                              </button>
                              {!isLocked && (
                                <button onClick={() => handleDeleteTask(task.id)} className="p-1.5 rounded-lg hover:bg-red-50 text-red-500" title="حذف">
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              )}
                            </div>
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
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="sm:col-span-2">
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
              <MobileSelect value={form.company_id} onChange={(v) => setForm({ ...form, company_id: v })}
                options={companies.map((c) => ({ value: c.id, label: c.name }))} placeholder="اختر الشركة" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">المنطقة</label>
              <MobileSelect value={form.region_id} onChange={(v) => setForm({ ...form, region_id: v })}
                options={regions.map((r) => ({ value: r.id, label: r.name }))} placeholder="اختر المنطقة" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">الموقع</label>
              <MobileSelect value={form.location_id} onChange={(v) => setForm({ ...form, location_id: v })}
                options={locations.filter((l: any) => !form.region_id || l.region_id === Number(form.region_id)).map((l) => ({ value: l.id, label: l.name }))} placeholder="اختر الموقع" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">المكلف</label>
              <MobileSelect value={form.assigned_to} onChange={(v) => setForm({ ...form, assigned_to: v })}
                options={employees.map((e) => ({ value: e.id, label: `${e.name} — ${e.job_title || ''}` }))} placeholder="اختر الموظف" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">الوصف</label>
            <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="w-full h-20 px-3 py-2 rounded-lg border-2 border-gray-200 text-sm focus:border-primary-500 outline-none resize-none" placeholder="وصف خطة العمل" />
          </div>

          <div className="border-t pt-4">
            <h4 className="font-medium text-sm mb-3">المهام الأولية</h4>
            <div className="space-y-3">
              {form.tasks.map((task, idx) => (
                <div key={idx} className="p-3 bg-gray-50 rounded-lg border border-gray-200 space-y-2">
                  <div className="flex gap-2 items-start">
                    <Input value={task.title} onChange={(e) => {
                      const newTasks = [...form.tasks];
                      newTasks[idx].title = e.target.value;
                      setForm({ ...form, tasks: newTasks });
                    }} placeholder={`مهمة ${idx + 1}`} className="flex-1" />
                    {form.tasks.length > 1 && (
                      <button onClick={() => setForm({ ...form, tasks: form.tasks.filter((_, i) => i !== idx) })} className="p-2 text-red-500 hover:bg-red-50 rounded-lg">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                    <MobileSelect value={task.assigned_to || ''} onChange={(v) => {
                      const newTasks = [...form.tasks];
                      newTasks[idx].assigned_to = v;
                      setForm({ ...form, tasks: newTasks });
                    }}
                      options={employees.map((emp) => ({ value: emp.id, label: emp.name }))} placeholder="بدون مسؤول" />
                    <Input type="date" value={task.start_date || ''} onChange={(e) => {
                      const newTasks = [...form.tasks];
                      newTasks[idx].start_date = e.target.value;
                      setForm({ ...form, tasks: newTasks });
                    }} />
                    <Input type="date" value={task.end_date || ''} onChange={(e) => {
                      const newTasks = [...form.tasks];
                      newTasks[idx].end_date = e.target.value;
                      setForm({ ...form, tasks: newTasks });
                    }} />
                  </div>
                </div>
              ))}
              <button onClick={() => setForm({ ...form, tasks: [...form.tasks, { title: '', description: '', assigned_to: '', priority: 'normal', start_date: '', end_date: '', region_id: '' }] })} className="text-sm text-primary-600 hover:underline flex items-center gap-1">
                <Plus className="w-4 h-4" /> إضافة مهمة
              </button>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setModalOpen(false)}>إلغاء</Button>
            <Button onClick={handleSave} disabled={saving || !form.title}>{saving ? 'جاري الحفظ...' : editItem ? 'تحديث' : 'حفظ'}</Button>
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
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">المسؤول</label>
              <MobileSelect value={taskForm.assigned_to} onChange={(v) => setTaskForm({ ...taskForm, assigned_to: v })}
                options={employees.map((emp) => ({ value: emp.id, label: emp.name }))} placeholder="اختر المسؤول" />
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
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">من تاريخ</label>
              <Input type="date" value={taskForm.start_date} onChange={(e) => setTaskForm({ ...taskForm, start_date: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">إلى تاريخ</label>
              <Input type="date" value={taskForm.end_date} onChange={(e) => setTaskForm({ ...taskForm, end_date: e.target.value })} />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">المنطقة</label>
              <MobileSelect value={taskForm.region_id} onChange={(v) => setTaskForm({ ...taskForm, region_id: v })}
                options={regions.map((r) => ({ value: r.id, label: r.name }))} placeholder="اختر المنطقة" />
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
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">المسؤول</label>
              <MobileSelect value={editTaskModal?.assigned_to || ''} onChange={(v) => setEditTaskModal({ ...editTaskModal, assigned_to: v })}
                options={employees.map((emp) => ({ value: emp.id, label: emp.name }))} placeholder="اختر المسؤول" />
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
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">من تاريخ</label>
              <Input type="date" value={editTaskModal?.start_date || ''} onChange={(e) => setEditTaskModal({ ...editTaskModal, start_date: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">إلى تاريخ</label>
              <Input type="date" value={editTaskModal?.end_date || ''} onChange={(e) => setEditTaskModal({ ...editTaskModal, end_date: e.target.value })} />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">المنطقة</label>
              <MobileSelect value={editTaskModal?.region_id || ''} onChange={(v) => setEditTaskModal({ ...editTaskModal, region_id: v })}
                options={regions.map((r) => ({ value: r.id, label: r.name }))} placeholder="اختر المنطقة" />
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

      {/* Daily Work Log Modal */}
      <Modal open={logModal.open} onClose={() => setLogModal({ open: false, taskId: 0 })} title="تسجيل عمل يومي">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">التاريخ *</label>
            <Input type="date" value={logForm.log_date} onChange={(e) => setLogForm({ ...logForm, log_date: e.target.value })} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">الأعمال المنجزة *</label>
            <textarea value={logForm.completed_work} onChange={(e) => setLogForm({ ...logForm, completed_work: e.target.value })}
              className="w-full h-24 px-3 py-2 rounded-lg border-2 border-gray-200 text-sm focus:border-primary-500 outline-none resize-none"
              placeholder="اكتب الأعمال التي تم إنجازها اليوم..." />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">نسبة الإنجاز {logForm.progress_percent}%</label>
            <input type="range" min="0" max="100" value={logForm.progress_percent}
              onChange={(e) => setLogForm({ ...logForm, progress_percent: Number(e.target.value) })}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary-500" />
            <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
              <span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">ملاحظات</label>
            <textarea value={logForm.notes} onChange={(e) => setLogForm({ ...logForm, notes: e.target.value })}
              className="w-full h-16 px-3 py-2 rounded-lg border-2 border-gray-200 text-sm focus:border-primary-500 outline-none resize-none"
              placeholder="ملاحظات إضافية..." />
          </div>
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setLogModal({ open: false, taskId: 0 })}>إلغاء</Button>
            <Button onClick={handleAddLog} disabled={saving || !logForm.completed_work.trim()}>{saving ? 'جاري الحفظ...' : 'حفظ السجل'}</Button>
          </div>
        </div>
      </Modal>

      {/* Task Logs Modal */}
      <Modal open={taskLogsModal.open} onClose={() => setTaskLogsModal({ open: false, task: null })} title={`سجلات العمل — ${taskLogsModal.task?.title || ''}`} size="lg">
        <div className="space-y-3">
          {taskLogs.length === 0 ? (
            <p className="text-gray-400 text-center py-6">لا توجد سجلات عمل بعد</p>
          ) : taskLogs.map((log: any) => (
            <div key={log.id} className="p-3 bg-gray-50 rounded-lg border border-gray-200">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-bold text-primary-600 bg-primary-50 px-2 py-0.5 rounded">{log.log_date}</span>
                    <span className="text-xs font-bold text-blue-600">{log.progress_percent}%</span>
                    {log.employee_name && <span className="text-xs text-gray-500">— {log.employee_name}</span>}
                  </div>
                  <p className="text-sm text-gray-700">{log.completed_work}</p>
                  {log.notes && <p className="text-xs text-gray-400 mt-1">{log.notes}</p>}
                </div>
                <button onClick={() => handleDeleteLog(log.id)} className="p-1 rounded hover:bg-red-50 text-red-400">
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </Modal>

      {/* Close Plan Modal */}
      <Modal open={closeModal.open} onClose={() => setCloseModal({ open: false, planId: 0 })} title="إغلاق خطة العمل">
        <div className="space-y-4">
          <p className="text-sm text-gray-600">هل أنت متأكد من إغلاق هذه الخطة؟ لن يمكن بعدها تعديلها أو إضافة مهام.</p>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">ملاحظات الإغلاق</label>
            <textarea value={closeNotes} onChange={(e) => setCloseNotes(e.target.value)}
              className="w-full h-20 px-3 py-2 rounded-lg border-2 border-gray-200 text-sm focus:border-primary-500 outline-none resize-none"
              placeholder="ملاحظات عند الإغلاق..." />
          </div>
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setCloseModal({ open: false, planId: 0 })}>إلغاء</Button>
            <Button onClick={handleClosePlan} disabled={saving} className="bg-purple-600 hover:bg-purple-700">{saving ? 'جاري الإغلاق...' : 'إغلاق الخطة'}</Button>
          </div>
        </div>
      </Modal>

      {/* Evaluation Summary Modal */}
      <Modal open={evalModal.open} onClose={() => setEvalModal({ open: false, data: null })} title="ملخص التقييم" size="lg">
        {evalModal.data && (
          <div className="space-y-6">
            <div>
              <h4 className="font-bold text-sm text-gray-700 mb-3">تقييم حسب العمال</h4>
              {evalModal.data.by_employee?.length === 0 ? (
                <p className="text-gray-400 text-sm text-center py-4">لا توجد بيانات تقييم</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead><tr className="bg-gray-50 border-b">
                      <th className="px-3 py-2 text-right text-xs font-semibold">العامل</th>
                      <th className="px-3 py-2 text-right text-xs font-semibold">المنطقة</th>
                      <th className="px-3 py-2 text-center text-xs font-semibold">المهام</th>
                      <th className="px-3 py-2 text-center text-xs font-semibold">المكتملة</th>
                      <th className="px-3 py-2 text-center text-xs font-semibold">الإنجاز</th>
                      <th className="px-3 py-2 text-center text-xs font-semibold">التقييم</th>
                    </tr></thead>
                    <tbody className="divide-y divide-gray-100">
                      {evalModal.data.by_employee.map((emp: any, i: number) => (
                        <tr key={i} className="hover:bg-gray-50">
                          <td className="px-3 py-2 font-medium">{emp.name}</td>
                          <td className="px-3 py-2 text-gray-500">{emp.region || '—'}</td>
                          <td className="px-3 py-2 text-center">{emp.tasks_total}</td>
                          <td className="px-3 py-2 text-center">{emp.tasks_completed}</td>
                          <td className="px-3 py-2 text-center">
                            <span className={`font-bold ${emp.avg_progress >= 80 ? 'text-green-600' : emp.avg_progress >= 50 ? 'text-amber-600' : 'text-red-600'}`}>
                              {emp.avg_progress}%
                            </span>
                          </td>
                          <td className="px-3 py-2 text-center">
                            {emp.avg_score > 0 ? (
                              <span className="inline-flex items-center gap-1">
                                <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
                                <span className="font-bold">{emp.avg_score}</span>
                              </span>
                            ) : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="border-t pt-4">
              <h4 className="font-bold text-sm text-gray-700 mb-3">تقييم حسب المناطق</h4>
              {evalModal.data.by_region?.length === 0 ? (
                <p className="text-gray-400 text-sm text-center py-4">لا توجد بيانات مناطق</p>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {evalModal.data.by_region.map((region: any, i: number) => (
                    <div key={i} className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                      <h5 className="font-bold text-sm text-gray-800 mb-2">{region.region}</h5>
                      <div className="space-y-1 text-xs text-gray-600">
                        <div className="flex justify-between"><span>العمال:</span><span className="font-bold">{region.employees_count}</span></div>
                        <div className="flex justify-between"><span>المهام:</span><span className="font-bold">{region.tasks_completed}/{region.tasks_total}</span></div>
                        <div className="flex justify-between"><span>الإنجاز:</span>
                          <span className={`font-bold ${region.completion_pct >= 80 ? 'text-green-600' : region.completion_pct >= 50 ? 'text-amber-600' : 'text-red-600'}`}>
                            {region.completion_pct}%
                          </span>
                        </div>
                        {region.avg_score > 0 && (
                          <div className="flex justify-between"><span>التقييم:</span>
                            <span className="font-bold flex items-center gap-1">
                              <Star className="w-3 h-3 fill-amber-400 text-amber-400" />{region.avg_score}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
