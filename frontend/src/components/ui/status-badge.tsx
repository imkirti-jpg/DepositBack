import { View, Text } from 'react-native';

export type BadgeType =
  | 'processing'
  | 'needs_review'
  | 'confirmed'
  | 'completed'
  | 'failed'
  | 'supported'
  | 'weak'
  | 'unsupported'
  | 'unclear'
  | 'draft'
  | 'sent';

type StatusBadgeProps = {
  status: BadgeType;
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const getColors = () => {
    switch (status) {
      case 'completed':
      case 'confirmed':
      case 'supported':
      case 'sent':
        return { bg: 'bg-emerald-50 border-emerald-200', text: 'text-emerald-700' };

      case 'processing':
      case 'draft':
        return { bg: 'bg-amber-50 border-amber-200', text: 'text-amber-700' };

      case 'needs_review':
      case 'unclear':
        return { bg: 'bg-indigo-50 border-indigo-200', text: 'text-indigo-700' };

      case 'weak':
        return { bg: 'bg-sky-50 border-sky-200', text: 'text-sky-700' };

      case 'failed':
      case 'unsupported':
      default:
        return { bg: 'bg-red-50 border-red-200', text: 'text-red-700' };
    }
  };

  const colors = getColors();

  return (
    <View className={`border rounded-full px-2.5 py-0.5 self-start ${colors.bg}`}>
      <Text className={`text-[10px] font-bold uppercase tracking-widest ${colors.text}`}>
        {status.replace('_', ' ')}
      </Text>
    </View>
  );
}
