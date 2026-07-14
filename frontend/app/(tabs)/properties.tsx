import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { ScrollView, Text, View } from 'react-native';
import { z } from 'zod';

import { EmptyState } from '@/components/ui/empty-state';
import { ErrorState } from '@/components/ui/error-state';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { Modal } from '@/components/ui/modal';
import { PropertyCard } from '@/components/ui/property-card';
import { useCreateProperty, useProperties } from '@/hooks/use-properties';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

const createPropertySchema = z.object({
  label: z.string().min(1, 'Property label/title is required.'),
  address: z.string().optional(),
  deposit_amount: z.number().positive('Deposit amount must be a positive number.'),
  lease_start_date: z.string().optional(),
  lease_end_date: z.string().optional(),
});

type CreatePropertyFormValues = z.infer<typeof createPropertySchema>;

export default function PropertiesScreen() {
  const { data: properties, isLoading, error, refetch } = useProperties();
  const createPropertyMutation = useCreateProperty();
  const [modalVisible, setModalVisible] = useState(false);

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreatePropertyFormValues>({
    resolver: zodResolver(createPropertySchema),
    defaultValues: {
      label: '',
      address: '',
      deposit_amount: undefined,
      lease_start_date: '',
      lease_end_date: '',
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    try {
      await createPropertyMutation.mutateAsync({
        label: values.label,
        address: values.address || undefined,
        deposit_amount: values.deposit_amount,
        lease_start_date: values.lease_start_date || undefined,
        lease_end_date: values.lease_end_date || undefined,
      });
      setModalVisible(false);
      reset();
    } catch {
      // Handled by react-query mutation
    }
  });

  if (isLoading) {
    return <LoadingSpinner fullscreen message="Fetching your properties..." />;
  }

  if (error) {
    return (
      <View className="flex-1 justify-center bg-slate-50 px-6">
        <ErrorState
          message={error instanceof Error ? error.message : 'Failed to load properties'}
          onRetry={refetch}
        />
      </View>
    );
  }

  return (
    <View className="flex-1 bg-slate-50 px-6 pb-6 pt-12">
      <View className="mb-6 flex-row items-center justify-between">
        <View>
          <Text className="text-3xl font-bold text-slate-900">Properties</Text>
          <Text className="mt-0.5 text-xs text-slate-500">
            Manage your rental property disputes
          </Text>
        </View>
        <Button label="Add Property" onPress={() => setModalVisible(true)} />
      </View>

      {properties && properties.length > 0 ? (
        <ScrollView className="flex-1 gap-4">
          {properties.map((property) => (
            <View key={property.id} className="mb-4">
              <PropertyCard
                id={property.id}
                label={property.label}
                address={property.address || undefined}
                depositAmount={property.deposit_amount}
                status={property.status}
              />
            </View>
          ))}
        </ScrollView>
      ) : (
        <View className="flex-1 justify-center">
          <EmptyState
            title="No Properties Yet"
            description="Add your first property address and deposit amount to start the dispute verifications."
            actionLabel="Add Property"
            onAction={() => setModalVisible(true)}
          />
        </View>
      )}

      <Modal visible={modalVisible} onClose={() => setModalVisible(false)} title="Add Property">
        <ScrollView showsVerticalScrollIndicator={false} className="max-h-96">
          <Controller
            control={control}
            name="label"
            render={({ field: { onChange, onBlur, value } }) => (
              <Input
                label="Label / Nickname"
                placeholder="e.g. 2BHK Indiranagar"
                onBlur={onBlur}
                onChangeText={onChange}
                value={value}
                errorMessage={errors.label?.message}
              />
            )}
          />

          <Controller
            control={control}
            name="address"
            render={({ field: { onChange, onBlur, value } }) => (
              <Input
                label="Full Address (Optional)"
                placeholder="Enter street, city, state"
                onBlur={onBlur}
                onChangeText={onChange}
                value={value}
                errorMessage={errors.address?.message}
              />
            )}
          />

          <Controller
            control={control}
            name="deposit_amount"
            render={({ field: { onChange, onBlur, value } }) => (
              <Input
                label="Security Deposit Amount"
                placeholder="e.g. 50000"
                keyboardType="numeric"
                onBlur={onBlur}
                onChangeText={(text) => onChange(text === '' ? undefined : Number(text))}
                value={value !== undefined ? String(value) : ''}
                errorMessage={errors.deposit_amount?.message}
              />
            )}
          />

          <Controller
            control={control}
            name="lease_start_date"
            render={({ field: { onChange, onBlur, value } }) => (
              <Input
                label="Lease Start Date (YYYY-MM-DD)"
                placeholder="e.g. 2025-01-01"
                onBlur={onBlur}
                onChangeText={onChange}
                value={value}
                errorMessage={errors.lease_start_date?.message}
              />
            )}
          />

          <Controller
            control={control}
            name="lease_end_date"
            render={({ field: { onChange, onBlur, value } }) => (
              <Input
                label="Lease End Date (YYYY-MM-DD)"
                placeholder="e.g. 2026-01-01"
                onBlur={onBlur}
                onChangeText={onChange}
                value={value}
                errorMessage={errors.lease_end_date?.message}
              />
            )}
          />

          <View className="mt-4 gap-2">
            <Button
              label="Create Case"
              loading={createPropertyMutation.isPending}
              onPress={() => void onSubmit()}
            />
            <Button label="Cancel" variant="outline" onPress={() => setModalVisible(false)} />
          </View>
        </ScrollView>
      </Modal>
    </View>
  );
}
