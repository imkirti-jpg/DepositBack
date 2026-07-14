import * as DocumentPicker from 'expo-document-picker';
import * as ImagePicker from 'expo-image-picker';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  RefreshControl,
  ScrollView,
  Text,
  TextInput,
  View,
} from 'react-native';

import { Card } from '@/components/ui/card';
import { ErrorState } from '@/components/ui/error-state';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { Modal } from '@/components/ui/modal';
import { StatusBadge } from '@/components/ui/status-badge';
import { UploadArea } from '@/components/ui/upload-area';
import { ClaimCard } from '@/components/ui/claim-card';
import { useDashboard } from '@/hooks/use-dashboard';
import { useNotice, useNoticeClaims, useUploadNotice, useUpdateClaim } from '@/hooks/use-claims';
import type { ClaimLabel, ClaimResponse } from '@/services/claim.service';
import { Button } from '@/components/ui/button';

export default function ClaimsScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const propertyId = id.replace('claim-', '');

  // Queries
  const {
    data: dashboard,
    isLoading: isDashboardLoading,
    refetch: refetchDashboard,
  } = useDashboard(propertyId);
  const [localNoticeId, setLocalNoticeId] = useState<string | null | undefined>(undefined);
  const activeNoticeId = localNoticeId !== undefined ? localNoticeId : dashboard?.notice_id || null;

  const {
    data: notice,
    isLoading: isNoticeLoading,
    error: noticeError,
    refetch: refetchNotice,
  } = useNotice(activeNoticeId || '');
  const { data: claims, refetch: refetchClaims } = useNoticeClaims(activeNoticeId || '');

  // Mutations
  const uploadNoticeMutation = useUploadNotice();
  const updateClaimMutation = useUpdateClaim(propertyId, activeNoticeId || '');

  useEffect(() => {
    if (notice?.status === 'completed') {
      void refetchDashboard();
      void refetchClaims();
    }
  }, [notice?.status]);

  // Local UI State
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isLocalUploading, setIsLocalUploading] = useState(false);
  const [isPastingText, setIsPastingText] = useState(false);
  const [pastedText, setPastedText] = useState('');
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Claim override modal state
  const [selectedClaim, setSelectedClaim] = useState<ClaimResponse | null>(null);
  const [claimModalVisible, setClaimModalVisible] = useState(false);

  const handleUpload = async (uri?: string, name?: string, type?: string, text?: string) => {
    setUploadError(null);
    setIsLocalUploading(true);
    try {
      const newNotice = await uploadNoticeMutation.mutateAsync({
        propertyId,
        fileUri: uri,
        fileName: name,
        fileType: type,
        rawText: text,
      });
      setLocalNoticeId(newNotice.id);
      setIsPastingText(false);
      setPastedText('');
      refetchDashboard();
    } catch (e: any) {
      setUploadError(e?.message || 'Failed to upload deduction notice.');
    } finally {
      setIsLocalUploading(false);
    }
  };

  const handleCamera = async () => {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) {
      Alert.alert('Permission Denied', 'Camera permissions are required.');
      return;
    }
    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: 'images',
      quality: 0.5,
    });
    if (!result.canceled && result.assets && result.assets.length > 0) {
      const asset = result.assets[0];
      void handleUpload(
        asset.uri,
        asset.fileName || 'camera_notice.jpg',
        asset.mimeType || 'image/jpeg',
      );
    }
  };

  const handleGallery = async () => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert('Permission Denied', 'Media library permissions are required.');
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: 'images',
      quality: 0.5,
    });
    if (!result.canceled && result.assets && result.assets.length > 0) {
      const asset = result.assets[0];
      void handleUpload(
        asset.uri,
        asset.fileName || 'gallery_notice.jpg',
        asset.mimeType || 'image/jpeg',
      );
    }
  };

  const handlePdf = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: 'application/pdf',
        copyToCacheDirectory: true,
      });
      if (!result.canceled && result.assets && result.assets.length > 0) {
        const asset = result.assets[0];
        void handleUpload(asset.uri, asset.name, asset.mimeType || 'application/pdf');
      }
    } catch {
      setUploadError('Failed to open PDF document picker.');
    }
  };

  const handleClaimOverride = async (verdict: ClaimLabel) => {
    if (!selectedClaim) return;
    try {
      await updateClaimMutation.mutateAsync({
        claimId: selectedClaim.id,
        data: { user_override_label: verdict },
      });
      setClaimModalVisible(false);
      setSelectedClaim(null);
    } catch {
      // Handled by API layer
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await Promise.all([refetchDashboard(), refetchNotice(), refetchClaims()]);
    } catch {
      // Ignored
    } finally {
      setIsRefreshing(false);
    }
  };

  const renderNoticePanel = () => {
    if (isDashboardLoading) {
      return <LoadingSpinner message="Checking notice status..." />;
    }

    if (isLocalUploading) {
      return (
        <Card title="Deduction Notice">
          <View className="items-center py-6">
            <ActivityIndicator color="#0f6cbd" size="large" />
            <Text className="mt-3 text-sm font-medium text-slate-600">
              Uploading notice file...
            </Text>
          </View>
        </Card>
      );
    }

    if (!activeNoticeId) {
      return (
        <Card
          title="Deduction Notice"
          subtitle="Upload the notice document or copy-paste the text to analyze the deductions."
        >
          {isPastingText ? (
            <View className="mb-4 gap-3">
              <Text className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Paste Notice text
              </Text>
              <TextInput
                multiline
                numberOfLines={6}
                className="min-h-32 w-full rounded-xl border border-slate-300 bg-white p-3 text-base text-slate-900 focus:border-brand-500"
                placeholder="e.g. Landlord deduction notice details..."
                placeholderTextColor="#94a3b8"
                onChangeText={setPastedText}
                value={pastedText}
              />
              <View className="flex-row gap-2">
                <View className="flex-1">
                  <Button
                    label="Submit Text Notice"
                    disabled={!pastedText.trim()}
                    onPress={() => void handleUpload(undefined, undefined, undefined, pastedText)}
                  />
                </View>
                <View className="flex-1">
                  <Button
                    label="Cancel"
                    variant="outline"
                    onPress={() => setIsPastingText(false)}
                  />
                </View>
              </View>
            </View>
          ) : (
            <>
              <UploadArea
                onPress={handlePdf}
                error={uploadError}
                label="Select deduction notice (PDF or Image)"
              />
              <View className="mt-4 flex-row flex-wrap gap-2">
                <View className="flex-1 min-w-[45%]">
                  <Button label="Camera" variant="outline" onPress={handleCamera} />
                </View>
                <View className="flex-1 min-w-[45%]">
                  <Button label="Gallery" variant="outline" onPress={handleGallery} />
                </View>
                <View className="flex-1 min-w-[45%]">
                  <Button label="PDF File" variant="outline" onPress={handlePdf} />
                </View>
                <View className="flex-1 min-w-[45%]">
                  <Button
                    label="Paste Text"
                    variant="outline"
                    onPress={() => setIsPastingText(true)}
                  />
                </View>
              </View>
            </>
          )}
        </Card>
      );
    }

    if (isNoticeLoading && !notice) {
      return <LoadingSpinner message="Loading notice..." />;
    }

    if (noticeError || !notice) {
      return (
        <Card title="Deduction Notice">
          <ErrorState message="Failed to load notice details." onRetry={refetchNotice} />
          <Button
            label="Upload Different File"
            variant="outline"
            className="mt-4"
            onPress={() => setLocalNoticeId(null)}
          />
        </Card>
      );
    }

    return (
      <Card title="Deduction Notice">
        <View className="mb-4 flex-row items-center justify-between">
          <Text className="text-sm font-semibold text-slate-500">Analysis Status</Text>
          <StatusBadge status={notice.status} />
        </View>

        {notice.status === 'processing' && (
          <View className="items-center border border-slate-100 bg-slate-50 py-4 rounded-xl">
            <ActivityIndicator color="#0f6cbd" size="small" />
            <Text className="mt-2.5 text-xs font-medium text-slate-500">
              AI is analyzing deductions against the lease...
            </Text>
          </View>
        )}

        {notice.status === 'failed' && (
          <View className="gap-3">
            <Text className="text-sm font-medium text-red-600">
              {"Notice analysis failed. The format couldn't be parsed."}
            </Text>
            <Button label="Reupload" variant="outline" onPress={() => setLocalNoticeId(null)} />
          </View>
        )}

        {notice.status === 'completed' && (
          <View className="gap-4">
            <View className="border border-slate-100 bg-slate-50 p-4 gap-3 rounded-xl">
              <Text className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Notice Summary
              </Text>
              <View className="flex-row justify-between border-b border-slate-200/50 py-1">
                <Text className="text-sm text-slate-500">Total Deductions</Text>
                <Text className="text-sm font-bold text-slate-800">
                  INR {((Number(dashboard?.total_supported_amount) || 0) + (Number(dashboard?.total_disputed_amount) || 0)).toLocaleString('en-IN')}
                </Text>
              </View>
              <View className="flex-row justify-between py-1">
                <Text className="text-sm text-slate-500">Supported by Lease</Text>
                <Text className="text-sm font-bold text-emerald-600">
                  INR {dashboard?.total_supported_amount.toLocaleString('en-IN') || 0}
                </Text>
              </View>
            </View>

            <Button
              label="Upload Different Notice"
              variant="outline"
              onPress={() => setLocalNoticeId(null)}
            />
          </View>
        )}
      </Card>
    );
  };

  return (
    <View className="flex-1 bg-slate-50 px-6 pb-6 pt-12">
      <View className="mb-6 flex-row items-center justify-between">
        <View>
          <Text className="text-xs font-semibold uppercase tracking-wider text-brand-500">
            Dispute Claims
          </Text>
          <Text className="text-3xl font-bold text-slate-900">Claims Analysis</Text>
        </View>
        <Button
          label="Back"
          variant="outline"
          onPress={() => {
            if (router.canGoBack()) {
              router.back();
            } else {
              router.replace('/(tabs)/properties');
            }
          }}
        />
      </View>

      <FlatList
        data={claims || []}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <View className="mb-4">
            <ClaimCard
              title={item.item_description}
              amount={item.claimed_amount || 0}
              verdict={item.effective_label || item.label}
              reasoning={item.reasoning}
              evidenceRefs={item.evidence_refs}
              confidence={
                typeof item.evidence_refs?.confidence === 'number'
                  ? item.evidence_refs.confidence
                  : undefined
              }
            />
            <Button
              label="Override Verdict"
              variant="outline"
              className="mt-2"
              onPress={() => {
                setSelectedClaim(item);
                setClaimModalVisible(true);
              }}
            />
          </View>
        )}
        ListHeaderComponent={
          <View className="mb-6">
            {renderNoticePanel()}
            {claims && claims.length > 0 ? (
              <Text className="mb-2 text-lg font-bold text-slate-900">Claim Breakdown</Text>
            ) : null}
          </View>
        }
        ListEmptyComponent={
          activeNoticeId && notice?.status === 'completed' ? (
            <Card>
              <Text className="py-4 text-center text-sm text-slate-400">
                No claims detected in this notice.
              </Text>
            </Card>
          ) : null
        }
        refreshControl={
          <RefreshControl
            refreshing={isRefreshing}
            onRefresh={handleRefresh}
            colors={['#0f6cbd']}
          />
        }
        contentContainerStyle={{ paddingBottom: 24 }}
        showsVerticalScrollIndicator={false}
      />

      {/* Modal for overriding claim label */}
      <Modal
        visible={claimModalVisible}
        onClose={() => {
          setClaimModalVisible(false);
          setSelectedClaim(null);
        }}
        title="Override Verdict"
      >
        {selectedClaim && (
          <ScrollView showsVerticalScrollIndicator={false} className="max-h-96">
            <Text className="mb-4 text-xs font-semibold text-slate-500">
              Claim Description: {selectedClaim.item_description}
            </Text>
            <Text className="mb-4 text-xs font-semibold text-slate-500">
              Amount: INR {selectedClaim.claimed_amount?.toLocaleString('en-IN')}
            </Text>
            <Text className="mb-4 text-sm font-semibold text-slate-700">
              Choose a verdict to override the AI recommendation:
            </Text>

            <View className="gap-2">
              <Button
                label="Supported"
                variant="outline"
                className="border-emerald-200 bg-emerald-50"
                onPress={() => void handleClaimOverride('supported')}
              />
              <Button
                label="Weak / Debatable"
                variant="outline"
                className="border-sky-200 bg-sky-50"
                onPress={() => void handleClaimOverride('weak')}
              />
              <Button
                label="Unsupported"
                variant="outline"
                className="border-red-200 bg-red-50"
                onPress={() => void handleClaimOverride('unsupported')}
              />
              <Button
                label="Unclear / Need Info"
                variant="outline"
                className="border-indigo-200 bg-indigo-50"
                onPress={() => void handleClaimOverride('unclear')}
              />
            </View>

            <Button
              label="Cancel"
              variant="outline"
              className="mt-4"
              onPress={() => {
                setClaimModalVisible(false);
                setSelectedClaim(null);
              }}
            />
          </ScrollView>
        )}
      </Modal>
    </View>
  );
}
