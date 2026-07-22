import { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Home, Users, CalendarCheck, Building2, Star, DollarSign,
  BookOpen, Truck, BarChart3, Settings, LogOut, Menu, X,
  FileText, UserCog, FileCheck, Bell, Search, Plus, ClipboardList, Coins,
  Calendar, Clock, User, Grid3x3, ClipboardCheck
} from 'lucide-react';
import api from '@/api/client';

const navItems = [
  { path: '/dashboard', label: 'الرئيسية', icon: Home, roles: ['admin', 'supervisor', 'accountant', 'viewer'] },
  { path: '/employees', label: 'الموظفين', icon: Users, roles: ['admin', 'supervisor'] },
  { path: '/attendance', label: 'الحضور', icon: CalendarCheck, roles: ['admin', 'supervisor'] },
  { path: '/attendance-grid', label: 'الحضور الشجري', icon: Grid3x3, roles: ['admin', 'supervisor'] },
  { path: '/attendance-report', label: 'تقرير الحضور', icon: ClipboardCheck, roles: ['admin', 'supervisor'] },
  { path: '/companies', label: 'الشركات', icon: Building2, roles: ['admin', 'supervisor', 'accountant'] },
  { path: '/contracts', label: 'العقود', icon: FileCheck, roles: ['admin', 'supervisor'] },
  { path: '/invoices', label: 'الفواتير', icon: FileText, roles: ['admin', 'supervisor', 'accountant'] },
  { path: '/evaluations', label: 'التقييمات', icon: Star, roles: ['admin', 'supervisor'] },
  { path: '/work-plans', label: 'خطط العمل', icon: ClipboardList, roles: ['admin', 'supervisor'] },
  { path: '/salaries', label: 'الرواتب', icon: Coins, roles: ['admin', 'accountant'] },
  { path: '/financial', label: 'المالية', icon: DollarSign, roles: ['admin', 'accountant'] },
  { path: '/accounts', label: 'الحسابات', icon: BookOpen, roles: ['admin', 'accountant'] },
  { path: '/suppliers', label: 'الموردين', icon: Truck, roles: ['admin', 'accountant'] },
  { path: '/supplier-invoices', label: 'فواتير الموردين', icon: FileText, roles: ['admin', 'accountant'] },
  { path: '/periods', label: 'الفترات المالية', icon: Calendar, roles: ['admin', 'accountant'] },
  { path: '/leaves', label: 'الإجازات', icon: Clock, roles: ['admin', 'supervisor'] },
  { path: '/reports', label: 'التقارير', icon: BarChart3, roles: ['admin', 'supervisor', 'accountant'] },
  { path: '/users', label: 'المستخدمين', icon: UserCog, roles: ['admin'] },
  { path: '/profile', label: 'الملف الشخصي', icon: User, roles: ['admin', 'supervisor', 'accountant', 'viewer', 'employee'] },
  { path: '/settings', label: 'الإعدادات', icon: Settings, roles: ['admin'] },
];

const shortcuts = [
  { label: 'موظف', icon: Users, path: '/employees' },
  { label: 'حضور', icon: CalendarCheck, path: '/attendance' },
  { label: 'فاتورة', icon: FileText, path: '/invoices' },
  { label: 'تقرير', icon: BarChart3, path: '/reports' },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [user, setUser] = useState<any>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    api.get('/auth/me').then(res => setUser(res.data.data)).catch(() => {});
  }, []);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setSearchOpen(true);
      }
      if (e.key === 'Escape') {
        setSearchOpen(false);
        setSearchQuery('');
        setSearchResults([]);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const handleSearch = async (q: string) => {
    setSearchQuery(q);
    if (q.length < 2) { setSearchResults([]); return; }
    setSearching(true);
    try {
      const [empRes, compRes, supRes] = await Promise.all([
        api.get('/employees').catch(() => ({ data: { data: [] } })),
        api.get('/companies').catch(() => ({ data: { data: [] } })),
        api.get('/suppliers').catch(() => ({ data: { data: [] } })),
      ]);
      const results: any[] = [];
      const ql = q.toLowerCase();
      (empRes.data.data || []).forEach((e: any) => {
        if (e.name?.toLowerCase().includes(ql) || e.job_title?.toLowerCase().includes(ql)) {
          results.push({ type: 'employee', label: e.name, sub: e.job_title || '', path: '/employees' });
        }
      });
      (compRes.data.data || []).forEach((c: any) => {
        if (c.name?.toLowerCase().includes(ql)) {
          results.push({ type: 'company', label: c.name, sub: 'شركة', path: '/companies' });
        }
      });
      (supRes.data.data || []).forEach((s: any) => {
        if (s.name?.toLowerCase().includes(ql)) {
          results.push({ type: 'supplier', label: s.name, sub: 'مورد', path: '/suppliers' });
        }
      });
      setSearchResults(results.slice(0, 10));
    } catch {}
    setSearching(false);
  };

  const handleLogout = () => {
    api.post('/auth/logout').catch(() => {});
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/login');
  };

  const currentPage = navItems.find(n => location.pathname === n.path || (n.path !== '/' && location.pathname.startsWith(n.path)));

  return (
    <div className="flex h-screen bg-gray-50/50">
      {/* Sidebar - Desktop */}
      <aside className={`hidden lg:flex flex-col bg-white border-l border-gray-100 transition-all duration-300 ${sidebarOpen ? 'w-64' : 'w-[72px]'}`}>
        {/* Logo */}
        <div className="p-4 border-b border-gray-50">
          <div className={`flex items-center ${sidebarOpen ? 'gap-3' : 'justify-center'}`}>
            <img src="/logo.png" alt="طلعت هائل" className="w-10 h-10 rounded-xl object-contain flex-shrink-0" />
            {sidebarOpen && (
              <div>
                <div className="font-bold text-gray-900 text-sm">طلعت هائل</div>
                <div className="text-[10px] text-gray-400 uppercase tracking-wider">Agricultural Services</div>
              </div>
            )}
          </div>
        </div>

        {/* Nav Items */}
        <nav className="flex-1 p-2 space-y-0.5 overflow-y-auto">
          {navItems.filter(item => {
            if (user?.role === 'employee') {
              const allowed = user?.allowed_pages || ['my-portal'];
              return item.path === '/' || allowed.includes(item.path.replace('/', ''));
            }
            return (item.roles || []).includes(user?.role || '');
          }).map((item) => {
            const isActive = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path));
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-primary-50 text-primary-700 shadow-sm'
                    : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                <Icon className={`w-5 h-5 flex-shrink-0 ${isActive ? 'text-primary-600' : ''}`} />
                {sidebarOpen && <span>{item.label}</span>}
              </Link>
            );
          })}
          {user?.role === 'employee' && (
            <Link
              to="/my-portal"
              onClick={() => setMobileMenuOpen(false)}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                location.pathname === '/my-portal'
                  ? 'bg-primary-50 text-primary-700 shadow-sm'
                  : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'
              }`}
            >
              <User className={`w-5 h-5 flex-shrink-0 ${location.pathname === '/my-portal' ? 'text-primary-600' : ''}`} />
              {sidebarOpen && <span>بوابة الموظف</span>}
            </Link>
          )}
        </nav>

        {/* Logout */}
        <div className="p-2 border-t border-gray-50">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 w-full px-3 py-2.5 rounded-xl text-sm font-medium text-red-500 hover:bg-red-50 transition-all"
          >
            <LogOut className="w-5 h-5 flex-shrink-0" />
            {sidebarOpen && <span>تسجيل الخروج</span>}
          </button>
        </div>
      </aside>

      {/* Main Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="h-16 bg-white border-b border-gray-100 flex items-center justify-between px-4 lg:px-6 flex-shrink-0">
          {/* Right side - Mobile menu + Search */}
          <div className="flex items-center gap-3">
            <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="lg:hidden p-2 rounded-xl hover:bg-gray-100">
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
            <button onClick={() => setSearchOpen(!searchOpen)} className="p-2 rounded-xl hover:bg-gray-100 text-gray-500 relative">
              <Search className="w-5 h-5" />
              <span className="hidden lg:block absolute -bottom-0.5 -left-0.5 text-[8px] bg-gray-200 text-gray-500 px-1 rounded">Ctrl+K</span>
            </button>
          </div>

          {/* Center - Quick shortcuts (desktop) */}
          <div className="hidden md:flex items-center gap-2">
            {user?.role === 'employee' ? (
              <>
                <button onClick={() => navigate('/my-portal')} className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs font-medium transition-all">
                  <User className="w-3.5 h-3.5" /> ملفي الشخصي
                </button>
                <button onClick={() => navigate('/my-portal')} className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-50 hover:bg-gray-100 text-gray-600 text-xs font-medium transition-all">
                  <Calendar className="w-3.5 h-3.5" /> حضوري
                </button>
                <button onClick={() => navigate('/my-portal')} className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-50 hover:bg-gray-100 text-gray-600 text-xs font-medium transition-all">
                  <DollarSign className="w-3.5 h-3.5" /> راتبي
                </button>
                <button onClick={() => navigate('/my-portal')} className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-50 hover:bg-gray-100 text-gray-600 text-xs font-medium transition-all">
                  <Clock className="w-3.5 h-3.5" /> إجازاتي
                </button>
              </>
            ) : shortcuts.map((s) => {
              const Icon = s.icon;
              return (
                <button
                  key={s.path}
                  onClick={() => navigate(s.path)}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-50 hover:bg-gray-100 text-gray-600 text-xs font-medium transition-all"
                >
                  <Icon className="w-3.5 h-3.5" />
                  {s.label}
                </button>
              );
            })}
          </div>

          {/* Left side - User + Notifications */}
          <div className="flex items-center gap-3">
            <button className="relative p-2 rounded-xl hover:bg-gray-100 text-gray-500">
              <Bell className="w-5 h-5" />
              <span className="absolute top-1.5 left-1.5 w-2 h-2 bg-red-500 rounded-full" />
            </button>
            {user && (
              <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigate('/settings')}>
                <div className="text-left hidden sm:block">
                  <p className="text-sm font-bold text-gray-900 leading-tight">{user.full_name}</p>
                  <p className="text-[10px] text-gray-400">{user.role === 'admin' ? 'مدير النظام' : user.role}</p>
                </div>
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center text-white font-bold text-sm shadow-sm">
                  {user.full_name?.[0]}
                </div>
              </div>
            )}
          </div>
        </header>

        {/* Search Overlay */}
        {searchOpen && (
          <div className="absolute top-16 left-0 right-0 z-50 bg-white border-b border-gray-100 shadow-lg p-4" onClick={() => { setSearchOpen(false); setSearchQuery(''); setSearchResults([]); }}>
            <div className="max-w-2xl mx-auto" onClick={(e) => e.stopPropagation()}>
              <div className="relative">
                <Search className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  autoFocus
                  value={searchQuery}
                  onChange={(e) => handleSearch(e.target.value)}
                  placeholder="بحث عن موظف، شركة، مورد... (Ctrl+K)"
                  className="w-full h-12 pr-12 pl-4 rounded-xl border-2 border-gray-200 text-sm focus:border-primary-500 outline-none"
                />
                {searching && <div className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 border-2 border-primary-500/20 border-t-primary-500 rounded-full animate-spin" />}
              </div>
              {searchResults.length > 0 && (
                <div className="mt-2 bg-white rounded-xl border border-gray-100 shadow-lg max-h-64 overflow-y-auto">
                  {searchResults.map((r, idx) => (
                    <button key={idx} onClick={() => { navigate(r.path); setSearchOpen(false); setSearchQuery(''); setSearchResults([]); }}
                      className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 text-right transition-colors">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold ${
                        r.type === 'employee' ? 'bg-blue-100 text-blue-600' :
                        r.type === 'company' ? 'bg-green-100 text-green-600' :
                        'bg-rose-100 text-rose-600'
                      }`}>
                        {r.type === 'employee' ? 'م' : r.type === 'company' ? 'ش' : 'و'}
                      </div>
                      <div className="flex-1 text-right">
                        <p className="text-sm font-medium text-gray-800">{r.label}</p>
                        <p className="text-xs text-gray-500">{r.sub}</p>
                      </div>
                    </button>
                  ))}
                </div>
              )}
              {searchQuery.length >= 2 && searchResults.length === 0 && !searching && (
                <div className="mt-2 bg-white rounded-xl border border-gray-100 shadow-lg p-4 text-center">
                  <p className="text-sm text-gray-500">لا توجد نتائج لـ "{searchQuery}"</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="lg:hidden fixed inset-0 z-40 bg-black/50" onClick={() => setMobileMenuOpen(false)}>
            <div className="absolute right-0 top-0 h-full w-72 bg-white shadow-xl flex flex-col" onClick={(e) => e.stopPropagation()}>
              {/* User info */}
              {user && (
                <div className="p-4 border-b border-gray-100">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center text-white font-bold">{user.full_name?.[0]}</div>
                    <div>
                      <p className="font-bold text-gray-900 text-sm">{user.full_name}</p>
                      <p className="text-xs text-gray-500">{user.role === 'admin' ? 'مدير النظام' : user.role}</p>
                    </div>
                  </div>
                </div>
              )}
              {/* Shortcuts */}
              <div className="p-3 border-b border-gray-100">
                <p className="text-xs text-gray-400 font-medium px-2 mb-2">اختصارات</p>
                <div className="grid grid-cols-4 gap-2">
                  {shortcuts.map((s) => {
                    const Icon = s.icon;
                    return (
                      <button key={s.path} onClick={() => { navigate(s.path); setMobileMenuOpen(false); }}
                        className="flex flex-col items-center gap-1 p-2 rounded-lg hover:bg-gray-50 text-gray-600">
                        <Icon className="w-4 h-4" /><span className="text-[10px]">{s.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
              {/* Nav */}
              <nav className="flex-1 p-2 space-y-0.5 overflow-y-auto">
                {navItems.filter(item => {
                  if (user?.role === 'employee') {
                    const allowed = user?.allowed_pages || ['my-portal'];
                    return item.path === '/' || allowed.includes(item.path.replace('/', ''));
                  }
                  return (item.roles || []).includes(user?.role || '');
                }).map((item) => {
                  const isActive = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path));
                  const Icon = item.icon;
                  return (
                    <Link key={item.path} to={item.path} onClick={() => setMobileMenuOpen(false)}
                      className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${isActive ? 'bg-primary-50 text-primary-700' : 'text-gray-500 hover:bg-gray-50'}`}>
                      <Icon className={`w-5 h-5 ${isActive ? 'text-primary-600' : ''}`} /><span>{item.label}</span>
                    </Link>
                  );
                })}
                {user?.role === 'employee' && (
                  <Link to="/my-portal" onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${location.pathname === '/my-portal' ? 'bg-primary-50 text-primary-700' : 'text-gray-500 hover:bg-gray-50'}`}>
                    <User className={`w-5 h-5 ${location.pathname === '/my-portal' ? 'text-primary-600' : ''}`} /><span>بوابة الموظف</span>
                  </Link>
                )}
              </nav>
              <div className="p-2 border-t border-gray-100">
                <button onClick={handleLogout} className="flex items-center gap-3 w-full px-3 py-2.5 rounded-xl text-sm font-medium text-red-500 hover:bg-red-50">
                  <LogOut className="w-5 h-5" /><span>تسجيل الخروج</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto">
          <div className="p-4 lg:p-6 max-w-7xl mx-auto">{children}</div>
        </main>
      </div>
    </div>
  );
}
