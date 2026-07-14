import { View, Text, Pressable } from 'react-native';
import { Link } from 'expo-router';
import { StatusBadge } from './status-badge';

type PropertyCardProps = {
  id: string;
  label: string;
  address?: string;
  depositAmount: number;
  status: 'active' | 'resolved';
};

export function PropertyCard({ id, label, address, depositAmount, status }: PropertyCardProps) {
  return (
    <Link href={{ pathname: '/property/[id]', params: { id } }} asChild>
      <Pressable 
        className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm active:opacity-95 active:scale-[0.99] transition-all"
        accessibilityRole="button"
        accessibilityLabel={`Property Case: ${label}, Status: ${status === 'active' ? 'active' : 'resolved'}`}
        accessibilityHint="Double tap to open case cockpit"
      >
        <View className="flex-row justify-between items-start mb-3 gap-2">
          <View className="flex-1">
            <Text className="text-lg font-bold text-slate-800 tracking-tight">{label}</Text>
            {address ? (
              <Text className="text-xs text-slate-500 mt-1 font-medium">{address}</Text>
            ) : null}
          </View>
          <StatusBadge status={status === 'active' ? 'processing' : 'completed'} />
        </View>

        <View className="flex-row justify-between items-center py-2.5 border-t border-slate-100/60 mt-2">
          <Text className="text-[11px] font-bold text-slate-500 uppercase tracking-widest">
            Security Deposit
          </Text>
          <Text className="text-base font-extrabold text-slate-800">
            INR {depositAmount.toLocaleString('en-IN')}
          </Text>
        </View>
      </Pressable>
    </Link>
  );
}
