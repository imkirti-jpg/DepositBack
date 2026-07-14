import { zodResolver } from '@hookform/resolvers/zod';
import * as DocumentPicker from 'expo-document-picker';
import * as ImagePicker from 'expo-image-picker';
import { Link, useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import {
  ActivityIndicator,
  Alert,
  Image,
  Platform,
  RefreshControl,
  ScrollView,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { z } from 'zod';

import { Card } from '@/components/ui/card';
import { ErrorState } from '@/components/ui/error-state';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { Modal } from '@/components/ui/modal';
import { StatusBadge } from '@/components/ui/status-badge';
import { UploadArea } from '@/components/ui/upload-area';
import { useDashboard } from '@/hooks/use-dashboard';
import { useLease, useReextractLease, useUploadLease, useUpdateLease } from '@/hooks/use-lease';
import { useProperty, useUpdateProperty, useDeleteProperty } from '@/hooks/use-properties';
import { useEvidenceList, useUploadEvidence, useDeleteEvidence, useReplaceEvidence, useRestoreEvidence } from '@/hooks/use-evidence';
import { ImageViewer } from '@/components/ui/image-viewer';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ConfirmDialog } from '@/components/ui/confirm-dialog';

const updatePropertySchema = z.object({
  label: z.string().min(1, 'Property label/title is required.'),
  address: z.string().optional(),
  deposit_amount: z.number().positive('Deposit amount must be a positive number.'),
  lease_start_date: z.string().optional(),
  lease_end_date: z.string().optional(),
  status: z.enum(['active', 'resolved']),
});

type UpdatePropertyFormValues = z.infer<typeof updatePropertySchema>;

export default function PropertyDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();

  // Queries
  const {
    data: property,
    isLoading: isPropertyLoading,
    error: propertyError,
    refetch: refetchProperty,
  } = useProperty(id);
  const {
    data: dashboard,
    isLoading: isDashboardLoading,
    refetch: refetchDashboard,
  } = useDashboard(id);

  const [localLeaseId, setLocalLeaseId] = useState<string | null | undefined>(undefined);
  const activeLeaseId = localLeaseId !== undefined ? localLeaseId : dashboard?.lease_id || null;

  const {
    data: lease,
    isLoading: isLeaseLoading,
    error: leaseError,
    refetch: refetchLease,
  } = useLease(activeLeaseId || '');

  // Evidence Queries & Mutations
  const [includeDeleted, setIncludeDeleted] = useState(false);
  const { data: evidenceList, isLoading: isEvidenceLoading } = useEvidenceList(id, undefined, includeDeleted);

  const updatePropertyMutation = useUpdateProperty(id);
  const uploadLeaseMutation = useUploadLease();
  const reextractMutation = useReextractLease(activeLeaseId || '');
  const uploadEvidenceMutation = useUploadEvidence();
  const deleteEvidenceMutation = useDeleteEvidence(id);
  const replaceEvidenceMutation = useReplaceEvidence(id);
  const restoreEvidenceMutation = useRestoreEvidence(id);
  const deletePropertyMutation = useDeleteProperty();

  // Local state
  const [modalVisible, setModalVisible] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isLocalUploading, setIsLocalUploading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showAllEvidence, setShowAllEvidence] = useState(false);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await Promise.all([refetchProperty(), refetchDashboard(), refetchLease()]);
    } catch {
      // Ignored
    } finally {
      setIsRefreshing(false);
    }
  };

  // Evidence upload form state
  const [pendingFiles, setPendingFiles] = useState<{
    uri: string;
    name: string;
    type: string;
  }[]>([]);
  const [evidenceModalVisible, setEvidenceModalVisible] = useState(false);
  const [evidenceCategory, setEvidenceCategory] = useState('move_in');
  const [roomLabel, setRoomLabel] = useState('');
  const [evidenceNotes, setEvidenceNotes] = useState('');
  const [evidenceUploadError, setEvidenceUploadError] = useState<string | null>(null);

  // Full Screen Image Viewer State
  const [viewerVisible, setViewerVisible] = useState(false);
  const [selectedEvidence, setSelectedEvidence] = useState<any>(null);

  // Action Menu State (Web-friendly action sheet)
  const [actionMenuVisible, setActionMenuVisible] = useState(false);
  const [actionMenuItem, setActionMenuItem] = useState<any>(null);

  const updateLeaseMutation = useUpdateLease(activeLeaseId || '');

  // Confirm dialog state variables
  const [deletePropConfirmVisible, setDeletePropConfirmVisible] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleteEvidenceConfirmVisible, setDeleteEvidenceConfirmVisible] = useState(false);
  const [replaceEvidenceConfirmVisible, setReplaceEvidenceConfirmVisible] = useState(false);
  const [reextractConfirmVisible, setReextractConfirmVisible] = useState(false);
  const [evidenceToAction, setEvidenceToAction] = useState<any>(null);

  // Lease editing form state
  const [leaseModalVisible, setLeaseModalVisible] = useState(false);
  const [editTenantName, setEditTenantName] = useState('');
  const [editLandlordName, setEditLandlordName] = useState('');
  const [editDepositAmount, setEditDepositAmount] = useState('');
  const [editMonthlyRent, setEditMonthlyRent] = useState('');
  const [leaseUpdateError, setLeaseUpdateError] = useState<string | null>(null);

  const handleOpenLeaseEdit = () => {
    if (!lease) return;
    const getVal = (field: any) => {
      if (field && typeof field === 'object' && 'value' in field) {
        return field.value;
      }
      return field;
    };
    setEditTenantName(getVal(lease.extracted_fields?.tenant_name) || '');
    setEditLandlordName(getVal(lease.extracted_fields?.landlord_name) || '');
    const depVal = getVal(
      lease.extracted_fields?.deposit_amount || lease.extracted_fields?.security_deposit,
    );
    setEditDepositAmount(depVal !== undefined && depVal !== null ? String(depVal) : '');
    const rentVal = getVal(lease.extracted_fields?.monthly_rent);
    setEditMonthlyRent(rentVal !== undefined && rentVal !== null ? String(rentVal) : '');
    setLeaseUpdateError(null);
    setLeaseModalVisible(true);
  };

  const handleSaveLease = async () => {
    if (!activeLeaseId || !lease) return;
    setLeaseUpdateError(null);
    try {
      const depositVal = editDepositAmount.trim();
      const rentVal = editMonthlyRent.trim();

      const payload: Record<string, any> = {
        ...lease.extracted_fields,
        tenant_name: editTenantName.trim() || null,
        landlord_name: editLandlordName.trim() || null,
        deposit_amount: depositVal ? Number(depositVal) : null,
        security_deposit: depositVal ? Number(depositVal) : null,
        monthly_rent: rentVal ? Number(rentVal) : null,
      };

      await updateLeaseMutation.mutateAsync(payload);
      setLeaseModalVisible(false);
    } catch (e: any) {
      setLeaseUpdateError(e?.message || 'Failed to update lease terms.');
    }
  };

  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<UpdatePropertyFormValues>({
    resolver: zodResolver(updatePropertySchema),
    values: property
      ? {
          label: property.label,
          address: property.address || '',
          deposit_amount: Number(property.deposit_amount),
          lease_start_date: property.lease_start_date || '',
          lease_end_date: property.lease_end_date || '',
          status: property.status,
        }
      : undefined,
  });

  const onSubmit = handleSubmit(async (values) => {
    try {
      await updatePropertyMutation.mutateAsync({
        label: values.label,
        address: values.address || undefined,
        deposit_amount: values.deposit_amount,
        lease_start_date: values.lease_start_date || undefined,
        lease_end_date: values.lease_end_date || undefined,
        status: values.status,
      });
      setModalVisible(false);
    } catch {
      // Handled by mutation error interceptor
    }
  });

  const handleUpload = async (uri: string, name: string, type: string) => {
    setUploadError(null);
    setIsLocalUploading(true);
    try {
      const newLease = await uploadLeaseMutation.mutateAsync({
        propertyId: id,
        fileUri: uri,
        fileName: name,
        fileType: type,
      });
      setLocalLeaseId(newLease.id);
      refetchDashboard();
    } catch (e: any) {
      setUploadError(e?.message || 'Failed to upload lease file.');
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
        asset.fileName || 'camera_lease.jpg',
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
        asset.fileName || 'gallery_lease.jpg',
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

  // Evidence Picker Actions
  const handleEvidenceFilesPicked = (picked: { uri: string; name: string; type: string }[], defaultCategory = 'move_in') => {
    setPendingFiles(picked);
    setEvidenceCategory(defaultCategory);
    setEvidenceUploadError(null);
    setEvidenceModalVisible(true);
  };

  const handleEvidenceCamera = async (category: string) => {
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
      handleEvidenceFilesPicked([{
        uri: asset.uri,
        name: asset.fileName || 'evidence_camera.jpg',
        type: asset.mimeType || 'image/jpeg',
      }], category);
    }
  };

  const handleEvidenceGallery = async (category: string) => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert('Permission Denied', 'Media library permissions are required.');
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: 'images',
      quality: 0.5,
      allowsMultipleSelection: true,
    });
    if (!result.canceled && result.assets && result.assets.length > 0) {
      const picked = result.assets.map(asset => ({
        uri: asset.uri,
        name: asset.fileName || 'evidence_gallery.jpg',
        type: asset.mimeType || 'image/jpeg',
      }));
      handleEvidenceFilesPicked(picked, category);
    }
  };

  const handleEvidencePdf = async (category: string) => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: 'application/pdf',
        copyToCacheDirectory: true,
        multiple: true,
      });
      if (!result.canceled && result.assets && result.assets.length > 0) {
        const picked = result.assets.map(asset => ({
          uri: asset.uri,
          name: asset.name,
          type: asset.mimeType || 'application/pdf',
        }));
        handleEvidenceFilesPicked(picked, category);
      }
    } catch {
      setUploadError('Failed to open PDF document picker.');
    }
  };

  const handleUploadEvidenceSubmit = async () => {
    if (pendingFiles.length === 0) return;
    setEvidenceUploadError(null);
    try {
      await uploadEvidenceMutation.mutateAsync({
        propertyId: id,
        category: evidenceCategory,
        fileUris: pendingFiles.map(f => f.uri),
        roomLabel: roomLabel.trim() || undefined,
        notes: evidenceNotes.trim() || undefined,
      });
      setEvidenceModalVisible(false);
      setPendingFiles([]);
      setRoomLabel('');
      setEvidenceNotes('');
      refetchDashboard();
    } catch (e: any) {
      setEvidenceUploadError(e?.message || 'Failed to upload evidence items.');
    }
  };

  const handleDelete = () => {
    setDeleteError(null);
    setDeletePropConfirmVisible(true);
  };

  const handleReplaceEvidence = async () => {
    if (!evidenceToAction) return;
    setReplaceEvidenceConfirmVisible(false);
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert('Permission Denied', 'Media library permission required to replace.');
      setEvidenceToAction(null);
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: 'images',
      quality: 0.5,
    });
    if (!result.canceled && result.assets && result.assets.length > 0) {
      try {
        await replaceEvidenceMutation.mutateAsync({
          evidenceId: evidenceToAction.id,
          uri: result.assets[0].uri,
        });
        setEvidenceToAction(null);
        setActionMenuItem(null);
      } catch (err: any) {
        Alert.alert('Error', err?.message || 'Failed to replace image.');
        setEvidenceToAction(null);
      }
    } else {
      setEvidenceToAction(null);
    }
  };

  const renderDashboardSection = () => {
    if (isDashboardLoading && !dashboard) {
      return (
        <Card title="Case Dashboard">
          <View className="gap-4 py-2">
            <View className="h-20 w-full rounded-xl bg-slate-200/60 animate-pulse" />
            <View className="h-16 w-full rounded-xl bg-slate-200/60 animate-pulse" />
            <View className="h-24 w-full rounded-xl bg-slate-200/60 animate-pulse" />
          </View>
        </Card>
      );
    }

    if (!dashboard) return null;

    // Build activities list dynamically
    const activities: { label: string; icon: string }[] = [];
    if (dashboard.documents && dashboard.documents.length > 0) {
      activities.push({
        label: `Dispute recovery draft generated (${dashboard.documents[0].doc_type})`,
        icon: '📄',
      });
    }
    if (dashboard.notice_id) {
      activities.push({
        label: `AI extracted ${dashboard.claims.length} claims from deduction notice`,
        icon: '🤖',
      });
    }
    const totalEvidence = (evidenceList || []).length;
    if (totalEvidence > 0) {
      activities.push({
        label: `Logged ${totalEvidence} condition photos & receipts`,
        icon: '📸',
      });
    }
    if (dashboard.lease_id) {
      activities.push({
        label: 'Rental lease agreement scanned & terms registered',
        icon: '🏢',
      });
    }
    if (activities.length === 0) {
      activities.push({
        label: 'Case initiated. Upload files to begin tracking activity.',
        icon: '🏁',
      });
    }

    // Determine current case status label
    let statusLabel = 'Awaiting Lease';
    let statusColor = 'text-slate-500 bg-slate-100 border-slate-200';
    if (!dashboard.lease_id) {
      statusLabel = 'Awaiting Lease';
      statusColor = 'text-slate-500 bg-slate-100 border-slate-200';
    } else if (!dashboard.notice_id) {
      statusLabel = 'Lease Registered';
      statusColor = 'text-blue-600 bg-blue-50 border-blue-100';
    } else if (dashboard.notice_status === 'processing') {
      statusLabel = 'AI Analyzing';
      statusColor = 'text-amber-600 bg-amber-50 border-amber-100';
    } else if (dashboard.documents && dashboard.documents.length > 0) {
      statusLabel = 'Dispute Ready';
      statusColor = 'text-emerald-600 bg-emerald-50 border-emerald-100';
    } else {
      statusLabel = 'Claims Extracted';
      statusColor = 'text-indigo-600 bg-indigo-50 border-indigo-100';
    }

    return (
      <Card title="Case Dashboard" subtitle="Overview of your recovery dispute">
        {/* Status & Next Action Card */}
        <View className="mb-4 rounded-2xl border border-brand-100 bg-brand-50/40 p-4 gap-3">
          <View className="flex-row items-center justify-between border-b border-brand-100/30 pb-2">
            <Text className="text-[10px] font-bold uppercase tracking-wider text-brand-600">
              Dispute Case Status
            </Text>
            <View className={`border rounded-full px-2.5 py-0.5 ${statusColor}`}>
              <Text className="text-[9px] font-bold uppercase tracking-wider text-center">{statusLabel}</Text>
            </View>
          </View>
          <View>
            <Text className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Next Recommended Action
            </Text>
            <Text className="mt-1 text-sm font-semibold text-slate-800 leading-relaxed">
              {dashboard.next_action || "Upload your lease agreement to start."}
            </Text>
          </View>
        </View>

        {/* Financial metrics summary */}
        <View className="mb-4 flex-row gap-2.5">
          <View className="flex-1 rounded-xl border border-slate-100 bg-slate-50/50 p-3 items-center">
            <Text className="text-[9px] font-bold uppercase tracking-widest text-slate-400 text-center">
              Total Deposit
            </Text>
            <Text className="mt-1 text-sm font-extrabold text-slate-800">
              INR {dashboard.deposit_amount.toLocaleString('en-IN')}
            </Text>
          </View>

          <View className="flex-1 rounded-xl border border-slate-100 bg-slate-50/50 p-3 items-center">
            <Text className="text-[9px] font-bold uppercase tracking-widest text-slate-400 text-center">
              Supported
            </Text>
            <Text className="mt-1 text-sm font-extrabold text-emerald-600">
              INR {dashboard.total_supported_amount.toLocaleString('en-IN')}
            </Text>
          </View>

          <View className="flex-1 rounded-xl border border-slate-100 bg-slate-50/50 p-3 items-center">
            <Text className="text-[9px] font-bold uppercase tracking-widest text-slate-400 text-center">
              Disputed
            </Text>
            <Text className="mt-1 text-sm font-extrabold text-amber-600">
              INR {dashboard.total_disputed_amount.toLocaleString('en-IN')}
            </Text>
          </View>
        </View>

        {/* Recent Activity List */}
        <View className="border-t border-slate-100 pt-4 mb-1">
          <Text className="mb-2.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
            Recent Case Activity
          </Text>
          <View className="gap-2.5">
            {activities.map((act, index) => (
              <View key={index} className="flex-row items-center gap-2.5">
                <Text className="text-base">{act.icon}</Text>
                <Text className="flex-1 text-xs font-medium text-slate-600 leading-relaxed">
                  {act.label}
                </Text>
              </View>
            ))}
          </View>
        </View>

        {/* Claims Summary List */}
        <View className="border-t border-slate-100 pt-4 mt-3">
          <View className="flex-row justify-between items-center mb-2.5">
            <Text className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Claims Summary ({dashboard.claims.length})
            </Text>
            <Link
              href={{ pathname: '/claims/[id]', params: { id: `claim-${id}` } }}
              asChild
            >
              <Button
                label="View Claims"
                variant="ghost"
                className="h-8 px-3 rounded-lg"
              />
            </Link>
          </View>
          {dashboard.claims && dashboard.claims.length > 0 ? (
            <View className="gap-2">
              {dashboard.claims.map((claim) => (
                <View
                  key={claim.id}
                  className="flex-row items-center justify-between border-b border-slate-100/50 pb-2"
                >
                  <Text
                    className="flex-1 text-xs text-slate-600 font-medium mr-2"
                    numberOfLines={1}
                  >
                    {claim.item_description}
                  </Text>
                  <View className="flex-row items-center gap-2">
                    {claim.claimed_amount !== null && (
                      <Text className="text-xs font-semibold text-slate-800">
                        INR {claim.claimed_amount.toLocaleString('en-IN')}
                      </Text>
                    )}
                    <StatusBadge status={claim.effective_label} />
                  </View>
                </View>
              ))}
            </View>
          ) : (
            <Text className="text-xs text-slate-400 italic">
              {'No claims detected. Upload a deduction notice to trigger analysis.'}
            </Text>
          )}
        </View>
      </Card>
    );
  };

  const renderLeasePanel = () => {
    if (isDashboardLoading) {
      return <LoadingSpinner message="Checking lease status..." />;
    }

    if (isLocalUploading) {
      return (
        <Card title="Lease Agreement">
          <View className="items-center py-4">
            <ActivityIndicator color="#0f6cbd" size="large" />
            <Text className="mt-3 text-sm font-medium text-slate-600">
              Uploading lease document...
            </Text>
          </View>
        </Card>
      );
    }

    if (!activeLeaseId) {
      return (
        <Card
          title="Lease Agreement"
          subtitle="Upload your rental agreement to analyze deposit terms."
        >
          <UploadArea
            onPress={handlePdf}
            error={uploadError}
            label="Select lease agreement (PDF or Image)"
          />
          <View className="mt-4 flex-row gap-2">
            <View className="flex-1">
              <Button label="Camera" variant="outline" onPress={handleCamera} />
            </View>
            <View className="flex-1">
              <Button label="Gallery" variant="outline" onPress={handleGallery} />
            </View>
            <View className="flex-1">
              <Button label="PDF File" variant="outline" onPress={handlePdf} />
            </View>
          </View>
        </Card>
      );
    }

    if (isLeaseLoading && !lease) {
      return <LoadingSpinner message="Loading lease..." />;
    }

    if (leaseError || !lease) {
      return (
        <Card title="Lease Agreement">
          <ErrorState message="Failed to load lease details." onRetry={refetchLease} />
          <Button
            label="Upload Different File"
            variant="outline"
            className="mt-4"
            onPress={() => setLocalLeaseId(null)}
          />
        </Card>
      );
    }

    return (
      <Card title="Lease Agreement">
        <View className="mb-4 flex-row items-center justify-between">
          <Text className="text-sm font-semibold text-slate-500">Extraction Status</Text>
          <StatusBadge status={lease.status} />
        </View>

        {lease.status === 'processing' && (
          <View className="items-center border border-slate-100 bg-slate-50 py-4 rounded-xl">
            <ActivityIndicator color="#0f6cbd" size="small" />
            <Text className="mt-2.5 text-xs font-medium text-slate-500">
              AI is extracting deposit parameters...
            </Text>
          </View>
        )}

        {lease.status === 'failed' && (
          <View className="gap-3">
            <Text className="text-sm font-medium text-red-600">
              {"We couldn't extract details from your document. Please verify the file is clear."}
            </Text>
            <View className="flex-row gap-2">
              <View className="flex-1">
                <Button
                  label="Retry Extraction"
                  onPress={() => setReextractConfirmVisible(true)}
                />
              </View>
              <View className="flex-1">
                <Button label="Reupload" variant="outline" onPress={() => setLocalLeaseId(null)} />
              </View>
            </View>
          </View>
        )}

        {(lease.status === 'confirmed' || lease.status === 'needs_review') && (
          <View className="gap-4">
            {lease.status === 'needs_review' && (
              <View className="border border-amber-200 bg-amber-50 p-3 rounded-xl">
                <Text className="text-xs font-semibold text-amber-800">
                  ⚠️ Some fields require confirmation. Please verify the AI extractions below.
                </Text>
              </View>
            )}

            <View className="border border-slate-100 bg-slate-50 p-4 gap-3 rounded-xl">
              <View className="flex-row justify-between items-center mb-1">
                <Text className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Extracted Terms
                </Text>
                <Button
                  label="Edit terms"
                  variant="outline"
                  className="h-7 px-2.5 rounded-lg"
                  onPress={handleOpenLeaseEdit}
                />
              </View>
              {(() => {
                const getVal = (field: any) => {
                  if (field && typeof field === 'object' && 'value' in field) {
                    return field.value;
                  }
                  return field;
                };

                const tenantName = getVal(lease.extracted_fields?.tenant_name);
                const landlordName = getVal(lease.extracted_fields?.landlord_name);
                const depositAmt = getVal(
                  lease.extracted_fields?.deposit_amount ||
                    lease.extracted_fields?.security_deposit,
                );
                const monthlyRent = getVal(lease.extracted_fields?.monthly_rent);

                return (
                  <>
                    <View className="flex-row justify-between border-b border-slate-200/50 py-1">
                      <Text className="text-sm text-slate-500">Tenant Name</Text>
                      <Text className="text-sm font-semibold text-slate-800">
                        {tenantName || 'Not found'}
                      </Text>
                    </View>

                    <View className="flex-row justify-between border-b border-slate-200/50 py-1">
                      <Text className="text-sm text-slate-500">Landlord Name</Text>
                      <Text className="text-sm font-semibold text-slate-800">
                        {landlordName || 'Not found'}
                      </Text>
                    </View>

                    <View className="flex-row justify-between border-b border-slate-200/50 py-1">
                      <Text className="text-sm text-slate-500">Deposit Amount</Text>
                      <Text className="text-sm font-bold text-slate-800">
                        {depositAmt !== undefined &&
                        depositAmt !== null &&
                        !isNaN(Number(depositAmt))
                          ? `INR ${Number(depositAmt).toLocaleString('en-IN')}`
                          : 'Not found'}
                      </Text>
                    </View>

                    <View className="flex-row justify-between py-1">
                      <Text className="text-sm text-slate-500">Monthly Rent</Text>
                      <Text className="text-sm font-semibold text-slate-800">
                        {monthlyRent !== undefined &&
                        monthlyRent !== null &&
                        !isNaN(Number(monthlyRent))
                          ? `INR ${Number(monthlyRent).toLocaleString('en-IN')}`
                          : 'Not found'}
                      </Text>
                    </View>
                  </>
                );
              })()}
            </View>

            <Button
              label="Upload Different Lease"
              variant="outline"
              onPress={() => setLocalLeaseId(null)}
            />
          </View>
        )}
      </Card>
    );
  };

  const renderEvidencePanel = () => {
    const categories = [
      { id: 'move_in', title: 'Move-in Photos', subtitle: 'Photos of property condition at move-in' },
      { id: 'move_out', title: 'Move-out Photos', subtitle: 'Photos of property condition at move-out' },
      { id: 'damage', title: 'Damage Photos', subtitle: 'Photos documenting specific damage' },
      { id: 'receipt', title: 'Receipts', subtitle: 'Invoices, repair estimates, and receipts' },
    ];

    const handleActionMenu = (item: any) => {
      setActionMenuItem(item);
      setActionMenuVisible(true);
    };

    return (
      <Card
        title="Evidence Gallery"
        subtitle="Manage property condition records, receipts, and supporting evidence."
      >
        {/* Toggle to show soft-deleted items */}
        <View className="mb-6 flex-row items-center justify-between border-b border-slate-100 pb-3">
          <Text className="text-sm font-semibold text-slate-600">Show Archived Items</Text>
          <Button
            label={includeDeleted ? "Hide Archived" : "Show Archived"}
            variant="outline"
            className="h-8 px-3 rounded-lg"
            onPress={() => setIncludeDeleted(!includeDeleted)}
          />
        </View>

        {isEvidenceLoading ? (
          <ActivityIndicator color="#0f6cbd" size="large" className="py-12" />
        ) : (
          <View className="gap-8">
            {categories.map((cat) => {
              const items = evidenceList?.filter((ev) => ev.category === cat.id) || [];
              
              return (
                <View key={cat.id} className="border-b border-slate-100 pb-6 last:border-b-0 last:pb-0">
                  <View className="flex-row items-center justify-between mb-2">
                    <View className="flex-1 pr-4">
                      <Text className="text-base font-bold text-slate-800">
                        {cat.title} ({items.length})
                      </Text>
                      <Text className="text-xs text-slate-400 mt-0.5">{cat.subtitle}</Text>
                    </View>
                    
                    {/* Add Buttons per category */}
                    <View className="flex-row gap-1">
                      <TouchableOpacity
                        onPress={() => void handleEvidenceCamera(cat.id)}
                        className="bg-slate-100 hover:bg-slate-200 p-2 rounded-lg"
                      >
                        <Text style={{ fontSize: 13 }}>📷</Text>
                      </TouchableOpacity>
                      <TouchableOpacity
                        onPress={() => void handleEvidenceGallery(cat.id)}
                        className="bg-slate-100 hover:bg-slate-200 p-2 rounded-lg"
                      >
                        <Text style={{ fontSize: 13 }}>🖼️</Text>
                      </TouchableOpacity>
                      <TouchableOpacity
                        onPress={() => void handleEvidencePdf(cat.id)}
                        className="bg-slate-100 hover:bg-slate-200 p-2 rounded-lg"
                      >
                        <Text style={{ fontSize: 13 }}>📄</Text>
                      </TouchableOpacity>
                    </View>
                  </View>

                  {items.length > 0 ? (
                    <View className="flex-row flex-wrap gap-3 mt-3">
                      {items.map((item) => {
                        const isPdf = item.mime_type === 'application/pdf' || item.file_url.endsWith('.pdf');
                        const isDeleted = !!item.deleted_at;
                        
                        return (
                          <TouchableOpacity
                            key={item.id}
                            onPress={() => handleActionMenu(item)}
                            className={`w-[29%] border p-1 rounded-xl items-center relative ${
                              isDeleted ? 'border-red-200 bg-red-50/30' : 'border-slate-100 bg-slate-50'
                            }`}
                          >
                            {/* Thumbnail */}
                            {isPdf ? (
                              <View className="w-full aspect-square bg-slate-200 rounded-lg items-center justify-center">
                                <Text className="text-2xl">📄</Text>
                                <Text className="text-[9px] text-slate-500 font-bold mt-1">PDF Document</Text>
                              </View>
                            ) : (
                              <Image
                                source={{ uri: item.thumbnail_url || item.file_url }}
                                className="w-full aspect-square rounded-lg bg-slate-200"
                                resizeMode="cover"
                              />
                            )}

                            {/* Info */}
                            <Text numberOfLines={1} className="text-[10px] font-bold text-slate-800 mt-2 px-1 text-center w-full">
                              {item.display_name}
                            </Text>
                            <Text className="text-[8px] text-slate-400 mt-0.5">
                              {new Date(item.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                            </Text>

                            {/* Deleted Badge */}
                            {isDeleted && (
                              <View className="absolute top-2 right-2 bg-red-600 px-1.5 py-0.5 rounded-md">
                                <Text className="text-[7px] text-white font-bold uppercase">Archived</Text>
                              </View>
                            )}
                          </TouchableOpacity>
                        );
                      })}
                    </View>
                  ) : (
                    <View className="py-4 items-center bg-slate-50/50 rounded-xl border border-dashed border-slate-200 mt-2">
                      <Text className="text-xs text-slate-400">No uploads in this section yet.</Text>
                    </View>
                  )}
                </View>
              );
            })}
          </View>
        )}

        {/* Render ImageViewer Modal */}
        {selectedEvidence && (
          <ImageViewer
            visible={viewerVisible}
            onClose={() => {
              setViewerVisible(false);
              setSelectedEvidence(null);
            }}
            imageUrl={selectedEvidence.full_image_url || selectedEvidence.file_url}
            displayName={selectedEvidence.display_name}
            category={selectedEvidence.category}
            uploadedAt={selectedEvidence.created_at}
          />
        )}

        {/* Render Action Menu Modal */}
        {actionMenuItem && (
          <Modal
            visible={actionMenuVisible}
            onClose={() => {
              setActionMenuVisible(false);
              setActionMenuItem(null);
            }}
            title={actionMenuItem.display_name}
          >
            <View className="gap-2">
              <Button
                label="View Fullscreen"
                onPress={() => {
                  setActionMenuVisible(false);
                  setSelectedEvidence(actionMenuItem);
                  setViewerVisible(true);
                  setActionMenuItem(null);
                }}
              />
              {actionMenuItem.deleted_at ? (
                <Button
                  label="Restore Evidence"
                  variant="secondary"
                  onPress={async () => {
                    setActionMenuVisible(false);
                    try {
                      await restoreEvidenceMutation.mutateAsync(actionMenuItem.id);
                      setActionMenuItem(null);
                    } catch (err: any) {
                      Alert.alert('Error', err?.message || 'Failed to restore evidence.');
                    }
                  }}
                />
              ) : (
                <>
                  <Button
                    label="Replace Image"
                    variant="outline"
                    onPress={() => {
                      setEvidenceToAction(actionMenuItem);
                      setActionMenuVisible(false);
                      setReplaceEvidenceConfirmVisible(true);
                    }}
                  />
                  <Button
                    label="Delete Evidence"
                    variant="danger"
                    onPress={() => {
                      setEvidenceToAction(actionMenuItem);
                      setActionMenuVisible(false);
                      setDeleteEvidenceConfirmVisible(true);
                    }}
                  />
                </>
              )}
              <Button
                label="Cancel"
                variant="secondary"
                onPress={() => {
                  setActionMenuVisible(false);
                  setActionMenuItem(null);
                }}
              />
            </View>
          </Modal>
        )}
      </Card>
    );
  };

  if (isPropertyLoading) {
    return <LoadingSpinner fullscreen message="Loading property details..." />;
  }

  if (propertyError || !property) {
    return (
      <View className="flex-1 justify-center bg-slate-50 px-6">
        <ErrorState
          title="Property Details Error"
          message={
            propertyError instanceof Error
              ? propertyError.message
              : 'Property not found or access denied.'
          }
          onRetry={refetchProperty}
        />
      </View>
    );
  }

  return (
    <View className="flex-1 bg-slate-50 px-6 pb-6 pt-12">
      <View className="mb-6 flex-row items-center justify-between">
        <View className="flex-1 pr-4 flex-row items-center gap-3">
          <TouchableOpacity
            onPress={() => {
              if (router.canGoBack()) {
                router.back();
              } else {
                router.replace('/(tabs)/properties');
              }
            }}
            className="w-10 h-10 bg-slate-100 active:bg-slate-200 rounded-xl items-center justify-center border border-slate-200"
            accessibilityRole="button"
            accessibilityLabel="Go back"
          >
            <Text style={{ fontSize: 16, fontWeight: 'bold' }}>←</Text>
          </TouchableOpacity>
          <View className="flex-1">
            <Text className="text-xs font-semibold uppercase tracking-wider text-brand-500">
              Property Details
            </Text>
            <Text className="text-2xl font-bold text-slate-900 leading-tight" numberOfLines={1}>
              {property.label}
            </Text>
            {property.address ? (
              <Text className="text-xs text-slate-500 mt-1 font-medium" numberOfLines={1}>{property.address}</Text>
            ) : null}
          </View>
        </View>
        <View className="flex-row items-center gap-2">
          <StatusBadge status={property.status === 'active' ? 'processing' : 'completed'} />
          <TouchableOpacity
            onPress={() => setModalVisible(true)}
            className="w-10 h-10 bg-slate-100 active:bg-slate-200 rounded-xl items-center justify-center border border-slate-200"
            accessibilityRole="button"
            accessibilityLabel="Settings"
            accessibilityHint="Open case settings"
          >
            <Text style={{ fontSize: 18 }}>⚙️</Text>
          </TouchableOpacity>
        </View>
      </View>

      <ScrollView
        className="flex-1 gap-6"
        refreshControl={
          <RefreshControl
            refreshing={isRefreshing}
            onRefresh={handleRefresh}
            colors={['#0f6cbd']}
          />
        }
      >
        {renderDashboardSection()}

        {renderLeasePanel()}

        {renderEvidencePanel()}

        <Card title="Dispute Actions">
          <View className="gap-3">
            <Link
              href={{ pathname: '/claims/[id]', params: { id: `claim-${id}` } }}
              asChild
            >
              <Button label="Go to Claims Analysis" />
            </Link>

            <Link
              href={{ pathname: '/documents/[id]', params: { id: `doc-${id}` } }}
              asChild
            >
              <Button label="Go to Document Generation" variant="secondary" />
            </Link>
          </View>
        </Card>

        <View className="mt-4 gap-3">
          <Button
            label="Back to Properties List"
            variant="secondary"
            onPress={() => {
              if (router.canGoBack()) {
                router.back();
              } else {
                router.replace('/(tabs)/properties');
              }
            }}
          />
        </View>

        <View className="mt-8 border-t border-slate-200 pt-6 gap-2">
          <Text className="text-[10px] font-bold uppercase tracking-wider text-red-500 mb-1">
            Danger Zone
          </Text>
          <Button
            label="Delete Property Case"
            variant="danger"
            onPress={handleDelete}
          />
        </View>
      </ScrollView>

      {/* Modal for editing property */}
      <Modal visible={modalVisible} onClose={() => setModalVisible(false)} title="Edit Property">
        <ScrollView showsVerticalScrollIndicator={false} className="max-h-96">
          <Controller
            control={control}
            name="label"
            render={({ field: { onChange, onBlur, value } }) => (
              <Input
                label="Label / Nickname"
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
                label="Full Address"
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
                onBlur={onBlur}
                onChangeText={onChange}
                value={value}
                errorMessage={errors.lease_end_date?.message}
              />
            )}
          />

          <View className="mb-4">
            <Text className="mb-1 text-sm font-semibold text-slate-700">Dispute Case Status</Text>
            <View className="mt-1 flex-row gap-2">
              <Controller
                control={control}
                name="status"
                render={({ field: { onChange, value } }) => (
                  <>
                    <View className="flex-1">
                      <Button
                        label="Active"
                        variant={value === 'active' ? 'primary' : 'outline'}
                        onPress={() => onChange('active')}
                      />
                    </View>
                    <View className="flex-1">
                      <Button
                        label="Resolved"
                        variant={value === 'resolved' ? 'primary' : 'outline'}
                        onPress={() => onChange('resolved')}
                      />
                    </View>
                  </>
                )}
              />
            </View>
          </View>

          <View className="mt-4 gap-2">
            <Button
              label="Save Changes"
              loading={updatePropertyMutation.isPending}
              onPress={() => void onSubmit()}
            />
            <Button label="Cancel" variant="outline" onPress={() => setModalVisible(false)} />
          </View>
        </ScrollView>
      </Modal>

      {/* Modal for uploading evidence room details */}
      <Modal
        visible={evidenceModalVisible}
        onClose={() => {
          setEvidenceModalVisible(false);
          setPendingFiles([]);
        }}
        title="Upload Evidence"
      >
        <ScrollView showsVerticalScrollIndicator={false} className="max-h-96">
          <Text className="mb-4 text-xs font-semibold text-slate-500">
            Selected: {pendingFiles.length === 1 ? pendingFiles[0].name : `${pendingFiles.length} files selected`}
          </Text>

          <Input
            label="Room Label (Optional)"
            placeholder="e.g. Living Room, Bedroom"
            onChangeText={setRoomLabel}
            value={roomLabel}
          />

          <Input
            label="Notes / Comments (Optional)"
            placeholder="e.g. Scratch on wall, stained carpet"
            onChangeText={setEvidenceNotes}
            value={evidenceNotes}
          />

          {evidenceUploadError ? (
            <Text className="mb-4 text-xs font-semibold text-red-600">{evidenceUploadError}</Text>
          ) : null}

          <View className="mt-4 gap-2">
            <Button
              label="Submit Upload"
              loading={uploadEvidenceMutation.isPending}
              onPress={() => void handleUploadEvidenceSubmit()}
            />
            <Button
              label="Cancel"
              variant="outline"
              onPress={() => {
                setEvidenceModalVisible(false);
                setPendingFiles([]);
              }}
            />
          </View>
        </ScrollView>
      </Modal>

      {/* Modal for editing lease terms */}
      <Modal
        visible={leaseModalVisible}
        onClose={() => setLeaseModalVisible(false)}
        title="Edit Lease Terms"
      >
        <ScrollView showsVerticalScrollIndicator={false} className="max-h-96">
          <Input
            label="Tenant Name"
            placeholder="Enter tenant name"
            onChangeText={setEditTenantName}
            value={editTenantName}
          />

          <Input
            label="Landlord Name"
            placeholder="Enter landlord name"
            onChangeText={setEditLandlordName}
            value={editLandlordName}
          />

          <Input
            label="Security Deposit Amount"
            placeholder="Enter deposit amount"
            keyboardType="numeric"
            onChangeText={setEditDepositAmount}
            value={editDepositAmount}
          />

          <Input
            label="Monthly Rent"
            placeholder="Enter monthly rent"
            keyboardType="numeric"
            onChangeText={setEditMonthlyRent}
            value={editMonthlyRent}
          />

          {leaseUpdateError ? (
            <Text className="mb-4 text-xs font-semibold text-red-600">{leaseUpdateError}</Text>
          ) : null}

          <View className="mt-4 gap-2">
            <Button
              label="Save Changes"
              loading={updateLeaseMutation.isPending}
              onPress={() => void handleSaveLease()}
            />
            <Button label="Cancel" variant="outline" onPress={() => setLeaseModalVisible(false)} />
          </View>
        </ScrollView>
      </Modal>

      {/* ConfirmDialog components */}
      <ConfirmDialog
        visible={deletePropConfirmVisible}
        title="Delete Property Case"
        message={deleteError ? `Error: ${deleteError}\n\nAre you sure you want to permanently delete this property case?` : "Are you sure you want to permanently delete this property case? This action cannot be undone."}
        confirmLabel="Delete"
        cancelLabel="Cancel"
        loading={deletePropertyMutation.isPending}
        variant="danger"
        onConfirm={async () => {
          try {
            setDeleteError(null);
            await deletePropertyMutation.mutateAsync(id);
            setDeletePropConfirmVisible(false);
            router.replace('/(tabs)/properties');
          } catch (e: any) {
            setDeleteError(e?.message || 'Failed to delete property.');
          }
        }}
        onCancel={() => setDeletePropConfirmVisible(false)}
      />

      <ConfirmDialog
        visible={deleteEvidenceConfirmVisible}
        title="Confirm Delete"
        message="Are you sure you want to delete this evidence? It will be archived."
        confirmLabel="Delete"
        cancelLabel="Cancel"
        loading={deleteEvidenceMutation.isPending}
        variant="danger"
        onConfirm={async () => {
          if (!evidenceToAction) return;
          try {
            await deleteEvidenceMutation.mutateAsync(evidenceToAction.id);
            setDeleteEvidenceConfirmVisible(false);
            setEvidenceToAction(null);
            setActionMenuItem(null);
          } catch (e: any) {
            setDeleteEvidenceConfirmVisible(false);
            setEvidenceToAction(null);
            Alert.alert('Error', e?.message || 'Failed to delete evidence.');
          }
        }}
        onCancel={() => {
          setDeleteEvidenceConfirmVisible(false);
          setEvidenceToAction(null);
        }}
      />

      <ConfirmDialog
        visible={replaceEvidenceConfirmVisible}
        title="Replace Evidence Image"
        message="Are you sure you want to replace this evidence item with a new photo? This will archive the previous file."
        confirmLabel="Replace"
        cancelLabel="Cancel"
        loading={replaceEvidenceMutation.isPending}
        onConfirm={handleReplaceEvidence}
        onCancel={() => {
          setReplaceEvidenceConfirmVisible(false);
          setEvidenceToAction(null);
        }}
      />

      <ConfirmDialog
        visible={reextractConfirmVisible}
        title="Confirm Re-extraction"
        message="Are you sure you want to retry AI extraction on this lease agreement?"
        confirmLabel="Retry"
        cancelLabel="Cancel"
        loading={reextractMutation.isPending}
        onConfirm={async () => {
          try {
            await reextractMutation.mutateAsync();
            setReextractConfirmVisible(false);
          } catch {
            setReextractConfirmVisible(false);
          }
        }}
        onCancel={() => setReextractConfirmVisible(false)}
      />
    </View>
  );
}
