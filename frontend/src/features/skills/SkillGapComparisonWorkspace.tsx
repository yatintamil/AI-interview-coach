import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Compass,
  Briefcase,
  AlertTriangle,
  CheckCircle2,
  ArrowRight,
  Play,
  Map,
  RefreshCw,
} from 'lucide-react';
import { useAppSession } from '../../context/AppSessionContext';
import { api } from '../../services/api';
import { SkillGapAnalysisResult } from '../../types/roadmap';

export const SkillGapComparisonWorkspace: React.FC = () => {
  const navigate = useNavigate();
  const { selectedCandidate, activeRoleId, setActiveRoleId } = useAppSession();

  const [targetRole, setTargetRole] = useState(
    activeRoleId || 'Distributed Systems Engineer'
  );
  const [availableRoles, setAvailableRoles] = useState<Array<{ key: string; display_name: string }>>([]);
  const [seniority, setSeniority] = useState('Mid');
  const [analysisResult, setAnalysisResult] = useState<SkillGapAnalysisResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isGeneratingRoadmap, setIsGeneratingRoadmap] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (typeof api.listTargetRoles === 'function') {
      api
        .listTargetRoles()
        .then((data) => {
          if (data && data.length > 0) {
            setAvailableRoles(data.map((d) => ({ key: d.key, display_name: d.display_name })));
          }
        })
        .catch(() => {});
    }
  }, []);

  const hasResume = Boolean(
    selectedCandidate && selectedCandidate.resumes && selectedCandidate.resumes.length > 0
  );
  const isResumeProcessed = Boolean(
    hasResume && selectedCandidate?.resumes?.some((r) => r.processing_status === 'COMPLETED')
  );

  const fetchGaps = async () => {
    if (!selectedCandidate || !hasResume || !isResumeProcessed) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.getSkillGaps(selectedCandidate.id, targetRole, seniority);
      setAnalysisResult(res);
      if (targetRole !== activeRoleId) {
        setActiveRoleId(targetRole);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to calculate role-specific skill gaps');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (selectedCandidate && hasResume && isResumeProcessed) {
      fetchGaps();
    }
  }, [selectedCandidate?.id, targetRole, seniority, hasResume, isResumeProcessed]);

  const handleGenerateRoadmap = async () => {
    if (!selectedCandidate) return;
    setIsGeneratingRoadmap(true);
    try {
      await api.generateRoadmap(selectedCandidate.id, targetRole, seniority);
      navigate('/roadmap');
    } catch (err: any) {
      alert(`Roadmap generation failed: ${err.message}`);
    } finally {
      setIsGeneratingRoadmap(false);
    }
  };

  if (!selectedCandidate) {
    return (
      <div className="page-container">
        <div className="empty-state-frame">
          <div className="empty-state-icon">
            <Compass size={24} />
          </div>
          <h2 className="empty-state-heading">Select a Candidate Profile</h2>
          <p className="empty-state-copy">
            Choose an active candidate to analyze competency requirements and transfer gaps.
          </p>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => navigate('/profile')}
          >
            Go to Candidate Profiles
          </button>
        </div>
      </div>
    );
  }

  if (!hasResume) {
    return (
      <div className="page-container" data-testid="skill-gaps-no-resume">
        <div className="empty-state-frame text-center py-12 max-w-2xl mx-auto">
          <div className="empty-state-icon mx-auto mb-4">
            <Compass size={28} className="text-indigo" />
          </div>
          <h2 className="empty-state-heading text-lg font-bold text-primary mb-2">Resume Evidence Required for Gap Analysis</h2>
          <p className="empty-state-copy text-sm text-secondary mb-6 leading-relaxed">
            Role gap analysis requires verified candidate evidence to benchmark personal competencies against target industry requirements.
            Upload your resume to calculate personalized gaps, or explore the standard role catalog.
          </p>
          <div className="flex justify-center gap-3">
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={() => navigate('/resume')}
            >
              Upload Resume to Enable Gap Analysis
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => navigate('/roles')}
            >
              Browse Role Requirements (Generic)
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!isResumeProcessed) {
    return (
      <div className="page-container" data-testid="skill-gaps-processing">
        <div className="empty-state-frame text-center py-12 max-w-2xl mx-auto">
          <RefreshCw size={28} className="animate-spin mx-auto mb-4 text-indigo" />
          <h2 className="empty-state-heading text-lg font-bold text-primary mb-2">Resume Parsing in Progress</h2>
          <p className="empty-state-copy text-sm text-secondary mb-6 leading-relaxed">
            Your resume has been submitted and is currently being parsed. Skill gap calculation will unlock once evidence extraction completes.
          </p>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => navigate('/resume')}
          >
            Check Parsing Status
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header-row mb-6">
        <div>
          <h1 className="page-main-heading">Role-Specific Skill Gap Analysis</h1>
          <p className="page-subheading">
            Competency comparison matrix comparing candidate empirical mastery against target
            engineering role requirements.
          </p>
        </div>

        <div className="flex gap-3">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={fetchGaps}
            disabled={isLoading}
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
            <span>Re-analyze</span>
          </button>

          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={handleGenerateRoadmap}
            disabled={isGeneratingRoadmap}
          >
            <Map size={14} />
            <span>{isGeneratingRoadmap ? 'Generating...' : 'Generate Roadmap'}</span>
          </button>
        </div>
      </div>

      {/* Role & Seniority Selector Bar */}
      <div className="surface-card p-4 mb-6">
        <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
          <div className="flex items-center gap-3 w-full md:w-auto flex-1">
            <Briefcase size={16} className="text-muted shrink-0" />
            <select
              className="select-control flex-1"
              value={targetRole}
              onChange={(e) => setTargetRole(e.target.value)}
            >
              {availableRoles.length > 0 ? (
                availableRoles.map((r) => (
                  <option key={r.key} value={r.display_name}>
                    {r.display_name}
                  </option>
                ))
              ) : (
                <>
                  <option value="Distributed Systems Engineer">Distributed Systems Engineer</option>
                  <option value="Distributed Database Reliability Engineer">Distributed Database Reliability Engineer</option>
                  <option value="Embedding Systems Engineer">Embedding Systems Engineer</option>
                  <option value="Machine Learning Engineer">Machine Learning Engineer</option>
                  <option value="Backend Systems Engineer">Backend Systems Engineer</option>
                  <option value="Cloud DevOps / SRE">Cloud DevOps / SRE</option>
                  <option value="Universal Software Engineering">Universal Software Engineering</option>
                </>
              )}
            </select>
          </div>

          <div className="flex items-center gap-3 w-full md:w-auto">
            <span className="text-xs text-muted font-semibold uppercase">Seniority:</span>
            <select
              className="select-control w-32"
              value={seniority}
              onChange={(e) => setSeniority(e.target.value)}
            >
              <option value="Junior">Junior</option>
              <option value="Mid">Mid</option>
              <option value="Senior">Senior</option>
              <option value="Staff">Staff</option>
            </select>
          </div>
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="surface-card p-12 text-center text-secondary">
          Calculating competency gap matrices and transfer deficits...
        </div>
      ) : error ? (
        <div className="surface-card p-6 text-danger">Error: {error}</div>
      ) : analysisResult ? (
        <>
          {/* Summary Stat Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-6">
            <div className="surface-card p-4">
              <div className="text-xs text-muted uppercase font-bold">Evaluated Competencies</div>
              <div className="text-2xl font-bold text-primary mt-1">
                {analysisResult.total_competencies_evaluated}
              </div>
              <div className="text-xs text-tertiary mt-1">Mapped for {analysisResult.target_role}</div>
            </div>

            <div className="surface-card p-4">
              <div className="text-xs text-muted uppercase font-bold">Satisfied Competencies</div>
              <div className="text-2xl font-bold text-emerald mt-1">
                {analysisResult.satisfied_competencies}
              </div>
              <div className="text-xs text-tertiary mt-1">Met required mastery baseline</div>
            </div>

            <div className="surface-card p-4">
              <div className="text-xs text-muted uppercase font-bold">Deficits Detected</div>
              <div className="text-2xl font-bold text-amber mt-1">
                {analysisResult.gaps_detected}
              </div>
              <div className="text-xs text-tertiary mt-1">Require targeted transfer interventions</div>
            </div>
          </div>

          {/* Competency Comparison Matrix */}
          <div className="surface-card">
            <div className="surface-header">
              <div className="surface-header-title">
                <AlertTriangle size={16} className="text-amber" />
                <h2>Competency-Oriented Comparison Matrix</h2>
              </div>
            </div>

            <div className="surface-body flex flex-col gap-3">
              {analysisResult.gaps.length === 0 ? (
                <div className="empty-state-frame">
                  <div className="empty-state-icon">
                    <CheckCircle2 size={24} className="text-emerald" />
                  </div>
                  <div className="empty-state-heading">No Competency Deficits Detected</div>
                  <div className="empty-state-copy">
                    Candidate satisfies all benchmark requirements for {analysisResult.target_role} at {seniority} level.
                  </div>
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={() => navigate('/transfer')}
                  >
                    <Play size={14} />
                    <span>Challenge with L5 Independent Transfer</span>
                  </button>
                </div>
              ) : (
                <div className="competency-comparison-matrix">
                  {analysisResult.gaps.map((gap, idx) => (
                    <div key={idx} className="comparison-row">
                      {/* Competency title & reasoning */}
                      <div>
                        <div className="font-semibold text-sm text-primary">
                          {gap.skill_name || gap.skill_id}
                        </div>
                        {gap.reasoning && (
                          <div className="text-xs text-muted mt-1 leading-relaxed">
                            {gap.reasoning}
                          </div>
                        )}
                      </div>

                      {/* Mastery meter comparison */}
                      <div>
                        <div className="flex justify-between items-center text-xs mb-1">
                          <span className="text-muted">Mastery vs Req</span>
                          <span className="font-mono text-secondary">
                            {Math.round(gap.candidate_mastery * 100)}% / {Math.round(gap.required_mastery * 100)}%
                          </span>
                        </div>
                        <div className="meter-track">
                          <div
                            className="meter-fill warning"
                            style={{ width: `${Math.round(gap.candidate_mastery * 100)}%` }}
                          />
                        </div>
                      </div>

                      {/* Transfer Level & Deficit */}
                      <div>
                        <div className="badge badge-warning">
                          Deficit: {Math.round((gap.effective_gap || gap.raw_gap || 0) * 100)}%
                        </div>
                        <div className="text-xs text-muted mt-1">
                          Level: <span className="text-indigo font-medium">{gap.highest_transfer_level}</span>
                        </div>
                      </div>

                      {/* Action */}
                      <div className="text-right flex items-center justify-end gap-2">
                        <button
                          type="button"
                          className="btn btn-primary btn-sm"
                          onClick={() => navigate(`/coaching?skillId=${encodeURIComponent(gap.skill_id)}`)}
                        >
                          <Play size={13} />
                          <span>Practice</span>
                        </button>
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          onClick={() => navigate('/roadmap')}
                        >
                          <span>Roadmap</span>
                          <ArrowRight size={13} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
};
