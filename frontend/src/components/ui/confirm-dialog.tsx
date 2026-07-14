import { View, Text } from 'react-native';
import { Modal } from './modal';
import { Button } from './button';

type ConfirmDialogProps = {
  visible: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void | Promise<void>;
  onCancel: () => void;
  loading?: boolean;
  variant?: 'danger' | 'primary';
};

export function ConfirmDialog({
  visible,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  onConfirm,
  onCancel,
  loading = false,
  variant = 'primary',
}: ConfirmDialogProps) {
  return (
    <Modal visible={visible} onClose={onCancel} title={title}>
      <View className="gap-4">
        <Text className="text-sm font-medium text-slate-600 leading-relaxed">
          {message}
        </Text>
        <View className="mt-4 gap-2">
          <Button
            label={confirmLabel}
            variant={variant === 'danger' ? 'danger' : 'primary'}
            loading={loading}
            onPress={onConfirm}
          />
          <Button
            label={cancelLabel}
            variant="outline"
            disabled={loading}
            onPress={onCancel}
          />
        </View>
      </View>
    </Modal>
  );
}
