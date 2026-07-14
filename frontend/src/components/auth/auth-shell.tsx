import { Text, View } from 'react-native';
import type { ReactNode } from 'react';

type AuthShellProps = {
  title: string;
  subtitle: string;
  children: ReactNode;
};

export function AuthShell({ title, subtitle, children }: AuthShellProps) {
  return (
    <View className="flex-1 bg-slate-50 px-6 pb-8 pt-16">
      <View className="mb-8">
        <Text className="text-3xl font-semibold text-slate-900">{title}</Text>
        <Text className="mt-2 text-sm text-slate-600">{subtitle}</Text>
      </View>

      <View className="rounded-2xl border border-slate-200 bg-white p-5">{children}</View>
    </View>
  );
}
