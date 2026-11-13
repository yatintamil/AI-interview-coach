"""
Deterministic application-level task set provider.
Implements the TaskSetProvider domain protocol for sysdesign_distributed_cache_v1.
Provides identical, reproducible task pools to all three experimental conditions.
"""

import random
from typing import Dict, Any, List, Optional
from backend.domain.experiments.enums import ExperimentPhase, TaskDifficulty
from backend.domain.experiments.ports import TaskSetProvider


TASK_DATABASE: Dict[str, Dict[str, Any]] = {
    "sysdesign_distributed_cache_v1": {
        "skill": "distributed_caching",
        "pretest": [
            {
                "task_id": "task_pretest_01",
                "phase": ExperimentPhase.PRETEST,
                "difficulty": TaskDifficulty.MEDIUM,
                "prompt": (
                    "Explain the operational architecture of an in-memory key-value cache. "
                    "How does consistent hashing distribute keys across nodes, and how are cache misses handled?"
                ),
                "expected_concepts": ["consistent hashing", "cache miss", "virtual nodes", "in-memory storage"],
                "topic": "In-Memory Caching Fundamentals",
                "transfer_level": "L0_RECALL",
                "transfer_distance": 0.0,
                "form_id": "FORM_A",
            }
        ],
        "training": {
            TaskDifficulty.EASY: [
                {
                    "task_id": "task_train_easy_01",
                    "phase": ExperimentPhase.TRAINING,
                    "difficulty": TaskDifficulty.EASY,
                    "prompt": (
                        "Design a single-node LRU cache. Describe the data structures used to achieve O(1) "
                        "get and put operations, and explain how eviction occurs under memory pressure."
                    ),
                    "expected_concepts": ["doubly linked list", "hash map", "O(1) lookup", "eviction policy"],
                    "topic": "LRU Eviction Fundamentals",
                    "transfer_level": "L1_SURFACE_VARIATION",
                    "transfer_distance": 0.10,
                    "form_id": "FORM_TR_EASY",
                }
            ],
            TaskDifficulty.MEDIUM: [
                {
                    "task_id": "task_train_med_01",
                    "phase": ExperimentPhase.TRAINING,
                    "difficulty": TaskDifficulty.MEDIUM,
                    "prompt": (
                        "Design a distributed Redis-like in-memory caching cluster. Explain hash slots, "
                        "master-replica replication, failover handling, and write-through vs write-back caching."
                    ),
                    "expected_concepts": ["hash slots", "replication", "write-through", "failover", "consistency"],
                    "topic": "Distributed Cache Cluster Architecture",
                    "transfer_level": "L1_SURFACE_VARIATION",
                    "transfer_distance": 0.15,
                    "form_id": "FORM_TR_MED",
                }
            ],
            TaskDifficulty.HARD: [
                {
                    "task_id": "task_train_hard_01",
                    "phase": ExperimentPhase.TRAINING,
                    "difficulty": TaskDifficulty.HARD,
                    "prompt": (
                        "Design a globally distributed multi-region cache with active-active replication. "
                        "Address cross-region latency, conflict resolution, stampede prevention (single-flight locking), "
                        "and high-throughput write buffering."
                    ),
                    "expected_concepts": ["active-active replication", "conflict resolution", "cache stampede", "single-flight"],
                    "topic": "Multi-Region Distributed Cache",
                    "transfer_level": "L1_SURFACE_VARIATION",
                    "transfer_distance": 0.25,
                    "form_id": "FORM_TR_HARD",
                }
            ],
        },
        "posttest": [
            {
                "task_id": "task_posttest_01",
                "phase": ExperimentPhase.POSTTEST,
                "difficulty": TaskDifficulty.MEDIUM,
                "prompt": (
                    "Design a distributed caching layer for an e-commerce catalog with flash sales. "
                    "Address hot-key invalidation, cache avalanche mitigation, and consistent hashing failover under traffic spikes."
                ),
                "expected_concepts": ["hot-key invalidation", "cache avalanche", "consistent hashing", "jittered TTL"],
                "topic": "High-Traffic Distributed Cache",
                "transfer_level": "L1_SURFACE_VARIATION",
                "transfer_distance": 0.20,
                "form_id": "FORM_B",
            }
        ],
        "transfer_test": [
            {
                "task_id": "task_transfer_l2_01",
                "phase": ExperimentPhase.TRANSFER_TEST,
                "difficulty": TaskDifficulty.MEDIUM,
                "prompt": (
                    "Design a distributed media streaming video chunk store. The store must cache 2MB byte-range "
                    "video segments, route playback requests across edge nodes using hash rings, and manage chunk "
                    "eviction under multi-gigabit throughput."
                ),
                "expected_concepts": ["Chunked LRU", "hash slot ring", "concurrent streaming buffer", "byte-range caching"],
                "topic": "Distributed Media Video Chunk Store",
                "transfer_level": "L2_STRUCTURAL_ISOMORPH",
                "transfer_distance": 0.45,
                "form_id": "FORM_T1",
            }
        ],
        "targeted_retraining": [
            {
                "task_id": "task_retrain_01",
                "phase": ExperimentPhase.TARGETED_RETRAINING,
                "difficulty": TaskDifficulty.MEDIUM,
                "prompt": (
                    "Address non-functional requirements for video chunk storage: evaluate chunk eviction algorithms, "
                    "segmented buffer locking, and throughput constraints when caching large multi-megabyte payloads "
                    "compared to small key-value strings."
                ),
                "expected_concepts": ["chunk eviction", "segmented ring routing", "buffer locking", "throughput optimization"],
                "topic": "Retraining: Large Chunk Buffering Tradeoffs",
                "transfer_level": "L2_STRUCTURAL_ISOMORPH",
                "transfer_distance": 0.45,
                "form_id": "FORM_R1",
            }
        ],
        "independent_transfer": [
            {
                "task_id": "task_independent_l5_01",
                "phase": ExperimentPhase.INDEPENDENT_TRANSFER,
                "difficulty": TaskDifficulty.HARD,
                "prompt": (
                    "Architect a real-time IoT high-frequency time-series sensor ingestion engine. "
                    "System must buffer incoming telemetry packets across partitioned ring buffers, downsample aged data points, "
                    "and guarantee sub-second query latency under backpressure."
                ),
                "expected_concepts": ["ring buffer", "telemetry partition", "downsampling", "backpressure handling", "time-series storage"],
                "topic": "IoT Sensor Stream Ingestion Engine",
                "transfer_level": "L5_COMPLEX_DISTANT",
                "transfer_distance": 0.85,
                "form_id": "FORM_L5",
            }
        ],
    }
}


class ApplicationTaskSetProvider(TaskSetProvider):
    """
    Deterministic Task Set Provider implementing domain TaskSetProvider protocol.
    Guarantees reproducible task selection across all experimental runs with identical seeds.
    """

    def list_available_task_sets(self) -> List[str]:
        return list(TASK_DATABASE.keys())

    def get_task(
        self,
        task_set_id: str,
        phase: ExperimentPhase,
        difficulty: Optional[TaskDifficulty] = None,
        seed: int = 42,
        form_order: Optional[str] = "FORM_AB",
    ) -> Dict[str, Any]:
        """
        Retrieves a task definition deterministically based on phase, difficulty tier, seed,
        and Form A/B crossover order ('FORM_AB' vs 'FORM_BA').
        """
        if task_set_id not in TASK_DATABASE:
            raise ValueError(f"Unknown task_set_id '{task_set_id}'. Available: {list(TASK_DATABASE.keys())}")

        task_set = TASK_DATABASE[task_set_id]
        rng = random.Random(seed)

        if phase == ExperimentPhase.PRETEST:
            if form_order == "FORM_BA":
                tasks = task_set["posttest"]
            else:
                tasks = task_set["pretest"]
        elif phase == ExperimentPhase.TRAINING:
            diff = difficulty or TaskDifficulty.MEDIUM
            tasks = task_set["training"].get(diff, task_set["training"][TaskDifficulty.MEDIUM])
        elif phase == ExperimentPhase.POSTTEST:
            if form_order == "FORM_BA":
                tasks = task_set["pretest"]
            else:
                tasks = task_set["posttest"]
        elif phase == ExperimentPhase.TRANSFER_TEST:
            tasks = task_set["transfer_test"]
        elif phase == ExperimentPhase.TARGETED_RETRAINING:
            tasks = task_set["targeted_retraining"]
        elif phase == ExperimentPhase.INDEPENDENT_TRANSFER:
            tasks = task_set["independent_transfer"]
        else:
            raise ValueError(f"No tasks defined for phase: {phase}")

        if not tasks:
            raise ValueError(f"Task pool empty for phase '{phase}' in task set '{task_set_id}'.")

        # Deterministic pick using seeded RNG
        idx = rng.randint(0, len(tasks) - 1)
        selected = dict(tasks[idx])
        selected["phase"] = phase
        return selected
