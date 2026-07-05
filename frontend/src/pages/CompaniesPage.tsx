import { useState, useEffect } from 'react';
import { Building2, MapPin, Plus, Trash2, ChevronDown, ChevronUp, Globe, Navigation, Users, BookOpen } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Modal } from '@/components/ui/modal';
import api from '@/api/client';
import { formatNum } from '@/lib/utils';

export default function CompaniesPage() {
  const [companies, setCompanies] = useState<any[]>([]);
  const [employees, setEmployees] = useState<any[]>([]);
  const [regions, setRegions] = useState<any[]>([]);
  const [locations, setLocations] = useState<any[]>([]);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [regionModal, setRegionModal] = useState(false);
  const [locationModal, setLocationModal] = useState(false);
  const [expandedCompany, setExpandedCompany] = useState<number | null>(null);
  const [expandedRegion, setExpandedRegion] = useState<number | null>(null);
  const [form, setForm] = useState({ name: '', contact_person: '', phone: '', email: '' });
  const [regionForm, setRegionForm] = useState({ name: '', company_id: '' });
  const [locationForm, setLocationForm] = useState({ name: '', region_id: '', address: '' });
  const [saving, setSaving] = useState(false);

  const loadData = () => {
    Promise.all([
      api.get('/companies'),
      api.get('/employees'),
      api.get('/regions'),
      api.get('/locations'),
      api.get('/accounts'),
    ]).then(([cRes, eRes, rRes, lRes, aRes]) => {
      setCompanies(cRes.data.data || []);
      setEmployees(eRes.data.data || []);
      setRegions(rRes.data.data || []);
      setLocations(lRes.data.data || []);
      setAccounts(aRes.data.data || []);
    }).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, []);

  const getAccountBalance = (company: any) => {
    if (!company.receivable_account_id) return null;
    const acc = accounts.find((a: any) => a.id === company.receivable_account_id);
    return acc ? (acc.balance || 0) : null;
  };

  const handleAddCompany = async () => {
    setSaving(true);
    try {
      await api.post('/companies', form);
      setModalOpen(false); setForm({ name: '', contact_person: '', phone: '', email: '' }); loadData();
    } catch (err: any) { alert(err.response?.data?.message || 'حدث خطأ'); }
    finally { setSaving(false); }
  };

  const handleDeleteCompany = async (id: number) => {
    if (!confirm('هل أنت متأكد من حذف هذه الشركة؟ سيتم حذف جميع المناطق والمواقع المرتبطة')) return;
    await api.delete(`/companies/${id}`);
    loadData();
  };

  const handleAddRegion = async () => {
    if (!regionForm.name || !regionForm.company_id) return;
    setSaving(true);
    try {
      await api.post('/regions', { ...regionForm, company_id: Number(regionForm.company_id) });
      setRegionModal(false); setRegionForm({ name: '', company_id: '' }); loadData();
    } catch (err: any) { alert(err.response?.data?.message || 'حدث خطأ'); }
    finally { setSaving(false); }
  };

  const handleDeleteRegion = async (id: number) => {
    if (!confirm('هل أنت متأكد من حذف هذه المنطقة؟')) return;
    await api.delete(`/regions/${id}`);
    loadData();
  };

  const handleAddLocation = async () => {
    if (!locationForm.name || !locationForm.region_id) return;
    setSaving(true);
    try {
      await api.post('/locations', { ...locationForm, region_id: Number(locationForm.region_id) });
      setLocationModal(false); setLocationForm({ name: '', region_id: '', address: '' }); loadData();
    } catch (err: any) { alert(err.response?.data?.message || 'حدث خطأ'); }
    finally { setSaving(false); }
  };

  const handleDeleteLocation = async (id: number) => {
    if (!confirm('هل أنت متأكد من حذف هذا الموقع؟')) return;
    await api.delete(`/locations/${id}`);
    loadData();
  };

  const getCompanyRegions = (companyId: number) => regions.filter(r => r.company_id === companyId);
  const getCompanyEmployees = (companyId: number) => employees.filter(e => e.company_id === companyId);
  const getRegionLocations = (regionId: number) => locations.filter(l => l.region_id === regionId);
  const getRegionEmployees = (regionId: number) => employees.filter(e => e.region_id === regionId);
  const getCompanyLocationsCount = (companyId: number) => {
    const crs = getCompanyRegions(companyId);
    return crs.reduce((acc, r) => acc + getRegionLocations(r.id).length, 0);
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
          <h1 className="text-2xl font-bold text-gray-900">الشركات والمناطق والمواقع</h1>
          <p className="text-gray-500 text-sm mt-1">{companies.length} شركة — {regions.length} منطقة — {locations.length} موقع — {employees.length} موظف</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button variant="outline" onClick={() => setRegionModal(true)}><Globe className="w-4 h-4" /> منطقة</Button>
          <Button variant="outline" onClick={() => setLocationModal(true)}><Navigation className="w-4 h-4" /> موقع</Button>
          <Button onClick={() => setModalOpen(true)}><Plus className="w-4 h-4" /> شركة</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {companies.map((company) => {
          const companyRegions = getCompanyRegions(company.id);
          const companyEmps = getCompanyEmployees(company.id);
          const isExpanded = expandedCompany === company.id;
          return (
            <Card key={company.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-14 h-14 rounded-xl bg-primary-100 flex items-center justify-center">
                      <Building2 className="w-7 h-7 text-primary-600" />
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-gray-900">{company.name}</h3>
                      {company.contact_person && <p className="text-sm text-gray-500">جهة الاتصال: {company.contact_person}</p>}
                      <div className="flex items-center gap-4 mt-2 text-xs text-gray-400">
                        <span className="flex items-center gap-1"><Users className="w-3.5 h-3.5" /> {companyEmps.length} موظف</span>
                        <span className="flex items-center gap-1"><Globe className="w-3.5 h-3.5" /> {companyRegions.length} منطقة</span>
                        <span className="flex items-center gap-1"><Navigation className="w-3.5 h-3.5" /> {getCompanyLocationsCount(company.id)} موقع</span>
                      </div>
                      {company.receivable_account_code && (
                        <div className="flex items-center gap-2 mt-2 text-xs">
                          <span className="flex items-center gap-1 text-gray-400"><BookOpen className="w-3 h-3" /> الحساب: <span className="font-mono text-primary-600">{company.receivable_account_code}</span></span>
                          {getAccountBalance(company) !== null && (
                            <span className={`font-bold ${getAccountBalance(company)! >= 0 ? 'text-green-600' : 'text-red-600'}`}>{formatNum(getAccountBalance(company)!)} ر.ي</span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <button onClick={() => setExpandedCompany(isExpanded ? null : company.id)} className="p-2 rounded-lg hover:bg-gray-100 text-gray-500">
                      {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                    </button>
                    <button onClick={() => handleDeleteCompany(company.id)} className="p-2 rounded-lg hover:bg-red-50 text-red-500">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Company Employees List */}
                {isExpanded && (
                  <div className="mt-6 space-y-4">
                    {/* Employees */}
                    <div className="bg-gray-50 rounded-xl p-4">
                      <h4 className="font-medium text-sm text-gray-700 mb-3 flex items-center gap-2">
                        <Users className="w-4 h-4" /> موظفي الشركة ({companyEmps.length})
                      </h4>
                      {companyEmps.length > 0 ? (
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                          {companyEmps.map((emp) => (
                            <div key={emp.id} className="bg-white rounded-lg p-3 border border-gray-100 flex items-center gap-3">
                              <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center text-primary-700 text-sm font-bold">{emp.name?.[0]}</div>
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium truncate">{emp.name}</p>
                                <p className="text-xs text-gray-400 truncate">{emp.job_title || 'بدون وظيفة'} — {emp.region_name || emp.region || 'بدون منطقة'}</p>
                              </div>
                              <span className={`w-2 h-2 rounded-full ${emp.is_active ? 'bg-green-400' : 'bg-gray-300'}`} />
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs text-gray-400">لا يوجد موظفين في هذه الشركة</p>
                      )}
                    </div>

                    {/* Regions */}
                    <div>
                      <h4 className="font-medium text-sm text-gray-700 mb-3 flex items-center gap-2">
                        <Globe className="w-4 h-4" /> المناطق ({companyRegions.length})
                      </h4>
                      {companyRegions.length === 0 ? (
                        <p className="text-xs text-gray-400">لا توجد مناطق — أضف منطقة من الزر أعلاه</p>
                      ) : (
                        <div className="space-y-3">
                          {companyRegions.map((region) => {
                            const regionLocs = getRegionLocations(region.id);
                            const regionEmps = getRegionEmployees(region.id);
                            const isRegExpanded = expandedRegion === region.id;
                            return (
                              <div key={region.id} className="bg-gray-50 rounded-xl p-4 border border-gray-200">
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-3">
                                    <Globe className="w-4 h-4 text-primary-500" />
                                    <div>
                                      <span className="font-medium text-sm">{region.name}</span>
                                      <div className="flex items-center gap-3 text-xs text-gray-400 mt-0.5">
                                        <span>{regionLocs.length} موقع</span>
                                        <span>{regionEmps.length} موظف</span>
                                      </div>
                                    </div>
                                  </div>
                                  <div className="flex items-center gap-1">
                                    <button onClick={() => setExpandedRegion(isRegExpanded ? null : region.id)} className="p-1 rounded hover:bg-gray-200">
                                      {isRegExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                                    </button>
                                    <button onClick={() => handleDeleteRegion(region.id)} className="p-1 rounded hover:bg-red-100 text-red-500">
                                      <Trash2 className="w-4 h-4" />
                                    </button>
                                  </div>
                                </div>

                                {isRegExpanded && (
                                  <div className="mt-3 ml-7 space-y-2">
                                    {/* Region Employees */}
                                    {regionEmps.length > 0 && (
                                      <div className="mb-3">
                                        <p className="text-xs font-medium text-gray-500 mb-1">العمال في هذه المنطقة:</p>
                                        <div className="flex flex-wrap gap-1.5">
                                          {regionEmps.map((emp) => (
                                            <span key={emp.id} className="inline-flex items-center gap-1 px-2 py-1 bg-primary-50 text-primary-700 rounded-full text-xs">
                                              <span className="w-1.5 h-1.5 rounded-full bg-primary-400" />
                                              {emp.name}
                                            </span>
                                          ))}
                                        </div>
                                      </div>
                                    )}

                                    {/* Locations */}
                                    {regionLocs.length === 0 ? (
                                      <p className="text-xs text-gray-400">لا توجد مواقع</p>
                                    ) : (
                                      regionLocs.map((loc) => (
                                        <div key={loc.id} className="flex items-center justify-between bg-white rounded-lg px-3 py-2 border border-gray-100">
                                          <div className="flex items-center gap-2">
                                            <Navigation className="w-3.5 h-3.5 text-green-500" />
                                            <div>
                                              <span className="text-sm font-medium">{loc.name}</span>
                                              {loc.address && <span className="block text-xs text-gray-400">{loc.address}</span>}
                                            </div>
                                          </div>
                                          <button onClick={() => handleDeleteLocation(loc.id)} className="p-1 rounded hover:bg-red-100 text-red-500">
                                            <Trash2 className="w-3 h-3" />
                                          </button>
                                        </div>
                                      ))
                                    )}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
        {companies.length === 0 && <p className="text-gray-400 text-center py-12">لا توجد شركات — أضف شركة جديدة</p>}
      </div>

      {/* Add Company Modal */}
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="إضافة شركة">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">اسم الشركة *</label>
            <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="اسم الشركة" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">جهة الاتصال</label>
            <Input value={form.contact_person} onChange={(e) => setForm({ ...form, contact_person: e.target.value })} placeholder="اسم جهة الاتصال" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">الهاتف</label>
              <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="رقم الهاتف" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">البريد الإلكتروني</label>
              <Input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="البريد الإلكتروني" />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setModalOpen(false)}>إلغاء</Button>
            <Button onClick={handleAddCompany} disabled={saving || !form.name}>{saving ? 'جاري الحفظ...' : 'حفظ'}</Button>
          </div>
        </div>
      </Modal>

      {/* Add Region Modal */}
      <Modal open={regionModal} onClose={() => setRegionModal(false)} title="إضافة منطقة">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">الشركة *</label>
            <select value={regionForm.company_id} onChange={(e) => setRegionForm({ ...regionForm, company_id: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
              <option value="">اختر الشركة</option>
              {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">اسم المنطقة *</label>
            <Input value={regionForm.name} onChange={(e) => setRegionForm({ ...regionForm, name: e.target.value })} placeholder="اسم المنطقة" />
          </div>
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setRegionModal(false)}>إلغاء</Button>
            <Button onClick={handleAddRegion} disabled={saving || !regionForm.name || !regionForm.company_id}>{saving ? 'جاري الحفظ...' : 'حفظ'}</Button>
          </div>
        </div>
      </Modal>

      {/* Add Location Modal */}
      <Modal open={locationModal} onClose={() => setLocationModal(false)} title="إضافة موقع">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">المنطقة *</label>
            <select value={locationForm.region_id} onChange={(e) => setLocationForm({ ...locationForm, region_id: e.target.value })} className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm">
              <option value="">اختر المنطقة</option>
              {regions.map((r) => <option key={r.id} value={r.id}>{r.name} — {r.company_name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">اسم الموقع *</label>
            <Input value={locationForm.name} onChange={(e) => setLocationForm({ ...locationForm, name: e.target.value })} placeholder="اسم الموقع" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">العنوان</label>
            <Input value={locationForm.address} onChange={(e) => setLocationForm({ ...locationForm, address: e.target.value })} placeholder="العنوان" />
          </div>
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setLocationModal(false)}>إلغاء</Button>
            <Button onClick={handleAddLocation} disabled={saving || !locationForm.name || !locationForm.region_id}>{saving ? 'جاري الحفظ...' : 'حفظ'}</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
