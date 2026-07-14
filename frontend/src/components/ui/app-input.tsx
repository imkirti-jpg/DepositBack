import { View } from 'react-native';
import { Input } from './input';
import type { TextInputProps } from 'react-native';

type AppInputProps = TextInputProps & {
  label: string;
  errorMessage?: string;
};

export function AppInput({ label, errorMessage, ...props }: AppInputProps) {
  return (
    <View className="mb-4">
      <Input
        label={label}
        errorMessage={errorMessage}
        {...props}
      />
    </View>
  );
}
