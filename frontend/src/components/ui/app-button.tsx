import { Button } from './button';
import type { PressableProps } from 'react-native';

type AppButtonProps = PressableProps & {
  label: string;
  loading?: boolean;
};

export function AppButton({ label, loading = false, disabled, ...props }: AppButtonProps) {
  return (
    <Button
      label={label}
      loading={loading}
      disabled={disabled}
      variant="primary"
      {...props}
    />
  );
}
