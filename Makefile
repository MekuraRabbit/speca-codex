# Configuration variables
TARGET_REPO ?= ethereum/go-ethereum
TARGET_REF ?= master
KEYWORDS ?= "geth,ethereum client,execution specs,EIP"
SPEC_URLS ?= "https://ethereum.github.io/execution-specs/src/,https://geth.ethereum.org/docs"
WORKDIR ?= target_workspace
OUTPUT_DIR ?= outputs
LOG_DIR ?= outputs/logs

# Claude environment
export CLAUDE_CODE_PERMISSIONS := bypassPermissions
export CLAUDE_CODE_MAX_OUTPUT_TOKENS := 100000

# Claude configuration
CLAUDE_FLAGS ?= --dangerously-skip-permissions --agent serena --output-format json

# Iteration counts
EXTRACT_ITERATIONS ?= 10
CHECKLIST_ITERATIONS ?= 10

.PHONY: all preparation audit init init-prep \
        01a 01b 01b-loop 01c 01d 01e \
        02a 02b 02b-loop 02c 02s \
        03 04 clean help

# Default target: run full pipeline
all: preparation audit

# Phase targets
# preparation: 01a → 01b (Nx) → 01c → 01d → 01e → 02s → 02a → 02b (Nx)
preparation: 02b-loop
	@echo "🎉 Preparation phase completed! Check $(OUTPUT_DIR)/"

audit: 04
	@echo "🎉 Audit phase completed! Check $(OUTPUT_DIR)/04_REVIEW_PARTIAL_*.json"

# ------------------------------------------------------
# Utilities
# ------------------------------------------------------

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Phase Targets:"
	@echo "  all         - Run full pipeline (preparation + audit)"
	@echo "  preparation - Run preparation phase (01a → 01b xN → 01c → 01d → 01e → 02s → 02a → 02b xN)"
	@echo "  audit       - Run audit phase (03 → 04)"
	@echo ""
	@echo "Specification Steps (01a-01e):"
	@echo "  init-prep  - Setup output directories (no git repo required)"
	@echo "  01a        - Discovery & Queuing (01a_crawl.md → 01a_STATE.json)"
	@echo "  01b        - Extraction (01b_extract.md) - Single run, processes one URL"
	@echo "  01b-loop   - Extraction (01b_extract.md) - Run $(EXTRACT_ITERATIONS) times"
	@echo "  01c        - Integration (01c_integrate.md → 01_SPEC.json)"
	@echo "  01d        - Trust Model (01d_trustmodel.md → 01d_TRUSTMODEL.json)"
	@echo "  01e        - Properties (01e_prop.md → 01e_PROP.json)"
	@echo ""
	@echo "Checklist Steps (02a-02s):"
	@echo "  02a        - Checklist Boundaries (02a_checklist.md → 02a_CHECKLIST_BOUNDARIES.json)"
	@echo "  02b        - Checklist Remaining (02b_checklistrem.md) - Single run"
	@echo "  02b-loop   - Checklist Remaining (02b_checklistrem.md) - Run $(CHECKLIST_ITERATIONS) times"
	@echo "  02c        - Checklist Merge (02c_checklistmerge.md → 02_CHECKLIST.json) [OPTIONAL]"
	@echo "  02s        - Review & Validate (02s_review.md → 02s_REVIEW_REPORT.json)"
	@echo ""
	@echo "Audit Steps:"
	@echo "  init   - Setup directories and check target workspace (git repo required)"
	@echo "  03     - Static Audit Map (03_auditmap.md) - Run iteratively"
	@echo "  04     - Audit Review (04_review.md) - Run iteratively"
	@echo ""
	@echo "Utilities:"
	@echo "  clean  - Remove generated outputs"
	@echo ""
	@echo "Configuration Variables:"
	@echo "  EXTRACT_ITERATIONS   - Number of 01b extractions (default: 10)"
	@echo "  CHECKLIST_ITERATIONS - Number of 02b iterations (default: 10)"
	@echo ""
	@echo "Example: make preparation EXTRACT_ITERATIONS=20 CHECKLIST_ITERATIONS=15"

# Init for audit phase (requires git repo)
init:
	@echo "Initializing workspace..."
	mkdir -p $(LOG_DIR)
	mkdir -p $(WORKDIR)/outputs
	@if [ ! -d "$(WORKDIR)/.git" ]; then \
		echo "Error: $(WORKDIR) is not a git repo. Please clone target repo:"; \
		echo "  git clone https://github.com/$(TARGET_REPO) $(WORKDIR)"; \
		exit 1; \
	fi
	@echo "Workspace ready at $(WORKDIR)"

# Init for preparation phase (no git repo required)
init-prep:
	@echo "Initializing for preparation phase..."
	mkdir -p $(LOG_DIR)
	mkdir -p $(OUTPUT_DIR)
	mkdir -p $(OUTPUT_DIR)/01b_SUBGRAPHS
	@echo "Output directories ready"

# Utilities
clean:
	@echo "Cleaning outputs..."
	rm -rf $(OUTPUT_DIR)/*.json
	rm -rf $(OUTPUT_DIR)/01b_SUBGRAPHS
	rm -rf $(LOG_DIR)/*.json
	rm -rf $(WORKDIR)/outputs/*.json
	@echo "✅ Clean completed"

# ------------------------------------------------------
# Specification Steps (01a - 01e)
# ------------------------------------------------------

# Step 01a: Discovery & Queuing
01a: $(OUTPUT_DIR)/01a_STATE.json
$(OUTPUT_DIR)/01a_STATE.json: prompts/01a_crawl.md | init-prep
	@echo "⭐ Running 01a_crawl.md (Discovery & Queuing)..."; \
	START_TIME=$$(date +%s); \
	claude $(CLAUDE_FLAGS) -p "$$(cat prompts/01a_crawl.md) KEYWORDS=$(KEYWORDS) SPEC_URLS=$(SPEC_URLS)" > $(LOG_DIR)/01a_crawl.json; \
	END_TIME=$$(date +%s); \
	DURATION=$$((END_TIME - START_TIME)); \
	if [ -f "$(OUTPUT_DIR)/01a_STATE.json" ]; then \
		INPUT_TOKENS=$$(grep -o '"input_tokens":[0-9]*' $(LOG_DIR)/01a_crawl.json | head -1 | cut -d: -f2); \
		OUTPUT_TOKENS=$$(grep -o '"output_tokens":[0-9]*' $(LOG_DIR)/01a_crawl.json | head -1 | cut -d: -f2); \
		COST=$$(grep -o '"total_cost_usd":[0-9.]*' $(LOG_DIR)/01a_crawl.json | head -1 | cut -d: -f2); \
		QUEUE_SIZE=$$(grep -o '"work_queue":\[[^]]*\]' $(OUTPUT_DIR)/01a_STATE.json | tr ',' '\n' | wc -l); \
		echo "✅ Finished 01a_crawl.md (Time: $${DURATION}s | URLs queued: ~$$QUEUE_SIZE | Cost: \$$$$COST)"; \
	else \
		echo "❌ Error: 01a_STATE.json not generated"; exit 1; \
	fi

# Step 01b: Extraction (Single run)
01b: | 01a
	@echo "⭐ Running 01b_extract.md (Extraction)..."; \
	START_TIME=$$(date +%s); \
	claude $(CLAUDE_FLAGS) -p "$$(cat prompts/01b_extract.md)" > $(LOG_DIR)/01b_extract_$$(date +%s).json; \
	END_TIME=$$(date +%s); \
	DURATION=$$((END_TIME - START_TIME)); \
	LOG_FILE=$$(ls -t $(LOG_DIR)/01b_extract_*.json | head -1); \
	INPUT_TOKENS=$$(grep -o '"input_tokens":[0-9]*' $$LOG_FILE | head -1 | cut -d: -f2); \
	OUTPUT_TOKENS=$$(grep -o '"output_tokens":[0-9]*' $$LOG_FILE | head -1 | cut -d: -f2); \
	COST=$$(grep -o '"total_cost_usd":[0-9.]*' $$LOG_FILE | head -1 | cut -d: -f2); \
	SUBGRAPH_COUNT=$$(ls $(OUTPUT_DIR)/01b_SUBGRAPHS/*.json 2>/dev/null | wc -l); \
	echo "✅ Finished 01b_extract.md (Time: $${DURATION}s | Subgraphs: $$SUBGRAPH_COUNT | Cost: \$$$$COST)"

# Step 01b-loop: Extraction (Multiple runs)
01b-loop: | 01a
	@echo "🔄 Running 01b_extract.md $(EXTRACT_ITERATIONS) times..."
	@for i in $$(seq 1 $(EXTRACT_ITERATIONS)); do \
		echo "⭐ Running 01b_extract.md (iteration $$i/$(EXTRACT_ITERATIONS))..."; \
		START_TIME=$$(date +%s); \
		claude $(CLAUDE_FLAGS) -p "$$(cat prompts/01b_extract.md)" > $(LOG_DIR)/01b_extract_$$i.json; \
		END_TIME=$$(date +%s); \
		DURATION=$$((END_TIME - START_TIME)); \
		INPUT_TOKENS=$$(grep -o '"input_tokens":[0-9]*' $(LOG_DIR)/01b_extract_$$i.json | head -1 | cut -d: -f2); \
		OUTPUT_TOKENS=$$(grep -o '"output_tokens":[0-9]*' $(LOG_DIR)/01b_extract_$$i.json | head -1 | cut -d: -f2); \
		COST=$$(grep -o '"total_cost_usd":[0-9.]*' $(LOG_DIR)/01b_extract_$$i.json | head -1 | cut -d: -f2); \
		echo "✅ Finished 01b_extract.md iter $$i (Time: $${DURATION}s | Cost: \$$$$COST)"; \
		if [ -f "$(OUTPUT_DIR)/01a_STATE.json" ]; then \
			REMAINING=$$(grep -o '"work_queue":\[[^]]*\]' $(OUTPUT_DIR)/01a_STATE.json | tr ',' '\n' | grep -c '"http' || echo "0"); \
			if [ "$$REMAINING" -eq 0 ] 2>/dev/null; then \
				echo "🎉 Work queue empty. Extraction complete."; \
				break; \
			fi; \
		fi; \
	done
	@SUBGRAPH_COUNT=$$(ls $(OUTPUT_DIR)/01b_SUBGRAPHS/*.json 2>/dev/null | wc -l); \
	echo "✅ Extraction complete. Total subgraphs: $$SUBGRAPH_COUNT"

# Step 01c: Integration
01c: $(OUTPUT_DIR)/01_SPEC.json
$(OUTPUT_DIR)/01_SPEC.json: prompts/01c_integrate.md | 01b-loop
	@echo "⭐ Running 01c_integrate.md (Integration)..."; \
	START_TIME=$$(date +%s); \
	claude $(CLAUDE_FLAGS) -p "$$(cat prompts/01c_integrate.md)" > $(LOG_DIR)/01c_integrate.json; \
	END_TIME=$$(date +%s); \
	DURATION=$$((END_TIME - START_TIME)); \
	if [ -f "$(OUTPUT_DIR)/01_SPEC.json" ]; then \
		INPUT_TOKENS=$$(grep -o '"input_tokens":[0-9]*' $(LOG_DIR)/01c_integrate.json | head -1 | cut -d: -f2); \
		OUTPUT_TOKENS=$$(grep -o '"output_tokens":[0-9]*' $(LOG_DIR)/01c_integrate.json | head -1 | cut -d: -f2); \
		COST=$$(grep -o '"total_cost_usd":[0-9.]*' $(LOG_DIR)/01c_integrate.json | head -1 | cut -d: -f2); \
		echo "✅ Finished 01c_integrate.md (Time: $${DURATION}s | Cost: \$$$$COST)"; \
	else \
		echo "❌ Error: 01_SPEC.json not generated"; exit 1; \
	fi

# Step 01d: Trust Model
01d: $(OUTPUT_DIR)/01d_TRUSTMODEL.json
$(OUTPUT_DIR)/01d_TRUSTMODEL.json: prompts/01d_trustmodel.md | 01c
	@echo "⭐ Running 01d_trustmodel.md (Trust Model)..."; \
	START_TIME=$$(date +%s); \
	claude $(CLAUDE_FLAGS) -p "$$(cat prompts/01d_trustmodel.md)" > $(LOG_DIR)/01d_trustmodel.json; \
	END_TIME=$$(date +%s); \
	DURATION=$$((END_TIME - START_TIME)); \
	if [ -f "$(OUTPUT_DIR)/01d_TRUSTMODEL.json" ]; then \
		INPUT_TOKENS=$$(grep -o '"input_tokens":[0-9]*' $(LOG_DIR)/01d_trustmodel.json | head -1 | cut -d: -f2); \
		OUTPUT_TOKENS=$$(grep -o '"output_tokens":[0-9]*' $(LOG_DIR)/01d_trustmodel.json | head -1 | cut -d: -f2); \
		COST=$$(grep -o '"total_cost_usd":[0-9.]*' $(LOG_DIR)/01d_trustmodel.json | head -1 | cut -d: -f2); \
		echo "✅ Finished 01d_trustmodel.md (Time: $${DURATION}s | Cost: \$$$$COST)"; \
	else \
		echo "❌ Error: 01d_TRUSTMODEL.json not generated"; exit 1; \
	fi

# Step 01e: Properties
01e: $(OUTPUT_DIR)/01e_PROP.json
$(OUTPUT_DIR)/01e_PROP.json: prompts/01e_prop.md | 01d
	@echo "⭐ Running 01e_prop.md (Properties)..."; \
	START_TIME=$$(date +%s); \
	claude $(CLAUDE_FLAGS) -p "$$(cat prompts/01e_prop.md)" > $(LOG_DIR)/01e_prop.json; \
	END_TIME=$$(date +%s); \
	DURATION=$$((END_TIME - START_TIME)); \
	if [ -f "$(OUTPUT_DIR)/01e_PROP.json" ]; then \
		INPUT_TOKENS=$$(grep -o '"input_tokens":[0-9]*' $(LOG_DIR)/01e_prop.json | head -1 | cut -d: -f2); \
		OUTPUT_TOKENS=$$(grep -o '"output_tokens":[0-9]*' $(LOG_DIR)/01e_prop.json | head -1 | cut -d: -f2); \
		COST=$$(grep -o '"total_cost_usd":[0-9.]*' $(LOG_DIR)/01e_prop.json | head -1 | cut -d: -f2); \
		echo "✅ Finished 01e_prop.md (Time: $${DURATION}s | Cost: \$$$$COST)"; \
	else \
		echo "❌ Error: 01e_PROP.json not generated"; exit 1; \
	fi

# ------------------------------------------------------
# Checklist Steps (02a - 02s)
# ------------------------------------------------------

# Step 02s: Review & Validate Preparation Outputs
02s: $(OUTPUT_DIR)/02s_REVIEW_REPORT.json
$(OUTPUT_DIR)/02s_REVIEW_REPORT.json: prompts/02s_review.md | 01e
	@echo "⭐ Running 02s_review.md (Preparation Review)..."; \
	START_TIME=$$(date +%s); \
	claude $(CLAUDE_FLAGS) -p "$$(cat prompts/02s_review.md)" > $(LOG_DIR)/02s_review.json; \
	END_TIME=$$(date +%s); \
	DURATION=$$((END_TIME - START_TIME)); \
	INPUT_TOKENS=$$(grep -o '"input_tokens":[0-9]*' $(LOG_DIR)/02s_review.json | head -1 | cut -d: -f2); \
	OUTPUT_TOKENS=$$(grep -o '"output_tokens":[0-9]*' $(LOG_DIR)/02s_review.json | head -1 | cut -d: -f2); \
	COST=$$(grep -o '"total_cost_usd":[0-9.]*' $(LOG_DIR)/02s_review.json | head -1 | cut -d: -f2); \
	if [ -f "$(OUTPUT_DIR)/02s_REVIEW_REPORT.json" ]; then \
		echo "✅ Finished 02s_review.md (Time: $${DURATION}s | Cost: \$$$$COST)"; \
		VERDICT=$$(grep -o '"overall_verdict":"[^"]*"' $(OUTPUT_DIR)/02s_REVIEW_REPORT.json | cut -d'"' -f4); \
		ISSUES=$$(grep -o '"total_issues":[0-9]*' $(OUTPUT_DIR)/02s_REVIEW_REPORT.json | cut -d: -f2); \
		echo "📊 Review: $$VERDICT ($$ISSUES issues)"; \
	else \
		echo "⚠️  Review report not generated (Time: $${DURATION}s | Cost: \$$$$COST)"; \
	fi

# Step 02a: Checklist Boundaries
02a: $(OUTPUT_DIR)/02a_CHECKLIST_BOUNDARIES.json
$(OUTPUT_DIR)/02a_CHECKLIST_BOUNDARIES.json: prompts/02a_checklist.md | 02s
	@echo "⭐ Running 02a_checklist.md (Checklist Boundaries)..."; \
	START_TIME=$$(date +%s); \
	claude $(CLAUDE_FLAGS) -p "$$(cat prompts/02a_checklist.md)" > $(LOG_DIR)/02a_checklist.json; \
	END_TIME=$$(date +%s); \
	DURATION=$$((END_TIME - START_TIME)); \
	if [ -f "$(OUTPUT_DIR)/02a_CHECKLIST_BOUNDARIES.json" ]; then \
		INPUT_TOKENS=$$(grep -o '"input_tokens":[0-9]*' $(LOG_DIR)/02a_checklist.json | head -1 | cut -d: -f2); \
		OUTPUT_TOKENS=$$(grep -o '"output_tokens":[0-9]*' $(LOG_DIR)/02a_checklist.json | head -1 | cut -d: -f2); \
		COST=$$(grep -o '"total_cost_usd":[0-9.]*' $(LOG_DIR)/02a_checklist.json | head -1 | cut -d: -f2); \
		echo "✅ Finished 02a_checklist.md (Time: $${DURATION}s | Cost: \$$$$COST)"; \
	else \
		echo "❌ Error: 02a_CHECKLIST_BOUNDARIES.json not generated"; exit 1; \
	fi

# Step 02b: Checklist Remaining (Single run)
02b: | 02a
	@N=$$(ls $(OUTPUT_DIR)/02b_CHECKLIST_PARTIAL_*.json 2>/dev/null | wc -l); \
	N=$$((N + 1)); \
	echo "⭐ Running 02b_checklistrem.md (iteration $$N)..."; \
	START_TIME=$$(date +%s); \
	claude $(CLAUDE_FLAGS) -p "$$(cat prompts/02b_checklistrem.md)" > $(LOG_DIR)/02b_checklistrem_$$N.json; \
	END_TIME=$$(date +%s); \
	DURATION=$$((END_TIME - START_TIME)); \
	INPUT_TOKENS=$$(grep -o '"input_tokens":[0-9]*' $(LOG_DIR)/02b_checklistrem_$$N.json | head -1 | cut -d: -f2); \
	OUTPUT_TOKENS=$$(grep -o '"output_tokens":[0-9]*' $(LOG_DIR)/02b_checklistrem_$$N.json | head -1 | cut -d: -f2); \
	COST=$$(grep -o '"total_cost_usd":[0-9.]*' $(LOG_DIR)/02b_checklistrem_$$N.json | head -1 | cut -d: -f2); \
	if [ -f "$(OUTPUT_DIR)/02b_CHECKLIST_PARTIAL_$$N.json" ]; then \
		echo "✅ Finished 02b_checklistrem.md iter $$N (Time: $${DURATION}s | Cost: \$$$$COST)"; \
	else \
		echo "⚠️  No new partial checklist generated in iteration $$N (Time: $${DURATION}s | Cost: \$$$$COST)"; \
	fi; \
	if [ -f "$(OUTPUT_DIR)/02b_STATE.json" ]; then \
		REMAINING=$$(grep -o '"unprocessed_property_ids":\[[^]]*\]' $(OUTPUT_DIR)/02b_STATE.json | tr ',' '\n' | grep -c '"PROP' || echo "0"); \
		if [ "$$REMAINING" -gt 0 ] 2>/dev/null; then \
			echo "📋 $$REMAINING properties remaining. Run 'make 02b' again."; \
		else \
			echo "🎉 All properties processed!"; \
		fi; \
	fi

# Step 02b-loop: Checklist Remaining (Multiple runs)
02b-loop: | 02a
	@echo "🔄 Running 02b_checklistrem.md $(CHECKLIST_ITERATIONS) times..."
	@for i in $$(seq 1 $(CHECKLIST_ITERATIONS)); do \
		N=$$(ls $(OUTPUT_DIR)/02b_CHECKLIST_PARTIAL_*.json 2>/dev/null | wc -l); \
		N=$$((N + 1)); \
		echo "⭐ Running 02b_checklistrem.md (iteration $$i/$(CHECKLIST_ITERATIONS), partial $$N)..."; \
		START_TIME=$$(date +%s); \
		claude $(CLAUDE_FLAGS) -p "$$(cat prompts/02b_checklistrem.md)" > $(LOG_DIR)/02b_checklistrem_$$N.json; \
		END_TIME=$$(date +%s); \
		DURATION=$$((END_TIME - START_TIME)); \
		INPUT_TOKENS=$$(grep -o '"input_tokens":[0-9]*' $(LOG_DIR)/02b_checklistrem_$$N.json | head -1 | cut -d: -f2); \
		OUTPUT_TOKENS=$$(grep -o '"output_tokens":[0-9]*' $(LOG_DIR)/02b_checklistrem_$$N.json | head -1 | cut -d: -f2); \
		COST=$$(grep -o '"total_cost_usd":[0-9.]*' $(LOG_DIR)/02b_checklistrem_$$N.json | head -1 | cut -d: -f2); \
		if [ -f "$(OUTPUT_DIR)/02b_CHECKLIST_PARTIAL_$$N.json" ]; then \
			echo "✅ Finished 02b_checklistrem.md iter $$i (Time: $${DURATION}s | Cost: \$$$$COST)"; \
		else \
			echo "⚠️  No new partial checklist generated in iteration $$i (Time: $${DURATION}s | Cost: \$$$$COST)"; \
		fi; \
	done
	@echo "✅ Completed all $(CHECKLIST_ITERATIONS) checklist iterations"

# Step 02c: Checklist Merge (Optional)
02c: $(OUTPUT_DIR)/02_CHECKLIST.json
$(OUTPUT_DIR)/02_CHECKLIST.json: prompts/02c_checklistmerge.md | 02a
	@echo "⭐ Running 02c_checklistmerge.md (Checklist Merge)..."; \
	START_TIME=$$(date +%s); \
	claude $(CLAUDE_FLAGS) -p "$$(cat prompts/02c_checklistmerge.md)" > $(LOG_DIR)/02c_checklistmerge.json; \
	END_TIME=$$(date +%s); \
	DURATION=$$((END_TIME - START_TIME)); \
	if [ -f "$(OUTPUT_DIR)/02_CHECKLIST.json" ]; then \
		INPUT_TOKENS=$$(grep -o '"input_tokens":[0-9]*' $(LOG_DIR)/02c_checklistmerge.json | head -1 | cut -d: -f2); \
		OUTPUT_TOKENS=$$(grep -o '"output_tokens":[0-9]*' $(LOG_DIR)/02c_checklistmerge.json | head -1 | cut -d: -f2); \
		COST=$$(grep -o '"total_cost_usd":[0-9.]*' $(LOG_DIR)/02c_checklistmerge.json | head -1 | cut -d: -f2); \
		echo "✅ Finished 02c_checklistmerge.md (Time: $${DURATION}s | Cost: \$$$$COST)"; \
	else \
		echo "❌ Error: 02_CHECKLIST.json not generated"; exit 1; \
	fi

# ------------------------------------------------------
# Audit Steps
# ------------------------------------------------------

# Step 03: Audit Map (Iterative)
03: | $(OUTPUT_DIR)/02a_CHECKLIST_BOUNDARIES.json
	@N=$$(ls $(OUTPUT_DIR)/03_AUDITMAP_PARTIAL_*.json 2>/dev/null | wc -l); \
	N=$$((N + 1)); \
	echo "⭐ Running 03_auditmap.md (iteration $$N)..."; \
	START_TIME=$$(date +%s); \
	cd $(WORKDIR) && claude $(CLAUDE_FLAGS) -p "$$(cat ../prompts/03_auditmap.md)" > ../$(LOG_DIR)/03_auditmap_$$N.json; \
	END_TIME=$$(date +%s); \
	DURATION=$$((END_TIME - START_TIME)); \
	INPUT_TOKENS=$$(grep -o '"input_tokens":[0-9]*' ../$(LOG_DIR)/03_auditmap_$$N.json | head -1 | cut -d: -f2); \
	OUTPUT_TOKENS=$$(grep -o '"output_tokens":[0-9]*' ../$(LOG_DIR)/03_auditmap_$$N.json | head -1 | cut -d: -f2); \
	COST=$$(grep -o '"total_cost_usd":[0-9.]*' ../$(LOG_DIR)/03_auditmap_$$N.json | head -1 | cut -d: -f2); \
	if [ -f "outputs/03_AUDITMAP_PARTIAL_$$N.json" ]; then \
		cp outputs/03_AUDITMAP_PARTIAL_$$N.json ../$(OUTPUT_DIR)/; \
		echo "✅ Finished 03_auditmap.md iter $$N (Time: $${DURATION}s | Cost: \$$$$COST)"; \
	else \
		echo "⚠️  No new partial auditmap generated in iteration $$N (Time: $${DURATION}s | Cost: \$$$$COST)"; \
	fi; \
	cp outputs/03_STATE.json ../$(OUTPUT_DIR)/ 2>/dev/null || true; \
	if [ -f "../$(OUTPUT_DIR)/03_STATE.json" ]; then \
		REMAINING=$$(grep -o '"remaining":[0-9]*' ../$(OUTPUT_DIR)/03_STATE.json | cut -d: -f2); \
		if [ "$$REMAINING" -gt 0 ] 2>/dev/null; then \
			echo "📋 $$REMAINING items remaining. Run 'make 03' again."; \
		else \
			echo "🎉 All items processed! Ready for 'make 04'."; \
		fi; \
	fi

# Step 04: Review (Iterative)
04: | init
	@if ! ls $(OUTPUT_DIR)/03_AUDITMAP_PARTIAL_*.json >/dev/null 2>&1; then \
		echo "❌ Error: No 03_AUDITMAP_PARTIAL_*.json files found. Run 'make 03' first."; exit 1; \
	fi; \
	N=$$(ls $(OUTPUT_DIR)/04_REVIEW_PARTIAL_*.json 2>/dev/null | wc -l); \
	N=$$((N + 1)); \
	echo "⭐ Running 04_review.md (iteration $$N)..."; \
	START_TIME=$$(date +%s); \
	cd $(WORKDIR) && claude $(CLAUDE_FLAGS) -p "$$(cat ../prompts/04_review.md)" > ../$(LOG_DIR)/04_review_$$N.json; \
	END_TIME=$$(date +%s); \
	DURATION=$$((END_TIME - START_TIME)); \
	INPUT_TOKENS=$$(grep -o '"input_tokens":[0-9]*' ../$(LOG_DIR)/04_review_$$N.json | head -1 | cut -d: -f2); \
	OUTPUT_TOKENS=$$(grep -o '"output_tokens":[0-9]*' ../$(LOG_DIR)/04_review_$$N.json | head -1 | cut -d: -f2); \
	COST=$$(grep -o '"total_cost_usd":[0-9.]*' ../$(LOG_DIR)/04_review_$$N.json | head -1 | cut -d: -f2); \
	if [ -f "outputs/04_REVIEW_PARTIAL_$$N.json" ]; then \
		cp outputs/04_REVIEW_PARTIAL_$$N.json ../$(OUTPUT_DIR)/; \
		echo "✅ Finished 04_review.md iter $$N (Time: $${DURATION}s | Cost: \$$$$COST)"; \
	else \
		echo "⚠️  No new partial review generated in iteration $$N (Time: $${DURATION}s | Cost: \$$$$COST)"; \
	fi; \
	cp outputs/04_STATE.json ../$(OUTPUT_DIR)/ 2>/dev/null || true; \
	if [ -f "../$(OUTPUT_DIR)/04_STATE.json" ]; then \
		REMAINING=$$(grep -o '"remaining":[0-9]*' ../$(OUTPUT_DIR)/04_STATE.json | cut -d: -f2); \
		if [ "$$REMAINING" -gt 0 ] 2>/dev/null; then \
			echo "📋 $$REMAINING items remaining. Run 'make 04' again."; \
		else \
			echo "🎉 All items reviewed! Audit complete."; \
		fi; \
	fi
