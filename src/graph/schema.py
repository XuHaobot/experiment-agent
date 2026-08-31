# =============================================================================
# V1 原有实体类型（向后兼容保留）
# =============================================================================
ENTITY_EXPERIMENT = "Experiment"
ENTITY_DATASET = "Dataset"
ENTITY_MODEL = "Model"
ENTITY_COMMAND = "Command"
ENTITY_PARAMETER = "Parameter"
ENTITY_ERROR = "Error"
ENTITY_SOLUTION = "Solution"
ENTITY_CONCLUSION = "Conclusion"
ENTITY_NEXT_STEP = "NextStep"

# =============================================================================
# V2 新增实体类型 — Research Graph 科研生命周期
# =============================================================================
ENTITY_RESEARCH_PROJECT = "ResearchProject"
ENTITY_RESEARCH_QUESTION = "ResearchQuestion"
ENTITY_HYPOTHESIS = "Hypothesis"
ENTITY_EXPERIMENT_RUN = "ExperimentRun"
ENTITY_OBSERVATION = "Observation"
ENTITY_ANALYSIS = "Analysis"
ENTITY_EVIDENCE = "Evidence"
ENTITY_PAPER = "Paper"
ENTITY_AUTHOR = "Author"
ENTITY_METHOD = "Method"
ENTITY_METRIC = "Metric"
ENTITY_ARTIFACT = "Artifact"

# =============================================================================
# V1 原有关系类型（向后兼容保留）
# =============================================================================
REL_USES_DATASET = "USES_DATASET"
REL_USES_MODEL = "USES_MODEL"
REL_RUNS_COMMAND = "RUNS_COMMAND"
REL_HAS_ORIGINAL_PARAMETER = "HAS_ORIGINAL_PARAMETER"
REL_HAS_ADJUSTED_PARAMETER = "HAS_ADJUSTED_PARAMETER"
REL_HAS_SUGGESTED_PARAMETER = "HAS_SUGGESTED_PARAMETER"
REL_HAS_ERROR = "HAS_ERROR"
REL_SOLVED_BY = "SOLVED_BY"
REL_ADJUSTS_PARAMETER = "ADJUSTS_PARAMETER"
REL_PRODUCES_CONCLUSION = "PRODUCES_CONCLUSION"
REL_SUGGESTS_NEXT_STEP = "SUGGESTS_NEXT_STEP"

# =============================================================================
# V2 新增关系类型 — Research Graph 科研生命周期
# =============================================================================
REL_HAS_QUESTION = "HAS_QUESTION"          # Project → ResearchQuestion
REL_HAS_HYPOTHESIS = "HAS_HYPOTHESIS"      # ResearchQuestion → Hypothesis
REL_TESTED_BY = "TESTED_BY"                # Hypothesis → Experiment
REL_HAS_RUN = "HAS_RUN"                    # Experiment → ExperimentRun
REL_PRODUCES = "PRODUCES"                  # ExperimentRun → Observation/Artifact
REL_ANALYZED_BY = "ANALYZED_BY"            # Observation → Analysis
REL_SUPPORTS = "SUPPORTS"                  # Evidence → Hypothesis
REL_REFUTES = "REFUTES"                    # Evidence → Hypothesis
REL_REFERENCES = "REFERENCES"              # Experiment → Paper
REL_BELONGS_TO = "BELONGS_TO"              # Experiment → ResearchProject
REL_GENERATES = "GENERATES"               # NextStep → Experiment
REL_AUTHORED_BY = "AUTHORED_BY"            # Paper → Author
REL_USES_METHOD = "USES_METHOD"            # Experiment → Method
REL_HAS_METRIC = "HAS_METRIC"              # Analysis → Metric


# =============================================================================
# 聚合列表（保持向后兼容，新增类型追加到末尾）
# =============================================================================
ENTITY_TYPES = [
    # V1
    ENTITY_EXPERIMENT,
    ENTITY_DATASET,
    ENTITY_MODEL,
    ENTITY_COMMAND,
    ENTITY_PARAMETER,
    ENTITY_ERROR,
    ENTITY_SOLUTION,
    ENTITY_CONCLUSION,
    ENTITY_NEXT_STEP,
    # V2
    ENTITY_RESEARCH_PROJECT,
    ENTITY_RESEARCH_QUESTION,
    ENTITY_HYPOTHESIS,
    ENTITY_EXPERIMENT_RUN,
    ENTITY_OBSERVATION,
    ENTITY_ANALYSIS,
    ENTITY_EVIDENCE,
    ENTITY_PAPER,
    ENTITY_AUTHOR,
    ENTITY_METHOD,
    ENTITY_METRIC,
    ENTITY_ARTIFACT,
]

RELATION_TYPES = [
    # V1
    REL_USES_DATASET,
    REL_USES_MODEL,
    REL_RUNS_COMMAND,
    REL_HAS_ORIGINAL_PARAMETER,
    REL_HAS_ADJUSTED_PARAMETER,
    REL_HAS_SUGGESTED_PARAMETER,
    REL_HAS_ERROR,
    REL_SOLVED_BY,
    REL_ADJUSTS_PARAMETER,
    REL_PRODUCES_CONCLUSION,
    REL_SUGGESTS_NEXT_STEP,
    # V2
    REL_HAS_QUESTION,
    REL_HAS_HYPOTHESIS,
    REL_TESTED_BY,
    REL_HAS_RUN,
    REL_PRODUCES,
    REL_ANALYZED_BY,
    REL_SUPPORTS,
    REL_REFUTES,
    REL_REFERENCES,
    REL_BELONGS_TO,
    REL_GENERATES,
    REL_AUTHORED_BY,
    REL_USES_METHOD,
    REL_HAS_METRIC,
]
