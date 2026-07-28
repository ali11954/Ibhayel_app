import { useEffect, useRef } from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  size?: 'sm' | 'md' | 'lg';
}

export function Modal({ open, onClose, title, children, size = 'md' }: ModalProps) {
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="absolute inset-0 flex items-end sm:items-center justify-center sm:p-4 pointer-events-none">
        <div className={`relative bg-white rounded-t-2xl sm:rounded-2xl shadow-xl w-full pointer-events-auto flex flex-col ${
          size === 'sm' ? 'sm:max-w-md' : size === 'lg' ? 'sm:max-w-2xl' : 'sm:max-w-lg'
        }`} style={{ maxHeight: 'min(95vh, 90vh)' }}>
          <div className="flex items-center justify-between px-4 sm:px-6 py-3 sm:py-4 border-b border-gray-100 flex-shrink-0">
            <h2 className="text-base sm:text-lg font-bold text-gray-900 truncate">{title}</h2>
            <button onClick={onClose} className="p-2 rounded-lg hover:bg-gray-100 text-gray-500 flex-shrink-0">
              <X className="w-5 h-5" />
            </button>
          </div>
          <div ref={contentRef} className="flex-1 overflow-y-auto p-4 sm:p-6 min-h-0"
            style={{ WebkitOverflowScrolling: 'touch' }}>
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
