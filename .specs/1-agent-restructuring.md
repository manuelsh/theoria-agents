# Specification 1: Restructure theoria-agents into Specialized Sub-Agents

## 1. Executive Summary

**1.1 Objective**: Split the monolithic ResearcherAgent into 4 specialized sub-agents, creating a clearer 8-agent pipeline with single-responsibility principle and strict guideline adherence.

**1.2 Current Problem**: ResearcherAgent handles too many responsibilities (research, assumption selection, dependency identification, and metadata filling), making it difficult to ensure strict CONTRIBUTING.md compliance.

**1.3 Solution**: Replace 1 agent with 4 focused agents:
- InformationGathererAgent (fast) - Pure information gathering
- MetadataFillerAgent (fast) - Metadata fields only
- AssumptionsDependenciesAgent (best) - Consult dataset, select/propose assumptions, identify dependencies
- EquationsSymbolsAgent (best) - Define equations and symbols with correct AsciiMath

**1.4 Impact**: Better quality control, clearer debugging, explicit dependency checking, and ability to flag missing foundational entries.

---

## 2. Context

**2.1 Current Issues**

The current theoria-agents pipeline has a single ResearcherAgent doing too many things at once:
1. Finding and curating information from Wikipedia
2. Loading existing assumptions and entries
3. Selecting applicable assumptions
4. Identifying dependencies
5. Proposing new assumptions
6. Partially filling in entry fields (result_id, result_name, domain, etc.)

This violates the single-responsibility principle and makes it difficult to ensure strict adherence to CONTRIBUTING.md guidelines.

**2.2 Quality Issues** (documented in guide.md):
- ResearcherAgent mixes research with data assembly
- Unclear if CONTRIBUTING.md guidelines are being followed strictly at each step
- No explicit check for existing entries when filling dependencies
- Logical independence problems in assumptions
- Shallow derivations
- AsciiMath notation errors
- Incomplete verification code

---

## 3. Analysis of Current Architecture

**3.1 Existing Pipeline (5 agents)**

1. **ResearcherAgent** - Gathers context AND fills metadata (too many responsibilities)
2. **DerivationAgent** - Creates mathematical derivations
3. **VerifierAgent** - Generates and executes SymPy code
4. **AssemblerAgent** - Combines outputs into TheoriaEntry
5. **ReviewerAgent** - Quality checking with 3 iteration self-correction

**3.2 Key Files**

- `src/agents/researcher.py` - Current ResearcherAgent implementation
- `src/agents/base.py` - BaseAgent class all agents inherit from
- `src/orchestrator.py` - PipelineOrchestrator that sequences agents
- `src/models.py` - Pydantic data models
- `theoria-dataset/CONTRIBUTING.md` - Guidelines (auto-generated from schema)
- `theoria-dataset/schemas/entry.schema.json` - Source of truth

---

## 4. Proposed Restructuring

### 4.1 Phase 1: Break ResearcherAgent into Specialized Sub-Agents

Replace the single ResearcherAgent with 4 focused sub-agents:

#### 4.1.1 InformationGathererAgent

**Responsibility:** Find, curate, and summarize information needed for the entry

**Tasks:**
- Perform Wikipedia searches via web API
- Extract relevant physics context
- Gather historical development information
- Find authoritative references (APA citations)
- Compile web context summary

**Output:** `InformationGatheringOutput`
- `web_context`: Curated summary of physics concept
- `historical_context`: Development period, key insights, importance
- `suggested_references`: List of potential APA citations

**Guidelines to Follow:**
- Focus on factual, graduate-level physics content
- Prioritize authoritative sources
- Truncate content appropriately (10k chars max)

**Model:** `fast`

#### 4.1.2 MetadataFillerAgent

**Responsibility:** Fill all entry metadata fields (except derivation) following CONTRIBUTING.md strictly

**Tasks:**
- Generate appropriate `result_id` (lowercase, underscores, descriptive)
- Create concise `result_name` (max 100 chars)
- Write `explanation` (2-5 sentences, max 800 chars, conceptual focus)
- Select appropriate `domain` (arXiv category)
- Determine `theory_status` (current/historical/approximation/limiting_case/generalized)
- Format `references` (1-3 APA citations)
- Add `contributor` information
- Set `review_status` to "draft"
- Add `historical_context` if relevant

**Input:** `InformationGatheringOutput` + user hints

**Output:** `MetadataOutput`
- All metadata fields properly filled
- Follows character limits and format requirements

**Guidelines to Follow:**
- CONTRIBUTING.md requirements for each field
- AsciiMath format for any math in explanation (enclosed in backticks)
- Appropriate arXiv taxonomy
- No derivation steps in explanation

**Model:** `fast`

#### 4.1.3 AssumptionsDependenciesAgent

**Responsibility:** Identify assumptions and dependencies by consulting existing dataset

**Tasks:**
- Load and review `globals/assumptions.json`
- Select applicable existing assumptions (avoiding duplication)
- Check for logical independence of assumptions
- Search existing entries for dependencies
- Identify if any dependencies are missing (need to be built first)
- Propose new assumptions if genuinely needed

**Input:** `InformationGatheringOutput` + `MetadataOutput`

**Output:** `AssumptionsDependenciesOutput`
- `assumptions`: Array of assumption IDs from globals/assumptions.json
- `new_assumptions`: Array of ProposedAssumption objects
- `depends_on`: Array of existing entry IDs
- `missing_dependencies`: Array of entries that need to be built first (with suggested IDs)

**Guidelines to Follow:**
- Check ALL existing assumptions before proposing new ones
- Ensure logical independence (no consequences as assumptions)
- Validate that depends_on entries actually exist
- Flag missing foundational entries explicitly
- Follow assumptions.json schema for new proposals

**Model:** `best` (critical decision-making)

#### 4.1.4 EquationsSymbolsAgent

**Responsibility:** Define result equations and symbols

**Tasks:**
- Identify the main result equations
- Write equations in AsciiMath format
- Generate equation IDs (eq1, eq2, etc.)
- Define ALL symbols used in equations
- Ensure AsciiMath notation correctness

**Input:** `InformationGatheringOutput` + `MetadataOutput` + `AssumptionsDependenciesOutput`

**Output:** `EquationsSymbolsOutput`
- `result_equations`: Array with id, equation, equation_title (optional initially)
- `definitions`: Array with symbol and definition for EVERY symbol

**Guidelines to Follow:**
- Proper AsciiMath notation (parentheses in fractions, derivatives, subscripts)
- No "to" in subscripts (renders as arrow)
- Multi-character subscripts need parentheses
- Math in definitions uses backticks + AsciiMath
- Self-contained (define every symbol)

**Model:** `best` (critical for correctness)

---

### 4.2 Phase 2: Keep Existing Specialized Agents (with Enhancements)

#### 4.2.1 DerivationAgent (EXISTING - enhance with stricter guidelines)

**Responsibility:** Generate step-by-step mathematical derivations following CONTRIBUTING.md

**Enhancements:**
- More explicit about starting from assumptions or depends_on
- Add `assumptions` field to individual steps
- More detailed steps (no skipping algebra)
- Use `equation_proven` to link to result equations
- Ensure AsciiMath correctness

**Input:** All outputs from Phase 1 agents

**Output:** `DerivationOutput` (same as current)

**Model:** `best`

#### 4.2.2 VerifierAgent (EXISTING - enhance verification depth)

**Responsibility:** Generate and execute SymPy verification code

**Enhancements:**
- Comment EVERY step with "# Step N"
- Add assertions for each major claim
- Verify intermediate steps, not just final equations
- Include sanity checks
- Print confirmation when all tests pass

**Input:** `DerivationOutput`

**Output:** `VerifierOutput` (same as current)

**Model:** `best`

#### 4.2.3 AssemblerAgent (UPDATE - new input structure)

**Responsibility:** Combine all outputs into complete TheoriaEntry

**Changes:**
- Accept outputs from all 4 new sub-agents + derivation + verification
- Pure data assembly (no LLM needed)

**Input:** All agent outputs (7 total)

**Output:** `TheoriaEntry`

**Model:** `fast` (no LLM actually used)

#### 4.2.4 ReviewerAgent (EXISTING - enhance with guide.md checklist)

**Responsibility:** Quality checking with self-correction (3 iterations)

**Enhancements:**
- Incorporate quality checklist from guide.md
- Special focus on logical independence of assumptions
- AsciiMath notation validation
- Derivation completeness check
- Verification depth check
- **NEW**: Validate proposed new assumptions

**Input:** `TheoriaEntry` + `new_assumptions` (if any)

**Output:** `ReviewResult` (same as current)

**Model:** `best`

---

## 5. Revised Pipeline Architecture

### 5.1 New Sequence (8 agents total)

```
Topic + Hints
    ↓
[1] InformationGathererAgent (fast)
    ↓
[2] MetadataFillerAgent (fast)
    ↓
[3] AssumptionsDependenciesAgent (best)
    ↓
    → IF missing_dependencies detected:
       STOP → Prompt user → Continue based on choice
    ↓
[4] EquationsSymbolsAgent (best)
    ↓
[5] DerivationAgent (best, enhanced)
    ↓
[6] VerifierAgent (best, enhanced)
    ↓
[7] AssemblerAgent (fast, updated)
    ↓
[8] ReviewerAgent (best, enhanced + new assumption validation)
    ↓
Final Entry + Proposed Assumptions (if any)
```

### 5.2 Benefits of This Structure

1. **Single Responsibility**: Each agent has one clear job
2. **Strict Guideline Adherence**: Each agent focuses on specific CONTRIBUTING.md sections
3. **Better Validation**: Can check assumptions/dependencies against existing dataset explicitly
4. **Clearer Debugging**: Know exactly which agent is responsible for each field
5. **Reusability**: Sub-agents can be reused for different workflows
6. **Explicit Dependencies**: AssumptionsDependenciesAgent can flag missing entries early
7. **Quality Focus**: Each agent can be prompted with specific quality requirements

---

## 6. User Decisions

### 6.1 Model Assignment - MIXED APPROACH

- **InformationGathererAgent**: `fast` model
- **MetadataFillerAgent**: `fast` model
- **AssumptionsDependenciesAgent**: `best` model (critical decision-making)
- **EquationsSymbolsAgent**: `best` model (critical for correctness)
- **DerivationAgent**: `best` model (existing)
- **VerifierAgent**: `best` model (existing)
- **AssemblerAgent**: `fast` model (existing, no LLM actually used)
- **ReviewerAgent**: `best` model (existing)

**Rationale**: Balance cost and quality - use fast for research/metadata, best for critical decisions about assumptions, equations, derivations, and review.

### 6.2 Missing Dependencies - STOP AND GET USER INPUT

When AssumptionsDependenciesAgent identifies missing foundational entries:
- **Stop the pipeline immediately**
- **Prompt user with options**:
  - Option A: Stop completely and generate missing entries first
  - Option B: Continue using mock IDs (to be built later)
- **User chooses** how to proceed

**Implementation**: Add interactive prompt in orchestrator when `missing_dependencies` is non-empty.

### 6.3 New Assumptions - SAVE SEPARATELY + REVIEW

When new assumptions are proposed:
- **Add to a separate file** (e.g., `proposed_assumptions.json` or similar)
- **Include in ReviewerAgent's review process**
  - ReviewerAgent validates new assumptions for:
    - Logical independence
    - No duplication with existing assumptions
    - Proper schema compliance
    - Clear, specific text
- **Final save**: If entry passes review, save both entry and new assumptions

**Implementation**:
- New assumptions stored in `AssumptionsDependenciesOutput.new_assumptions`
- ReviewerAgent gets special instructions to validate new assumptions
- Orchestrator saves new assumptions separately only after review passes

### 6.4 Pipeline Execution - SEQUENTIAL

All agents run **sequentially** for quality control and clear data flow. No parallelization needed at this level (individual agents can still parallelize internally if needed).

### 6.5 Backwards Compatibility - FULL REPLACEMENT

Remove ResearcherAgent completely. Clean break with better architecture.

---

## 7. Critical Files to Modify

### 7.1 New Files to Create

1. `src/agents/information_gatherer.py` - New agent
2. `src/agents/metadata_filler.py` - New agent
3. `src/agents/assumptions_dependencies.py` - New agent
4. `src/agents/equations_symbols.py` - New agent

### 7.2 Files to Modify

1. `src/models.py` - Add new output models (InformationGatheringOutput, MetadataOutput, AssumptionsDependenciesOutput, EquationsSymbolsOutput)
2. `src/orchestrator.py` - Update PipelineOrchestrator to use 8-agent sequence
3. `src/agents/derivation.py` - Enhance with stricter guidelines
4. `src/agents/verifier.py` - Enhance verification depth
5. `src/agents/assembler.py` - Update to accept new input structure
6. `src/agents/reviewer.py` - Add guide.md quality checklist + new assumption validation
7. `config/settings.yaml` - Add model assignments for 4 new agents

### 7.3 Files to Remove

1. `src/agents/researcher.py` - Replaced by 4 new sub-agents

---

## 8. Implementation Steps

### 8.1 Step 1: Create New Data Models
- Add `InformationGatheringOutput` to models.py
- Add `MetadataOutput` to models.py
- Add `AssumptionsDependenciesOutput` to models.py
- Add `EquationsSymbolsOutput` to models.py
- Keep existing models (DerivationOutput, VerifierOutput, etc.)

### 8.2 Step 2: Implement InformationGathererAgent
- Inherit from BaseAgent
- Use web_search utility
- Focus purely on information gathering
- Output structured summary

### 8.3 Step 3: Implement MetadataFillerAgent
- Inherit from BaseAgent
- Load CONTRIBUTING.md guidelines via get_guidelines()
- Focus on metadata fields only
- Strict format validation

### 8.4 Step 4: Implement AssumptionsDependenciesAgent
- Inherit from BaseAgent
- Load dataset.load_assumptions() and dataset.load_entries()
- Check for duplicates and logical independence
- Flag missing dependencies explicitly

### 8.5 Step 5: Implement EquationsSymbolsAgent
- Inherit from BaseAgent
- Focus on AsciiMath correctness
- Validate notation (fractions, derivatives, subscripts)
- Define all symbols

### 8.6 Step 6: Enhance DerivationAgent
- Add explicit guidelines about starting from assumptions/depends_on
- Emphasize step-by-step completeness
- Add examples of using `assumptions` field in steps
- Add examples of using `equation_proven` field

### 8.7 Step 7: Enhance VerifierAgent
- Add guidelines about commenting every step
- Emphasize assertions for intermediate steps
- Add examples of thorough verification

### 8.8 Step 8: Update AssemblerAgent
- Modify to accept new input structure (7 outputs instead of 3)
- Update assembly logic

### 8.9 Step 9: Enhance ReviewerAgent
- Incorporate quality checklist from guide.md
- Add specific checks for logical independence
- Add AsciiMath validation
- Add new assumption validation logic
- Keep 3-iteration self-correction loop

### 8.10 Step 10: Update PipelineOrchestrator
- Modify generate_entry() to call 8 agents in sequence
- Thread data through new pipeline
- Update error handling
- Add missing dependencies prompt

### 8.11 Step 11: Update Configuration
- Add model assignments for 4 new agents in settings.yaml:
  ```yaml
  agent_models:
    information_gatherer: "fast"
    metadata_filler: "fast"
    assumptions_dependencies: "best"
    equations_symbols: "best"
    derivation: "best"
    verifier: "best"
    assembler: "fast"
    reviewer: "best"
  ```
- Document new agent structure

### 8.12 Step 12: Add User Interaction for Missing Dependencies
- Modify orchestrator to detect missing_dependencies
- Add interactive prompt when missing dependencies found:
  - Display which entries are missing with suggested IDs
  - Offer options: (A) Stop and build them first, (B) Continue with mock IDs
  - Handle user choice appropriately

### 8.13 Step 13: Implement Proposed Assumptions Workflow
- Create data structure for proposed_assumptions tracking
- Modify ReviewerAgent to validate new assumptions:
  - Check logical independence
  - Validate against existing assumptions for duplicates
  - Verify schema compliance
- Save new assumptions to separate file only after review passes

### 8.14 Step 14: Update CLI
- Add flag for handling missing dependencies: `--auto-continue-missing-deps` (default: false, prompts user)
- Add flag for new assumptions: `--review-new-assumptions` (default: true)
- Otherwise interface remains the same

### 8.15 Step 15: Update Documentation
**Files to update:**

#### README.md
- Update architecture section to reflect 8-agent pipeline
- Add section explaining each agent's responsibility:
  - InformationGathererAgent: Web research and context gathering
  - MetadataFillerAgent: Entry metadata (ID, name, explanation, domain, etc.)
  - AssumptionsDependenciesAgent: Assumptions and dependencies with dataset consultation
  - EquationsSymbolsAgent: Result equations and symbol definitions
  - DerivationAgent: Step-by-step mathematical derivations
  - VerifierAgent: Programmatic verification with SymPy
  - AssemblerAgent: Combines all outputs into TheoriaEntry
  - ReviewerAgent: Quality checking with guide.md checklist
- Update pipeline diagram/flowchart
- Update usage examples if needed
- Add section documenting new CLI flags (--auto-continue-missing-deps, --review-new-assumptions)
- Update model assignments section in configuration

#### CONTRIBUTING.md (if exists, or create it)
- Add development guidelines for the new agent structure
- Update testing instructions with TDD approach
- Document how to add new agents:
  - Inherit from BaseAgent
  - Define agent_name
  - Implement run() method
  - Add to settings.yaml for model assignment
  - Write comprehensive unit tests
- Explain fixture usage for tests
- Document mocking strategy for LLM and dataset
- Add examples of proper test structure

#### guide.md
- **Critical**: This file contains agent workflow documentation
- Replace all references to ResearcherAgent with the 4 new agents
- Update workflow examples to show new 8-agent pipeline flow
- Add specific sections for each new agent:
  - Information gathering guidelines
  - Metadata filling requirements (following CONTRIBUTING.md strictly)
  - Assumptions/dependencies selection criteria (logical independence!)
  - Equations/symbols guidelines (AsciiMath correctness)
- Update quality checklist to reflect distributed responsibilities
- Add examples of good vs bad outputs for each agent
- Document common pitfalls for each agent type

---

## 9. Test-Driven Development Plan

**Testing Philosophy**: Write tests FIRST, then implement agents to pass the tests.

### 9.1 Test Structure

```
tests/
├── unit/
│   ├── agents/
│   │   ├── test_information_gatherer.py
│   │   ├── test_metadata_filler.py
│   │   ├── test_assumptions_dependencies.py
│   │   ├── test_equations_symbols.py
│   │   ├── test_derivation_enhanced.py
│   │   ├── test_verifier_enhanced.py
│   │   ├── test_assembler_updated.py
│   │   └── test_reviewer_enhanced.py
│   └── models/
│       └── test_new_models.py
├── integration/
│   ├── test_pipeline_flow.py
│   ├── test_missing_dependencies.py
│   └── test_new_assumptions.py
└── fixtures/
    ├── sample_topics.py
    ├── mock_wikipedia_responses.py
    └── expected_outputs.py
```

---

### 9.2 Unit Tests (Write These First)

#### 9.2.1 test_information_gatherer.py

**Purpose**: Test InformationGathererAgent in isolation

**Test Cases**:
1. `test_information_gatherer_initialization`
   - Verify agent inherits from BaseAgent
   - Verify model assignment is "fast"
   - Verify web_search utility is accessible

2. `test_gather_wikipedia_context_success`
   - Mock Wikipedia API response
   - Input: topic="Special Relativity"
   - Expected output: InformationGatheringOutput with web_context populated
   - Verify web_context length ≤ 10k chars
   - Verify graduate-level physics content

3. `test_gather_historical_context`
   - Mock Wikipedia API with historical information
   - Input: topic="Newton's Laws"
   - Expected output: historical_context with development_period, key_insights, importance
   - Verify all fields are non-empty strings

4. `test_suggest_references`
   - Mock Wikipedia API with references
   - Input: topic="Maxwell's Equations"
   - Expected output: suggested_references list with 1-3 APA citations
   - Verify APA format correctness

5. `test_truncate_long_content`
   - Mock Wikipedia API with >10k char response
   - Verify output is truncated to exactly 10k chars
   - Verify truncation doesn't break mid-sentence

6. `test_handle_wikipedia_not_found`
   - Mock Wikipedia API 404 response
   - Verify graceful handling (empty context or fallback search)
   - No exceptions raised

**Fixtures Needed**:
- Mock Wikipedia responses for various physics topics
- Expected InformationGatheringOutput samples

---

#### 9.2.2 test_metadata_filler.py

**Purpose**: Test MetadataFillerAgent in isolation

**Test Cases**:
1. `test_metadata_filler_initialization`
   - Verify agent inherits from BaseAgent
   - Verify model assignment is "fast"
   - Verify CONTRIBUTING.md guidelines loaded via get_guidelines()

2. `test_generate_result_id`
   - Input: topic="Lorentz Transformation"
   - Expected: result_id="lorentz_transformation"
   - Verify pattern: ^[a-z0-9_]+$
   - Verify descriptive and lowercase

3. `test_generate_result_name`
   - Input: topic="Schrödinger Equation"
   - Expected: result_name with ≤100 chars
   - Verify concise and descriptive

4. `test_write_explanation`
   - Input: InformationGatheringOutput with physics context
   - Expected: explanation with 2-5 sentences, ≤800 chars
   - Verify conceptual focus (no derivation steps)
   - Verify includes: definition, importance, usage
   - Verify math uses backticks + AsciiMath

5. `test_select_domain`
   - Input: topic="General Relativity"
   - Expected: domain="gr-qc" (valid arXiv category)
   - Verify pattern: ^[a-z][a-z\-\.]+$

6. `test_determine_theory_status`
   - Input: topic="Newtonian Mechanics"
   - Expected: theory_status="historical" or "limiting_case"
   - Verify enum value (current/historical/approximation/limiting_case/generalized)

7. `test_format_references`
   - Input: suggested_references from InformationGathererAgent
   - Expected: 1-3 references with id and citation in APA format
   - Verify APA format correctness

8. `test_add_contributor_info`
   - Input: contributor_name="John Doe", contributor_id="https://orcid.org/0000-0001-2345-6789"
   - Expected: contributors array with full_name and identifier

9. `test_set_review_status_draft`
   - Verify review_status always set to "draft"

10. `test_add_historical_context_when_relevant`
    - Input: topic with historical significance
    - Expected: historical_context object with importance, development_period, key_insights

11. `test_explanation_no_derivation_steps`
    - Input: InformationGatheringOutput with derivation details
    - Expected: explanation WITHOUT any derivation steps
    - Verify only conceptual content

**Fixtures Needed**:
- Sample InformationGatheringOutput objects
- Expected MetadataOutput samples for various topics
- Mock CONTRIBUTING.md guidelines

---

#### 9.2.3 test_assumptions_dependencies.py

**Purpose**: Test AssumptionsDependenciesAgent in isolation (CRITICAL)

**Test Cases**:
1. `test_assumptions_dependencies_initialization`
   - Verify agent inherits from BaseAgent
   - Verify model assignment is "best"
   - Verify dataset.load_assumptions() accessible
   - Verify dataset.load_entries() accessible

2. `test_select_existing_assumptions`
   - Mock globals/assumptions.json with 10 assumptions
   - Input: topic="Harmonic Oscillator"
   - Expected: assumptions array with existing assumption IDs
   - Verify no duplication
   - Verify logical independence

3. `test_avoid_duplicate_assumptions`
   - Mock globals/assumptions.json with assumption "conservation_of_energy"
   - Input: topic requiring energy conservation
   - Expected: assumptions=["conservation_of_energy"]
   - Verify NO new_assumptions proposed for existing ones

4. `test_logical_independence_check`
   - Input: topic where consequence might be listed as assumption
   - Expected: Only fundamental assumptions selected
   - Verify no derived properties in assumptions
   - Example: If "central_force" assumed, don't also assume "angular_momentum_conserved"

5. `test_identify_existing_dependencies`
   - Mock theoria-dataset entries
   - Input: topic="Schrödinger Equation" (depends on quantum postulates)
   - Expected: depends_on array with valid existing entry IDs
   - Verify all IDs exist in dataset

6. `test_flag_missing_dependencies`
   - Input: topic="Quantum Harmonic Oscillator" when "harmonic_oscillator" entry doesn't exist
   - Expected: missing_dependencies array with suggested IDs
   - Verify clear description of what's missing

7. `test_propose_new_assumption_when_needed`
   - Mock globals/assumptions.json WITHOUT a needed assumption
   - Input: topic requiring unique assumption
   - Expected: new_assumptions array with ProposedAssumption objects
   - Verify schema compliance (id, title, text, type)

8. `test_new_assumption_has_proper_type`
   - Input: topic requiring new assumption
   - Expected: new_assumptions[0].type in ["principle", "empirical", "approximation"]
   - Verify correct categorization

9. `test_new_assumption_has_clear_text`
   - Input: topic requiring new assumption
   - Expected: new_assumptions[0].text with 10-1000 chars
   - Verify clear, specific description (not vague)

10. `test_new_assumption_with_mathematical_expressions`
    - Input: topic requiring assumption with math
    - Expected: new_assumptions[0].mathematical_expressions (array)
    - Expected: new_assumptions[0].symbol_definitions (array)
    - Verify AsciiMath format

11. `test_empty_missing_dependencies_when_all_exist`
    - Mock complete dataset with all needed entries
    - Input: topic="Simple topic"
    - Expected: missing_dependencies=[]

12. `test_empty_new_assumptions_when_all_exist`
    - Mock complete assumptions.json
    - Input: topic="Common topic"
    - Expected: new_assumptions=[]

**Fixtures Needed**:
- Mock globals/assumptions.json with various assumption types
- Mock theoria-dataset entries
- Expected AssumptionsDependenciesOutput samples
- Examples of logical independence violations

---

#### 9.2.4 test_equations_symbols.py

**Purpose**: Test EquationsSymbolsAgent in isolation (CRITICAL for AsciiMath)

**Test Cases**:
1. `test_equations_symbols_initialization`
   - Verify agent inherits from BaseAgent
   - Verify model assignment is "best"

2. `test_identify_result_equations`
   - Input: topic="Newton's Second Law"
   - Expected: result_equations with at least 1 equation
   - Verify proper structure (id, equation, optional equation_title)

3. `test_asciimath_fraction_notation`
   - Input: equation with fractions
   - Expected: `(numerator)/(denominator)` format
   - Verify parentheses present
   - Example: `(dp)/(dt)` not `dp/dt`

4. `test_asciimath_derivative_notation`
   - Input: equation with derivatives
   - Expected: `(d property)/(d variable)` format
   - Verify proper parentheses
   - Example: `(dx)/(dt)` not `dx/dt`

5. `test_asciimath_subscript_notation`
   - Input: equation with multi-character subscripts
   - Expected: `variable_(subscript)` format
   - Verify parentheses for multi-char subscripts
   - Example: `E_(kinetic)` not `E_kinetic`

6. `test_asciimath_no_to_in_subscripts`
   - Input: equation that might use "to" in subscript
   - Expected: NO "to" in subscripts (renders as arrow)
   - Use alternative notation

7. `test_define_all_symbols`
   - Input: result_equations=["F = m a", "E = (1)/(2) m v^2"]
   - Expected: definitions for F, m, a, E, v (every symbol)
   - Verify complete symbol coverage

8. `test_definitions_use_asciimath_in_backticks`
   - Input: definitions containing math
   - Expected: Math enclosed in backticks with AsciiMath
   - Example: "where `F` is force"

9. `test_equation_ids_sequential`
   - Input: multiple equations
   - Expected: ids=["eq1", "eq2", "eq3", ...]
   - Verify sequential and unique

10. `test_self_contained_entry`
    - Input: complex topic with many symbols
    - Expected: Every symbol in result_equations has definition
    - Verify no undefined symbols

11. `test_asciimath_validation_comprehensive`
    - Input: Various mathematical expressions
    - Run AsciiMath validator on all equations
    - Verify no common errors (missing parens, wrong operators, etc.)

**Fixtures Needed**:
- Sample equations with correct AsciiMath
- Sample equations with incorrect AsciiMath (for validation)
- Expected EquationsSymbolsOutput samples
- AsciiMath validation rules

---

#### 9.2.5 test_derivation_enhanced.py

**Purpose**: Test enhanced DerivationAgent

**Test Cases**:
1. `test_derivation_starts_from_assumptions`
   - Input: AssumptionsDependenciesOutput with assumptions
   - Expected: First derivation step references assumptions
   - Verify explicit citation

2. `test_derivation_starts_from_dependencies`
   - Input: AssumptionsDependenciesOutput with depends_on
   - Expected: First derivation step references dependency entries
   - Verify explicit citation

3. `test_no_skipped_algebra_steps`
   - Input: topic requiring multi-step derivation
   - Expected: All intermediate algebraic steps present
   - Verify completeness (human-followable)

4. `test_step_has_assumptions_field`
   - Input: derivation step using specific assumption
   - Expected: step.assumptions array with assumption IDs
   - Verify explicit linkage

5. `test_equation_proven_linkage`
   - Input: result_equations with equation_title
   - Expected: At least one derivation step with equation_proven=eq_id
   - Verify proper linkage

6. `test_asciimath_correctness_in_derivation`
   - Input: derivation with mathematical expressions
   - Expected: All equations in AsciiMath format
   - Run AsciiMath validator

7. `test_description_clarity`
   - Input: derivation step
   - Expected: description with clear rationale
   - Verify no excessive formulas (goes in equation field)

8. `test_sequential_step_numbers`
   - Input: full derivation
   - Expected: step numbers sequential starting from 1
   - Verify no gaps

**Fixtures Needed**:
- Sample inputs from all Phase 1 agents
- Expected DerivationOutput samples
- Known-good derivations for comparison

---

#### 9.2.6 test_verifier_enhanced.py

**Purpose**: Test enhanced VerifierAgent

**Test Cases**:
1. `test_comment_every_step`
   - Input: DerivationOutput with 10 steps
   - Expected: programmatic_verification with "# Step N" for each step
   - Verify complete coverage

2. `test_assertions_for_major_claims`
   - Input: derivation with key equations
   - Expected: assert statements verifying each major claim
   - Verify no untested claims

3. `test_verify_intermediate_steps`
   - Input: multi-step derivation
   - Expected: Verification of intermediate steps, not just final
   - Verify thoroughness

4. `test_include_sanity_checks`
   - Input: derivation
   - Expected: Sanity checks at end (e.g., units, special cases)
   - Verify completeness

5. `test_print_confirmation`
   - Input: derivation
   - Expected: Print statement when all tests pass
   - Verify message present

6. `test_code_execution_success`
   - Input: valid derivation
   - Expected: execution_success=True
   - Verify code runs without errors

7. `test_code_execution_failure_handling`
   - Input: invalid derivation (intentionally wrong)
   - Expected: execution_success=False
   - Expected: execution_output with error details

8. `test_correct_library_version`
   - Expected: language="python 3.11.12" (or current)
   - Expected: library="sympy 1.13.1" (or current)
   - Verify version format: `^[A-Za-z]+\s\d+\.\d+\.\d+$`

**Fixtures Needed**:
- Sample DerivationOutput objects
- Expected VerifierOutput samples
- Intentionally incorrect derivations for testing

---

#### 9.2.7 test_assembler_updated.py

**Purpose**: Test updated AssemblerAgent

**Test Cases**:
1. `test_assembler_accepts_7_inputs`
   - Input: All 7 agent outputs
   - Expected: No errors
   - Verify correct assembly

2. `test_assembler_produces_theoria_entry`
   - Input: All 7 agent outputs
   - Expected: Complete TheoriaEntry object
   - Verify all required fields present

3. `test_assembler_no_llm_needed`
   - Verify no LLM calls made
   - Pure data assembly logic

4. `test_assembler_preserves_all_data`
   - Input: All 7 agent outputs
   - Expected: No data loss
   - Verify all fields from all agents preserved

**Fixtures Needed**:
- Complete set of 7 agent outputs
- Expected TheoriaEntry sample

---

#### 9.2.8 test_reviewer_enhanced.py

**Purpose**: Test enhanced ReviewerAgent

**Test Cases**:
1. `test_reviewer_uses_guideMd_checklist`
   - Input: TheoriaEntry
   - Expected: Issues list referencing guide.md checklist items
   - Verify comprehensive review

2. `test_reviewer_checks_logical_independence`
   - Input: TheoriaEntry with assumptions violating independence
   - Expected: issues array flagging the violation
   - Example: "angular_momentum_conserved is consequence of central_force"

3. `test_reviewer_validates_asciimath`
   - Input: TheoriaEntry with incorrect AsciiMath
   - Expected: issues array with AsciiMath errors
   - Example: "Missing parentheses in fraction"

4. `test_reviewer_checks_derivation_completeness`
   - Input: TheoriaEntry with skipped steps
   - Expected: issues array flagging incomplete derivation
   - Example: "Step 5 to Step 6 jumps without explanation"

5. `test_reviewer_checks_verification_depth`
   - Input: TheoriaEntry with shallow verification
   - Expected: issues array flagging insufficient verification
   - Example: "Only final equation verified, intermediate steps not checked"

6. `test_reviewer_validates_new_assumptions`
   - Input: TheoriaEntry + new_assumptions
   - Expected: Validation of new assumptions
   - Check: logical independence, no duplicates, schema compliance

7. `test_reviewer_self_correction_loop`
   - Input: TheoriaEntry with issues
   - Expected: Up to 3 correction iterations
   - Verify corrected_entry returned if fixable

8. `test_reviewer_passes_good_entry`
   - Input: High-quality TheoriaEntry
   - Expected: passed=True, issues=[]
   - Verify no false positives

9. `test_reviewer_fails_bad_entry`
   - Input: Low-quality TheoriaEntry
   - Expected: passed=False, issues=[list of problems]
   - Verify accurate detection

**Fixtures Needed**:
- High-quality TheoriaEntry samples
- Low-quality TheoriaEntry samples with known issues
- Sample new_assumptions for validation

---

#### 9.2.9 test_new_models.py

**Purpose**: Test new Pydantic data models

**Test Cases**:
1. `test_information_gathering_output_schema`
   - Create InformationGatheringOutput
   - Verify all fields: web_context, historical_context, suggested_references
   - Test Pydantic validation

2. `test_metadata_output_schema`
   - Create MetadataOutput
   - Verify all metadata fields present
   - Test Pydantic validation

3. `test_assumptions_dependencies_output_schema`
   - Create AssumptionsDependenciesOutput
   - Verify fields: assumptions, new_assumptions, depends_on, missing_dependencies
   - Test Pydantic validation

4. `test_equations_symbols_output_schema`
   - Create EquationsSymbolsOutput
   - Verify fields: result_equations, definitions
   - Test Pydantic validation

5. `test_proposed_assumption_schema`
   - Create ProposedAssumption
   - Verify matches assumptions.schema.json
   - Test Pydantic validation

**Fixtures Needed**:
- Sample data for each model

---

### 9.3 Integration Tests (Write After Unit Tests)

#### 9.3.1 test_pipeline_flow.py

**Purpose**: Test complete 8-agent pipeline end-to-end

**Test Cases**:
1. `test_full_pipeline_known_topic`
   - Input: topic="Special Relativity", hints={}
   - Expected: Complete TheoriaEntry generated
   - Compare to existing special_relativity_transformations.json
   - Verify similar quality

2. `test_pipeline_sequential_execution`
   - Input: any topic
   - Verify agents called in order: 1→2→3→4→5→6→7→8
   - Verify data flow between agents

3. `test_pipeline_with_user_hints`
   - Input: topic="Maxwell's Equations", hints={domain: "physics.class-ph", depends_on: ["vector_calculus"]}
   - Expected: Hints respected in MetadataFillerAgent and AssumptionsDependenciesAgent

4. `test_pipeline_error_handling`
   - Input: topic triggering error in agent 3
   - Expected: Graceful error handling, clear error message
   - Verify pipeline stops at failure point

5. `test_pipeline_generates_valid_entry`
   - Input: any topic
   - Expected: TheoriaEntry passing schema validation
   - Run schema validator

**Fixtures Needed**:
- Known topics with expected outputs
- Mock LLM responses for consistent testing

---

#### 9.3.2 test_missing_dependencies.py

**Purpose**: Test missing dependencies workflow

**Test Cases**:
1. `test_detect_missing_dependencies`
   - Input: topic depending on non-existent entry
   - Expected: Pipeline stops at AssumptionsDependenciesAgent
   - Expected: missing_dependencies populated

2. `test_user_prompt_for_missing_dependencies`
   - Mock user interaction
   - Expected: Prompt displayed with options A and B
   - Verify options: (A) Stop, (B) Continue with mock IDs

3. `test_user_chooses_stop`
   - Mock user selecting option A
   - Expected: Pipeline halts
   - Expected: Clear message about which entries to build first

4. `test_user_chooses_continue_with_mock_ids`
   - Mock user selecting option B
   - Expected: Pipeline continues with mock IDs in depends_on
   - Expected: Entry generated with placeholder dependencies

5. `test_cli_flag_auto_continue`
   - Input: topic with missing deps, CLI flag `--auto-continue-missing-deps`
   - Expected: No user prompt, automatically continue with mock IDs

**Fixtures Needed**:
- Topics with missing dependencies
- Mock user input

---

#### 9.3.3 test_new_assumptions.py

**Purpose**: Test new assumptions workflow

**Test Cases**:
1. `test_propose_new_assumption`
   - Input: topic requiring new assumption
   - Expected: new_assumptions populated in AssumptionsDependenciesOutput
   - Verify ProposedAssumption structure

2. `test_reviewer_validates_new_assumption`
   - Input: TheoriaEntry + valid new_assumptions
   - Expected: ReviewerAgent validates successfully
   - Expected: passed=True

3. `test_reviewer_rejects_duplicate_assumption`
   - Input: TheoriaEntry + new_assumption duplicating existing
   - Expected: ReviewerAgent flags duplication
   - Expected: issues array with "Duplicate assumption" error

4. `test_reviewer_rejects_logically_dependent_assumption`
   - Input: TheoriaEntry + new_assumption that's a consequence
   - Expected: ReviewerAgent flags logical dependence
   - Expected: issues array with "Not logically independent" error

5. `test_save_new_assumptions_separately`
   - Input: Entry passing review with new_assumptions
   - Expected: New assumptions saved to separate file (not assumptions.json directly)
   - Verify file format and content

6. `test_cli_flag_review_new_assumptions`
   - Input: topic proposing new assumption, CLI flag `--review-new-assumptions=true`
   - Expected: ReviewerAgent validates assumptions
   - Verify enabled by default

**Fixtures Needed**:
- Topics requiring new assumptions
- Valid and invalid ProposedAssumption samples

---

### 9.4 Testing Infrastructure

#### 9.4.1 Test Fixtures (`tests/fixtures/`)

**sample_topics.py**:
- Known physics topics with expected characteristics
- Topics requiring missing dependencies
- Topics requiring new assumptions
- Simple and complex topics

**mock_wikipedia_responses.py**:
- Pre-recorded Wikipedia API responses for deterministic testing
- Various physics topics
- Edge cases (not found, very long content, etc.)

**expected_outputs.py**:
- Expected outputs for each agent given specific inputs
- Known-good TheoriaEntry samples

#### 9.4.2 Test Utilities

**validators.py**:
- AsciiMath validation function
- Schema validation helper
- Logical independence checker
- Reference format validator (APA)

**mock_helpers.py**:
- Mock LLM response generator
- Mock dataset loader
- Mock Wikipedia API

---

### 9.5 Testing Execution Order

**Phase 1: Models**
1. Run test_new_models.py
2. Ensure all Pydantic models defined and validated

**Phase 2: Individual Agents (Unit Tests)**
3. Run test_information_gatherer.py
4. Run test_metadata_filler.py
5. Run test_assumptions_dependencies.py
6. Run test_equations_symbols.py
7. Run test_derivation_enhanced.py
8. Run test_verifier_enhanced.py
9. Run test_assembler_updated.py
10. Run test_reviewer_enhanced.py

**Phase 3: Integration Tests**
11. Run test_pipeline_flow.py
12. Run test_missing_dependencies.py
13. Run test_new_assumptions.py

**Phase 4: Full System Tests**
14. Run existing theoria-dataset validation suite
15. Generate entries for known topics and compare to existing

---

### 9.6 Test Commands

```bash
# Run all tests
pytest tests/ -v

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests only
pytest tests/integration/ -v

# Run specific agent tests
pytest tests/unit/agents/test_assumptions_dependencies.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run tests in parallel
pytest tests/ -n auto
```

---

### 9.7 Success Criteria

**All tests must pass before implementation is considered complete:**
- ✅ 100% of unit tests pass
- ✅ 100% of integration tests pass
- ✅ Code coverage ≥ 80%
- ✅ All generated entries pass schema validation
- ✅ Manual review of 3 generated entries passes guide.md checklist
- ✅ No regressions in existing functionality

---

## 10. Implementation Strategy (After Tests Pass)

**Order**: Write tests → Implement code to pass tests → Refactor → Repeat

1. Write all unit tests for models
2. Implement Pydantic models to pass tests
3. Write unit tests for InformationGathererAgent
4. Implement InformationGathererAgent to pass tests
5. Write unit tests for MetadataFillerAgent
6. Implement MetadataFillerAgent to pass tests
7. Write unit tests for AssumptionsDependenciesAgent
8. Implement AssumptionsDependenciesAgent to pass tests
9. Write unit tests for EquationsSymbolsAgent
10. Implement EquationsSymbolsAgent to pass tests
11. Enhance DerivationAgent based on tests
12. Enhance VerifierAgent based on tests
13. Update AssemblerAgent based on tests
14. Enhance ReviewerAgent based on tests
15. Write integration tests
16. Update PipelineOrchestrator to pass integration tests
17. Update configuration
18. Update CLI
19. Run full test suite
20. Manual verification

Each step follows TDD: Red (write failing test) → Green (make it pass) → Refactor (improve code)
