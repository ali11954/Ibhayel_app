import { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown } from 'lucide-react';

interface SelectOption {
  value: string | number;
  label: string;
}

interface MobileSelectProps {
  value: string | number | '';
  onChange: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  className?: string;
}

export function MobileSelect({ value, onChange, options, placeholder = 'اختر...', className = '' }: MobileSelectProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ top: 0, left: 0, width: 0 });

  const calcPosition = useCallback(() => {
    if (ref.current) {
      const rect = ref.current.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      const dropdownHeight = Math.min(options.length * 42 + 44, 240);
      const openUp = spaceBelow < dropdownHeight && rect.top > dropdownHeight;
      setPosition({
        top: openUp ? rect.top - dropdownHeight - 4 : rect.bottom + 4,
        left: rect.left,
        width: rect.width,
      });
    }
  }, [options.length]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  useEffect(() => {
    if (open) calcPosition();
  }, [open, calcPosition]);

  const selected = options.find(o => String(o.value) === String(value));

  return (
    <div ref={ref} className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full h-10 px-3 rounded-lg border-2 border-gray-200 text-sm text-left flex items-center justify-between gap-2 bg-white focus:border-primary-500 outline-none"
      >
        <span className={`truncate ${selected ? 'text-gray-900' : 'text-gray-400'}`}>
          {selected?.label || placeholder}
        </span>
        <ChevronDown className={`w-4 h-4 text-gray-400 flex-shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && createPortal(
        <div
          className="fixed z-[9999] bg-white border border-gray-200 rounded-lg shadow-xl max-h-60 overflow-y-auto"
          style={{ top: position.top, left: position.left, width: position.width }}
        >
          <button
            type="button"
            onClick={() => { onChange(''); setOpen(false); }}
            className="w-full px-3 py-2.5 text-sm text-right text-gray-400 hover:bg-gray-50 border-b border-gray-100"
          >
            {placeholder}
          </button>
          {options.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => { onChange(String(opt.value)); setOpen(false); }}
              className={`w-full px-3 py-2.5 text-sm text-right hover:bg-primary-50 transition-colors ${
                String(opt.value) === String(value) ? 'bg-primary-50 text-primary-700 font-medium' : 'text-gray-700'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>,
        document.body
      )}
    </div>
  );
}
