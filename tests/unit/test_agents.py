"""Tests for the agent layer — gated bridge, tools, packing, analyze flow."""

import json

import pytest

from hw4.services.agents.context import compact_history, pack
from hw4.services.agents.crew import analyze_flow
from hw4.services.agents.llm_bridge import GatedCrewLLM
from hw4.services.agents.payloads import AnalysisRequest, IterationVerdict
from hw4.services.agents.roles import ROLE_DEFINITIONS, make_agent
from hw4.services.agents.tools import assert_serializable, read_artifact, run_detectors

from .test_llm_client import response
from .test_operations import MINI_REPO, make_sdk


class TestGatedBridge:
    def test_bridge_demands_the_gated_client(self):
        """T303: no LlmClient (hence no gatekeeper) -> no agent LLM. Period."""
        with pytest.raises(TypeError, match="gated"):
            GatedCrewLLM(object(), role="analyst")

    def test_calls_flow_through_ledger_with_role_tag(self, tmp_path):
        sdk, transport = make_sdk(tmp_path)
        transport.script.append(response(text="narrative"))
        bridge = GatedCrewLLM(sdk.llm, role="analyst")
        assert bridge.call("hello") == "narrative"
        assert sdk.ledger.entries()[-1].purpose_tag == "agent.analyst"

    def test_message_list_normalized(self, tmp_path):
        sdk, transport = make_sdk(tmp_path)
        transport.script.append(response(text="ok"))
        bridge = GatedCrewLLM(sdk.llm, role="qa")
        bridge.call([{"role": "user", "content": "ping"}])
        assert transport.calls[-1]["messages"] == [{"role": "user", "content": "ping"}]


class TestRolesAndPayloads:
    def test_all_four_roles_build_agents(self, tmp_path):
        sdk, _ = make_sdk(tmp_path)
        for name in ROLE_DEFINITIONS:
            agent = make_agent(name, sdk.llm)
            assert agent.role == ROLE_DEFINITIONS[name]["role"]

    def test_payloads_round_trip(self):
        request = AnalysisRequest(repo_path="ws/target", iteration=2)
        assert AnalysisRequest.from_json(request.to_json()) == request
        verdict = IterationVerdict(verdict="improved", tests_green=True, stop=True,
                                   reason="GOAL_METRIC_REACHED")
        assert IterationVerdict.from_json(verdict.to_json()) == verdict


class TestTools:
    def test_run_detectors_is_serializable_delegate(self, tmp_path):
        sdk, _ = make_sdk(tmp_path)
        result = assert_serializable(run_detectors(sdk))
        assert result["count"] == len(json.loads(
            (tmp_path / "results" / "findings.json").read_text())["findings"])

    def test_read_artifact_is_path_jailed(self, tmp_path):
        sdk, _ = make_sdk(tmp_path)
        with pytest.raises(PermissionError):
            read_artifact(sdk, "../config/setup.json")


class TestContextPacking:
    RULES = "RULE-1: cite evidence class. RULE-2: never delete on similarity."

    def test_pack_order_rules_first_task_last(self):
        text = pack(self.RULES, "payload-middle", "the task")
        assert text.startswith(self.RULES)
        assert text.rstrip().endswith("the task")

    def test_compaction_halves_tokens_and_keeps_rules_verbatim(self, tmp_path):
        sdk, transport = make_sdk(tmp_path)
        transport.script.append(response(text="- F-001 fixed, tests green"))
        history = [f"iteration {i}: long chatter about nothing in particular, "
                   f"repeated context, tool output dumps..." * 5 for i in range(6)]
        compacted, stats = compact_history(sdk.llm, self.RULES, history)
        assert stats["reduction"] >= 0.5  # T300
        assert self.RULES in compacted  # rules survive verbatim
        assert sdk.ledger.entries()[-1].purpose_tag == "compact"


class TestAnalyzeFlow:
    def test_findings_match_direct_sdk_path(self, tmp_path):
        """T302: agent path and direct path produce identical findings."""
        sdk, _ = make_sdk(tmp_path)
        direct_ids = [f.id for f in sdk.analyze()]
        result = analyze_flow(sdk, AnalysisRequest(repo_path=str(MINI_REPO)))
        agent_ids = [
            f["id"] for f in json.loads(
                (tmp_path / "results" / "findings.json").read_text())["findings"]
        ]
        assert agent_ids == direct_ids
        assert result["findings_count"] == len(direct_ids)
        assert result["narrative_path"]
        tags = {e.purpose_tag for e in sdk.ledger.entries()}
        assert "agent.analyst" in tags  # T306

    def test_budget_firewall_halts_gracefully(self, tmp_path):
        """T304: deterministic spine completes; LLM narrative halts cleanly."""
        sdk, _ = make_sdk(tmp_path)
        sdk.ledger.record(purpose_tag="prime", model="model-cheap",
                          input_tokens=10_000_000, output_tokens=0, latency_ms=0)
        result = analyze_flow(sdk, AnalysisRequest(repo_path=str(MINI_REPO)))
        assert result["halted"].startswith("budget firewall")
        assert result["findings_count"] > 0  # detectors ran anyway (no LLM)
        assert result["trace"][-1]["result"]["written"] == 0


class TestSkillWiring:
    def test_analyst_prompt_carries_skill_procedure(self, tmp_path):
        """T398: the SKILL procedure rides into every narrative prompt."""
        import shutil

        sdk, transport = make_sdk(tmp_path)
        (tmp_path / "docs").mkdir()
        repo_root = MINI_REPO.parents[2]
        shutil.copyfile(repo_root / "docs" / "SKILL.md", tmp_path / "docs" / "SKILL.md")
        analyze_flow(sdk, AnalysisRequest(repo_path=str(MINI_REPO), narrative_top_n=1))
        prompt = transport.calls[-1]["messages"][0]["content"]
        assert "Read `index.md` first" in prompt
        assert prompt.startswith("Rules (non-negotiable)")
