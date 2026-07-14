import { View, Text } from 'react-native';
import type { ReactNode } from 'react';

type CardProps = {
  title?: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
};

export function Card({ title, subtitle, children, className = '' }: CardProps) {
  return (
    <View className={`rounded-2xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>
      {title ? (
        <View className="mb-4">
          <Text className="text-lg font-bold text-slate-800 tracking-tight leading-snug">{title}</Text>
          {subtitle ? <Text className="text-xs font-medium text-slate-400 mt-1 leading-relaxed">{subtitle}</Text> : null}
        </View>
      ) : null}
      {children}
    </View>
  );
}
