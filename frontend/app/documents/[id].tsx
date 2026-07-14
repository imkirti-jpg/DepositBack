import { useRouter, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  Text,
  TextInput,
  View,
  Clipboard,
} from 'react-native';

import { Card } from '@/components/ui/card';
import { ErrorState } from '@/components/ui/error-state';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { Modal } from '@/components/ui/modal';
import { StatusBadge } from '@/components/ui/status-badge';
import { useDashboard } from '@/hooks/use-dashboard';
import {
  useDocumentsList,
  useDocument,
  useCreateDocument,
  useUpdateDocument,
  useMarkDocumentSent,
} from '@/hooks/use-documents';
import type { DocType } from '@/services/document.service';
import { Button } from '@/components/ui/button';
import { ConfirmDialog } from '@/components/ui/confirm-dialog';

export default function DocumentsScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const propertyId = id.replace('doc-', '');

  // Queries
  const { data: dashboard } = useDashboard(propertyId);
  const {
    data: documents,
    isLoading: isListLoading,
    refetch: refetchList,
  } = useDocumentsList(propertyId);

  // Active document selection state
  const [activeDocId, setActiveDocId] = useState<string | null>(null);
  const activeDocIdToShow = activeDocId || documents?.[0]?.id || '';
  const {
    data: activeDoc,
    isLoading: isDocLoading,
    error: docError,
  } = useDocument(activeDocIdToShow);

  // Mutations
  const createDocMutation = useCreateDocument();
  const updateDocMutation = useUpdateDocument(activeDocIdToShow);
  const markSentMutation = useMarkDocumentSent(activeDocIdToShow);

  // UI state
  const [docType, setDocType] = useState<DocType>('message');
  const [isEditing, setIsEditing] = useState(false);
  const [editedText, setEditedText] = useState('');
  const [modalVisible, setModalVisible] = useState(false);
  const [regenerateConfirmVisible, setRegenerateConfirmVisible] = useState(false);

  const confirmGenerate = async () => {
    setRegenerateConfirmVisible(false);
    try {
      const newDoc = await createDocMutation.mutateAsync({
        property_id: propertyId,
        deduction_notice_id: dashboard?.notice_id || '',
        doc_type: docType,
      });
      setActiveDocId(newDoc.id);
      setModalVisible(false);
      refetchList();
    } catch (e: any) {
      Alert.alert('Generation Error', e?.message || 'Failed to trigger document generation.');
    }
  };

  const handleGenerate = async () => {
    if (!dashboard?.notice_id) {
      Alert.alert(
        'Claims Analysis Required',
        'Please upload a deduction notice and perform claims analysis before generating dispute documents.',
        [{ text: 'OK' }],
      );
      return;
    }
    setRegenerateConfirmVisible(true);
  };

  const handleSave = async () => {
    if (!activeDocId) return;
    try {
      await updateDocMutation.mutateAsync({
        edited_content: editedText,
      });
      setIsEditing(false);
    } catch (e: any) {
      Alert.alert('Save Error', e?.message || 'Failed to save changes.');
    }
  };

  const handleMarkSent = async () => {
    if (!activeDocId) return;
    try {
      await markSentMutation.mutateAsync();
      refetchList();
    } catch (e: any) {
      Alert.alert('Error', e?.message || 'Failed to update status.');
    }
  };

  const handleCopyToClipboard = () => {
    const text = activeDoc?.display_content;
    if (text) {
      Clipboard.setString(text);
      Alert.alert('Copied', 'Document content copied to clipboard.');
    }
  };

  const renderMarkdown = (text: string) => {
    if (!text) return null;

    const paragraphs = text.split('\n\n');
    return paragraphs.map((para, i) => {
      const lines = para.split('\n');

      return (
        <View key={i} className="mb-4">
          {lines.map((line, j) => {
            if (line.startsWith('#')) {
              const headingText = line.replace(/^#+\s*/, '');
              return (
                <Text key={j} className="mb-2 mt-3 text-lg font-bold text-slate-900">
                  {headingText}
                </Text>
              );
            }
            if (line.trim().startsWith('-') || line.trim().startsWith('*')) {
              const bulletText = line.replace(/^[\s-*]+\s*/, '');
              return (
                <Text key={j} className="mb-1 pl-4 text-sm text-slate-700 leading-relaxed">
                  • {bulletText}
                </Text>
              );
            }
            return (
              <Text key={j} className="mb-1 text-sm text-slate-700 leading-relaxed">
                {line.split('**').map((part, k) => {
                  if (k % 2 === 1) {
                    return (
                      <Text key={k} className="font-bold text-slate-900">
                        {part}
                      </Text>
                    );
                  }
                  return part;
                })}
              </Text>
            );
          })}
        </View>
      );
    });
  };

  const renderActiveDocumentPanel = () => {
    if (isListLoading || (activeDocId && isDocLoading && !activeDoc)) {
      return <LoadingSpinner message="Checking documents snapshot..." />;
    }

    if (!activeDocId) {
      return (
        <Card title="Generated Document">
          <View className="py-8 items-center justify-center">
            <Text className="mb-6 text-center text-sm text-slate-400 max-w-xs">
              No recovery documents generated for this case yet.
            </Text>
            <Button
              label="Generate Dispute Document"
              disabled={!dashboard?.notice_id}
              onPress={() => setModalVisible(true)}
            />
          </View>
        </Card>
      );
    }

    if (docError || !activeDoc) {
      return (
        <Card title="Generated Document">
          <ErrorState message="Failed to load document content." onRetry={refetchList} />
          <Button
            label="Try Again"
            variant="outline"
            className="mt-4"
            onPress={() => setActiveDocId(null)}
          />
        </Card>
      );
    }

    return (
      <Card
        title={activeDoc.doc_type === 'message' ? 'WhatsApp/Email Draft' : 'Formal Dispute Letter'}
        subtitle={`Created on ${new Date(activeDoc.created_at).toLocaleDateString()}`}
      >
        <View className="mb-4 flex-row items-center justify-between border-b border-slate-100 pb-3">
          <Text className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Document Status
          </Text>
          <StatusBadge status={activeDoc.status} />
        </View>

        {activeDoc.status === 'processing' && (
          <View className="items-center border border-slate-100 bg-slate-50 py-8 rounded-xl">
            <ActivityIndicator color="#0f6cbd" size="large" />
            <Text className="mt-3 text-xs font-semibold text-slate-500">
              AI is writing dispute document draft...
            </Text>
          </View>
        )}

        {activeDoc.status === 'failed' && (
          <View className="gap-3">
            <Text className="text-sm font-medium text-red-600">
              Dispute generation failed. AI model returned a response timeout.
            </Text>
            <Button label="Regenerate" onPress={() => setModalVisible(true)} />
          </View>
        )}

        {activeDoc.status !== 'processing' && activeDoc.status !== 'failed' && (
          <View className="gap-4">
            {isEditing ? (
              <View className="gap-3">
                <TextInput
                  multiline
                  className="min-h-80 w-full rounded-xl border border-slate-300 bg-white p-4 text-base text-slate-800 focus:border-brand-500 font-mono"
                  value={editedText}
                  onChangeText={setEditedText}
                />
                <View className="flex-row gap-2">
                  <View className="flex-1">
                    <Button
                      label="Save Changes"
                      loading={updateDocMutation.isPending}
                      onPress={() => void handleSave()}
                    />
                  </View>
                  <View className="flex-1">
                    <Button label="Cancel" variant="outline" onPress={() => setIsEditing(false)} />
                  </View>
                </View>
              </View>
            ) : (
              <View>
                <ScrollView className="max-h-96 border border-slate-100 bg-slate-50 p-4 rounded-xl mb-4">
                  {renderMarkdown(activeDoc.display_content || '')}
                </ScrollView>

                <View className="gap-2">
                  <Button label="Copy to Clipboard" onPress={handleCopyToClipboard} />
                  <View className="flex-row gap-2">
                    <View className="flex-1">
                      <Button
                        label="Edit Draft"
                        variant="outline"
                        onPress={() => {
                          setEditedText(activeDoc?.display_content || '');
                          setIsEditing(true);
                        }}
                      />
                    </View>
                    {activeDoc.status === 'draft' ? (
                      <View className="flex-1">
                        <Button
                          label="Mark Sent"
                          variant="secondary"
                          loading={markSentMutation.isPending}
                          onPress={() => void handleMarkSent()}
                        />
                      </View>
                    ) : null}
                  </View>
                </View>
              </View>
            )}
          </View>
        )}
      </Card>
    );
  };

  const renderHistoryPanel = () => {
    if (!documents || documents.length <= 1) return null;

    return (
      <Card title="Dispute History" subtitle="Switch between generated dispute drafts.">
        <View className="gap-2">
          {documents.map((doc) => (
            <Button
              key={doc.id}
              label={`${doc.doc_type === 'message' ? 'Short Message' : 'Formal Letter'} (${new Date(
                doc.created_at,
              ).toLocaleDateString()})`}
              variant={activeDocId === doc.id ? 'primary' : 'outline'}
              onPress={() => {
                setActiveDocId(doc.id);
                setIsEditing(false);
              }}
            />
          ))}
        </View>
      </Card>
    );
  };

  return (
    <View className="flex-1 bg-slate-50 px-6 pb-6 pt-12">
      <View className="mb-6 flex-row items-center justify-between">
        <View>
          <Text className="text-xs font-semibold uppercase tracking-wider text-brand-500">
            Document Generation
          </Text>
          <Text className="text-3xl font-bold text-slate-900">Recovery Drafts</Text>
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

      <ScrollView className="flex-1 gap-6">
        {!dashboard?.notice_id && (
          <View className="mb-4 border border-amber-200 bg-amber-50 p-4 rounded-xl">
            <Text className="text-sm font-semibold text-amber-800">
              ⚠️ Claims Analysis Required: You must upload a landlord notice and perform claim
              verdict checks before generating dispute documents.
            </Text>
          </View>
        )}

        {renderActiveDocumentPanel()}

        {renderHistoryPanel()}

        {dashboard?.notice_id && (
          <Button
            label="Generate New dispute Document"
            variant="secondary"
            className="mt-4"
            onPress={() => setModalVisible(true)}
          />
        )}
      </ScrollView>

      {/* Modal for selecting template type */}
      <Modal
        visible={modalVisible}
        onClose={() => setModalVisible(false)}
        title="Generate Document"
      >
        <View className="gap-4">
          <Text className="text-sm font-semibold text-slate-700">
            Select a recovery letter style to generate:
          </Text>

          <View className="flex-row gap-2">
            <View className="flex-1">
              <Button
                label="WhatsApp/Email (~200 words)"
                variant={docType === 'message' ? 'primary' : 'outline'}
                onPress={() => setDocType('message')}
              />
            </View>
            <View className="flex-1">
              <Button
                label="Formal Letter (PDF format)"
                variant={docType === 'formal_letter' ? 'primary' : 'outline'}
                onPress={() => setDocType('formal_letter')}
              />
            </View>
          </View>

          <View className="mt-6 gap-2">
            <Button
              label="Generate Draft"
              loading={createDocMutation.isPending}
              onPress={() => void handleGenerate()}
            />
            <Button label="Cancel" variant="outline" onPress={() => setModalVisible(false)} />
          </View>
        </View>
      </Modal>

      <ConfirmDialog
        visible={regenerateConfirmVisible}
        title="Generate Dispute Draft"
        message="Are you sure you want to generate a new dispute letter draft? This will create a new version of the recovery document."
        confirmLabel="Generate"
        cancelLabel="Cancel"
        loading={createDocMutation.isPending}
        onConfirm={confirmGenerate}
        onCancel={() => setRegenerateConfirmVisible(false)}
      />
    </View>
  );
}
