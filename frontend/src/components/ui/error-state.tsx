import { View, Text } from 'react-native';
import { Button } from './button';

type ErrorStateProps = {
  title?: string;
  message: string;
  onRetry?: () => void;
};

export function ErrorState({ title = 'Something went wrong', message, onRetry }: ErrorStateProps) {
  return (
    <View className="items-center justify-center p-8 rounded-2xl border border-red-200 bg-red-50/5">
      <Text className="text-5xl mb-3">⚠️</Text>
      <Text className="text-lg font-bold text-red-800 tracking-tight text-center leading-snug">{title}</Text>
      <Text className="mt-2 mb-6 text-sm font-normal text-red-600/80 text-center max-w-xs leading-relaxed">{message}</Text>
      {onRetry ? <Button label="Try Again" onPress={onRetry} /> : null}
    </View>
  );
}
