import { View, Text } from 'react-native';

type ProgressCardProps = {
  step: number;
  totalSteps: number;
  label: string;
};

export function ProgressCard({ step, totalSteps, label }: ProgressCardProps) {
  const percentage = Math.round((step / totalSteps) * 100);

  return (
    <View className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <View className="flex-row justify-between items-center mb-2">
        <Text className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          Step {step} of {totalSteps}
        </Text>
        <Text className="text-xs font-bold text-brand-500">{percentage}% Complete</Text>
      </View>
      <Text className="text-base font-bold text-slate-800 tracking-tight leading-snug mb-3">{label}</Text>

      {/* Progress Bar background */}
      <View className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
        {/* Progress Bar foreground fill */}
        <View style={{ width: `${percentage}%` }} className="h-full bg-brand-500 rounded-full" />
      </View>
    </View>
  );
}
