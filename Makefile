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

# Max iteration counts (safety limit)
MAX_ITERATIONS ?= 100

# Parallel execution configuration
WORKERS ?= 4

.PHONY: all preparation audit init init-prep \
        01a 01b 01b-loop 01b-parallel 01c 01d 01e \
        02a 02b 02b-loop 02b-parallel 02c 02s \
        03 03-loop 03-parallel 04 04-loop 04-parallel \
        clean help

# Default target: run full pipeline
all: preparation audit

# Phase targets
# preparation: 01a → 01b (Nx) → 01c → 01d → 01e → 02s → 02a → 02b (Nx)
preparation: 02b-loop
	@echo "🎉 Preparation phase completed! Check $(OUTPUT_DIR)/"

audit: 04-loop
	@echo "🎉 Audit phase completed! Check $(OUTPUT_DIR)/04_REVIEW_PARTIAL_*.json"

# ------------------------------------------------------
# Utilities
# ------------------------------------------------------

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Phase Targets:"
	@echo "  all                  - Run full pipeline (preparation + audit)"
	@echo "  all-parallel         - Run full pipeline with parallel workers"
	@echo "  preparation          - Run preparation phase (sequential)"
	@echo "  preparation-parallel - Run preparation phase with parallel workers"
	@echo "  audit                - Run audit phase (sequential)"
	@echo "  audit-parallel       - Run audit phase with parallel workers"
	@echo ""
	@echo "Specification Steps (01a-01e):"
	@echo "  init-prep    - Setup output directories (no git repo required)"
	@echo "  01a          - Discovery & Queuing (01a_crawl.md → 01a_STATE.json)"
	@echo "  01b          - Extraction (01b_extract.md) - Single run"
	@echo "  01b-loop     - Extraction (01b_extract.md) - Sequential loop"
	@echo "  01b-parallel - Extraction with parallel workers"
	@echo "  01c          - Integration (01c_integrate.md → 01_SPEC.json)"
	@echo "  01d          - Trust Model (01d_trustmodel.md → 01d_TRUSTMODEL.json)"
	@echo "  01e          - Properties (01e_prop.md → 01e_PROP.json)"
	@echo ""
	@echo "Checklist Steps (02a-02s):"
	@echo "  02a          - Checklist Boundaries (02a_checklist.md)"
	@echo "  02b          - Checklist Remaining (02b_checklistrem.md) - Single run"
	@echo "  02b-loop     - Checklist Remaining - Sequential loop"
	@echo "  02b-parallel - Checklist Remaining with parallel workers"
	@echo "  02c          - Checklist Merge (02c_checklistmerge.md) [OPTIONAL]"
	@echo "  02s          - Review & Validate (02s_review.md)"
	@echo ""
	@echo "Audit Steps:"
	@echo "  init         - Setup directories and check target workspace"
	@echo "  03           - Static Audit Map (03_auditmap.md) - Single run"
	@echo "  03-loop      - Static Audit Map - Sequential loop"
	@echo "  03-parallel  - Static Audit Map with parallel workers"
	@echo "  04           - Audit Review (04_review.md) - Single run"
	@echo "  04-loop      - Audit Review - Sequential loop"
	@echo "  04-parallel  - Audit Review with parallel workers"
	@echo ""
	@echo "Utilities:"
	@echo "  clean  - Remove generated outputs"
	@echo ""
	@echo "Configuration Variables:"
	@echo "  MAX_ITERATIONS - Safety limit for loop iterations (default: 100)"
	@echo "  WORKERS        - Number of parallel workers (default: 4)"
	@echo ""
	@echo "Examples:"
	@echo "  make preparation MAX_ITERATIONS=50"
	@echo "  make 01b-parallel WORKERS=8"
	@echo "  make all-parallel WORKERS=4 MAX_ITERATIONS=100"

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
01a:
	@mkdir -p $(LOG_DIR) $(OUTPUT_DIR)
	@if [ -f "$(OUTPUT_DIR)/01a_STATE.json" ]; then \
		echo "⏭️  Skipping 01a: $(OUTPUT_DIR)/01a_STATE.json already exists"; \
	else \
		echo "⭐ Running 01a_crawl.md (Discovery & Queuing)..."; \
		START_TIME=$$(date +%s); \
		claude $(CLAUDE_FLAGS) -p "$$(cat prompts/01a_crawl.md) KEYWORDS=$(KEYWORDS) SPEC_URLS=$(SPEC_URLS)" > $(LOG_DIR)/01a_crawl.json; \
		END_TIME=$$(date +%s); \
		DURATION=$$((END_TIME - START_TIME)); \
		if [ -f "$(OUTPUT_DIR)/01a_STATE.json" ]; then \
			COST=$$(grep -o '"total_cost_usd":[0-9.]*' $(LOG_DIR)/01a_crawl.json | head -1 | cut -d: -f2); \
			QUEUE_SIZE=$$(grep -o '"work_queue":\[[^]]*\]' $(OUTPUT_DIR)/01a_STATE.json | tr ',' '\n' | wc -l); \
			echo "✅ Finished 01a_crawl.md (Time: $${DURATION}s | URLs queued: ~$$QUEUE_SIZE | Cost: \$$$$COST)"; \
		else \
			echo "❌ Error: 01a_STATE.json not generated"; exit 1; \
		fi; \
	fi

# Step 01b: Extraction (Single run)
01b:
	@if [ ! -f "$(OUTPUT_DIR)/01a_STATE.json" ]; then \
		echo "❌ Error: $(OUTPUT_DIR)/01a_STATE.json not found. Run 01a first."; exit 1; \
	fi
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

# Step 01b-loop: Extraction (run until work_queue is empty)
# Skip if: 01_SPEC.json exists
01b-loop:
	@if [ ! -f "$(OUTPUT_DIR)/01a_STATE.json" ]; then \
		echo "❌ Error: $(OUTPUT_DIR)/01a_STATE.json not found. Run 01a first."; exit 1; \
	fi
	@if [ -f "$(OUTPUT_DIR)/01_SPEC.json" ]; then \
		echo "⏭️  Skipping 01b-loop: 01_SPEC.json exists"; exit 0; \
	fi
	@echo "🔄 Running 01b_extract.md until work_queue is empty..."
	@i=0; \
	while [ $$i -lt $(MAX_ITERATIONS) ]; do \
		REMAINING=$$(python3 -c "import json; d=json.load(open('$(OUTPUT_DIR)/01a_STATE.json')); print(len(d.get('work_queue', [])))" 2>/dev/null || echo "0"); \
		if [ "$$REMAINING" -eq 0 ] 2>/dev/null; then \
			echo "🎉 Work queue empty. Extraction complete."; \
			break; \
		fi; \
		echo "📋 $$REMAINING URLs remaining in work_queue"; \
		i=$$((i + 1)); \
		echo "⭐ Running 01b_extract.md (iteration $$i)..."; \
		START_TIME=$$(date +%s); \
		claude $(CLAUDE_FLAGS) -p "$$(cat prompts/01b_extract.md)" > $(LOG_DIR)/01b_extract_$$i.json; \
		END_TIME=$$(date +%s); \
		DURATION=$$((END_TIME - START_TIME)); \
		COST=$$(grep -o '"total_cost_usd":[0-9.]*' $(LOG_DIR)/01b_extract_$$i.json | head -1 | cut -d: -f2); \
		echo "✅ Finished 01b_extract.md iter $$i (Time: $${DURATION}s | Cost: \$$$$COST)"; \
	done
	@SUBGRAPH_COUNT=$$(ls $(OUTPUT_DIR)/01b_SUBGRAPHS/*.json 2>/dev/null | wc -l); \
	echo "✅ Extraction complete. Total subgraphs: $$SUBGRAPH_COUNT"

# Step 01b-parallel: Parallel extraction using multiple workers
# Skip if: 01_SPEC.json exists
01b-parallel:
	@if [ ! -f "$(OUTPUT_DIR)/01a_STATE.json" ]; then \
		echo "❌ Error: $(OUTPUT_DIR)/01a_STATE.json not found. Run 01a first."; exit 1; \
	fi
	@if [ -f "$(OUTPUT_DIR)/01_SPEC.json" ]; then \
		echo "⏭️  Skipping 01b-parallel: 01_SPEC.json exists"; exit 0; \
	fi
	@echo "🚀 Running 01b_extract.md in parallel with $(WORKERS) workers..."
	@python3 scripts/run_parallel.py --phase 01b --workers $(WORKERS) --max-iterations $(MAX_ITERATIONS)
	@SUBGRAPH_COUNT=$$(ls $(OUTPUT_DIR)/01b_SUBGRAPHS/*.json 2>/dev/null | wc -l); \
	echo "✅ Parallel extraction complete. Total subgraphs: $$SUBGRAPH_COUNT"

# Step 01c: Integration
01c:
	@if [ -f "$(OUTPUT_DIR)/01_SPEC.json" ]; then \
		echo "⏭️  Skipping 01c: $(OUTPUT_DIR)/01_SPEC.json already exists"; \
	else \
		if [ ! -d "$(OUTPUT_DIR)/01b_SUBGRAPHS" ] || [ -z "$$(ls $(OUTPUT_DIR)/01b_SUBGRAPHS/*.json 2>/dev/null)" ]; then \
			echo "❌ Error: No subgraphs found in $(OUTPUT_DIR)/01b_SUBGRAPHS/. Run 01b-loop or 01b-parallel first."; exit 1; \
		fi; \
		echo "⭐ Running 01c_integrate.md (Integration)..."; \
		START_TIME=$$(date +%s); \
		claude $(CLAUDE_FLAGS) -p "$$(cat prompts/01c_integrate.md)" > $(LOG_DIR)/01c_integrate.json; \
		END_TIME=$$(date +%s); \
		DURATION=$$((END_TIME - START_TIME)); \
		if [ -f "$(OUTPUT_DIR)/01_SPEC.json" ]; then \
			COST=$$(grep -o '"total_cost_usd":[0-9.]*' $(LOG_DIR)/01c_integrate.json | head -1 | cut -d: -f2); \
			echo "✅ Finished 01c_integrate.md (Time: $${DURATION}s | Cost: \$$$$COST)"; \
		else \
			echo "❌ Error: 01_SPEC.json not generated"; exit 1; \
		fi; \
	fi

# Step 01d: Trust Model
01d:
	@if [ -f "$(OUTPUT_DIR)/01d_TRUSTMODEL.json" ]; then \
		echo "⏭️  Skipping 01d: $(OUTPUT_DIR)/01d_TRUSTMODEL.json already exists"; \
	else \
		if [ ! -f "$(OUTPUT_DIR)/01_SPEC.json" ]; then \
			echo "❌ Error: $(OUTPUT_DIR)/01_SPEC.json not found. Run 01c first."; exit 1; \
		fi; \
		echo "⭐ Running 01d_trustmodel.md (Trust Model)..."; \
		START_TIME=$$(date +%s); \
		claude $(CLAUDE_FLAGS) -p "$$(cat prompts/01d_trustmodel.md)" > $(LOG_DIR)/01d_trustmodel.json; \
		END_TIME=$$(date +%s); \
		DURATION=$$((END_TIME - START_TIME)); \
		if [ -f "$(OUTPUT_DIR)/01d_TRUSTMODEL.json" ]; then \
			COST=$$(grep -o '"total_cost_usd":[0-9.]*' $(LOG_DIR)/01d_trustmodel.json | head -1 | cut -d: -f2); \
			echo "✅ Finished 01d_trustmodel.md (Time: $${DURATION}s | Cost: \$$$$COST)"; \
		else \
			echo "❌ Error: 01d_TRUSTMODEL.json not generated"; exit 1; \
		fi; \
	fi

# Step 01e: Properties
01e:
	@if [ -f "$(OUTPUT_DIR)/01e_PROP.json" ]; then \
		echo "⏭️  Skipping 01e: $(OUTPUT_DIR)/01e_PROP.json already exists"; \
	else \
		if [ ! -f "$(OUTPUT_DIR)/01d_TRUSTMODEL.json" ]; then \
			echo "❌ Error: $(OUTPUT_DIR)/01d_TRUSTMODEL.json not found. Run 01d first."; exit 1; \
		fi; \
		echo "⭐ Running 01e_prop.md (Properties)..."; \
		START_TIME=$$(date +%s); \
		claude $(CLAUDE_FLAGS) -p "$$(cat prompts/01e_prop.md)" > $(LOG_DIR)/01e_prop.json; \
		END_TIME=$$(date +%s); \
		DURATION=$$((END_TIME - START_TIME)); \
		if [ -f "$(OUTPUT_DIR)/01e_PROP.json" ]; then \
			COST=$$(grep -o '"total_cost_usd":[0-9.]*' $(LOG_DIR)/01e_prop.json | head -1 | cut -d: -f2); \
			echo "✅ Finished 01e_prop.md (Time: $${DURATION}s | Cost: \$$$$COST)"; \
		else \
			echo "❌ Error: 01e_PROP.json not generated"; exit 1; \
		fi; \
	fi

# ------------------------------------------------------
# Checklist Steps (02a - 02s)
# ------------------------------------------------------

# Step 02s: Review & Validate Preparation Outputs
02s:
	@if [ -f "$(OUTPUT_DIR)/02s_REVIEW_REPORT.json" ]; then \
		echo "⏭️  Skipping 02s: $(OUTPUT_DIR)/02s_REVIEW_REPORT.json already exists"; \
	else \
		if [ ! -f "$(OUTPUT_DIR)/01e_PROP.json" ]; then \
			echo "❌ Error: $(OUTPUT_DIR)/01e_PROP.json not found. Run 01e first."; exit 1; \
		fi; \
		echo "⭐ Running 02s_review.md (Preparation Review)..."; \
		START_TIME=$$(date +%s); \
		claude $(CLAUDE_FLAGS) -p "$$(cat prompts/02s_review.md)" > $(LOG_DIR)/02s_review.json; \
		END_TIME=$$(date +%s); \
		DURATION=$$((END_TIME - START_TIME)); \
		COST=$$(grep -o '"total_cost_usd":[0-9.]*' $(LOG_DIR)/02s_review.json | head -1 | cut -d: -f2); \
		if [ -f "$(OUTPUT_DIR)/02s_REVIEW_REPORT.json" ]; then \
			echo "✅ Finished 02s_review.md (Time: $${DURATION}s | Cost: \$$$$COST)"; \
			VERDICT=$$(grep -o '"overall_verdict":"[^"]*"' $(OUTPUT_DIR)/02s_REVIEW_REPORT.json | cut -d'"' -f4); \
			ISSUES=$$(grep -o '"total_issues":[0-9]*' $(OUTPUT_DIR)/02s_REVIEW_REPORT.json | cut -d: -f2); \
			echo "📊 Review: $$VERDICT ($$ISSUES issues)"; \
		else \
			echo "⚠️  Review report not generated (Time: $${DURATION}s | Cost: \$$$$COST)"; \
		fi; \
	fi

# Step 02a: Checklist Boundaries
02a:
	@if [ -f "$(OUTPUT_DIR)/02a_CHECKLIST_BOUNDARIES.json" ]; then \
		echo "⏭️  Skipping 02a: $(OUTPUT_DIR)/02a_CHECKLIST_BOUNDARIES.json already exists"; \
	else \
		if [ ! -f "$(OUTPUT_DIR)/02s_REVIEW_REPORT.json" ]; then \
			echo "❌ Error: $(OUTPUT_DIR)/02s_REVIEW_REPORT.json not found. Run 02s first."; exit 1; \
		fi; \
		echo "⭐ Running 02a_checklist.md (Checklist Boundaries)..."; \
		START_TIME=$$(date +%s); \
		claude $(CLAUDE_FLAGS) -p "$$(cat prompts/02a_checklist.md)" > $(LOG_DIR)/02a_checklist.json; \
		END_TIME=$$(date +%s); \
		DURATION=$$((END_TIME - START_TIME)); \
		if [ -f "$(OUTPUT_DIR)/02a_CHECKLIST_BOUNDARIES.json" ]; then \
			COST=$$(grep -o '"total_cost_usd":[0-9.]*' $(LOG_DIR)/02a_checklist.json | head -1 | cut -d: -f2); \
			echo "✅ Finished 02a_checklist.md (Time: $${DURATION}s | Cost: \$$$$COST)"; \
		else \
			echo "❌ Error: 02a_CHECKLIST_BOUNDARIES.json not generated"; exit 1; \
		fi; \
	fi

# Step 02b: Checklist Remaining (Single run)
02b:
	@if [ ! -f "$(OUTPUT_DIR)/02a_CHECKLIST_BOUNDARIES.json" ]; then \
		echo "❌ Error: $(OUTPUT_DIR)/02a_CHECKLIST_BOUNDARIES.json not found. Run 02a first."; exit 1; \
	fi
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

# Step 02b-loop: Checklist Remaining (run until unprocessed_property_ids is empty)
# Skip if: 03_AUDITMAP_PARTIAL_*.json exists
02b-loop:
	@if [ ! -f "$(OUTPUT_DIR)/02a_CHECKLIST_BOUNDARIES.json" ]; then \
		echo "❌ Error: $(OUTPUT_DIR)/02a_CHECKLIST_BOUNDARIES.json not found. Run 02a first."; exit 1; \
	fi
	@if ls $(OUTPUT_DIR)/03_AUDITMAP_PARTIAL_*.json >/dev/null 2>&1; then \
		echo "⏭️  Skipping 02b-loop: 03_AUDITMAP_PARTIAL_*.json exists"; exit 0; \
	fi
	@echo "🔄 Running 02b_checklistrem.md until all properties are processed..."
	@i=0; \
	while [ $$i -lt $(MAX_ITERATIONS) ]; do \
		if [ -f "$(OUTPUT_DIR)/02b_STATE.json" ]; then \
			REMAINING=$$(python3 -c "import json; d=json.load(open('$(OUTPUT_DIR)/02b_STATE.json')); print(len(d.get('unprocessed_property_ids', [])))" 2>/dev/null || echo "0"); \
			if [ "$$REMAINING" -eq 0 ] 2>/dev/null; then \
				echo "🎉 All properties processed!"; \
				break; \
			fi; \
			echo "📋 $$REMAINING properties remaining"; \
		fi; \
		i=$$((i + 1)); \
		N=$$(ls $(OUTPUT_DIR)/02b_CHECKLIST_PARTIAL_*.json 2>/dev/null | wc -l); \
		N=$$((N + 1)); \
		echo "⭐ Running 02b_checklistrem.md (iteration $$i, partial $$N)..."; \
		START_TIME=$$(date +%s); \
		claude $(CLAUDE_FLAGS) -p "$$(cat prompts/02b_checklistrem.md)" > $(LOG_DIR)/02b_checklistrem_$$N.json; \
		END_TIME=$$(date +%s); \
		DURATION=$$((END_TIME - START_TIME)); \
		COST=$$(grep -o '"total_cost_usd":[0-9.]*' $(LOG_DIR)/02b_checklistrem_$$N.json | head -1 | cut -d: -f2); \
		if [ -f "$(OUTPUT_DIR)/02b_CHECKLIST_PARTIAL_$$N.json" ]; then \
			echo "✅ Finished 02b_checklistrem.md iter $$i (Time: $${DURATION}s | Cost: \$$$$COST)"; \
		else \
			echo "⚠️  No new partial checklist generated in iteration $$i (Time: $${DURATION}s | Cost: \$$$$COST)"; \
		fi; \
	done
	@echo "✅ Checklist generation complete"

# Step 02b-parallel: Parallel checklist generation using multiple workers
# Skip if: 03_AUDITMAP_PARTIAL_*.json exists
02b-parallel:
	@if [ ! -f "$(OUTPUT_DIR)/02a_CHECKLIST_BOUNDARIES.json" ]; then \
		echo "❌ Error: $(OUTPUT_DIR)/02a_CHECKLIST_BOUNDARIES.json not found. Run 02a first."; exit 1; \
	fi
	@if ls $(OUTPUT_DIR)/03_AUDITMAP_PARTIAL_*.json >/dev/null 2>&1; then \
		echo "⏭️  Skipping 02b-parallel: 03_AUDITMAP_PARTIAL_*.json exists"; exit 0; \
	fi
	@echo "🚀 Running 02b_checklistrem.md in parallel with $(WORKERS) workers..."
	@python3 scripts/run_parallel.py --phase 02b --workers $(WORKERS) --max-iterations $(MAX_ITERATIONS)
	@echo "✅ Parallel checklist generation complete"

# Step 02c: Checklist Merge (Optional)
02c:
	@if [ -f "$(OUTPUT_DIR)/02_CHECKLIST.json" ]; then \
		echo "⏭️  Skipping 02c: $(OUTPUT_DIR)/02_CHECKLIST.json already exists"; \
	else \
		if [ ! -f "$(OUTPUT_DIR)/02a_CHECKLIST_BOUNDARIES.json" ]; then \
			echo "❌ Error: $(OUTPUT_DIR)/02a_CHECKLIST_BOUNDARIES.json not found. Run 02a first."; exit 1; \
		fi; \
		echo "⭐ Running 02c_checklistmerge.md (Checklist Merge)..."; \
		START_TIME=$$(date +%s); \
		claude $(CLAUDE_FLAGS) -p "$$(cat prompts/02c_checklistmerge.md)" > $(LOG_DIR)/02c_checklistmerge.json; \
		END_TIME=$$(date +%s); \
		DURATION=$$((END_TIME - START_TIME)); \
		if [ -f "$(OUTPUT_DIR)/02_CHECKLIST.json" ]; then \
			COST=$$(grep -o '"total_cost_usd":[0-9.]*' $(LOG_DIR)/02c_checklistmerge.json | head -1 | cut -d: -f2); \
			echo "✅ Finished 02c_checklistmerge.md (Time: $${DURATION}s | Cost: \$$$$COST)"; \
		else \
			echo "❌ Error: 02_CHECKLIST.json not generated"; exit 1; \
		fi; \
	fi

# ------------------------------------------------------
# Audit Steps
# ------------------------------------------------------

# Step 03: Audit Map (Single run)
03:
	@if [ ! -f "$(OUTPUT_DIR)/02a_CHECKLIST_BOUNDARIES.json" ]; then \
		echo "❌ Error: $(OUTPUT_DIR)/02a_CHECKLIST_BOUNDARIES.json not found. Run 02a first."; exit 1; \
	fi
	@N=$$(ls $(OUTPUT_DIR)/03_AUDITMAP_PARTIAL_*.json 2>/dev/null | wc -l); \
	N=$$((N + 1)); \
	echo "⭐ Running 03_auditmap.md (iteration $$N)..."; \
	START_TIME=$$(date +%s); \
	cd $(WORKDIR) && claude $(CLAUDE_FLAGS) -p "$$(cat ../prompts/03_auditmap.md)" > ../$(LOG_DIR)/03_auditmap_$$N.json; \
	END_TIME=$$(date +%s); \
	DURATION=$$((END_TIME - START_TIME)); \
	COST=$$(grep -o '"total_cost_usd":[0-9.]*' ../$(LOG_DIR)/03_auditmap_$$N.json | head -1 | cut -d: -f2); \
	if [ -f "outputs/03_AUDITMAP_PARTIAL_$$N.json" ]; then \
		cp outputs/03_AUDITMAP_PARTIAL_$$N.json ../$(OUTPUT_DIR)/; \
		echo "✅ Finished 03_auditmap.md iter $$N (Time: $${DURATION}s | Cost: \$$$$COST)"; \
	else \
		echo "⚠️  No new partial auditmap generated in iteration $$N (Time: $${DURATION}s | Cost: \$$$$COST)"; \
	fi; \
	cp outputs/03_STATE.json ../$(OUTPUT_DIR)/ 2>/dev/null || true; \
	if [ -f "../$(OUTPUT_DIR)/03_STATE.json" ]; then \
		REMAINING=$$(python3 -c "import json; d=json.load(open('../$(OUTPUT_DIR)/03_STATE.json')); print(len(d.get('unprocessed_checklist_ids', [])))" 2>/dev/null || echo "0"); \
		if [ "$$REMAINING" -gt 0 ] 2>/dev/null; then \
			echo "📋 $$REMAINING items remaining. Run 'make 03' again or use 'make 03-loop'."; \
		else \
			echo "🎉 All items processed! Ready for 'make 04'."; \
		fi; \
	fi

# Step 03-loop: Audit Map (run until unprocessed_checklist_ids is empty)
# Skip if: 04_REVIEW_PARTIAL_*.json exists
03-loop:
	@if [ ! -f "$(OUTPUT_DIR)/02a_CHECKLIST_BOUNDARIES.json" ]; then \
		echo "❌ Error: $(OUTPUT_DIR)/02a_CHECKLIST_BOUNDARIES.json not found. Run 02a first."; exit 1; \
	fi
	@if [ ! -d "$(WORKDIR)/.git" ]; then \
		echo "❌ Error: $(WORKDIR) is not a git repo. Please clone target repo first."; exit 1; \
	fi
	@if ls $(OUTPUT_DIR)/04_REVIEW_PARTIAL_*.json >/dev/null 2>&1; then \
		echo "⏭️  Skipping 03-loop: 04_REVIEW_PARTIAL_*.json exists"; exit 0; \
	fi
	@echo "🔄 Running 03_auditmap.md until all checklist items are processed..."
	@i=0; \
	while [ $$i -lt $(MAX_ITERATIONS) ]; do \
		if [ -f "$(OUTPUT_DIR)/03_STATE.json" ]; then \
			REMAINING=$$(python3 -c "import json; d=json.load(open('$(OUTPUT_DIR)/03_STATE.json')); print(len(d.get('unprocessed_checklist_ids', [])))" 2>/dev/null || echo "0"); \
			if [ "$$REMAINING" -eq 0 ] 2>/dev/null; then \
				echo "🎉 All checklist items processed!"; \
				break; \
			fi; \
			echo "📋 $$REMAINING checklist items remaining"; \
		fi; \
		i=$$((i + 1)); \
		N=$$(ls $(OUTPUT_DIR)/03_AUDITMAP_PARTIAL_*.json 2>/dev/null | wc -l); \
		N=$$((N + 1)); \
		echo "⭐ Running 03_auditmap.md (iteration $$i, partial $$N)..."; \
		START_TIME=$$(date +%s); \
		cd $(WORKDIR) && claude $(CLAUDE_FLAGS) -p "$$(cat ../prompts/03_auditmap.md)" > ../$(LOG_DIR)/03_auditmap_$$N.json; \
		END_TIME=$$(date +%s); \
		DURATION=$$((END_TIME - START_TIME)); \
		COST=$$(grep -o '"total_cost_usd":[0-9.]*' ../$(LOG_DIR)/03_auditmap_$$N.json | head -1 | cut -d: -f2); \
		if [ -f "outputs/03_AUDITMAP_PARTIAL_$$N.json" ]; then \
			cp outputs/03_AUDITMAP_PARTIAL_$$N.json ../$(OUTPUT_DIR)/; \
			echo "✅ Finished 03_auditmap.md iter $$i (Time: $${DURATION}s | Cost: \$$$$COST)"; \
		else \
			echo "⚠️  No new partial auditmap generated in iteration $$i (Time: $${DURATION}s | Cost: \$$$$COST)"; \
		fi; \
		cp outputs/03_STATE.json ../$(OUTPUT_DIR)/ 2>/dev/null || true; \
	done
	@echo "✅ Audit map generation complete"

# Step 03-parallel: Parallel audit map using multiple workers
# Skip if: 04_REVIEW_PARTIAL_*.json exists
03-parallel:
	@if [ ! -f "$(OUTPUT_DIR)/02a_CHECKLIST_BOUNDARIES.json" ]; then \
		echo "❌ Error: $(OUTPUT_DIR)/02a_CHECKLIST_BOUNDARIES.json not found. Run 02a first."; exit 1; \
	fi
	@if [ ! -d "$(WORKDIR)/.git" ]; then \
		echo "❌ Error: $(WORKDIR) is not a git repo. Please clone target repo first."; exit 1; \
	fi
	@if ls $(OUTPUT_DIR)/04_REVIEW_PARTIAL_*.json >/dev/null 2>&1; then \
		echo "⏭️  Skipping 03-parallel: 04_REVIEW_PARTIAL_*.json exists"; exit 0; \
	fi
	@echo "🚀 Running 03_auditmap.md in parallel with $(WORKERS) workers..."
	@python3 scripts/run_parallel.py --phase 03 --workers $(WORKERS) --max-iterations $(MAX_ITERATIONS)
	@echo "✅ Parallel audit map generation complete"

# Step 04: Review (Single run)
04:
	@if [ ! -d "$(WORKDIR)/.git" ]; then \
		echo "❌ Error: $(WORKDIR) is not a git repo. Please clone target repo first."; exit 1; \
	fi
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
	COST=$$(grep -o '"total_cost_usd":[0-9.]*' ../$(LOG_DIR)/04_review_$$N.json | head -1 | cut -d: -f2); \
	if [ -f "outputs/04_REVIEW_PARTIAL_$$N.json" ]; then \
		cp outputs/04_REVIEW_PARTIAL_$$N.json ../$(OUTPUT_DIR)/; \
		echo "✅ Finished 04_review.md iter $$N (Time: $${DURATION}s | Cost: \$$$$COST)"; \
	else \
		echo "⚠️  No new partial review generated in iteration $$N (Time: $${DURATION}s | Cost: \$$$$COST)"; \
	fi; \
	cp outputs/04_STATE.json ../$(OUTPUT_DIR)/ 2>/dev/null || true; \
	if [ -f "../$(OUTPUT_DIR)/04_STATE.json" ]; then \
		REMAINING=$$(python3 -c "import json; d=json.load(open('../$(OUTPUT_DIR)/04_STATE.json')); print(len(d.get('unprocessed_audit_items', [])))" 2>/dev/null || echo "0"); \
		if [ "$$REMAINING" -gt 0 ] 2>/dev/null; then \
			echo "📋 $$REMAINING items remaining. Run 'make 04' again or use 'make 04-loop'."; \
		else \
			echo "🎉 All items reviewed! Audit complete."; \
		fi; \
	fi

# Step 04-loop: Review (run until unprocessed_audit_items is empty)
04-loop:
	@if [ ! -d "$(WORKDIR)/.git" ]; then \
		echo "❌ Error: $(WORKDIR) is not a git repo. Please clone target repo first."; exit 1; \
	fi
	@if ! ls $(OUTPUT_DIR)/03_AUDITMAP_PARTIAL_*.json >/dev/null 2>&1; then \
		echo "❌ Error: No 03_AUDITMAP_PARTIAL_*.json files found. Run 03-loop or 03-parallel first."; exit 1; \
	fi
	@if [ -f "$(OUTPUT_DIR)/04_STATE.json" ]; then \
		REMAINING=$$(python3 -c "import json; d=json.load(open('$(OUTPUT_DIR)/04_STATE.json')); print(len(d.get('unprocessed_audit_items', [])))" 2>/dev/null || echo "0"); \
		if [ "$$REMAINING" -eq 0 ] 2>/dev/null; then \
			PARTIAL_COUNT=$$(ls $(OUTPUT_DIR)/04_REVIEW_PARTIAL_*.json 2>/dev/null | wc -l); \
			echo "⏭️  Skipping 04-loop: all audit items reviewed ($$PARTIAL_COUNT partial files exist)"; \
			exit 0; \
		fi; \
	fi
	@echo "🔄 Running 04_review.md until all audit items are reviewed..."
	@i=0; \
	while [ $$i -lt $(MAX_ITERATIONS) ]; do \
		if [ -f "$(OUTPUT_DIR)/04_STATE.json" ]; then \
			REMAINING=$$(python3 -c "import json; d=json.load(open('$(OUTPUT_DIR)/04_STATE.json')); print(len(d.get('unprocessed_audit_items', [])))" 2>/dev/null || echo "0"); \
			if [ "$$REMAINING" -eq 0 ] 2>/dev/null; then \
				echo "🎉 All audit items reviewed!"; \
				break; \
			fi; \
			echo "📋 $$REMAINING audit items remaining"; \
		fi; \
		i=$$((i + 1)); \
		N=$$(ls $(OUTPUT_DIR)/04_REVIEW_PARTIAL_*.json 2>/dev/null | wc -l); \
		N=$$((N + 1)); \
		echo "⭐ Running 04_review.md (iteration $$i, partial $$N)..."; \
		START_TIME=$$(date +%s); \
		cd $(WORKDIR) && claude $(CLAUDE_FLAGS) -p "$$(cat ../prompts/04_review.md)" > ../$(LOG_DIR)/04_review_$$N.json; \
		END_TIME=$$(date +%s); \
		DURATION=$$((END_TIME - START_TIME)); \
		COST=$$(grep -o '"total_cost_usd":[0-9.]*' ../$(LOG_DIR)/04_review_$$N.json | head -1 | cut -d: -f2); \
		if [ -f "outputs/04_REVIEW_PARTIAL_$$N.json" ]; then \
			cp outputs/04_REVIEW_PARTIAL_$$N.json ../$(OUTPUT_DIR)/; \
			echo "✅ Finished 04_review.md iter $$i (Time: $${DURATION}s | Cost: \$$$$COST)"; \
		else \
			echo "⚠️  No new partial review generated in iteration $$i (Time: $${DURATION}s | Cost: \$$$$COST)"; \
		fi; \
		cp outputs/04_STATE.json ../$(OUTPUT_DIR)/ 2>/dev/null || true; \
	done
	@echo "✅ Audit review complete"

# Step 04-parallel: Parallel audit review using multiple workers
04-parallel:
	@if [ ! -d "$(WORKDIR)/.git" ]; then \
		echo "❌ Error: $(WORKDIR) is not a git repo. Please clone target repo first."; exit 1; \
	fi
	@if ! ls $(OUTPUT_DIR)/03_AUDITMAP_PARTIAL_*.json >/dev/null 2>&1; then \
		echo "❌ Error: No 03_AUDITMAP_PARTIAL_*.json files found. Run 03-loop or 03-parallel first."; exit 1; \
	fi
	@if [ -f "$(OUTPUT_DIR)/04_STATE.json" ]; then \
		REMAINING=$$(python3 -c "import json; d=json.load(open('$(OUTPUT_DIR)/04_STATE.json')); print(len(d.get('unprocessed_audit_items', [])))" 2>/dev/null || echo "0"); \
		if [ "$$REMAINING" -eq 0 ] 2>/dev/null; then \
			PARTIAL_COUNT=$$(ls $(OUTPUT_DIR)/04_REVIEW_PARTIAL_*.json 2>/dev/null | wc -l); \
			echo "⏭️  Skipping 04-parallel: all audit items reviewed ($$PARTIAL_COUNT partial files exist)"; \
			exit 0; \
		fi; \
	fi
	@echo "🚀 Running 04_review.md in parallel with $(WORKERS) workers..."
	@python3 scripts/run_parallel.py --phase 04 --workers $(WORKERS) --max-iterations $(MAX_ITERATIONS)
	@echo "✅ Parallel audit review complete"

# ------------------------------------------------------
# Full Parallel Pipeline
# ------------------------------------------------------

# Parallel preparation phase
preparation-parallel: 02b-parallel
	@echo "🎉 Parallel preparation phase completed! Check $(OUTPUT_DIR)/"

# Parallel audit phase
audit-parallel: 04-parallel
	@echo "🎉 Parallel audit phase completed! Check $(OUTPUT_DIR)/"

# Full parallel pipeline
all-parallel: preparation-parallel audit-parallel
	@echo "🎉 Full parallel pipeline completed!"
