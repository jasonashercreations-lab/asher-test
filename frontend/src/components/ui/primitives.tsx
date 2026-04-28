import * as React from 'react';
import { cn } from '@/lib/utils';
import * as RSlider from '@radix-ui/react-slider';
import * as RSwitch from '@radix-ui/react-switch';

export const Button = React.forwardRef<HTMLButtonElement, React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'default' | 'ghost' | 'accent' | 'danger' }>(
  ({ className, variant = 'default', ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-md border text-sm font-medium px-3 py-1.5 transition-colors',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        variant === 'default' && 'bg-panel-2 border-border hover:bg-border text-text',
        variant === 'ghost'   && 'bg-transparent border-transparent hover:bg-panel-2 text-text',
        variant === 'accent'  && 'bg-accent text-black border-transparent hover:opacity-90',
        variant === 'danger'  && 'bg-red-900 border-red-800 hover:bg-red-800 text-white',
        className,
      )}
      {...props}
    />
  ),
);

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        'w-full rounded-md border border-border bg-panel px-2 py-1 text-sm',
        'focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent',
        className,
      )}
      {...props}
    />
  ),
);

export const Select = React.forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, ...props }, ref) => (
    <select
      ref={ref}
      className={cn(
        'w-full rounded-md border border-border bg-panel px-2 py-1 text-sm cursor-pointer',
        'focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent',
        className,
      )}
      {...props}
    />
  ),
);

export function Slider({
  value, min = 0, max = 1, step = 0.01, onChange,
}: { value: number; min?: number; max?: number; step?: number; onChange: (v: number) => void }) {
  return (
    <RSlider.Root
      className="relative flex items-center select-none touch-none w-full h-5"
      value={[value]} min={min} max={max} step={step}
      onValueChange={([v]) => onChange(v)}
    >
      <RSlider.Track className="bg-panel-2 relative grow rounded-full h-1">
        <RSlider.Range className="absolute bg-accent rounded-full h-full" />
      </RSlider.Track>
      <RSlider.Thumb className="block w-3 h-3 bg-accent rounded-full shadow focus:outline-none" />
    </RSlider.Root>
  );
}

export function Switch({ checked, onChange }: { checked: boolean; onChange: (b: boolean) => void }) {
  return (
    <RSwitch.Root
      checked={checked}
      onCheckedChange={onChange}
      className="w-9 h-5 bg-panel-2 rounded-full relative data-[state=checked]:bg-accent transition-colors border border-border"
    >
      <RSwitch.Thumb className="block w-4 h-4 bg-text rounded-full transition-transform translate-x-0.5 will-change-transform data-[state=checked]:translate-x-[18px]" />
    </RSwitch.Root>
  );
}

export function Section({ title, children, action }: { title: string; children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="px-3 py-2 border-b border-border">
      <div className="flex items-center justify-between mb-2">
        <div className="text-[11px] uppercase tracking-wider text-muted font-semibold">{title}</div>
        {action}
      </div>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

export function Field({ label, children, hint }: { label: string; children: React.ReactNode; hint?: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <label className="text-xs text-muted shrink-0" title={hint}>{label}</label>
      <div className="flex-1 min-w-0 flex justify-end items-center gap-2">{children}</div>
    </div>
  );
}

export function ColorField({ value, onChange }: { value: { r: number; g: number; b: number }; onChange: (rgb: { r: number; g: number; b: number }) => void }) {
  const hex = '#' + [value.r, value.g, value.b].map((v) => v.toString(16).padStart(2, '0')).join('');
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs font-mono text-muted">{hex}</span>
      <input
        type="color"
        value={hex}
        onChange={(e) => {
          const h = e.target.value.replace('#', '');
          onChange({
            r: parseInt(h.slice(0, 2), 16),
            g: parseInt(h.slice(2, 4), 16),
            b: parseInt(h.slice(4, 6), 16),
          });
        }}
      />
    </div>
  );
}
