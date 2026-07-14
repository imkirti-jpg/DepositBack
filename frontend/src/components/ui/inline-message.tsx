import { Text } from 'react-native';

type InlineMessageProps = {
  type: 'error' | 'success';
  message: string;
};

export function InlineMessage({ type, message }: InlineMessageProps) {
  return (
    <Text className={`mb-4 text-xs font-semibold uppercase tracking-wider ${type === 'error' ? 'text-red-600' : 'text-emerald-700'}`}>
      {message}
    </Text>
  );
}
