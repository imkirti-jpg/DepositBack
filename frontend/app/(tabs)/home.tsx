import { ScrollView, Text, View } from 'react-native';
import { Link } from 'expo-router';

import { useAuth } from '@/auth/auth-context';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

export default function HomeScreen() {
  const { logout, user } = useAuth();

  return (
    <ScrollView
      showsVerticalScrollIndicator={false}
      className="flex-1 bg-slate-50"
      contentContainerStyle={{ paddingHorizontal: 24, paddingVertical: 48 }}
    >
      {/* Premium Gradient Welcome Header Banner */}
      <View className="bg-brand-500 rounded-3xl p-6 shadow-md mb-6">
        <Text className="text-white text-xs font-semibold uppercase tracking-widest opacity-80">
          Tenant Dispute Portal
        </Text>
        <Text className="text-white text-3xl font-extrabold mt-1">DepositBack</Text>
        <Text className="text-white/90 text-sm mt-3 leading-relaxed">
          Hello! Securely track your security deposits, visual move-in/move-out evidence, landlord
          notice claims, and automatically generate recovery draft letters.
        </Text>
        <Text className="text-white/60 text-xs font-mono mt-4">Signed in: {user?.email}</Text>
      </View>

      {/* Quick Action Grid */}
      <Text className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-3">
        Quick Access
      </Text>
      <View className="flex-row gap-4 mb-6">
        <Link href="/(tabs)/properties" asChild className="flex-1">
          <View className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm justify-between min-h-[140px] active:bg-slate-50">
            <View>
              <Text className="text-2xl mb-1">🏢</Text>
              <Text className="text-base font-bold text-slate-800">Properties</Text>
              <Text className="text-xs text-slate-400 mt-1">Manage cases & agreements</Text>
            </View>
            <Text className="text-xs font-bold text-brand-500 mt-2">Open cases →</Text>
          </View>
        </Link>

        <Link href="/(tabs)/profile" asChild className="flex-1">
          <View className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm justify-between min-h-[140px] active:bg-slate-50">
            <View>
              <Text className="text-2xl mb-1">👤</Text>
              <Text className="text-base font-bold text-slate-800">My Profile</Text>
              <Text className="text-xs text-slate-400 mt-1">Account & notification rules</Text>
            </View>
            <Text className="text-xs font-bold text-brand-500 mt-2">Manage preferences →</Text>
          </View>
        </Link>
      </View>

      {/* Stepper dispute lifecycle guide */}
      <Card title="Dispute Recovery Blueprint">
        <View className="gap-5">
          <View className="flex-row gap-3">
            <View className="w-8 h-8 rounded-full bg-blue-100 items-center justify-center">
              <Text className="text-sm font-bold text-blue-700">1</Text>
            </View>
            <View className="flex-1">
              <Text className="text-sm font-bold text-slate-800">Add Property Details</Text>
              <Text className="text-xs text-slate-500 mt-0.5">
                Register addresses, lease terms, and deposit amount.
              </Text>
            </View>
          </View>

          <View className="flex-row gap-3">
            <View className="w-8 h-8 rounded-full bg-blue-100 items-center justify-center">
              <Text className="text-sm font-bold text-blue-700">2</Text>
            </View>
            <View className="flex-1">
              <Text className="text-sm font-bold text-slate-800">Log Evidence Folders</Text>
              <Text className="text-xs text-slate-500 mt-0.5">
                Upload move-in & move-out inspection pictures for complete item protection.
              </Text>
            </View>
          </View>

          <View className="flex-row gap-3">
            <View className="w-8 h-8 rounded-full bg-blue-100 items-center justify-center">
              <Text className="text-sm font-bold text-blue-700">3</Text>
            </View>
            <View className="flex-1">
              <Text className="text-sm font-bold text-slate-800">Verify AI Claims</Text>
              <Text className="text-xs text-slate-500 mt-0.5">
                Import deduction notices to run AI checks matching leases against logged evidence.
              </Text>
            </View>
          </View>

          <View className="flex-row gap-3">
            <View className="w-8 h-8 rounded-full bg-blue-100 items-center justify-center">
              <Text className="text-sm font-bold text-blue-700">4</Text>
            </View>
            <View className="flex-1">
              <Text className="text-sm font-bold text-slate-800">Generate Legal Drafts</Text>
              <Text className="text-xs text-slate-500 mt-0.5">
                Draft legal message scripts or formal letters to send to the landlord.
              </Text>
            </View>
          </View>
        </View>
      </Card>

      <View className="mt-8">
        <Button label="Sign Out" variant="danger" onPress={() => void logout()} />
      </View>
    </ScrollView>
  );
}
