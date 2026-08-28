"""The lineups workflow wakes on a fixed backbone, whatever else fails.

The generated wake blocks depend on a weekly reschedule run and on GitHub
firing crons on time; on 28 August 2026 neither happened for the evening
game. A fixed every-two-hours cron through the football day, every day,
survives both: the watcher exits in under a minute when nothing kicks off
in the next six hours and sleeps until T-65 when something does."""

from pathlib import Path

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "lineups.yml"


def test_the_backbone_cron_is_present_and_outside_the_generated_block():
    text = WORKFLOW.read_text()
    backbone = '- cron: "5 6,8,10,12,14,16,18,20 * * *"'
    assert backbone in text
    generated = text.split("# BEGIN generated", 1)[1].split("# END generated", 1)[0]
    assert backbone not in generated, "the rescheduler would overwrite it"
