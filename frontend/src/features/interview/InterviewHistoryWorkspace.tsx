import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  History,
  Video,
  ArrowRight,
  Plus,
  CheckCircle,
  PlayCircle,
  FileText,
} from 'lucide-react';
import { useAppSession } from '../../context/AppSessionContext';
import { api } from '../../services/api';
import { InterviewSession } from '../../types';

export const InterviewHistoryWorkspace: React.FC = () => {
  const navigate = useNavigate();
  const { selectedCandidate } = useAppSession();

  const [sessions, setSessions] = useState<InterviewSession[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedCandidate) {
      setSessions([]);
      return;
    }

    let isMounted = true;
    setIsLoading(true);
    setError(null);

    api
      .listCandidateInterviews(selectedCandidate.id)
      .then((data) => {
        if (!isMounted) return;
        const sorted = [...(data || [])].sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );
        setSessions(sorted);
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err.message || 'Failed to load candidate interview history');
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [selectedCandidate?.id]);

  if (!selectedCandidate) {
    return (
      <div className="page-container">
        <div className="empty-state-frame">
          <div className="empty-state-icon">
            <History size={24} />
          </div>
          <h2 className="empty-state-heading">No Candidate Profile Selected</h2>
          <p className="empty-state-copy">
            Select or register a candidate profile to inspect past assessment debriefs.
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

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header-row mb-6">
        <div>
          <h1 className="page-main-heading">Interview Session History</h1>
          <p className="page-subheading">
            Assessment audit logs and evaluation reports for candidate{' '}
            <strong>{selectedCandidate.full_name}</strong>.
          </p>
        </div>

        <button
          type="button"
          className="btn btn-primary btn-sm"
          onClick={() => navigate('/interview')}
        >
          <Plus size={15} />
          <span>New Interview</span>
        </button>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="surface-card p-12 text-center text-secondary">
          Loading interview sessions...
        </div>
      ) : error ? (
        <div className="surface-card p-6 text-danger">Error: {error}</div>
      ) : sessions.length === 0 ? (
        <div className="surface-card">
          <div className="empty-state-frame">
            <div className="empty-state-icon">
              <Video size={24} />
            </div>
            <h3 className="empty-state-heading">No Interview Sessions Found</h3>
            <p className="empty-state-copy">
              {selectedCandidate.full_name} has not completed any adaptive interviews yet.
            </p>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={() => navigate('/interview')}
            >
              <Video size={15} />
              <span>Launch First Interview Session</span>
            </button>
          </div>
        </div>
      ) : (
        <div className="surface-card">
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Target Role & Session</th>
                  <th>Type & Depth</th>
                  <th>Date</th>
                  <th>Turns</th>
                  <th>Status</th>
                  <th>Composite Score</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((sess) => {
                  const isCompleted = sess.status === 'COMPLETED';
                  const score = sess.report?.final_score;

                  return (
                    <tr key={sess.id}>
                      <td>
                        <div className="font-semibold text-primary">{sess.target_role}</div>
                        <div className="font-mono text-xs text-muted">{sess.id}</div>
                      </td>
                      <td>
                        <div className="flex gap-2">
                          <span className="badge badge-neutral">{sess.interview_type}</span>
                          <span className="badge badge-neutral">{sess.difficulty_level}</span>
                        </div>
                      </td>
                      <td>
                        <div className="text-xs text-muted">
                          {new Date(sess.created_at).toLocaleDateString(undefined, {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric',
                          })}
                        </div>
                      </td>
                      <td>
                        <div className="text-xs text-muted">
                          {sess.history?.length || 0} / {sess.target_question_count}
                        </div>
                      </td>
                      <td>
                        {isCompleted ? (
                          <span className="badge badge-success">
                            <CheckCircle size={12} />
                            <span>Completed</span>
                          </span>
                        ) : (
                          <span className="badge badge-warning">
                            <PlayCircle size={12} />
                            <span>{sess.status}</span>
                          </span>
                        )}
                      </td>
                      <td>
                        {score !== undefined ? (
                          <span className="font-bold text-indigo font-mono">
                            {Math.round(score)} / 100
                          </span>
                        ) : (
                          <span className="text-muted">&mdash;</span>
                        )}
                      </td>
                      <td>
                        {isCompleted ? (
                          <button
                            type="button"
                            className="btn btn-ghost btn-sm"
                            onClick={() => navigate(`/debrief/${sess.id}`)}
                          >
                            <FileText size={14} />
                            <span>Debrief</span>
                          </button>
                        ) : (
                          <button
                            type="button"
                            className="btn btn-primary btn-sm"
                            onClick={() => navigate(`/interview/${sess.id}`)}
                          >
                            <span>Resume</span>
                            <ArrowRight size={13} />
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
