import tempfile
import unittest
from pathlib import Path

from yaaw3d.contracts import ExportReport, QAReport
from yaaw3d.orchestrator import (
    begin_build,
    create_plan,
    gate_status,
    lock_brief,
    questions_for,
    record_answers,
    record_export,
    record_qa,
    resume_correction,
    revise_brief,
)
from yaaw3d.storage import create_job, load_state, read_json, write_json


ANSWERS = {
    "purpose": {"choice": "A"},
    "quality": {"choice": "B"},
    "style": {"choice": "A"},
    "geometry": {"choice": "B"},
    "topology": {"choice": "B"},
    "physical_accuracy": {"choice": "B"},
    "materials": {"choice": "B"},
    "animation": {"choice": "A"},
    "presentation": {"choice": "A"},
    "delivery": {"choice": "A"},
}


class WorkflowTests(unittest.TestCase):
    def make_job(self) -> Path:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        return create_job(Path(self.temp.name), "Create a soccer ball")

    def answer_and_lock(self, job: Path):
        record_answers(job, ANSWERS)
        return lock_brief(job)

    def test_first_batch_is_exactly_ten(self) -> None:
        job = self.make_job()
        batch = questions_for(job)
        self.assertEqual(len(batch), 10)
        self.assertTrue(all(len(q["choices"]) == 3 for q in batch))
        self.assertTrue(all("custom" in q for q in batch))

    def test_blender_gate_requires_locked_brief(self) -> None:
        job = self.make_job()
        gate = gate_status(job)
        self.assertFalse(gate["can_execute_blender"])
        self.assertIn("state INTAKE is not a Blender execution state", gate["reasons"])
        with self.assertRaises(ValueError):
            lock_brief(job)

    def test_lock_reuses_current_draft_and_is_idempotent(self) -> None:
        job = self.make_job()
        record_answers(job, ANSWERS)
        from yaaw3d.orchestrator import compile_brief
        draft = compile_brief(job)
        self.assertEqual(draft.version, 1)
        locked = lock_brief(job)
        self.assertEqual(locked.status, "locked")
        self.assertEqual(locked.version, 1)
        self.assertEqual(load_state(job).state, "BRIEF_LOCKED")
        self.assertEqual(len(list(job.glob("brief.v*.json"))), 1)
        self.assertEqual(lock_brief(job).version, 1)
        self.assertEqual(len(list(job.glob("brief.v*.json"))), 1)

    def test_post_lock_answer_is_blocked_and_current_brief_stays_locked(self) -> None:
        job = self.make_job()
        locked = self.answer_and_lock(job)
        with self.assertRaisesRegex(ValueError, "immutable after brief lock"):
            record_answers(job, {"style": {"choice": "B"}})
        current = read_json(job / "brief.current.json")
        self.assertEqual(current["status"], "locked")
        self.assertEqual(current["version"], locked.version)
        self.assertEqual(current["requirements"]["style"], "Photorealistic")

    def test_revise_brief_invalidates_downstream_and_preserves_locked_version(self) -> None:
        job = self.make_job()
        self.answer_and_lock(job)
        create_plan(job, {"milestones": [{"id": "blockout"}]})
        begin_build(job)
        draft = revise_brief(job, {"style": {"choice": "B"}})
        state = load_state(job)
        self.assertEqual(state.state, "INTAKE")
        self.assertEqual(state.plan_version, 0)
        self.assertFalse(state.critic_pass)
        self.assertFalse(state.validator_pass)
        self.assertEqual(draft.status, "draft")
        self.assertEqual(draft.version, 2)
        self.assertEqual(draft.requirements["style"], "Stylized")
        self.assertEqual(read_json(job / "brief.v1.json")["status"], "locked")

    def test_gate_detects_tampered_current_brief(self) -> None:
        job = self.make_job()
        self.answer_and_lock(job)
        create_plan(job, {"milestones": [{"id": "blockout"}]})
        current = read_json(job / "brief.current.json")
        current["status"] = "draft"
        write_json(job / "brief.current.json", current)
        with self.assertRaisesRegex(ValueError, "current brief is not locked"):
            begin_build(job)

    def test_failed_critic_creates_artifact_scoped_correction_loop(self) -> None:
        job = self.make_job()
        self.answer_and_lock(job)
        create_plan(job, {"milestones": [{"id": "blockout"}]})
        begin_build(job)
        record_qa(job, QAReport(domain="visual", passed=False, findings=["panel seams are too deep"], artifact_id="asset-v1"))
        state = load_state(job)
        self.assertEqual(state.state, "CORRECTION")
        self.assertEqual(state.iteration, 1)
        ticket = read_json(job / "corrections" / "iteration-1.json")
        self.assertEqual(ticket["artifact_id"], "asset-v1")
        resume_correction(job)
        self.assertEqual(load_state(job).state, "BUILDING")

    def test_visual_and_technical_pass_unlock_export_then_complete(self) -> None:
        job = self.make_job()
        self.answer_and_lock(job)
        create_plan(job, {"milestones": [{"id": "build"}]})
        begin_build(job)
        self.assertTrue(gate_status(job)["can_execute_blender"])
        record_qa(job, QAReport(domain="visual", passed=True, findings=[], artifact_id="asset-v1"))
        self.assertEqual(load_state(job).state, "VALIDATION")
        record_qa(job, QAReport(domain="technical", passed=True, findings=[], artifact_id="asset-v1"))
        self.assertEqual(load_state(job).state, "EXPORT")
        record_export(job, ExportReport(artifact_id="asset-v1", passed=True, files=["exports/asset-v1.blend"], evidence=["metadata checked"]))
        self.assertEqual(load_state(job).state, "COMPLETE")

    def test_followups_are_conditional_and_clear_when_answered(self) -> None:
        job = self.make_job()
        game_answers = dict(ANSWERS)
        game_answers["purpose"] = {"choice": "B"}
        game_answers["delivery"] = {"choice": "B"}
        record_answers(job, game_answers)
        self.assertEqual({q["id"] for q in questions_for(job)}, {"scale", "uv", "lod", "naming"})
        with self.assertRaises(ValueError):
            lock_brief(job)
        record_answers(job, {"scale": {"choice": "B"}, "uv": {"choice": "B"}, "lod": {"choice": "B"}, "naming": {"choice": "B"}})
        self.assertEqual(questions_for(job), [])
        self.assertEqual(lock_brief(job).status, "locked")


if __name__ == "__main__":
    unittest.main()
