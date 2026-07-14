import { View, Text } from 'react-native';
import { StatusBadge } from './status-badge';
import type { BadgeType } from './status-badge';

type ClaimCardProps = {
  title: string;
  amount: number;
  verdict: BadgeType;
  reasoning: string;
  evidenceRefs?: Record<string, any>;
  confidence?: number;
};

export function ClaimCard({
  title,
  amount,
  verdict,
  reasoning,
  evidenceRefs,
  confidence,
}: ClaimCardProps) {
  return (
    <View className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <View className="mb-3 flex-row items-start justify-between gap-2">
        <View className="flex-1">
          <Text className="text-base font-bold text-slate-800 tracking-tight leading-snug">{title}</Text>
          <Text className="mt-1 text-sm font-semibold text-slate-500">
            Disputed Amount: INR {amount.toLocaleString('en-IN')}
          </Text>
        </View>
        <View className="items-end gap-1">
          <StatusBadge status={verdict} />
          {confidence !== undefined ? (
            <Text className="text-[10px] font-semibold text-slate-400">
              AI Confidence: {confidence}%
            </Text>
          ) : null}
        </View>
      </View>

      <View className="rounded-lg bg-slate-50 p-3">
        <Text className="mb-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
          Reasoning & Verdict
        </Text>
        <Text className="text-sm font-normal text-slate-600 leading-relaxed">{reasoning}</Text>

        {evidenceRefs && Object.keys(evidenceRefs).length > 0 ? (
          <View className="mt-3 border-t border-slate-200/60 pt-3">
            <Text className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Supporting Evidence References
            </Text>
            {evidenceRefs.lease_clauses && evidenceRefs.lease_clauses.length > 0 && (
              <Text className="text-xs font-normal text-slate-500 mb-1">
                • <Text className="font-semibold text-slate-500">Lease Clauses</Text>: {evidenceRefs.lease_clauses.join(', ')}
              </Text>
            )}
            {evidenceRefs.landlord_evidence && evidenceRefs.landlord_evidence.length > 0 && (
              <Text className="text-xs font-normal text-slate-500 mb-1">
                • <Text className="font-semibold text-slate-500">Landlord-Referenced</Text>: {evidenceRefs.landlord_evidence.join(', ')}
              </Text>
            )}
            {evidenceRefs.evidence_names && evidenceRefs.evidence_names.length > 0 && (
              <Text className="text-xs font-normal text-slate-500 mb-1">
                • <Text className="font-semibold text-slate-500">Tenant-Uploaded</Text>: {evidenceRefs.evidence_names.join(', ')}
              </Text>
            )}
            {evidenceRefs.needed_evidence && evidenceRefs.needed_evidence.length > 0 && (
              <Text className="text-xs font-normal text-slate-500">
                • <Text className="font-semibold text-slate-500">Needed Evidence</Text>: {evidenceRefs.needed_evidence.join(', ')}
              </Text>
            )}
          </View>
        ) : null}
      </View>
    </View>
  );
}
