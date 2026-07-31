import { useState, useEffect } from 'react';
import { Plus, Search, DollarSign, Trash2, Edit3, Eye, Package, Users, CreditCard, BarChart3, Filter, X, Check, Clock, Truck, AlertCircle, Printer } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Modal } from '@/components/ui/modal';
import { formatNum } from '@/lib/utils';
import api from '@/api/client';

type Tab = 'orders' | 'customers' | 'payments' | 'reports';

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-amber-100 text-amber-700',
  confirmed: 'bg-blue-100 text-blue-700',
  delivered: 'bg-green-100 text-green-700',
  cancelled: 'bg-red-100 text-red-700',
};

const PAYMENT_METHODS = [
  { value: 'cash', label: 'نقدي' },
  { value: 'bank', label: 'تحويل بنكي' },
  { value: 'transfer', label: 'تحويل' },
  { value: 'credit', label: 'آجل' },
];

const emptyOrder = {
  customer_id: '', order_number: '', order_date: new Date().toISOString().split('T')[0],
  delivery_date: '', status: 'pending', discount: '', tax_rate: '',
  payment_method: 'cash', delivery_address: '', notes: '', initial_payment: '',
  items: [{ product_name: 'المولاس', description: '', quantity: '1', unit: 'طن', unit_price: '' }],
};

const emptyCustomer = {
  name: '', phone: '', secondary_phone: '', address: '', company: '',
  tax_number: '', contact_person: '', credit_limit: '', notes: '',
};

export default function MolasSalesPage() {
  const [tab, setTab] = useState<Tab>('orders');
  const [loading, setLoading] = useState(true);

  const [orders, setOrders] = useState<any[]>([]);
  const [customers, setCustomers] = useState<any[]>([]);
  const [payments, setPayments] = useState<any[]>([]);

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [customerFilter, setCustomerFilter] = useState('');

  const [orderModal, setOrderModal] = useState(false);
  const [editOrder, setEditOrder] = useState<any>(null);
  const [orderForm, setOrderForm] = useState<any>({ ...emptyOrder });

  const [customerModal, setCustomerModal] = useState(false);
  const [editCustomer, setEditCustomer] = useState<any>(null);
  const [customerForm, setCustomerForm] = useState<any>({ ...emptyCustomer });

  const [payModal, setPayModal] = useState<any>(null);
  const [payForm, setPayForm] = useState({ amount: '', payment_method: 'cash', payment_date: new Date().toISOString().split('T')[0], notes: '' });

  const [detailModal, setDetailModal] = useState<any>(null);

  const [reportSummary, setReportSummary] = useState<any>(null);
  const [stmtCustomer, setStmtCustomer] = useState('');
  const [stmtData, setStmtData] = useState<any>(null);

  const [saving, setSaving] = useState(false);

  const loadData = () => {
    setLoading(true);
    const params: any = {};
    if (search) params.search = search;
    if (statusFilter) params.status = statusFilter;
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    if (customerFilter) params.customer_id = customerFilter;

    Promise.allSettled([
      api.get('/molas/orders', { params }),
      api.get('/molas/customers'),
      api.get('/molas/payments', { params: { date_from: dateFrom, date_to: dateTo, customer_id: customerFilter } }),
    ]).then(([oRes, cRes, pRes]) => {
      setOrders(oRes.status === 'fulfilled' ? (oRes.value.data.data || []) : []);
      setCustomers(cRes.status === 'fulfilled' ? (cRes.value.data.data || []) : []);
      setPayments(pRes.status === 'fulfilled' ? (pRes.value.data.data || []) : []);
    }).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, [search, statusFilter, dateFrom, dateTo, customerFilter]);

  const loadReport = () => {
    const params: any = {};
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    api.get('/molas/reports/summary', { params }).then(r => setReportSummary(r.data.data)).catch(console.error);
  };

  const loadStatement = () => {
    if (!stmtCustomer) return;
    api.get('/molas/reports/customer-statement', { params: { customer_id: stmtCustomer } })
      .then(r => setStmtData(r.data.data)).catch(console.error);
  };

  // ---- Order CRUD ----
  const handleOrderSave = async () => {
    setSaving(true);
    try {
      const payload = {
        ...orderForm,
        customer_id: parseInt(orderForm.customer_id),
        discount: parseFloat(orderForm.discount) || 0,
        tax_rate: parseFloat(orderForm.tax_rate) || 0,
        initial_payment: parseFloat(orderForm.initial_payment) || 0,
        items: orderForm.items.map((it: any) => ({
          ...it,
          quantity: parseFloat(it.quantity) || 0,
          unit_price: parseFloat(it.unit_price) || 0,
        })),
      };
      if (editOrder) {
        await api.put(`/molas/orders/${editOrder.id}`, payload);
      } else {
        await api.post('/molas/orders', payload);
      }
      setOrderModal(false);
      setEditOrder(null);
      setOrderForm({ ...emptyOrder });
      loadData();
    } catch (err: any) {
      alert(err.response?.data?.message || 'حدث خطأ');
    } finally { setSaving(false); }
  };

  const handleOrderDelete = async (id: number) => {
    if (!confirm('هل أنت متأكد من حذف الطلب؟')) return;
    try { await api.delete(`/molas/orders/${id}`); loadData(); }
    catch (err: any) { alert(err.response?.data?.message || 'حدث خطأ'); }
  };

  const openEditOrder = (o: any) => {
    setEditOrder(o);
    setOrderForm({
      customer_id: o.customer_id, order_number: o.order_number, order_date: o.order_date,
      delivery_date: o.delivery_date || '', status: o.status,
      discount: o.discount || '', tax_rate: o.tax_rate || '',
      payment_method: o.payment_method, delivery_address: o.delivery_address, notes: o.notes,
      initial_payment: '',
      items: o.items.length > 0 ? o.items.map((it: any) => ({
        product_name: it.product_name, description: it.description,
        quantity: String(it.quantity), unit: it.unit, unit_price: String(it.unit_price),
      })) : [{ product_name: 'المولاس', description: '', quantity: '1', unit: 'طن', unit_price: '' }],
    });
    setOrderModal(true);
  };

  // ---- Customer CRUD ----
  const handleCustomerSave = async () => {
    setSaving(true);
    try {
      const payload = { ...customerForm, credit_limit: parseFloat(customerForm.credit_limit) || 0 };
      if (editCustomer) {
        await api.put(`/molas/customers/${editCustomer.id}`, payload);
      } else {
        await api.post('/molas/customers', payload);
      }
      setCustomerModal(false);
      setEditCustomer(null);
      setCustomerForm({ ...emptyCustomer });
      loadData();
    } catch (err: any) {
      alert(err.response?.data?.message || 'حدث خطأ');
    } finally { setSaving(false); }
  };

  const handleCustomerDelete = async (id: number) => {
    if (!confirm('هل أنت متأكد من حذف العميل؟')) return;
    try { await api.delete(`/molas/customers/${id}`); loadData(); }
    catch (err: any) { alert(err.response?.data?.message || 'حدث خطأ'); }
  };

  // ---- Payment ----
  const handlePaymentSave = async () => {
    if (!payModal) return;
    setSaving(true);
    try {
      await api.post('/molas/payments', {
        order_id: payModal.id,
        amount: parseFloat(payForm.amount) || 0,
        payment_method: payForm.payment_method,
        payment_date: payForm.payment_date,
        notes: payForm.notes,
      });
      setPayModal(null);
      setPayForm({ amount: '', payment_method: 'cash', payment_date: new Date().toISOString().split('T')[0], notes: '' });
      loadData();
    } catch (err: any) {
      alert(err.response?.data?.message || 'حدث خطأ');
    } finally { setSaving(false); }
  };

  // ---- Computed ----
  const totalOrders = orders.reduce((s, o) => s + (o.final_amount || 0), 0);
  const totalPaid = orders.reduce((s, o) => s + (o.paid_amount || 0), 0);
  const totalRemaining = totalOrders - totalPaid;
  const totalTons = orders.filter(o => o.status !== 'cancelled').reduce((s, o) => s + (o.items || []).reduce((ss: number, it: any) => ss + (it.quantity || 0), 0), 0);

  const filteredOrders = orders.filter(o => {
    if (search && !o.order_number?.includes(search) && !o.customer_name?.includes(search)) return false;
    if (statusFilter && o.status !== statusFilter) return false;
    if (customerFilter && o.customer_id !== parseInt(customerFilter)) return false;
    return true;
  });

  const addItem = () => setOrderForm({ ...orderForm, items: [...orderForm.items, { product_name: 'المولاس', description: '', quantity: '1', unit: 'طن', unit_price: '' }] });
  const removeItem = (i: number) => setOrderForm({ ...orderForm, items: orderForm.items.filter((_: any, j: number) => j !== i) });
  const updateItem = (i: number, field: string, val: string) => {
    const items = [...orderForm.items];
    items[i] = { ...items[i], [field]: val };
    setOrderForm({ ...orderForm, items });
  };

  const tabs = [
    { key: 'orders', label: 'طلبات البيع', icon: Package },
    { key: 'customers', label: 'العملاء', icon: Users },
    { key: 'payments', label: 'المدفوعات', icon: CreditCard },
    { key: 'reports', label: 'التقارير', icon: BarChart3 },
  ];

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-8 h-8 border-3 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Package className="w-7 h-7 text-emerald-600" />
            تسويق وبيع المولاس
          </h1>
          <p className="text-sm text-gray-500 mt-1">إدارة طلبات البيع والعملاء والمدفوعات — الأسعار بالدولار والكميات بالطن</p>
        </div>
        {tab === 'orders' && (
          <Button onClick={() => { setEditOrder(null); setOrderForm({ ...emptyOrder }); setOrderModal(true); }} className="bg-emerald-600 hover:bg-emerald-700">
            <Plus className="w-4 h-4" /> طلب جديد
          </Button>
        )}
        {tab === 'customers' && (
          <Button onClick={() => { setEditCustomer(null); setCustomerForm({ ...emptyCustomer }); setCustomerModal(true); }} className="bg-emerald-600 hover:bg-emerald-700">
            <Plus className="w-4 h-4" /> عميل جديد
          </Button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-xl overflow-x-auto">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key as Tab)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all whitespace-nowrap ${
              tab === t.key ? 'bg-white text-emerald-700 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}>
            <t.icon className="w-4 h-4" />
            {t.label}
          </button>
        ))}
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-0 shadow-sm bg-gradient-to-br from-emerald-50 to-white">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-100 flex items-center justify-center"><Package className="w-5 h-5 text-emerald-600" /></div>
              <div>
                <div className="text-2xl font-black text-emerald-700">{orders.length}</div>
                <div className="text-xs text-gray-500">إجمالي الطلبات</div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-0 shadow-sm bg-gradient-to-br from-blue-50 to-white">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center"><DollarSign className="w-5 h-5 text-blue-600" /></div>
              <div>
                <div className="text-2xl font-black text-blue-700">${formatNum(totalOrders)}</div>
                <div className="text-xs text-gray-500">إجمالي القيمة ($)</div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-0 shadow-sm bg-gradient-to-br from-green-50 to-white">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-green-100 flex items-center justify-center"><Check className="w-5 h-5 text-green-600" /></div>
              <div>
                <div className="text-2xl font-black text-green-700">${formatNum(totalPaid)}</div>
                <div className="text-xs text-gray-500">المدفوع ($)</div>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-0 shadow-sm bg-gradient-to-br from-amber-50 to-white">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center"><AlertCircle className="w-5 h-5 text-amber-600" /></div>
              <div>
                <div className="text-2xl font-black text-amber-700">${formatNum(totalRemaining)}</div>
                <div className="text-xs text-gray-500">المتبقي ($)</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ===== ORDERS TAB ===== */}
      {tab === 'orders' && (
        <>
          {/* Filters */}
          <div className="flex flex-wrap gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="بحث برقم الطلب أو اسم العميل..."
                className="w-full h-10 pr-10 pl-4 rounded-xl border border-gray-200 text-sm focus:border-emerald-500 outline-none" />
            </div>
            <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
              className="h-10 px-4 rounded-xl border border-gray-200 text-sm focus:border-emerald-500 outline-none bg-white">
              <option value="">كل الحالات</option>
              <option value="pending">قيد الانتظار</option>
              <option value="confirmed">مؤكد</option>
              <option value="delivered">تم التوصيل</option>
              <option value="cancelled">ملغي</option>
            </select>
            <select value={customerFilter} onChange={e => setCustomerFilter(e.target.value)}
              className="h-10 px-4 rounded-xl border border-gray-200 text-sm focus:border-emerald-500 outline-none bg-white">
              <option value="">كل العملاء</option>
              {customers.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)}
              className="h-10 px-3 rounded-xl border border-gray-200 text-sm focus:border-emerald-500 outline-none" />
            <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)}
              className="h-10 px-3 rounded-xl border border-gray-200 text-sm focus:border-emerald-500 outline-none" />
          </div>

          {/* Orders Table */}
          <Card className="border-0 shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-emerald-600 text-white">
                    <th className="px-4 py-3 text-right font-semibold">رقم الطلب</th>
                    <th className="px-4 py-3 text-right font-semibold">العميل</th>
                    <th className="px-4 py-3 text-right font-semibold">التاريخ</th>
                    <th className="px-4 py-3 text-right font-semibold">الكمية (طن)</th>
                    <th className="px-4 py-3 text-right font-semibold">القيمة ($)</th>
                    <th className="px-4 py-3 text-right font-semibold">المدفوع ($)</th>
                    <th className="px-4 py-3 text-right font-semibold">المتبقي ($)</th>
                    <th className="px-4 py-3 text-right font-semibold">الحالة</th>
                    <th className="px-4 py-3 text-center font-semibold">إجراءات</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredOrders.length === 0 ? (
                    <tr><td colSpan={9} className="px-4 py-12 text-center text-gray-400">لا توجد طلبات</td></tr>
                  ) : filteredOrders.map(o => (
                    <tr key={o.id} className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors">
                      <td className="px-4 py-3 font-bold text-emerald-700">{o.order_number}</td>
                      <td className="px-4 py-3">{o.customer_name}</td>
                      <td className="px-4 py-3 text-gray-500">{o.order_date}</td>
                      <td className="px-4 py-3 font-semibold">{(o.items || []).reduce((s: number, it: any) => s + (it.quantity || 0), 0).toFixed(1)} طن</td>
                      <td className="px-4 py-3 font-bold">${formatNum(o.final_amount)}</td>
                      <td className="px-4 py-3 text-green-600 font-semibold">${formatNum(o.paid_amount)}</td>
                      <td className="px-4 py-3 text-amber-600 font-semibold">${formatNum(o.remaining_amount)}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${STATUS_COLORS[o.status] || 'bg-gray-100 text-gray-600'}`}>
                          {o.status_name}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-center gap-1">
                          <button onClick={() => setDetailModal(o)} className="p-1.5 rounded-lg hover:bg-blue-50 text-blue-600" title="تفاصيل"><Eye className="w-4 h-4" /></button>
                          <button onClick={() => openEditOrder(o)} className="p-1.5 rounded-lg hover:bg-amber-50 text-amber-600" title="تعديل"><Edit3 className="w-4 h-4" /></button>
                          {o.remaining_amount > 0 && (
                            <button onClick={() => setPayModal(o)} className="p-1.5 rounded-lg hover:bg-green-50 text-green-600" title="دفع"><DollarSign className="w-4 h-4" /></button>
                          )}
                          <button onClick={() => handleOrderDelete(o.id)} className="p-1.5 rounded-lg hover:bg-red-50 text-red-600" title="حذف"><Trash2 className="w-4 h-4" /></button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}

      {/* ===== CUSTOMERS TAB ===== */}
      {tab === 'customers' && (
        <Card className="border-0 shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-emerald-600 text-white">
                  <th className="px-4 py-3 text-right font-semibold">العميل</th>
                  <th className="px-4 py-3 text-right font-semibold">الهاتف</th>
                  <th className="px-4 py-3 text-right font-semibold">الشركة</th>
                  <th className="px-4 py-3 text-right font-semibold">الرصيد ($)</th>
                  <th className="px-4 py-3 text-center font-semibold">إجراءات</th>
                </tr>
              </thead>
              <tbody>
                {customers.length === 0 ? (
                  <tr><td colSpan={5} className="px-4 py-12 text-center text-gray-400">لا يوجد عملاء</td></tr>
                ) : customers.map(c => (
                  <tr key={c.id} className="border-b border-gray-50 hover:bg-gray-50/50">
                    <td className="px-4 py-3 font-bold">{c.name}</td>
                    <td className="px-4 py-3 text-gray-500" dir="ltr">{c.phone}</td>
                    <td className="px-4 py-3 text-gray-500">{c.company || '-'}</td>
                    <td className={`px-4 py-3 font-bold ${c.balance > 0 ? 'text-amber-600' : 'text-green-600'}`}>${formatNum(c.balance)}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-center gap-1">
                        <button onClick={() => { setEditCustomer(c); setCustomerForm(c); setCustomerModal(true); }}
                          className="p-1.5 rounded-lg hover:bg-amber-50 text-amber-600"><Edit3 className="w-4 h-4" /></button>
                        <button onClick={() => handleCustomerDelete(c.id)}
                          className="p-1.5 rounded-lg hover:bg-red-50 text-red-600"><Trash2 className="w-4 h-4" /></button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* ===== PAYMENTS TAB ===== */}
      {tab === 'payments' && (
        <>
          <div className="flex flex-wrap gap-3">
            <select value={customerFilter} onChange={e => setCustomerFilter(e.target.value)}
              className="h-10 px-4 rounded-xl border border-gray-200 text-sm focus:border-emerald-500 outline-none bg-white">
              <option value="">كل العملاء</option>
              {customers.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)}
              className="h-10 px-3 rounded-xl border border-gray-200 text-sm focus:border-emerald-500 outline-none" placeholder="من تاريخ" />
            <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)}
              className="h-10 px-3 rounded-xl border border-gray-200 text-sm focus:border-emerald-500 outline-none" placeholder="إلى تاريخ" />
          </div>
          <Card className="border-0 shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-emerald-600 text-white">
                    <th className="px-4 py-3 text-right font-semibold">التاريخ</th>
                    <th className="px-4 py-3 text-right font-semibold">رقم الطلب</th>
                    <th className="px-4 py-3 text-right font-semibold">العميل</th>
                    <th className="px-4 py-3 text-right font-semibold">المبلغ ($)</th>
                    <th className="px-4 py-3 text-right font-semibold">طريقة الدفع</th>
                    <th className="px-4 py-3 text-right font-semibold">ملاحظات</th>
                  </tr>
                </thead>
                <tbody>
                  {payments.length === 0 ? (
                    <tr><td colSpan={6} className="px-4 py-12 text-center text-gray-400">لا توجد مدفوعات</td></tr>
                  ) : payments.map(p => (
                    <tr key={p.id} className="border-b border-gray-50 hover:bg-gray-50/50">
                      <td className="px-4 py-3 text-gray-500">{p.payment_date}</td>
                      <td className="px-4 py-3 font-bold text-emerald-700">{p.order_number}</td>
                      <td className="px-4 py-3">{p.customer_name}</td>
                      <td className="px-4 py-3 font-bold text-green-600">${formatNum(p.amount)}</td>
                      <td className="px-4 py-3 text-gray-500">{p.payment_method_name}</td>
                      <td className="px-4 py-3 text-gray-400 text-xs">{p.notes || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}

      {/* ===== REPORTS TAB ===== */}
      {tab === 'reports' && (
        <div className="space-y-6">
          <div className="flex flex-wrap gap-3">
            <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)}
              className="h-10 px-3 rounded-xl border border-gray-200 text-sm focus:border-emerald-500 outline-none" />
            <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)}
              className="h-10 px-3 rounded-xl border border-gray-200 text-sm focus:border-emerald-500 outline-none" />
            <Button onClick={loadReport} className="bg-emerald-600 hover:bg-emerald-700">
              <BarChart3 className="w-4 h-4" /> عرض التقرير
            </Button>
          </div>

          {reportSummary && (
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
              <Card className="border-0 shadow-sm bg-emerald-50"><CardContent className="p-4 text-center">
                <div className="text-3xl font-black text-emerald-700">{reportSummary.total_orders}</div>
                <div className="text-sm text-gray-500 mt-1">إجمالي الطلبات</div>
              </CardContent></Card>
              <Card className="border-0 shadow-sm bg-blue-50"><CardContent className="p-4 text-center">
                <div className="text-3xl font-black text-blue-700">${formatNum(reportSummary.total_amount)}</div>
                <div className="text-sm text-gray-500 mt-1">إجمالي القيمة ($)</div>
              </CardContent></Card>
              <Card className="border-0 shadow-sm bg-green-50"><CardContent className="p-4 text-center">
                <div className="text-3xl font-black text-green-700">${formatNum(reportSummary.total_paid)}</div>
                <div className="text-sm text-gray-500 mt-1">المدفوع ($)</div>
              </CardContent></Card>
              <Card className="border-0 shadow-sm bg-amber-50"><CardContent className="p-4 text-center">
                <div className="text-3xl font-black text-amber-700">${formatNum(reportSummary.total_remaining)}</div>
                <div className="text-sm text-gray-500 mt-1">المتبقي ($)</div>
              </CardContent></Card>
              <Card className="border-0 shadow-sm bg-green-50"><CardContent className="p-4 text-center">
                <div className="text-3xl font-black text-green-700">{reportSummary.delivered_count}</div>
                <div className="text-sm text-gray-500 mt-1">تم التوصيل</div>
              </CardContent></Card>
              <Card className="border-0 shadow-sm bg-amber-50"><CardContent className="p-4 text-center">
                <div className="text-3xl font-black text-amber-700">{reportSummary.pending_count}</div>
                <div className="text-sm text-gray-500 mt-1">قيد الانتظار</div>
              </CardContent></Card>
            </div>
          )}

          {/* Customer Statement */}
          <Card className="border-0 shadow-sm">
            <CardContent className="p-4">
              <h3 className="font-bold text-gray-900 mb-3">كشف حساب عميل</h3>
              <div className="flex gap-3 mb-4">
                <select value={stmtCustomer} onChange={e => { setStmtCustomer(e.target.value); setStmtData(null); }}
                  className="h-10 px-4 rounded-xl border border-gray-200 text-sm focus:border-emerald-500 outline-none bg-white flex-1">
                  <option value="">اختر العميل</option>
                  {customers.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
                <Button onClick={loadStatement} variant="outline"><Search className="w-4 h-4" /> بحث</Button>
              </div>
              {stmtData && (
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-4">
                    <div className="bg-blue-50 rounded-xl p-3 text-center">
                      <div className="text-xl font-black text-blue-700">${formatNum(stmtData.total_orders)}</div>
                      <div className="text-xs text-gray-500">إجمالي الطلبات ($)</div>
                    </div>
                    <div className="bg-green-50 rounded-xl p-3 text-center">
                      <div className="text-xl font-black text-green-700">${formatNum(stmtData.total_paid)}</div>
                      <div className="text-xs text-gray-500">المدفوع ($)</div>
                    </div>
                    <div className="bg-amber-50 rounded-xl p-3 text-center">
                      <div className="text-xl font-black text-amber-700">${formatNum(stmtData.balance)}</div>
                      <div className="text-xs text-gray-500">الرصيد ($)</div>
                    </div>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-gray-100 text-gray-600">
                          <th className="px-3 py-2 text-right text-xs">رقم الطلب</th>
                          <th className="px-3 py-2 text-right text-xs">التاريخ</th>
                          <th className="px-3 py-2 text-right text-xs">القيمة ($)</th>
                          <th className="px-3 py-2 text-right text-xs">المدفوع ($)</th>
                          <th className="px-3 py-2 text-right text-xs">المتبقي ($)</th>
                          <th className="px-3 py-2 text-right text-xs">الحالة</th>
                        </tr>
                      </thead>
                      <tbody>
                        {stmtData.orders.map((o: any) => (
                          <tr key={o.id} className="border-b border-gray-50">
                            <td className="px-3 py-2 font-bold text-emerald-700">{o.order_number}</td>
                            <td className="px-3 py-2 text-gray-500">{o.order_date}</td>
                            <td className="px-3 py-2 font-bold">${formatNum(o.final_amount)}</td>
                            <td className="px-3 py-2 text-green-600">${formatNum(o.paid_amount)}</td>
                            <td className="px-3 py-2 text-amber-600">${formatNum(o.remaining_amount)}</td>
                            <td className="px-3 py-2"><span className={`px-2 py-0.5 rounded-full text-xs font-bold ${STATUS_COLORS[o.status] || ''}`}>{o.status_name}</span></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* ===== ORDER MODAL ===== */}
      <Modal open={orderModal} onClose={() => { setOrderModal(false); setEditOrder(null); }}
        title={editOrder ? `تعديل الطلب ${editOrder.order_number}` : 'طلب بيع جديد'}>
        <div className="space-y-4 max-h-[70vh] overflow-y-auto p-1">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">العميل *</label>
              <select value={orderForm.customer_id} onChange={e => setOrderForm({ ...orderForm, customer_id: e.target.value })}
                className="w-full h-10 px-3 rounded-xl border border-gray-200 text-sm focus:border-emerald-500 outline-none bg-white">
                <option value="">اختر العميل</option>
                {customers.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">رقم الطلب</label>
              <Input value={orderForm.order_number} onChange={e => setOrderForm({ ...orderForm, order_number: e.target.value })}
                placeholder="اتركه فارغاً للإنشاء التلقائي" className="h-10" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">تاريخ الطلب</label>
              <Input type="date" value={orderForm.order_date} onChange={e => setOrderForm({ ...orderForm, order_date: e.target.value })} className="h-10" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">تاريخ التوصيل</label>
              <Input type="date" value={orderForm.delivery_date} onChange={e => setOrderForm({ ...orderForm, delivery_date: e.target.value })} className="h-10" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">الحالة</label>
              <select value={orderForm.status} onChange={e => setOrderForm({ ...orderForm, status: e.target.value })}
                className="w-full h-10 px-3 rounded-xl border border-gray-200 text-sm focus:border-emerald-500 outline-none bg-white">
                <option value="pending">قيد الانتظار</option>
                <option value="confirmed">مؤكد</option>
                <option value="delivered">تم التوصيل</option>
                <option value="cancelled">ملغي</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">طريقة الدفع</label>
              <select value={orderForm.payment_method} onChange={e => setOrderForm({ ...orderForm, payment_method: e.target.value })}
                className="w-full h-10 px-3 rounded-xl border border-gray-200 text-sm focus:border-emerald-500 outline-none bg-white">
                {PAYMENT_METHODS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
            </div>
          </div>

          {/* Items */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-semibold text-gray-600">بنود الطلب (طن / دولار)</label>
              <button onClick={addItem} className="text-xs text-emerald-600 hover:text-emerald-700 font-semibold flex items-center gap-1">
                <Plus className="w-3 h-3" /> إضافة بند
              </button>
            </div>
            <div className="space-y-2">
              {orderForm.items.map((item: any, i: number) => (
                <div key={i} className="flex gap-2 items-end bg-gray-50 rounded-xl p-3">
                  <div className="flex-1">
                    <label className="block text-[10px] text-gray-500 mb-0.5">المنتج</label>
                    <Input value={item.product_name} onChange={e => updateItem(i, 'product_name', e.target.value)} className="h-9 text-xs" />
                  </div>
                  <div className="w-20">
                    <label className="block text-[10px] text-gray-500 mb-0.5">الكمية (طن)</label>
                    <Input type="number" value={item.quantity} onChange={e => updateItem(i, 'quantity', e.target.value)} className="h-9 text-xs" />
                  </div>
                  <div className="w-24">
                    <label className="block text-[10px] text-gray-500 mb-0.5">سعر الوحدة ($)</label>
                    <Input type="number" value={item.unit_price} onChange={e => updateItem(i, 'unit_price', e.target.value)} className="h-9 text-xs" />
                  </div>
                  <div className="w-24">
                    <label className="block text-[10px] text-gray-500 mb-0.5">الإجمالي ($)</label>
                    <div className="h-9 px-3 flex items-center text-xs font-bold text-emerald-700 bg-white border border-gray-200 rounded-xl">
                      ${formatNum((parseFloat(item.quantity) || 0) * (parseFloat(item.unit_price) || 0))}
                    </div>
                  </div>
                  {orderForm.items.length > 1 && (
                    <button onClick={() => removeItem(i)} className="p-1.5 rounded-lg hover:bg-red-50 text-red-500 mb-0.5"><X className="w-4 h-4" /></button>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">الخصم ($)</label>
              <Input type="number" value={orderForm.discount} onChange={e => setOrderForm({ ...orderForm, discount: e.target.value })} className="h-10" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">الضريبة (%)</label>
              <Input type="number" value={orderForm.tax_rate} onChange={e => setOrderForm({ ...orderForm, tax_rate: e.target.value })} className="h-10" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">دفعة مبدئية ($)</label>
              <Input type="number" value={orderForm.initial_payment} onChange={e => setOrderForm({ ...orderForm, initial_payment: e.target.value })} className="h-10" />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">عنوان التوصيل</label>
            <Input value={orderForm.delivery_address} onChange={e => setOrderForm({ ...orderForm, delivery_address: e.target.value })} className="h-10" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">ملاحظات</label>
            <textarea value={orderForm.notes} onChange={e => setOrderForm({ ...orderForm, notes: e.target.value })}
              className="w-full h-16 px-3 py-2 rounded-xl border border-gray-200 text-sm focus:border-emerald-500 outline-none resize-none" />
          </div>

          {/* Total Preview */}
          <div className="bg-emerald-50 rounded-xl p-4 flex justify-between items-center">
            <span className="text-sm font-semibold text-gray-600">الإجمالي النهائي</span>
            <span className="text-2xl font-black text-emerald-700">
              ${formatNum(orderForm.items.reduce((s: number, it: any) => s + (parseFloat(it.quantity) || 0) * (parseFloat(it.unit_price) || 0), 0) - (parseFloat(orderForm.discount) || 0))}
            </span>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => { setOrderModal(false); setEditOrder(null); }}>إلغاء</Button>
            <Button onClick={handleOrderSave} disabled={saving} className="bg-emerald-600 hover:bg-emerald-700">
              {saving ? 'جاري الحفظ...' : editOrder ? 'تحديث' : 'إنشاء الطلب'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* ===== CUSTOMER MODAL ===== */}
      <Modal open={customerModal} onClose={() => { setCustomerModal(false); setEditCustomer(null); }}
        title={editCustomer ? 'تعديل العميل' : 'عميل جديد'}>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="block text-xs font-semibold text-gray-600 mb-1">اسم العميل *</label>
              <Input value={customerForm.name} onChange={e => setCustomerForm({ ...customerForm, name: e.target.value })} className="h-10" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">الهاتف</label>
              <Input value={customerForm.phone} onChange={e => setCustomerForm({ ...customerForm, phone: e.target.value })} className="h-10" dir="ltr" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">هاتف ثانوي</label>
              <Input value={customerForm.secondary_phone} onChange={e => setCustomerForm({ ...customerForm, secondary_phone: e.target.value })} className="h-10" dir="ltr" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">الشركة</label>
              <Input value={customerForm.company} onChange={e => setCustomerForm({ ...customerForm, company: e.target.value })} className="h-10" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">الرقم الضريبي</label>
              <Input value={customerForm.tax_number} onChange={e => setCustomerForm({ ...customerForm, tax_number: e.target.value })} className="h-10" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">شخص الاتصال</label>
              <Input value={customerForm.contact_person} onChange={e => setCustomerForm({ ...customerForm, contact_person: e.target.value })} className="h-10" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">حد الائتمان ($)</label>
              <Input type="number" value={customerForm.credit_limit} onChange={e => setCustomerForm({ ...customerForm, credit_limit: e.target.value })} className="h-10" />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-semibold text-gray-600 mb-1">العنوان</label>
              <Input value={customerForm.address} onChange={e => setCustomerForm({ ...customerForm, address: e.target.value })} className="h-10" />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-semibold text-gray-600 mb-1">ملاحظات</label>
              <textarea value={customerForm.notes} onChange={e => setCustomerForm({ ...customerForm, notes: e.target.value })}
                className="w-full h-16 px-3 py-2 rounded-xl border border-gray-200 text-sm focus:border-emerald-500 outline-none resize-none" />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => { setCustomerModal(false); setEditCustomer(null); }}>إلغاء</Button>
            <Button onClick={handleCustomerSave} disabled={saving} className="bg-emerald-600 hover:bg-emerald-700">
              {saving ? 'جاري الحفظ...' : editCustomer ? 'تحديث' : 'إضافة'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* ===== PAY MODAL ===== */}
      <Modal open={!!payModal} onClose={() => setPayModal(null)}
        title={`تسجيل دفع — ${payModal?.order_number || ''}`}>
        {payModal && (
          <div className="space-y-4">
            <div className="bg-gray-50 rounded-xl p-3 grid grid-cols-3 gap-3 text-center text-sm">
              <div><div className="text-gray-400 text-xs">الإجمالي</div><div className="font-bold">${formatNum(payModal.final_amount)}</div></div>
              <div><div className="text-gray-400 text-xs">المدفوع</div><div className="font-bold text-green-600">${formatNum(payModal.paid_amount)}</div></div>
              <div><div className="text-gray-400 text-xs">المتبقي</div><div className="font-bold text-amber-600">${formatNum(payModal.remaining_amount)}</div></div>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">المبلغ ($) *</label>
              <Input type="number" value={payForm.amount} onChange={e => setPayForm({ ...payForm, amount: e.target.value })}
                className="h-10" placeholder="أدخل المبلغ" max={payModal.remaining_amount} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1">طريقة الدفع</label>
                <select value={payForm.payment_method} onChange={e => setPayForm({ ...payForm, payment_method: e.target.value })}
                  className="w-full h-10 px-3 rounded-xl border border-gray-200 text-sm focus:border-emerald-500 outline-none bg-white">
                  {PAYMENT_METHODS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1">التاريخ</label>
                <Input type="date" value={payForm.payment_date} onChange={e => setPayForm({ ...payForm, payment_date: e.target.value })} className="h-10" />
              </div>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1">ملاحظات</label>
              <Input value={payForm.notes} onChange={e => setPayForm({ ...payForm, notes: e.target.value })} className="h-10" />
            </div>
            <div className="flex justify-end gap-2 pt-4 border-t">
              <Button variant="outline" onClick={() => setPayModal(null)}>إلغاء</Button>
              <Button onClick={handlePaymentSave} disabled={saving} className="bg-green-600 hover:bg-green-700">
                {saving ? 'جاري الحفظ...' : 'تسجيل الدفع'}
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* ===== DETAIL MODAL ===== */}
      <Modal open={!!detailModal} onClose={() => setDetailModal(null)}
        title={`تفاصيل الطلب — ${detailModal?.order_number || ''}`}>
        {detailModal && (
          <div className="space-y-4 max-h-[70vh] overflow-y-auto p-1">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div><span className="text-gray-400">العميل:</span> <span className="font-bold">{detailModal.customer_name}</span></div>
              <div><span className="text-gray-400">التاريخ:</span> <span className="font-bold">{detailModal.order_date}</span></div>
              <div><span className="text-gray-400">التوصيل:</span> <span className="font-bold">{detailModal.delivery_date || '-'}</span></div>
              <div><span className="text-gray-400">الحالة:</span>
                <span className={`mr-2 px-2 py-0.5 rounded-full text-xs font-bold ${STATUS_COLORS[detailModal.status] || ''}`}>{detailModal.status_name}</span>
              </div>
              <div><span className="text-gray-400">طريقة الدفع:</span> <span className="font-bold">{detailModal.payment_method_name}</span></div>
              <div><span className="text-gray-400">أنشأ:</span> <span className="font-bold">{detailModal.creator_name}</span></div>
            </div>

            {/* Items */}
            <div>
              <h4 className="font-bold text-sm mb-2">البنود</h4>
              <table className="w-full text-sm border border-gray-100 rounded-xl overflow-hidden">
                <thead><tr className="bg-gray-50 text-gray-600 text-xs">
                  <th className="px-3 py-2 text-right">المنتج</th>
                  <th className="px-3 py-2 text-right">الكمية (طن)</th>
                  <th className="px-3 py-2 text-right">السعر ($)</th>
                  <th className="px-3 py-2 text-right">الإجمالي ($)</th>
                </tr></thead>
                <tbody>
                  {(detailModal.items || []).map((it: any) => (
                    <tr key={it.id} className="border-t border-gray-50">
                      <td className="px-3 py-2 font-semibold">{it.product_name}</td>
                      <td className="px-3 py-2">{it.quantity} {it.unit}</td>
                      <td className="px-3 py-2">${formatNum(it.unit_price)}</td>
                      <td className="px-3 py-2 font-bold text-emerald-700">${formatNum(it.total_price)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Totals */}
            <div className="bg-emerald-50 rounded-xl p-4 space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-gray-500">المجموع الفرعي:</span><span className="font-bold">${formatNum(detailModal.total_amount)}</span></div>
              {detailModal.discount > 0 && <div className="flex justify-between"><span className="text-gray-500">الخصم:</span><span className="font-bold text-red-600">-${formatNum(detailModal.discount)}</span></div>}
              {detailModal.tax_amount > 0 && <div className="flex justify-between"><span className="text-gray-500">الضريبة ({detailModal.tax_rate}%):</span><span className="font-bold">+${formatNum(detailModal.tax_amount)}</span></div>}
              <div className="flex justify-between border-t border-emerald-200 pt-2"><span className="font-bold">الإجمالي النهائي:</span><span className="text-xl font-black text-emerald-700">${formatNum(detailModal.final_amount)}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">المدفوع:</span><span className="font-bold text-green-600">${formatNum(detailModal.paid_amount)}</span></div>
              <div className="flex justify-between"><span className="text-gray-500">المتبقي:</span><span className="font-bold text-amber-600">${formatNum(detailModal.remaining_amount)}</span></div>
            </div>

            {/* Payments History */}
            {detailModal.payments && detailModal.payments.length > 0 && (
              <div>
                <h4 className="font-bold text-sm mb-2">سجل المدفوعات</h4>
                <table className="w-full text-sm border border-gray-100 rounded-xl overflow-hidden">
                  <thead><tr className="bg-gray-50 text-gray-600 text-xs">
                    <th className="px-3 py-2 text-right">التاريخ</th>
                    <th className="px-3 py-2 text-right">المبلغ ($)</th>
                    <th className="px-3 py-2 text-right">الطريقة</th>
                  </tr></thead>
                  <tbody>
                    {detailModal.payments.map((p: any) => (
                      <tr key={p.id} className="border-t border-gray-50">
                        <td className="px-3 py-2 text-gray-500">{p.payment_date}</td>
                        <td className="px-3 py-2 font-bold text-green-600">${formatNum(p.amount)}</td>
                        <td className="px-3 py-2 text-gray-500">{p.payment_method_name}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {detailModal.notes && (
              <div className="bg-amber-50 rounded-xl p-3 text-sm text-gray-600">
                <span className="font-bold">ملاحظات:</span> {detailModal.notes}
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
