import { useState } from 'react';
import {
  useGroupPipelineStatus,
  useGroups,
  useRunDiscovery,
  useRunFingerprint,
  useRunReferenceMap,
  useRunConflictCheck,
  useRunGroupExtraction,
  useRunValidation,
} from '../hooks/useGroupPipeline';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Search, Fingerprint, Map, AlertTriangle, CheckCircle2, Loader2, RefreshCw,
} from 'lucide-react';
import { GroupPipelineStepper } from './GroupPipelineStepper';
import { GroupList } from './GroupList';
import { GroupDetail } from './GroupDetail';
import { ConflictReport } from './ConflictReport';
import { DryRunPreview } from './DryRunPreview';
import { BatchExtractionPanel } from './BatchExtractionPanel';
import type { ConflictCheckResponse, GroupExtractionResponse } from '@/types/grouping';
import type { LucideIcon } from 'lucide-react';

function PhaseBtn({ icon: Icon, label, loading, onClick, disabled }: {
  icon: LucideIcon; label: string; loading: boolean; onClick: () => void; disabled: boolean;
}) {
  return (
    <Button variant="outline" size="sm" onClick={onClick} disabled={disabled}>
      {loading ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Icon className="h-4 w-4 mr-1.5" />}
      {label}
    </Button>
  );
}

export function GroupPipelineTab() {
  const { status, isLoading: statusLoading, refetch: refetchStatus } = useGroupPipelineStatus();
  const { groups, refetch: refetchGroups } = useGroups();

  const { mutate: runDiscovery, isLoading: discovering } = useRunDiscovery();
  const { mutate: runFingerprint, isLoading: fingerprinting } = useRunFingerprint();
  const { mutate: runReferenceMap, isLoading: mapping } = useRunReferenceMap();
  const { mutate: runConflictCheck, isLoading: conflictChecking } = useRunConflictCheck();
  const { mutate: runExtraction, isLoading: extracting } = useRunGroupExtraction();
  const { mutate: runValidation, isLoading: validating } = useRunValidation();

  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);
  const [conflicts, setConflicts] = useState<ConflictCheckResponse | null>(null);
  const [dryRunResult, setDryRunResult] = useState<GroupExtractionResponse | null>(null);
  const [dryRunGroup, setDryRunGroup] = useState<string>('');
  const [showBatch, setShowBatch] = useState(false);

  const phases = status?.phases ?? {};
  const hasDiscovery = Boolean(phases.discovery);
  const hasFingerprint = Boolean(phases.fingerprint);
  const hasReferenceMap = Boolean(phases.reference_map);
  const hasConflictCheck = Boolean(phases.conflict_check);
  const hasExtract = Boolean(phases.extract);

  const anyRunning = discovering || fingerprinting || mapping || conflictChecking || extracting || validating;

  const handleDiscovery = async () => {
    await runDiscovery();
    refetchStatus();
    refetchGroups();
  };

  const handleFingerprint = async () => {
    await runFingerprint();
    refetchStatus();
    refetchGroups();
  };

  const handleReferenceMap = async () => {
    await runReferenceMap();
    refetchStatus();
  };

  const handleConflictCheck = async () => {
    const res = await runConflictCheck();
    if (res) setConflicts(res);
    refetchStatus();
  };

  const handleValidation = async () => {
    await runValidation();
    refetchStatus();
  };

  const handleGroupSelect = async (name: string) => {
    setSelectedGroup(name);
    // Trigger dry run preview when selecting a group
    const res = await runExtraction(name, { dry_run: true });
    if (res) {
      setDryRunResult(res);
      setDryRunGroup(name);
    }
  };

  const handleCommitExtraction = async () => {
    if (!dryRunGroup) return;
    const res = await runExtraction(dryRunGroup, { dry_run: false });
    if (res) {
      setDryRunResult(res);
    }
    refetchStatus();
    refetchGroups();
  };

  return (
    <div className="space-y-4">
      {/* Pipeline Stepper */}
      <Card>
        <CardContent className="pt-4 pb-2">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-neutral-700">Pipeline Progress</h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => { refetchStatus(); refetchGroups(); }}
              disabled={statusLoading}
            >
              <RefreshCw className={`h-4 w-4 ${statusLoading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
          <GroupPipelineStepper status={status} isLoading={statusLoading} />
        </CardContent>
      </Card>

      {/* Action Bar */}
      <Card>
        <CardContent className="py-3">
          <div className="flex items-center gap-2 flex-wrap">
            <PhaseBtn icon={Search} label="Discovery" loading={discovering} onClick={handleDiscovery} disabled={anyRunning} />
            <PhaseBtn icon={Fingerprint} label="Fingerprint" loading={fingerprinting} onClick={handleFingerprint} disabled={anyRunning || !hasDiscovery} />
            <PhaseBtn icon={Map} label="Reference Map" loading={mapping} onClick={handleReferenceMap} disabled={anyRunning || !hasFingerprint} />
            <PhaseBtn icon={AlertTriangle} label="Conflict Check" loading={conflictChecking} onClick={handleConflictCheck} disabled={anyRunning || !hasReferenceMap} />
            <PhaseBtn icon={CheckCircle2} label="Validate" loading={validating} onClick={handleValidation} disabled={anyRunning || !hasExtract} />
            <div className="flex-1" />
            {groups.length > 0 && hasConflictCheck && (
              <Button size="sm" onClick={() => setShowBatch((v) => !v)}>
                {showBatch ? 'Hide Batch' : 'Batch Extract'}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Conflict Report (after conflict check) */}
      {conflicts && (
        <ConflictReport conflicts={conflicts} isLoading={conflictChecking} />
      )}

      {/* Batch Extraction Panel */}
      {showBatch && groups.length > 0 && (
        <BatchExtractionPanel groups={groups} />
      )}

      {/* Group List */}
      {groups.length > 0 && (
        <GroupList onGroupSelect={handleGroupSelect} />
      )}

      {/* Selected Group Detail + Dry Run Preview */}
      {selectedGroup && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <GroupDetail
            groupName={selectedGroup}
            onClose={() => {
              setSelectedGroup(null);
              setDryRunResult(null);
              setDryRunGroup('');
            }}
          />
          <DryRunPreview
            result={dryRunResult}
            groupName={dryRunGroup}
            onCommit={handleCommitExtraction}
            isLoading={extracting}
          />
        </div>
      )}
    </div>
  );
}
