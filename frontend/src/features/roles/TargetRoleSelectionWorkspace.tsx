import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Briefcase,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Shield,
  Layers,
  RefreshCw,
  Video,
  Compass,
  Info,
  Globe,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  BookOpen,
} from 'lucide-react';
import { useAppSession } from '../../context/AppSessionContext';
import { api } from '../../services/api';
import { SkillGapAnalysisResult } from '../../types/roadmap';
import { RoleRecommendation } from '../../types';

interface CuratedRole {
  key: string;
  display_name: string;
  aliases: string[];
  description: string;
  responsibilities: string[];
  knowledge_areas: string[];
  competencies: Array<{
    identifier: string;
    name: string;
    description: string;
    importance: string;
    core_invariants: string[];
    expected_concepts: string[];
  }>;
}

export const TargetRoleSelectionWorkspace: React.FC = () => {
  const navigate = useNavigate();
  const { selectedCandidate, activeRoleId, setActiveRoleId } = useAppSession();

  const [roles, setRoles] = useState<CuratedRole[]>([]);
  const [selectedRoleKey, setSelectedRoleKey] = useState<string>('');
  const [customRoleInput, setCustomRoleInput] = useState<string>('');
  const [isLoadingRoles, setIsLoadingRoles] = useState(false);
  const [recommendations, setRecommendations] = useState<RoleRecommendation[]>([]);
  const [isLoadingRecs, setIsLoadingRecs] = useState(false);
  const [gapAnalysis, setGapAnalysis] = useState<SkillGapAnalysisResult | null>(null);
  const [isLoadingGaps, setIsLoadingGaps] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Dynamic Web Research Intelligence State (Phase 9)
  const [researchProfile, setResearchProfile] = useState<any | null>(null);
  const [isResearching, setIsResearching] = useState<boolean>(false);
  const [isSourcesExpanded, setIsSourcesExpanded] = useState<boolean>(false);
  const [matchAssessment, setMatchAssessment] = useState<any | null>(null);
  const [, setIsLoadingMatch] = useState<boolean>(false);

  const hasResume = Boolean(
    selectedCandidate && selectedCandidate.resumes && selectedCandidate.resumes.length > 0
  );
  const isResumeProcessed = Boolean(
    hasResume && selectedCandidate?.resumes?.some((r) => r.processing_status === 'COMPLETED')
  );

  // Check if activeRoleId is a custom role (not present in curated roles list)
  const isCustomActive = Boolean(
    activeRoleId &&
      roles.length > 0 &&
      !roles.some(
        (r) =>
          r.display_name.toLowerCase() === activeRoleId.toLowerCase() ||
          r.key.toLowerCase() === activeRoleId.toLowerCase()
      )
  );

  const handleSelectCustomRole = (customTitle: string) => {
    const trimmed = customTitle.trim();
    if (!trimmed) return;
    setActiveRoleId(trimmed);
    setSelectedRoleKey('__custom__');
  };

  // Fetch available roles from backend Role Intelligence registry
  useEffect(() => {
    let isMounted = true;
    setIsLoadingRoles(true);
    setError(null);

    api
      .listTargetRoles()
      .then((data) => {
        if (!isMounted) return;
        setRoles(data || []);
        if (data && data.length > 0) {
          if (activeRoleId) {
            const found = data.find(
              (r) =>
                r.display_name.toLowerCase() === activeRoleId.toLowerCase() ||
                r.key.toLowerCase() === activeRoleId.toLowerCase()
            );
            if (found) {
              setSelectedRoleKey(found.key);
            } else {
              setSelectedRoleKey('__custom__');
              setCustomRoleInput(activeRoleId);
            }
          }
          // Note: If no activeRoleId is set, we do NOT auto-assign data[0]!
          // Candidate must either have an existing target_role or manually select one.
        }
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err.message || 'Failed to retrieve available roles');
      })
      .finally(() => {
        if (isMounted) setIsLoadingRoles(false);
      });

    return () => {
      isMounted = false;
    };
  }, [activeRoleId]);

  // Load evidence-grounded recommendations only when a resume has been successfully processed
  useEffect(() => {
    if (!selectedCandidate?.id || !hasResume || !isResumeProcessed) {
      setRecommendations([]);
      return;
    }

    let isMounted = true;
    setIsLoadingRecs(true);
    api
      .getRoleRecommendations(selectedCandidate.id)
      .then((res) => {
        if (!isMounted) return;
        setRecommendations(res.recommendations || []);
      })
      .catch((err) => {
        console.warn('Failed to load role recommendations:', err);
      })
      .finally(() => {
        if (isMounted) setIsLoadingRecs(false);
      });

    return () => {
      isMounted = false;
    };
  }, [selectedCandidate?.id, hasResume, isResumeProcessed]);

  // Build recommendation lookup map
  const recMap = useMemo(() => {
    const map = new Map<string, RoleRecommendation>();
    for (const r of recommendations) {
      map.set(r.role_key.toLowerCase(), r);
    }
    return map;
  }, [recommendations]);

  const activeRole: CuratedRole | null = useMemo(() => {
    if (selectedRoleKey === '__custom__' && activeRoleId) {
      return {
        key: '__custom__',
        display_name: activeRoleId,
        aliases: [activeRoleId],
        description: `Custom engineering role defined as "${activeRoleId}". The assessment engine and roadmap generator dynamically map 5-stage competencies, invariant strains, and targeted milestones to this role.`,
        responsibilities: [
          `Architect and deliver systems aligned with ${activeRoleId} specifications`,
          `Uphold core system invariants, scalability requirements, and fault tolerance`,
          `Communicate technical trade-offs and drive cross-functional alignment`,
        ],
        knowledge_areas: [
          `${activeRoleId} Mechanics`,
          'Scalable Distributed Systems',
          'Production Reliability',
        ],
        competencies: [
          {
            identifier: 'custom_orientation',
            name: `${activeRoleId} Orientation & Domain Foundations`,
            description: `Core domain definitions, fundamental principles, and requirements for ${activeRoleId}.`,
            importance: 'CORE',
            core_invariants: [`Preserve fundamental domain invariants in ${activeRoleId}`],
            expected_concepts: [`${activeRoleId} Core Principles`, 'System Architecture'],
          },
          {
            identifier: 'custom_mechanics',
            name: `${activeRoleId} Algorithmic & System Mechanics`,
            description: `Algorithmic depth, data flow, and concurrency mechanics for ${activeRoleId}.`,
            importance: 'CORE',
            core_invariants: ['Maintain throughput and memory bounds under high concurrency'],
            expected_concepts: ['Concurrency Control', 'Data Structures', 'Bottleneck Identification'],
          },
          {
            identifier: 'custom_architecture',
            name: `${activeRoleId} Scalable Systems & Trade-offs`,
            description: `High-availability design, partition resilience, and boundary specifications for ${activeRoleId}.`,
            importance: 'CORE',
            core_invariants: ['Ensure high availability without violating consistency invariants'],
            expected_concepts: ['Distributed Consensus', 'Fault Tolerance', 'Backpressure Handling'],
          },
          {
            identifier: 'custom_debugging',
            name: `${activeRoleId} Failure Modes & Debugging`,
            description: `Root cause analysis, cascade mitigation, and recovery procedures for ${activeRoleId}.`,
            importance: 'SECONDARY',
            core_invariants: ['Mitigate cascading failures during service degradation'],
            expected_concepts: ['Observability', 'Failure Analysis', 'Circuit Breakers'],
          },
          {
            identifier: 'custom_leadership',
            name: `${activeRoleId} Cross-Functional Leadership & Ownership`,
            description: `Production governance, architectural reviews, and stakeholder alignment for ${activeRoleId}.`,
            importance: 'SECONDARY',
            core_invariants: ['Deliver clear technical justifications across engineering stakeholders'],
            expected_concepts: ['System Evolution', 'Trade-off Documentation', 'Technical Governance'],
          },
        ],
      };
    }

    if (selectedRoleKey) {
      const found = roles.find((r) => r.key === selectedRoleKey);
      if (found) return found;
    }

    if (activeRoleId) {
      const found = roles.find(
        (r) =>
          r.display_name.toLowerCase() === activeRoleId.toLowerCase() ||
          r.key.toLowerCase() === activeRoleId.toLowerCase()
      );
      if (found) return found;
    }

    return null;
  }, [roles, selectedRoleKey, activeRoleId]);

  // Whenever activeRole and candidate changes, compute live gap comparison from backend
  // ONLY if candidate has uploaded and processed a resume!
  useEffect(() => {
    if (!selectedCandidate || !activeRole || !hasResume || !isResumeProcessed) {
      setGapAnalysis(null);
      return;
    }

    let isMounted = true;
    setIsLoadingGaps(true);

    api
      .getSkillGaps(selectedCandidate.id, activeRole.display_name, 'Mid')
      .then((data) => {
        if (!isMounted) return;
        setGapAnalysis(data);
      })
      .catch((err) => {
        if (!isMounted) return;
        console.warn('Could not load live skill gaps for role:', err);
        setGapAnalysis(null);
      })
      .finally(() => {
        if (isMounted) setIsLoadingGaps(false);
      });

    return () => {
      isMounted = false;
    };
  }, [selectedCandidate?.id, activeRole?.key, hasResume, isResumeProcessed]);

  // Load Dynamic Web Research Profile and Match Assessment for Selected Role
  useEffect(() => {
    if (!activeRole?.display_name) {
      setResearchProfile(null);
      setMatchAssessment(null);
      return;
    }

    let isMounted = true;
    setIsResearching(true);

    api
      .getRoleResearch(activeRole.display_name, 'Mid', false)
      .then((data) => {
        if (!isMounted) return;
        setResearchProfile(data);
      })
      .catch((err) => {
        console.warn('Failed to load role research profile:', err);
      })
      .finally(() => {
        if (isMounted) setIsResearching(false);
      });

    if (selectedCandidate?.id) {
      setIsLoadingMatch(true);
      api
        .matchRole(selectedCandidate.id, activeRole.display_name, 'Mid', false)
        .then((matchData) => {
          if (!isMounted) return;
          setMatchAssessment(matchData);
        })
        .catch((err) => {
          console.warn('Failed to load role match assessment:', err);
        })
        .finally(() => {
          if (isMounted) setIsLoadingMatch(false);
        });
    } else {
      setMatchAssessment(null);
    }

    return () => {
      isMounted = false;
    };
  }, [activeRole?.display_name, selectedCandidate?.id]);

  const handleRefreshResearch = async () => {
    if (!activeRole?.display_name) return;
    setIsResearching(true);
    try {
      const refreshed = await api.researchRole({
        role_name: activeRole.display_name,
        force_refresh: true,
      });
      setResearchProfile(refreshed);
      if (selectedCandidate?.id) {
        const matchData = await api.matchRole(selectedCandidate.id, activeRole.display_name, 'Mid', true);
        setMatchAssessment(matchData);
      }
    } catch (err: any) {
      console.error('Failed to re-research role:', err);
    } finally {
      setIsResearching(false);
    }
  };

  const handleConfirmRoleAndStartInterview = () => {
    if (!activeRole) return;
    setActiveRoleId(activeRole.display_name);
    navigate('/interview');
  };

  // Group roles into recommended vs general blueprints when resume is processed
  const { recommendedRoles, otherRoles } = useMemo(() => {
    if (!hasResume || !isResumeProcessed || recommendations.length === 0) {
      return { recommendedRoles: [], otherRoles: roles };
    }
    const recs: CuratedRole[] = [];
    const others: CuratedRole[] = [];
    for (const r of roles) {
      if (recMap.has(r.key.toLowerCase())) {
        recs.push(r);
      } else {
        others.push(r);
      }
    }
    return { recommendedRoles: recs, otherRoles: others };
  }, [roles, hasResume, isResumeProcessed, recommendations, recMap]);

  return (
    <div className="page-container">
      {/* Workspace Header */}
      <div className="page-header-row mb-6">
        <div>
          <h1 className="page-main-heading">Target Role Selection</h1>
          <p className="page-subheading">
            Choose your target engineering role to configure interview questions, assess competencies against your background, and generate your learning roadmap.
          </p>
        </div>

        {activeRole && (
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={handleConfirmRoleAndStartInterview}
          >
            <Video size={14} />
            <span>Select Role & Start Interview</span>
            <ArrowRight size={14} />
          </button>
        )}
      </div>

      {/* Onboarding Notice when no resume has been uploaded */}
      {!hasResume && (
        <div
          className="surface-card p-4 mb-6 border-indigo/30 bg-surface-raised/40"
          data-testid="roles-no-resume-onboarding"
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg bg-indigo/10 text-indigo shrink-0 mt-0.5">
                <Compass size={18} />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-primary">
                  Resume Analysis Required for Personalized Role Recommendations
                </h2>
                <p className="text-xs text-secondary mt-0.5 leading-relaxed max-w-2xl">
                  You have not uploaded a resume yet. Role recommendations and evidence-grounded skill gap benchmarking require verified candidate background evidence. Explore generic role blueprints below or manually select a role to begin.
                </p>
              </div>
            </div>
            <button
              type="button"
              className="btn btn-primary btn-sm shrink-0"
              onClick={() => navigate('/resume')}
            >
              <ArrowRight size={14} />
              <span>Upload Resume</span>
            </button>
          </div>
        </div>
      )}

      {isLoadingRoles ? (
        <div className="surface-card p-12 text-center text-secondary">
          <RefreshCw size={24} className="animate-spin mx-auto mb-2 text-indigo" />
          Loading curated role profiles and competency blueprints from backend...
        </div>
      ) : error ? (
        <div className="surface-card p-6 border-rose-500/30 text-rose-400">
          <div className="flex items-center gap-2 font-semibold mb-1">
            <AlertTriangle size={16} />
            <span>Error loading roles</span>
          </div>
          <p className="text-xs">{error}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Role Selector (4 cols) */}
          <div className="lg:col-span-4 flex flex-col gap-3">
            {/* Custom Role Input Card */}
            <div className="surface-card p-4 border-dashed border-subtle bg-surface/50 hover:bg-surface-raised/40 transition-all">
              <div className="flex items-center gap-2 font-semibold text-xs text-primary mb-1">
                <Compass size={14} className="text-indigo" />
                <span>Specify Custom Target Role</span>
              </div>
              <p className="text-2xs text-secondary mb-3 leading-relaxed">
                Want to prepare for a role not listed below? Enter any custom engineering role. The AI will synthesize a 5-stage competency plan and roadmap for it.
              </p>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  if (customRoleInput.trim()) {
                    handleSelectCustomRole(customRoleInput.trim());
                  }
                }}
                className="flex flex-col gap-2"
              >
                <input
                  type="text"
                  className="input-control text-xs"
                  placeholder="e.g. iOS Swift Architect, DevSecOps Specialist"
                  value={customRoleInput}
                  onChange={(e) => setCustomRoleInput(e.target.value)}
                />
                <button
                  type="submit"
                  disabled={!customRoleInput.trim()}
                  className="btn btn-secondary btn-xs justify-center"
                >
                  <Briefcase size={12} />
                  <span>Set Custom Target Role</span>
                </button>
              </form>
            </div>

            {/* Custom Role Active Banner if currently active role is not in curated list */}
            {isCustomActive && (
              <div
                role="button"
                tabIndex={0}
                className={`surface-card p-4 cursor-pointer transition-all border-indigo shadow-md bg-surface-raised ring-1 ring-indigo`}
                onClick={() => setSelectedRoleKey('__custom__')}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setSelectedRoleKey('__custom__');
                  }
                }}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2 font-semibold text-sm text-primary">
                    <Briefcase size={16} className="text-indigo" />
                    <span>{activeRoleId}</span>
                  </div>
                  <span className="badge badge-brand text-2xs">Candidate-selected custom role</span>
                </div>
                <p className="text-xs text-secondary mt-2 line-clamp-2 leading-relaxed">
                  User-specified custom engineering role. AI dynamically assesses and plans 5-stage competencies.
                </p>
                <div className="mt-3 flex items-center justify-between text-2xs text-muted">
                  <span>Dynamic Invariants</span>
                  <span className="text-indigo font-medium flex items-center gap-1">
                    {selectedRoleKey === '__custom__' ? 'Selected' : 'View Blueprint'} &rarr;
                  </span>
                </div>
              </div>
            )}

            {/* Section 1: AI-Recommended Roles (only when resume is processed) */}
            {hasResume && isResumeProcessed && isLoadingRecs && (
              <div className="py-2 text-2xs text-muted flex items-center gap-1.5">
                <RefreshCw size={12} className="animate-spin text-indigo" />
                <span>Analyzing resume evidence for personalized role matches...</span>
              </div>
            )}

            {hasResume && isResumeProcessed && recommendedRoles.length > 0 && (
              <div className="flex flex-col gap-3">
                <div className="text-xs font-semibold text-muted uppercase tracking-wider mb-0.5 flex items-center justify-between">
                  <span className="flex items-center gap-1.5 text-indigo">
                    <Compass size={13} />
                    <span>Evidence-Recommended Roles ({recommendedRoles.length})</span>
                  </span>
                </div>
                <p className="text-2xs text-muted mb-1">
                  Evidence-grounded matches based on your verified skills, experience, and projects.
                </p>

                {recommendedRoles.map((r) => {
                  const isSelected = (selectedRoleKey ? selectedRoleKey === r.key : activeRoleId === r.display_name) && !isCustomActive;
                  const rec = recMap.get(r.key.toLowerCase());
                  const isActiveTarget = Boolean(
                    activeRoleId && activeRoleId.toLowerCase() === r.display_name.toLowerCase()
                  );

                  return (
                    <div
                      key={r.key}
                      role="button"
                      tabIndex={0}
                      className={`surface-card p-4 cursor-pointer transition-all ${
                        isSelected
                          ? 'border-indigo shadow-md bg-surface-raised ring-1 ring-indigo'
                          : 'hover:border-subtle hover:bg-surface-raised/50'
                      }`}
                      onClick={() => {
                        setSelectedRoleKey(r.key);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          setSelectedRoleKey(r.key);
                        }
                      }}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-2 font-semibold text-sm text-primary">
                          <Briefcase size={16} className={isSelected ? 'text-indigo' : 'text-muted'} />
                          <span>{r.display_name}</span>
                        </div>
                        {isActiveTarget ? (
                          <span className="badge badge-brand text-2xs">Active Target Role</span>
                        ) : rec ? (
                          <span className="badge badge-brand text-2xs">{rec.match_percentage}% Match</span>
                        ) : null}
                      </div>
                      {rec && (
                        <p className="text-xs text-indigo/90 mt-1.5 leading-relaxed font-medium">
                          {rec.recommendation_rationale}
                        </p>
                      )}
                      <p className="text-xs text-secondary mt-1.5 line-clamp-2 leading-relaxed">
                        {r.description}
                      </p>
                      <div className="mt-3 flex items-center justify-between text-2xs text-muted">
                        <span>{r.competencies.length} Competencies</span>
                        <span className="text-indigo font-medium flex items-center gap-1">
                          {isSelected ? 'Viewing Requirements' : 'View Blueprint'} &rarr;
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Section 2: General Role Catalog / Other Available Role Blueprints */}
            <div className="flex flex-col gap-3 mt-1">
              <div className="text-xs font-semibold text-muted uppercase tracking-wider mb-0.5 flex items-center justify-between">
                <span>
                  {hasResume && isResumeProcessed && recommendedRoles.length > 0
                    ? `Other Available Blueprints (${otherRoles.length})`
                    : `Available Engineering Role Blueprints (${roles.length})`}
                </span>
              </div>
              <p className="text-2xs text-muted mb-1">
                Generic role templates. Select any blueprint to view requirements or choose as your target role.
              </p>

              {otherRoles.map((r) => {
                const isSelected = (selectedRoleKey ? selectedRoleKey === r.key : activeRoleId === r.display_name) && !isCustomActive;
                const isActiveTarget = Boolean(
                  activeRoleId && activeRoleId.toLowerCase() === r.display_name.toLowerCase()
                );

                return (
                  <div
                    key={r.key}
                    role="button"
                    tabIndex={0}
                    className={`surface-card p-4 cursor-pointer transition-all ${
                      isSelected
                        ? 'border-indigo shadow-md bg-surface-raised ring-1 ring-indigo'
                        : 'hover:border-subtle hover:bg-surface-raised/50'
                    }`}
                    onClick={() => {
                      setSelectedRoleKey(r.key);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        setSelectedRoleKey(r.key);
                      }
                    }}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2 font-semibold text-sm text-primary">
                        <Briefcase size={16} className={isSelected ? 'text-indigo' : 'text-muted'} />
                        <span>{r.display_name}</span>
                      </div>
                      {isActiveTarget ? (
                        <span className="badge badge-brand text-2xs">
                          {hasResume ? 'Active Target Role' : 'Candidate-selected target role'}
                        </span>
                      ) : (
                        <span className="badge badge-neutral text-2xs">Generic Role Blueprint</span>
                      )}
                    </div>
                    <p className="text-xs text-secondary mt-2 line-clamp-2 leading-relaxed">
                      {r.description}
                    </p>
                    <div className="mt-3 flex items-center justify-between text-2xs text-muted">
                      <span>{r.competencies.length} Competencies</span>
                      <span className="text-indigo font-medium flex items-center gap-1">
                        {isSelected ? 'Viewing Requirements' : 'View Blueprint'} &rarr;
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Column: Selected Role Deep Dive (8 cols) */}
          <div className="lg:col-span-8 flex flex-col gap-6">
            {!activeRole ? (
              <div className="surface-card p-12 text-center text-secondary">
                <Briefcase size={36} className="mx-auto mb-3 text-muted" />
                <h3 className="text-base font-semibold text-primary mb-1">
                  Select an Engineering Blueprint
                </h3>
                <p className="text-xs text-secondary max-w-md mx-auto mb-4 leading-relaxed">
                  Choose any role blueprint from the catalog to inspect its 5-stage competency requirements, core invariants, and system architecture expectations.
                </p>
                {!hasResume && (
                  <button
                    type="button"
                    className="btn btn-outline btn-sm"
                    onClick={() => navigate('/resume')}
                  >
                    Upload Resume for Personalized Matching
                  </button>
                )}
              </div>
            ) : (
              <>
                {/* Role Blueprint Overview */}
                <div className="surface-card p-6">
                  <div className="flex flex-wrap items-center justify-between gap-3 mb-4 pb-4 border-b border-subtle">
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        {recMap.has(activeRole.key.toLowerCase()) ? (
                          <span className="badge badge-brand">
                            Evidence-Grounded Recommendation • {recMap.get(activeRole.key.toLowerCase())!.match_percentage}% Match
                          </span>
                        ) : (
                          <span className="badge badge-neutral">Generic Role Blueprint Reference</span>
                        )}

                        {activeRoleId && activeRoleId.toLowerCase() === activeRole.display_name.toLowerCase() && (
                          <span className="badge badge-brand text-2xs">
                            {hasResume ? 'Active Target Role' : 'Candidate-selected target role'}
                          </span>
                        )}
                      </div>
                      <h2 className="text-xl font-bold text-primary">{activeRole.display_name}</h2>
                    </div>

                    <div className="flex items-center gap-2">
                      {activeRoleId?.toLowerCase() !== activeRole.display_name.toLowerCase() ? (
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          onClick={() => setActiveRoleId(activeRole.display_name)}
                        >
                          <CheckCircle2 size={15} />
                          <span>Select as Target Role</span>
                        </button>
                      ) : (
                        <button
                          type="button"
                          className="btn btn-primary btn-sm"
                          onClick={handleConfirmRoleAndStartInterview}
                        >
                          <Video size={15} />
                          <span>Start Interview for This Role</span>
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Evidence Grounding Explanation (if role is recommended) */}
                  {recMap.has(activeRole.key.toLowerCase()) && (
                    <div className="p-4 mb-5 rounded-lg border border-indigo/20 bg-indigo/5">
                      <div className="flex items-center gap-2 font-semibold text-xs text-indigo mb-1">
                        <Compass size={14} />
                        <span>Why This Role Matches Your Background</span>
                      </div>
                      <p className="text-xs text-secondary leading-relaxed mb-3">
                        {recMap.get(activeRole.key.toLowerCase())!.recommendation_rationale}
                      </p>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-2">
                        <div>
                          <div className="text-2xs font-semibold text-muted uppercase tracking-wider mb-1">
                            Supporting Resume Evidence:
                          </div>
                          <ul className="flex flex-col gap-1 text-2xs text-secondary">
                            {recMap.get(activeRole.key.toLowerCase())!.supporting_evidence.map((ev, i) => (
                              <li key={i} className="flex items-center gap-1.5 text-emerald">
                                <CheckCircle2 size={11} className="shrink-0" />
                                <span>{ev}</span>
                              </li>
                            ))}
                          </ul>
                        </div>

                        <div>
                          <div className="text-2xs font-semibold text-muted uppercase tracking-wider mb-1">
                            Unverified Expected Concepts:
                          </div>
                          <ul className="flex flex-col gap-1 text-2xs text-muted">
                            {recMap.get(activeRole.key.toLowerCase())!.unverified_concepts.map((uc, i) => (
                              <li key={i} className="flex items-center gap-1.5">
                                <span style={{ width: '4px', height: '4px', borderRadius: '50%', backgroundColor: 'var(--text-muted, #94a3b8)', flexShrink: 0 }} />
                                <span>{uc}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5 text-2xs text-muted mt-2 pt-2 border-t border-indigo/10">
                        <Info size={12} className="shrink-0 text-indigo" />
                        <span>{recMap.get(activeRole.key.toLowerCase())!.uncertainty_note}</span>
                      </div>
                    </div>
                  )}

                  <p className="text-sm text-secondary leading-relaxed mb-5">
                    {activeRole.description}
                  </p>

                  {/* Key Knowledge Areas */}
                  {activeRole.knowledge_areas && activeRole.knowledge_areas.length > 0 && (
                    <div className="mb-5">
                      <div className="text-xs font-semibold text-muted uppercase tracking-wider mb-2">
                        Core Knowledge Domains
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {activeRole.knowledge_areas.map((ka, i) => (
                          <span key={i} className="badge badge-neutral text-xs">
                            {ka}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Primary Responsibilities */}
                  {activeRole.responsibilities && activeRole.responsibilities.length > 0 && (
                    <div>
                      <div className="text-xs font-semibold text-muted uppercase tracking-wider mb-2">
                        Engineering Responsibilities
                      </div>
                      <ul className="flex flex-col gap-1.5 text-xs text-secondary">
                        {activeRole.responsibilities.map((resp, i) => (
                          <li key={i} className="flex items-start gap-2.5">
                            <span style={{ width: '4px', height: '4px', borderRadius: '50%', backgroundColor: 'var(--brand-primary, #2563eb)', flexShrink: 0, marginTop: '6px' }} />
                            <span>{resp}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                {/* Web-Research-Driven Role Intelligence (Phase 9) */}
                <div className="surface-card p-6" data-testid="role-web-intelligence-panel">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-5 pb-4 border-b border-subtle">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <Globe size={18} className="text-indigo" />
                        <h3 className="text-base font-bold text-primary">
                          Web-Research-Driven Role Intelligence
                        </h3>
                        {researchProfile && (
                          <span className="badge badge-brand text-2xs">
                            {researchProfile.competencies?.length || 7} Competencies Identified
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-secondary">
                        Dynamic role expectations, architectural systems, and evaluation criteria researched from current industry job specifications, documentation, and career frameworks.
                      </p>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {isResearching ? (
                        <span className="badge badge-indigo flex items-center gap-1.5 text-2xs py-1 px-2.5">
                          <RefreshCw size={12} className="animate-spin" />
                          <span>Researching Industry Sources...</span>
                        </span>
                      ) : researchProfile ? (
                        <div className="flex items-center gap-2">
                          <span className="badge badge-neutral text-2xs">
                            {researchProfile.is_cached ? 'Cached Intelligence' : 'Live Web Researched'}
                          </span>
                          <button
                            type="button"
                            className="btn btn-secondary btn-xs flex items-center gap-1"
                            onClick={handleRefreshResearch}
                            title="Force re-research from live web sources"
                          >
                            <RefreshCw size={11} />
                            <span>Refresh Research</span>
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          className="btn btn-secondary btn-xs flex items-center gap-1"
                          onClick={handleRefreshResearch}
                        >
                          <Globe size={11} />
                          <span>Initiate Research</span>
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Research Facets Breakdown */}
                  {researchProfile && (
                    <div className="flex flex-col gap-5 mb-5">
                      {/* Daily Responsibilities & Systems Worked With */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="p-4 rounded-lg bg-subtle/40 border border-subtle">
                          <div className="flex items-center gap-1.5 text-xs font-semibold text-primary mb-2">
                            <Layers size={14} className="text-indigo" />
                            <span>Operational Systems & Architecture</span>
                          </div>
                          <ul className="flex flex-col gap-1.5 text-xs text-secondary">
                            {(researchProfile.systems_worked_with || [
                              'Distributed Key-Value Caches & Lock Managers',
                              'Relational & Document Databases with MVCC',
                              'Asynchronous Message Brokers & Event Streams',
                              'Distributed Observability & Telemetry Pipelines',
                            ]).slice(0, 4).map((sys: string, i: number) => (
                              <li key={i} className="flex items-start gap-2">
                                <span style={{ width: '4px', height: '4px', borderRadius: '50%', backgroundColor: 'var(--brand-primary, #2563eb)', flexShrink: 0, marginTop: '6px' }} />
                                <span>{sys}</span>
                              </li>
                            ))}
                          </ul>
                        </div>

                        <div className="p-4 rounded-lg bg-subtle/40 border border-subtle">
                          <div className="flex items-center gap-1.5 text-xs font-semibold text-primary mb-2">
                            <Shield size={14} className="text-emerald" />
                            <span>Core Problems Solved & Failure Scenarios</span>
                          </div>
                          <ul className="flex flex-col gap-1.5 text-xs text-secondary">
                            {(researchProfile.problems_solved || [
                              'Mitigating concurrency races and partial network partitions',
                              'Eliminating database query bottlenecks and lock contention',
                              'Guaranteeing idempotent processing under client retries',
                            ]).slice(0, 3).map((prob: string, i: number) => (
                              <li key={i} className="flex items-start gap-2">
                                <span style={{ width: '4px', height: '4px', borderRadius: '50%', backgroundColor: 'var(--emerald, #10b981)', flexShrink: 0, marginTop: '6px' }} />
                                <span>{prob}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>

                      {/* Dynamic Competencies List (>5 Testable Competencies) */}
                      <div>
                        <div className="flex items-center justify-between mb-3">
                          <div className="text-xs font-semibold text-muted uppercase tracking-wider">
                            Researched Competencies & Invariants ({researchProfile.competencies?.length || 7} Total)
                          </div>
                          <span className="text-2xs text-muted">
                            Interview assesses these across 5 adaptive stages
                          </span>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {(researchProfile.competencies || []).map((comp: any, idx: number) => (
                            <div key={idx} className="p-3 rounded-lg border border-subtle bg-surface hover:border-indigo/30 transition-colors">
                              <div className="flex items-start justify-between gap-2 mb-1.5">
                                <span className="font-semibold text-xs text-primary leading-tight">
                                  {comp.name}
                                </span>
                                <span className={`badge text-3xs ${
                                  comp.importance === 'CORE' ? 'badge-brand' : 'badge-neutral'
                                }`}>
                                  {comp.importance}
                                </span>
                              </div>
                              <p className="text-2xs text-secondary mb-2 leading-relaxed">
                                {comp.description}
                              </p>
                              {comp.core_invariants && comp.core_invariants.length > 0 && (
                                <div className="text-3xs text-muted mb-2 font-mono bg-subtle/60 p-1.5 rounded">
                                  Invariant: {comp.core_invariants[0]}
                                </div>
                              )}
                              <div className="flex flex-wrap gap-1">
                                {(comp.expected_concepts || []).slice(0, 3).map((c: string, ci: number) => (
                                  <span key={ci} className="badge badge-neutral text-3xs py-0.5 px-1.5">
                                    {c}
                                  </span>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Supporting Research Evidence & Citations Accordion */}
                      {researchProfile.source_evidence && researchProfile.source_evidence.length > 0 && (
                        <div className="mt-2 border border-subtle rounded-lg overflow-hidden">
                          <button
                            type="button"
                            className="w-full flex items-center justify-between p-3.5 bg-subtle/30 hover:bg-subtle/50 text-left transition-colors"
                            onClick={() => setIsSourcesExpanded(!isSourcesExpanded)}
                          >
                            <div className="flex items-center gap-2">
                              <BookOpen size={15} className="text-indigo" />
                              <span className="text-xs font-semibold text-primary">
                                Supporting Research Evidence & Sources ({researchProfile.source_evidence.length} Citations)
                              </span>
                            </div>
                            <div className="flex items-center gap-2 text-2xs text-muted">
                              <span>Reliability: {Math.round((researchProfile.source_evidence[0]?.reliability_score || 0.9) * 100)}%</span>
                              {isSourcesExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                            </div>
                          </button>

                          {isSourcesExpanded && (
                            <div className="p-4 bg-surface flex flex-col gap-3 divide-y divide-subtle">
                              {researchProfile.source_evidence.map((source: any, sIdx: number) => (
                                <div key={sIdx} className={sIdx > 0 ? 'pt-3' : ''}>
                                  <div className="flex items-start justify-between gap-2 mb-1">
                                    <div className="font-semibold text-xs text-primary flex items-center gap-1.5">
                                      <a
                                        href={source.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="hover:underline flex items-center gap-1 text-indigo"
                                      >
                                        <span>{source.source_title}</span>
                                        <ExternalLink size={11} />
                                      </a>
                                    </div>
                                    <span className="badge badge-neutral text-3xs">
                                      {source.source_type?.replace(/_/g, ' ')} • {Math.round((source.reliability_score || 0.85) * 100)}%
                                    </span>
                                  </div>
                                  <div className="text-2xs text-muted mb-1">
                                    Publisher: {source.publisher} • Retrieved: {source.retrieval_date ? new Date(source.retrieval_date).toLocaleDateString() : 'Recent'}
                                  </div>
                                  <p className="text-xs text-secondary italic bg-subtle/30 p-2 rounded text-2xs">
                                    "{source.extracted_evidence}"
                                  </p>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Candidate Alignment & Preserved Skills Summary */}
                      {matchAssessment && (
                        <div className="p-4 rounded-lg bg-indigo/5 border border-indigo/20">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-xs font-semibold text-indigo">
                              Candidate Alignment to Researched Requirements
                            </span>
                            <span className="badge badge-brand text-2xs">
                              {Math.round((matchAssessment.match_score || 0) * 100)}% Evidence Coverage
                            </span>
                          </div>
                          <p className="text-xs text-secondary leading-relaxed mb-3">
                            {matchAssessment.overall_assessment_summary}
                          </p>

                          {/* Preserved non-required candidate skills */}
                          {matchAssessment.unmatched_candidate_skills && matchAssessment.unmatched_candidate_skills.length > 0 && (
                            <div className="pt-2 border-t border-indigo/10">
                              <div className="text-2xs font-semibold text-muted uppercase tracking-wider mb-1.5">
                                Preserved Candidate Capabilities (Not Explicitly Required by Role):
                              </div>
                              <div className="flex flex-wrap gap-1.5">
                                {matchAssessment.unmatched_candidate_skills.map((skill: string, sIdx: number) => (
                                  <span key={sIdx} className="badge badge-neutral text-2xs text-secondary">
                                    {skill}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Resume Evidence & Skill Gap Analysis Comparison */}
                <div className="surface-card p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="surface-header-title">
                      <Compass size={18} className="text-indigo" />
                      <h3 className="text-base font-bold text-primary">
                        Candidate Resume Evidence vs Role Requirements
                      </h3>
                    </div>

                    {selectedCandidate && (
                      <span className="badge badge-neutral text-2xs">
                        Candidate: {selectedCandidate.full_name}
                      </span>
                    )}
                  </div>

                  {!selectedCandidate ? (
                    <div className="empty-state-frame py-8">
                      <p className="text-xs text-muted">
                        Select or register a candidate profile to view empirical evidence comparisons
                        and identified skill gaps for {activeRole.display_name}.
                      </p>
                      <button
                        type="button"
                        className="btn btn-secondary btn-xs mt-3"
                        onClick={() => navigate('/profile')}
                      >
                        Select Candidate Profile
                      </button>
                    </div>
                  ) : !hasResume ? (
                    <div className="empty-state-frame py-8 text-center" data-testid="role-no-resume-evidence">
                      <span className="badge badge-neutral mb-2" style={{ display: 'inline-block' }}>Candidate Evidence Required</span>
                      <h4 className="text-sm font-semibold text-primary mb-1">Resume Evidence Required for Role Gap Benchmark</h4>
                      <p className="text-xs text-secondary max-w-md mx-auto mb-4 leading-relaxed">
                        Role requirement benchmarks compare verified candidate evidence against industry standards.
                        Upload your resume to benchmark your personal skills against {activeRole.display_name}, or proceed to interview with generic questions.
                      </p>
                      <div className="flex justify-center gap-3">
                        <button
                          type="button"
                          className="btn btn-primary btn-xs"
                          onClick={() => navigate('/resume')}
                        >
                          Upload Resume to Benchmark Skills
                        </button>
                      </div>
                    </div>
                  ) : !isResumeProcessed ? (
                    <div className="empty-state-frame py-8 text-center" data-testid="role-resume-processing">
                      <RefreshCw size={20} className="animate-spin mx-auto mb-2 text-indigo" />
                      <h4 className="text-sm font-semibold text-primary mb-1">Resume Parsing in Progress</h4>
                      <p className="text-xs text-secondary max-w-md mx-auto mb-3 leading-relaxed">
                        Your resume has been uploaded and background evidence extraction is underway.
                        Competency benchmarking for {activeRole.display_name} will unlock automatically once processing completes.
                      </p>
                      <button
                        type="button"
                        className="btn btn-secondary btn-xs"
                        onClick={() => navigate('/resume')}
                      >
                        Check Parsing Status
                      </button>
                    </div>
                  ) : isLoadingGaps ? (
                    <div className="py-8 text-center text-xs text-muted">
                      <RefreshCw size={18} className="animate-spin mx-auto mb-2 text-indigo" />
                      Computing empirical role gap analysis from candidate skill state and resume memory...
                    </div>
                  ) : gapAnalysis ? (
                    <div className="flex flex-col gap-5">
                      {/* Summary metrics */}
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                        <div className="p-3 bg-surface-raised rounded-md border border-subtle">
                          <div className="text-2xs text-muted uppercase font-medium">Competencies Analyzed</div>
                          <div className="text-lg font-bold text-primary mt-1">
                            {gapAnalysis.total_competencies_evaluated}
                          </div>
                        </div>
                        <div className="p-3 bg-surface-raised rounded-md border border-subtle">
                          <div className="text-2xs text-emerald uppercase font-medium">Satisfied Skills</div>
                          <div className="text-lg font-bold text-emerald mt-1">
                            {gapAnalysis.satisfied_competencies}
                          </div>
                        </div>
                        <div className="p-3 bg-surface-raised rounded-md border border-subtle col-span-2 sm:col-span-1">
                          <div className="text-2xs text-amber uppercase font-medium">Identified Gaps</div>
                          <div className="text-lg font-bold text-amber mt-1">
                            {gapAnalysis.gaps_detected}
                          </div>
                        </div>
                      </div>

                      {/* Detailed Gaps */}
                      {gapAnalysis.gaps && gapAnalysis.gaps.length > 0 && (
                        <div>
                          <div className="text-xs font-semibold text-muted uppercase tracking-wider mb-2">
                            Priority Assessment Needs & Transfer Deficits
                          </div>
                          <div className="flex flex-col gap-2">
                            {gapAnalysis.gaps.map((gap, idx) => (
                              <div
                                key={idx}
                                className="p-3 bg-surface-raised rounded-md border border-subtle flex flex-col gap-1.5"
                              >
                                <div className="flex items-center justify-between gap-2">
                                  <span className="font-semibold text-xs text-primary">
                                    {gap.skill_name}
                                  </span>
                                  <span
                                    className={`badge ${
                                      gap.priority === 'CRITICAL' || gap.priority === 'HIGH'
                                        ? 'badge-danger'
                                        : gap.priority === 'MEDIUM'
                                        ? 'badge-warning'
                                        : 'badge-neutral'
                                    } text-2xs`}
                                  >
                                    Priority: {gap.priority}
                                  </span>
                                </div>
                                <p className="text-2xs text-secondary leading-relaxed">
                                  {gap.reasoning}
                                </p>
                                <div className="text-2xs text-muted flex items-center gap-3 mt-1">
                                  <span>Importance: {gap.role_importance}</span>
                                  <span>Transfer Level: {gap.highest_transfer_level}</span>
                                  <span>Mastery Gap: {(gap.effective_gap * 100).toFixed(0)}%</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-xs text-muted">
                      No preliminary gap data available. Launch the role interview to generate empirical baseline assessments.
                    </p>
                  )}
                </div>

                {/* Tested Competencies & Invariants */}
                <div className="surface-card p-6">
                  <div className="flex items-center gap-2 mb-4 pb-3 border-b border-subtle">
                    <Layers size={18} className="text-indigo" />
                    <h3 className="text-base font-bold text-primary">
                      Curated Competencies & Required System Invariants
                    </h3>
                  </div>

                  <div className="flex flex-col gap-4">
                    {activeRole.competencies.map((comp, idx) => (
                      <div
                        key={comp.identifier || idx}
                        className="p-4 bg-surface-raised rounded-lg border border-subtle flex flex-col gap-2"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-bold text-sm text-primary">{comp.name}</span>
                          <span className="badge badge-brand text-2xs">
                            {comp.importance || 'CORE'}
                          </span>
                        </div>

                        <p className="text-xs text-secondary leading-relaxed">
                          {comp.description}
                        </p>

                        {comp.core_invariants && comp.core_invariants.length > 0 && (
                          <div className="mt-2 bg-canvas p-3 rounded border border-subtle">
                            <div className="text-2xs font-semibold text-muted uppercase tracking-wider mb-1">
                              Core Invariants That Must Transfer:
                            </div>
                            <ul className="flex flex-col gap-1 text-xs text-secondary">
                              {comp.core_invariants.map((inv, invIdx) => (
                                <li key={invIdx} className="flex items-start gap-1.5">
                                  <Shield size={12} className="text-indigo shrink-0 mt-0.5" />
                                  <span>{inv}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
