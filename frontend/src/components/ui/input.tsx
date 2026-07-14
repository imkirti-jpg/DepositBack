import { Text, TextInput, View } from 'react-native';
import type { TextInputProps } from 'react-native';

type InputProps = TextInputProps & {
  label: string;
  errorMessage?: string;
  helperText?: string;
};

export function Input({ label, errorMessage, helperText, ...props }: InputProps) {
  return (
    <View className="mb-4 w-full">
      <Text className="mb-1.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">{label}</Text>
      <TextInput
        className={`h-12 rounded-xl border px-3.5 text-sm font-normal bg-white text-slate-700 ${
          errorMessage
            ? 'border-red-500 focus:border-red-600'
            : 'border-slate-300 focus:border-brand-500'
        }`}
        placeholderTextColor="#94a3b8"
        accessibilityLabel={label}
        accessibilityHint={helperText || errorMessage}
        {...props}
      />
      {errorMessage ? (
        <Text className="mt-1 text-xs font-semibold text-red-600">{errorMessage}</Text>
      ) : helperText ? (
        <Text className="mt-1 text-xs font-normal text-slate-400 leading-normal">{helperText}</Text>
      ) : null}
    </View>
  );
}
