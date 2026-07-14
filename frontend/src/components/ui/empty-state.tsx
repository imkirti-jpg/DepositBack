import { View, Text } from 'react-native';
import { Button } from './button';

type EmptyStateProps = {
  title: string;
  description: string;
  icon?: string;
  actionLabel?: string;
  onAction?: () => void;
};

export function EmptyState({
  title,
  description,
  icon = '📭',
  actionLabel,
  onAction,
}: EmptyStateProps) {
  return (
    <View className="items-center justify-center p-8 rounded-2xl border border-slate-200 bg-white">
      <Text className="text-5xl mb-3">{icon}</Text>
      <Text className="text-lg font-bold text-slate-800 tracking-tight text-center leading-snug">{title}</Text>
      <Text className="mt-2 mb-6 text-sm font-normal text-slate-400 text-center max-w-xs leading-relaxed">{description}</Text>
      {actionLabel && onAction ? <Button label={actionLabel} onPress={onAction} /> : null}
    </View>
  );
}
