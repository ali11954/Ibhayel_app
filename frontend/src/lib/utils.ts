import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNum(n: number | undefined | null, decimals = 0): string {
  return (n ?? 0).toLocaleString('en-US', { maximumFractionDigits: decimals, minimumFractionDigits: decimals });
}

export function formatCurrency(amount: number): string {
  return formatNum(amount) + ' ر.ي';
}

export function formatDate(date: string): string {
  return new Date(date).toLocaleDateString('ar-YE');
}

export function formatDateTime(date: string): string {
  return new Date(date).toLocaleString('ar-YE');
}
