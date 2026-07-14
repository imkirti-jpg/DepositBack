import { View, Text, Pressable, ActivityIndicator } from 'react-native';

type UploadAreaProps = {
  onPress: () => void;
  loading?: boolean;
  fileName?: string;
  error?: string | null;
  label?: string;
  supportedFormats?: string;
};

export function UploadArea({
  onPress,
  loading = false,
  fileName,
  error,
  label = 'Upload lease file, notice, or evidence',
  supportedFormats = 'PDF, JPEG, PNG, or WEBP (Max 20MB)',
}: UploadAreaProps) {
  return (
    <Pressable
      onPress={onPress}
      disabled={loading}
      className={`border-2 border-dashed rounded-2xl p-6 items-center justify-center bg-slate-50/50 active:bg-slate-50 ${
        error
          ? 'border-red-400 bg-red-50/10'
          : fileName
            ? 'border-brand-400 bg-brand-50/10'
            : 'border-slate-300'
      }`}
      accessibilityRole="button"
      accessibilityLabel={fileName ? `File uploaded: ${fileName}` : label}
      accessibilityHint={fileName ? "Click to replace file" : "Double tap to select a file to upload"}
      accessibilityState={{ disabled: loading, busy: loading }}
    >
      {loading ? (
        <View className="items-center py-4">
          <ActivityIndicator color="#0f6cbd" size="large" />
          <Text className="mt-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Uploading and processing document...
          </Text>
        </View>
      ) : fileName ? (
        <View className="items-center py-2">
          <Text className="text-3xl mb-1">📄</Text>
          <Text className="text-sm font-semibold text-slate-800 text-center">{fileName}</Text>
          <Text className="mt-1 text-xs font-semibold text-brand-500">Click to replace file</Text>
        </View>
      ) : (
        <View className="items-center py-4">
          <Text className="text-4xl mb-2">📤</Text>
          <Text className="text-sm font-semibold text-slate-800 text-center">{label}</Text>
          <Text className="mt-1 text-xs font-normal text-slate-400 text-center">{supportedFormats}</Text>
          {error ? (
            <Text className="mt-3 text-xs font-semibold text-red-600 text-center">{error}</Text>
          ) : null}
        </View>
      )}
    </Pressable>
  );
}
