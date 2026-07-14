import { Modal as RNModal, Pressable, Text, View } from 'react-native';
import type { ReactNode } from 'react';

type ModalProps = {
  visible: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
};

export function Modal({ visible, onClose, title, children }: ModalProps) {
  return (
    <RNModal transparent visible={visible} animationType="fade" onRequestClose={onClose} accessibilityViewIsModal={true}>
      <Pressable 
        onPress={onClose} 
        className="flex-1 bg-black/40 items-center justify-center p-6"
        accessibilityLabel="Close modal overlay backdrop"
      >
        <Pressable
          className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-6 shadow-xl"
          onPress={(e) => e.stopPropagation()}
        >
          <View className="flex-row items-center justify-between mb-4">
            <Text className="text-xl font-bold text-slate-900">{title}</Text>
            <Pressable 
              onPress={onClose} 
              className="w-11 h-11 items-center justify-center active:bg-slate-100 rounded-lg"
              accessibilityRole="button"
              accessibilityLabel="Close Modal"
            >
              <Text className="text-lg font-semibold text-slate-500">✕</Text>
            </Pressable>
          </View>
          {children}
        </Pressable>
      </Pressable>
    </RNModal>
  );
}
