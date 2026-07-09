import { useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';

const features = [
  { icon: '🌿', text: 'حلول زراعية متكاملة' },
  { icon: '💧', text: 'شبكات الري الحديثة' },
  { icon: '📊', text: 'إدارة مالية متطورة' },
  { icon: '👨‍🌾', text: 'فريق عمل متخصص' },
];

const services = [
  { icon: '🌱', text: 'إدارة المزارع' },
  { icon: '🏗️', text: 'تصميم الحدائق' },
  { icon: '📈', text: 'الاستشارات الزراعية' },
  { icon: '📋', text: 'الخدمات الإدارية' },
];

const stats = [
  { num: '6+', label: 'سنوات خبرة' },
  { num: '28+', label: 'موظف' },
  { num: '3+', label: 'مشاريع نشطة' },
];

export default function WelcomePage() {
  const navigate = useNavigate();
  const [currentFeature, setCurrentFeature] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentFeature((prev) => (prev + 1) % features.length);
    }, 3000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a1628] via-[#0f1d35] to-[#0a1628] flex flex-col items-center justify-center px-4 py-8 relative overflow-hidden">
      {/* Background decorations */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 right-20 w-72 h-72 bg-green-500/5 rounded-full blur-3xl" />
        <div className="absolute bottom-20 left-20 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-green-500/3 rounded-full blur-[100px]" />
      </div>

      <div className="relative z-10 flex flex-col items-center max-w-2xl w-full">
        {/* Logo */}
        <div className="mb-6 animate-fade-in">
          <img
            src="/logo.png"
            alt="طلعت هائل"
            className="w-24 h-24 md:w-28 md:h-28 rounded-2xl shadow-2xl shadow-green-500/20 border-2 border-white/10 bg-white p-2"
          />
        </div>

        {/* Company Name */}
        <h1 className="text-4xl md:text-5xl font-black text-white mb-2 text-center tracking-tight">
          طلعت هائل
        </h1>
        <div className="flex items-center gap-3 mb-6">
          <div className="h-px w-12 bg-gradient-to-r from-transparent to-green-400" />
          <p className="text-green-400 text-base md:text-lg font-semibold">
            للخدمات والاستشارات الزراعية
          </p>
          <div className="h-px w-12 bg-gradient-to-l from-transparent to-green-400" />
        </div>

        {/* Feature badges */}
        <div className="flex flex-wrap justify-center gap-3 mb-8">
          {features.map((f, i) => (
            <span
              key={i}
              className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium border transition-all duration-500 ${
                i === currentFeature
                  ? 'bg-green-500/20 border-green-400/50 text-green-300 shadow-lg shadow-green-500/10'
                  : 'bg-white/5 border-white/10 text-gray-400'
              }`}
            >
              <span>{f.icon}</span>
              <span>{f.text}</span>
            </span>
          ))}
        </div>

        {/* CTA Buttons */}
        <div className="flex gap-4 mb-10">
          <button
            onClick={() => navigate('/login')}
            className="px-8 py-3 bg-gradient-to-r from-green-500 to-emerald-600 text-white font-bold rounded-xl shadow-lg shadow-green-500/30 hover:shadow-green-500/50 hover:scale-105 transition-all duration-300 text-sm"
          >
            سجل الآن
          </button>
          <button
            onClick={() => {
              const el = document.getElementById('mission-section');
              el?.scrollIntoView({ behavior: 'smooth' });
            }}
            className="px-8 py-3 bg-white/10 text-white font-bold rounded-xl border border-white/20 hover:bg-white/15 hover:scale-105 transition-all duration-300 text-sm backdrop-blur-sm"
          >
            تعرف علينا
          </button>
        </div>

        {/* Mission Card */}
        <div
          id="mission-section"
          className="w-full bg-white/5 backdrop-blur-md rounded-2xl border border-white/10 p-6 md:p-8 mb-8"
        >
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-green-500/20 flex items-center justify-center flex-shrink-0">
              <span className="text-2xl">🎯</span>
            </div>
            <div>
              <h3 className="text-white font-bold text-lg mb-2">رسالتنا</h3>
              <p className="text-gray-300 text-sm leading-relaxed">
                نسعى لأن نكون الخيار الأول في مجال الخدمات والاستشارات الزراعية في اليمن، من خلال تقديم حلول
                مبتكرة تلبي احتياجات عملائنا بأعلى معايير الجودة والكفاءة والاحترافية.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3 mt-5">
            {services.map((s, i) => (
              <span
                key={i}
                className="flex items-center gap-2 px-3 py-1.5 bg-white/5 rounded-lg text-xs text-gray-300 border border-white/5"
              >
                <span>{s.icon}</span>
                <span>{s.text}</span>
              </span>
            ))}
          </div>
        </div>

        {/* Stats */}
        <div className="flex gap-8 mb-8">
          {stats.map((s, i) => (
            <div key={i} className="text-center">
              <div className="text-2xl md:text-3xl font-black text-green-400">{s.num}</div>
              <div className="text-xs text-gray-500 mt-1">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Footer credit */}
        <p className="text-gray-600 text-xs">
          تصميم وتطوير{' '}
          <span className="text-gray-400 font-semibold">الغيث لتصميم التطبيقات والأنظمة</span>
        </p>
      </div>

      <style>{`
        @keyframes fade-in {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fade-in {
          animation: fade-in 0.8s ease forwards;
        }
      `}</style>
    </div>
  );
}
