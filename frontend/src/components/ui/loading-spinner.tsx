import { ActivityIndicator, View, Text } from 'react-native';

type LoadingSpinnerProps = {
  fullscreen?: boolean;
  message?: string;
};

export function LoadingSpinner({
  fullscreen = false,
  message = 'Loading...',
}: LoadingSpinnerProps) {
  if (fullscreen) {
    return (
      <View className="flex-1 items-center justify-center bg-slate-50 p-6">
        <ActivityIndicator color="#0f6cbd" size="large" />
        {message ? (
          <Text className="mt-4 text-sm font-normal text-slate-500 leading-normal">{message}</Text>
        ) : null}
      </View>
    );
  }

  return (
    <View className="flex-row items-center justify-center p-4 gap-2">
      <ActivityIndicator color="#0f6cbd" size="small" />
      {message ? <Text className="text-sm font-normal text-slate-500 leading-normal">{message}</Text> : null}
    </View>
  );
}
