import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Leaf, Shield, Eye, EyeOff, ArrowRight } from 'lucide-react';
import { authAPI } from '@/api/client';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await authAPI.login(username, password);
      localStorage.setItem('token', 'session');
      localStorage.setItem('user', JSON.stringify(res.data.data?.user));
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.message || 'خطأ في تسجيل الدخول');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-800 via-primary-700 to-primary-600 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-2xl overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-primary-50 to-primary-100 px-8 py-10 text-center border-b border-gray-100 relative">
            <button
              type="button"
              onClick={() => navigate('/')}
              className="absolute top-4 left-4 flex items-center gap-1 text-xs text-gray-400 hover:text-primary-600 transition-colors"
            >
              <ArrowRight className="w-3.5 h-3.5" />
              الرئيسية
            </button>
            <img src="/logo.png" alt="طلعت هائل" className="w-16 h-16 rounded-2xl object-contain mx-auto mb-4" />
            <h1 className="text-2xl font-bold text-primary-800">طلعت هائل</h1>
            <p className="text-sm text-gray-500 mt-1">للخدمات والاستشارات الزراعية</p>
            <div className="inline-flex items-center gap-2 bg-primary-50 text-primary-700 px-3 py-1.5 rounded-full text-xs font-semibold mt-4">
              <Shield className="w-3.5 h-3.5" />
              نظام آمن ومحمي
            </div>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="p-8 space-y-5">
            {error && (
              <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg text-sm font-medium border border-red-200">
                {error}
              </div>
            )}

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                اسم المستخدم
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full h-11 px-4 rounded-lg border-2 border-gray-200 text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500 outline-none transition-all"
                placeholder="أدخل اسم المستخدم"
                required
                autoFocus
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                كلمة المرور
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full h-11 px-4 pl-11 rounded-lg border-2 border-gray-200 text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500 outline-none transition-all"
                  placeholder="أدخل كلمة المرور"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full h-11 bg-primary-600 hover:bg-primary-700 text-white font-semibold rounded-lg transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                'تسجيل الدخول'
              )}
            </button>
          </form>

          {/* Footer */}
          <div className="bg-gray-50 px-8 py-4 text-center border-t border-gray-100">
            <p className="text-xs text-gray-400">
              طلعت هائل للخدمات والاستشارات الزراعية
            </p>
            <p className="text-xs text-gray-400 mt-0.5">
              الجمهورية اليمنية - محافظة الحديدة
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
