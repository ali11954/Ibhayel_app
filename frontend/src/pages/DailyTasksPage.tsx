import { useEffect, useState } from 'react';

type DailyTasksHeightMessage = {
  type?: string;
  height?: number;
};

export default function DailyTasksPage() {
  const [frameHeight, setFrameHeight] = useState(1100);

  useEffect(() => {
    const handleMessage = (event: MessageEvent<DailyTasksHeightMessage>) => {
      if (event.origin !== window.location.origin) return;

      const data = event.data;
      if (!data || data.type !== 'daily-tasks:height') return;

      const nextHeight = Number(data.height);
      if (Number.isFinite(nextHeight)) {
        setFrameHeight(Math.min(18000, Math.max(760, Math.ceil(nextHeight))));
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  return (
    <div className="w-full min-w-0 overflow-hidden">
      <iframe
        title="المهام اليومية"
        src="/daily-tasks/?embed=1"
        style={{
          width: '100%',
          height: `${frameHeight}px`,
          border: 0,
          display: 'block',
          background: 'transparent',
        }}
        loading="eager"
        referrerPolicy="same-origin"
      />
    </div>
  );
}
