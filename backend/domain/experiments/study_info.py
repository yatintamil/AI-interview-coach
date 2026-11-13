"""
Configurable Study Information and Participant Protocol Metadata.
Defines study purpose, procedures, foreseeable risks, data handling, and withdrawal terms.
Does NOT fabricate institutional IRB approval.
"""

from backend.domain.experiments.schemas import StudyInformationDTO

DEFAULT_STUDY_INFO = StudyInformationDTO(
    study_id="study_transfer_eval_v1",
    title="Transfer-Aware AI Interview Coaching Feasibility Study",
    principal_investigator="Senior Research Team (Supervised Feasibility Pilot)",
    purpose=(
        "To investigate whether targeted diagnostic AI coaching accelerates the transfer of software "
        "architecture principles to novel, structurally distinct technical interview challenges."
    ),
    procedures=(
        "You will complete 5 sequential phases: "
        "(1) A pretest baseline assessment, "
        "(2) An assigned technical training session, "
        "(3) A posttest assessment, "
        "(4) A far-transfer structural isomorph challenge, and "
        "(5) An autonomous independent transfer validation task (L5). "
        "Each phase presents architectural design questions evaluated using grounded technical rubrics."
    ),
    risks_and_benefits=(
        "Risks: Minimal cognitive fatigue comparable to completing a standard technical interview or practice problem. "
        "Benefits: You receive structured architectural feedback, diagnostic remediation, and technical practice."
    ),
    voluntary_participation=(
        "Participation is entirely voluntary. You may decline to participate or discontinue your participation "
        "at any time without penalty or loss of regular platform access."
    ),
    data_handling=(
        "All telemetry (candidate responses, scores, timestamps, and scaffold requests) will be recorded "
        "pseudonymously. Research exports use non-reversible cryptographic hashes (SHA-256) and contain zero direct identifiers "
        "(no names, emails, or IP addresses). Raw responses are stored in secured research tables."
    ),
    ethics_statement=(
        "Notice: This platform is currently deployed as an internal supervised technical feasibility pilot. "
        "Formal Institutional Review Board (IRB) ethics clearance must be obtained prior to conducting a "
        "definitive randomized controlled trial with external human cohorts."
    ),
    consent_version="v1.0-feasibility-study",
    withdrawal_policy=(
        "You may voluntarily withdraw at any point via the study interface. Upon withdrawal, ongoing sessions "
        "will be marked as abandoned and subsequent participation will be blocked. In accordance with study data policy, "
        "withdrawn participants are excluded by default from primary research evaluation datasets."
    ),
)
