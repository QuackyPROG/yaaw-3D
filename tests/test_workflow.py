import tempfile
import unittest
from pathlib import Path

from yaaw3d.contracts import QAReport
from yaaw3d.orchestrator import (
    begin_build,
    create_plan,
    lock_brief,
    questions_for,
    record_answers,
    record_qa,
    resume_correction,
)
from yaaw3d.state_machine import can_execute_blender
from yaaw3d.storage import create_job, load_state


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

    def test_first_batch_is_exactly_ten(self) -> None:
        job = self.make_job()
        self.assertEqual(len(questions_for(job)), 10)

    def test_blender_gate_requires_locked_brief(self) -> None:
        job = self.make_job()
        self.assertFalse(can_execute_blender(load_state(job)))
        with self.assertRaises(ValueError):
            lock_brief(job)

    def test_lock_versions_brief_and_allows_planning(self) -> None:
        job = self.make_job()
        record_answers(job, ANSWERS)
        brief = lock_brief(job)
        state = load_state(job)
        self.assertEqual(brief.status, "locked")
        self.assertEqual(brief.version, 1)
        self.assertEqual(state.state, "BRIEF_LOCKED")
        self.assertEqual(state.brief_version, 1)
        self.assertTrue((job / "brief.v1.json").exists())

    def test_failed_critic_creates_correction_loop(self) -> None:
        job = self.make_job()
        record_answers(job, ANSWERS)
        lock_brief(job)
        create_plan(job, {"milestones": ["blockout", "lookdev", "qa"]})
        begin_build(job)
        record_qa(job, QAReport(domain="visual", passed=False, findings=["panel seams are too deep"]))
        state = load_state(job)
        self.assertEqual(state.state, "CORRECTION")
        self.assertEqual(state.iteration, 1)
        self.assertTrue((job / "corrections" / "iteration-1.json").exists())
        resume_correction(job)
        self.assertEqual(load_state(job).state, "BUILDING")

    def test_visual_and_technical_pass_unlock_export(self) -> None:
        job = self.make_job()
        record_answers(job, ANSWERS)
        lock_brief(job)
        create_plan(job, {"milestones": ["build"]})
        begin_build(job)
        record_qa(job, QAReport(domain="visual", passed=True, findings=[]))
        self.assertEqual(load_state(job).state, "VALIDATION")
        record_qa(job, QAReport(domain="technical", passed=True, findings=[]))
        self.assertEqual(load_state(job).state, "EXPORT")


if __name__ == "__main__":
    unittest.main()
