import { ActivityIndicator, Pressable, Text } from 'react-native';
import type { PressableProps } from 'react-native';

export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'danger' | 'ghost';

type ButtonProps = PressableProps & {
  label: string;
  variant?: ButtonVariant;
  loading?: boolean;
};

export function Button({
  label,
  variant = 'primary',
  loading = false,
  disabled,
  ...props
}: ButtonProps) {
  const isDisabled = disabled || loading;

  const getVariantStyles = () => {
    if (isDisabled) {
      return 'bg-slate-100 border border-slate-200/60 opacity-60';
    }
    switch (variant) {
      case 'secondary':
        return 'bg-slate-100 border border-slate-200 active:bg-slate-200';
      case 'outline':
        return 'bg-transparent border border-slate-300 active:bg-slate-50';
      case 'danger':
        return 'bg-red-600 active:bg-red-700';
      case 'ghost':
        return 'bg-transparent active:bg-slate-100';
      case 'primary':
      default:
        return 'bg-brand-500 active:bg-brand-600';
    }
  };

  const getLabelStyles = () => {
    if (isDisabled) {
      return 'text-slate-400';
    }
    switch (variant) {
      case 'secondary':
        return 'text-slate-700';
      case 'outline':
        return 'text-slate-700';
      case 'danger':
        return 'text-white';
      case 'ghost':
        return 'text-slate-600';
      case 'primary':
      default:
        return 'text-white';
    }
  };

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: isDisabled, busy: loading }}
      disabled={isDisabled}
      className={`h-12 items-center justify-center rounded-xl px-5 flex-row gap-2 ${getVariantStyles()}`}
      {...props}
    >
      {loading ? (
        <ActivityIndicator
          color={variant === 'outline' || variant === 'secondary' || variant === 'ghost' ? '#475569' : '#ffffff'}
          size="small"
        />
      ) : (
        <Text className={`text-sm font-semibold tracking-wide ${getLabelStyles()}`}>{label}</Text>
      )}
    </Pressable>
  );
}
