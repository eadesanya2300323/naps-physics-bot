from app.services.versioning import MaterialVersion, status_label, version_plan


def test_first_upload_starts_at_version_one():
    plan = version_plan([])
    assert plan.version == 1
    assert plan.supersede_ids == ()


def test_same_material_bumps_and_supersedes_the_current_row():
    plan = version_plan([MaterialVersion(11, 2, True), MaterialVersion(4, 1, False)])
    assert plan.version == 3
    assert plan.supersede_ids == (11,)


def test_history_only_still_bumps_the_highest_version():
    plan = version_plan([MaterialVersion(7, 4, False)])
    assert plan.version == 5
    assert plan.supersede_ids == ()


def test_status_labels():
    assert status_label(True) == "Current"
    assert status_label(False) == "Outdated"
