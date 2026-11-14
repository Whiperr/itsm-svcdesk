# ai-generated: 90% - boundary and property unit tests for slaclock.py specification (P-29)
from datetime import datetime, timedelta
import pytest
import slaclock


def test_constants():
    assert slaclock.OPENING == 480
    assert slaclock.CLOSING == 960
    assert slaclock.MAX_DAYS == 366
    assert slaclock.WARNING_PERCENT == 75
    assert slaclock.TARGETS == {
        "P1": (15, 240),
        "P2": (60, 480),
        "P3": (240, 1440),
        "P4": (480, 4320),
    }


def test_priority_of_all_cells_non_vip():
    # Sprawdzenie domyslnego vip=False oraz jawnego vip=False dla calej macierzy 3x3
    expected = {
        (1, 1): "P1",
        (1, 2): "P2",
        (2, 1): "P2",
        (1, 3): "P3",
        (2, 2): "P3",
        (3, 1): "P3",
        (2, 3): "P4",
        (3, 2): "P4",
        (3, 3): "P4",
    }
    for (imp, urg), prio in expected.items():
        assert slaclock.priority_of(imp, urg) == prio
        assert slaclock.priority_of(imp, urg, False) == prio


def test_priority_of_all_cells_vip():
    assert slaclock.priority_of(1, 1, True) == "P1"
    assert slaclock.priority_of(1, 2, True) == "P2"
    assert slaclock.priority_of(2, 1, True) == "P2"
    for imp, urg in [(1, 3), (2, 2), (3, 1), (2, 3), (3, 2), (3, 3)]:
        assert slaclock.priority_of(imp, urg, True) == "P2"


@pytest.mark.parametrize(
    "bad_val",
    [0, 4, -1, 2.0, 1.0, True, False, "1", "2", None, [1]],
)
def test_priority_of_invalid_inputs(bad_val):
    with pytest.raises(ValueError):
        slaclock.priority_of(bad_val, 2)
    with pytest.raises(ValueError):
        slaclock.priority_of(2, bad_val)


def test_targets_valid_and_invalid():
    assert slaclock.targets("P1") == (15, 240)
    assert slaclock.targets("P2") == (60, 480)
    assert slaclock.targets("P3") == (240, 1440)
    assert slaclock.targets("P4") == (480, 4320)

    for bad in ["p1", "p2", "p3", "p4", " P1", "P1 ", "P0", "P5", "", "1"]:
        with pytest.raises(ValueError):
            slaclock.targets(bad)


def test_sla_state_boundaries():
    # Docstring example: target=15 (75% = 11.25)
    assert slaclock.sla_state(0, 15) == "ok"
    assert slaclock.sla_state(11, 15) == "ok"
    assert slaclock.sla_state(12, 15) == "warning"
    assert slaclock.sla_state(15, 15) == "warning"
    assert slaclock.sla_state(16, 15) == "breached"

    # Dokladna granica 75% (elapsed * 100 == target * 75) oraz 100%
    assert slaclock.sla_state(0, 100) == "ok"
    assert slaclock.sla_state(74, 100) == "ok"
    assert slaclock.sla_state(75, 100) == "warning"
    assert slaclock.sla_state(99, 100) == "warning"
    assert slaclock.sla_state(100, 100) == "warning"
    assert slaclock.sla_state(101, 100) == "breached"

    # Male wartosci: target=4 (75% = 3.0), target=1
    assert slaclock.sla_state(2, 4) == "ok"
    assert slaclock.sla_state(3, 4) == "warning"
    assert slaclock.sla_state(4, 4) == "warning"
    assert slaclock.sla_state(5, 4) == "breached"
    assert slaclock.sla_state(0, 1) == "ok"
    assert slaclock.sla_state(1, 1) == "warning"
    assert slaclock.sla_state(2, 1) == "breached"


@pytest.mark.parametrize(
    "elapsed,target",
    [(-1, 15), (-5, 100), (0, 0), (1, 0), (0, -1), (10, -5), (-1, 0)],
)
def test_sla_state_invalid(elapsed, target):
    with pytest.raises(ValueError):
        slaclock.sla_state(elapsed, target)


def test_is_business_time_boundaries():
    # Poniedzialek (2026-05-04) do Piatku (2026-05-08)
    for day in range(4, 9):
        assert slaclock.is_business_time(datetime(2026, 5, day, 0, 0)) is False
        assert slaclock.is_business_time(datetime(2026, 5, day, 7, 59, 59, 999999)) is False
        assert slaclock.is_business_time(datetime(2026, 5, day, 8, 0, 0)) is True
        assert slaclock.is_business_time(datetime(2026, 5, day, 8, 1, 0)) is True
        assert slaclock.is_business_time(datetime(2026, 5, day, 12, 30, 45)) is True
        assert slaclock.is_business_time(datetime(2026, 5, day, 15, 59, 59, 999999)) is True
        assert slaclock.is_business_time(datetime(2026, 5, day, 16, 0, 0)) is False
        assert slaclock.is_business_time(datetime(2026, 5, day, 16, 1, 0)) is False
        assert slaclock.is_business_time(datetime(2026, 5, day, 23, 59, 0)) is False

    # Sobota (2026-05-09) i Niedziela (2026-05-10)
    for weekend_day in (9, 10):
        assert slaclock.is_business_time(datetime(2026, 5, weekend_day, 8, 0)) is False
        assert slaclock.is_business_time(datetime(2026, 5, weekend_day, 12, 0)) is False
        assert slaclock.is_business_time(datetime(2026, 5, weekend_day, 15, 59)) is False


def test_add_business_minutes_core_and_boundaries():
    with pytest.raises(ValueError):
        slaclock.add_business_minutes(datetime(2026, 5, 4, 9, 0), -1)

    # Ignorowanie sekund i mikrosekund oraz 0 minut w godzinach pracy
    assert slaclock.add_business_minutes(datetime(2026, 5, 4, 9, 15, 45, 999), 0) == datetime(2026, 5, 4, 9, 15)
    assert slaclock.add_business_minutes(datetime(2026, 5, 4, 8, 0, 30), 0) == datetime(2026, 5, 4, 8, 0)

    # 0 minut poza godzinami pracy przesuwa na najblizsze otwarcie 08:00
    assert slaclock.add_business_minutes(datetime(2026, 5, 4, 7, 59), 0) == datetime(2026, 5, 4, 8, 0)
    assert slaclock.add_business_minutes(datetime(2026, 5, 4, 16, 0), 0) == datetime(2026, 5, 5, 8, 0)
    assert slaclock.add_business_minutes(datetime(2026, 5, 4, 18, 30), 0) == datetime(2026, 5, 5, 8, 0)
    assert slaclock.add_business_minutes(datetime(2026, 5, 8, 16, 0), 0) == datetime(2026, 5, 11, 8, 0)
    assert slaclock.add_business_minutes(datetime(2026, 5, 9, 10, 0), 0) == datetime(2026, 5, 11, 8, 0)
    assert slaclock.add_business_minutes(datetime(2026, 5, 10, 10, 0), 0) == datetime(2026, 5, 11, 8, 0)

    # Koniec dokladnie o 16:00 zostaje w tym samym dniu o 16:00
    assert slaclock.add_business_minutes(datetime(2026, 5, 4, 8, 0), 480) == datetime(2026, 5, 4, 16, 0)
    assert slaclock.add_business_minutes(datetime(2026, 5, 4, 15, 0), 60) == datetime(2026, 5, 4, 16, 0)
    assert slaclock.add_business_minutes(datetime(2026, 5, 4, 15, 0), 61) == datetime(2026, 5, 5, 8, 1)
    assert slaclock.add_business_minutes(datetime(2026, 5, 4, 7, 0), 480) == datetime(2026, 5, 4, 16, 0)

    # Przejscie przez weekend (piatek -> poniedzialek)
    assert slaclock.add_business_minutes(datetime(2026, 5, 8, 15, 30), 30) == datetime(2026, 5, 8, 16, 0)
    assert slaclock.add_business_minutes(datetime(2026, 5, 8, 15, 30), 31) == datetime(2026, 5, 11, 8, 1)
    assert slaclock.add_business_minutes(datetime(2026, 5, 8, 16, 0), 15) == datetime(2026, 5, 11, 8, 15)

    # Granica MAX_DAYS = 366 dni kalendarzowych
    # Od 2026-05-04 (poniedzialek) do 2027-05-05 (sroda, +366 dni) jest dokladnie 262 dni roboczych
    start_max = datetime(2026, 5, 4, 8, 0)
    assert slaclock.add_business_minutes(start_max, 261 * 480 + 60) == datetime(2027, 5, 5, 9, 0)
    assert slaclock.add_business_minutes(start_max, 262 * 480) == datetime(2027, 5, 5, 16, 0)
    with pytest.raises(ValueError):
        slaclock.add_business_minutes(start_max, 262 * 480 + 1)


def test_business_minutes_between_boundaries():
    # Ignorowanie sekund i mikrosekund
    assert slaclock.business_minutes_between(
        datetime(2026, 5, 4, 9, 0, 59, 999),
        datetime(2026, 5, 4, 9, 0, 0, 0),
    ) == 0
    assert slaclock.business_minutes_between(
        datetime(2026, 5, 4, 9, 0, 59),
        datetime(2026, 5, 4, 9, 10, 1),
    ) == 10

    # end < start po obcieciu sekund rzuca ValueError
    with pytest.raises(ValueError):
        slaclock.business_minutes_between(
            datetime(2026, 5, 4, 9, 1, 0),
            datetime(2026, 5, 4, 9, 0, 59),
        )

    # Przedzialy poza godzinami pracy w dzien roboczy oraz w weekend
    assert slaclock.business_minutes_between(datetime(2026, 5, 4, 6, 0), datetime(2026, 5, 4, 7, 30)) == 0
    assert slaclock.business_minutes_between(datetime(2026, 5, 4, 7, 0), datetime(2026, 5, 4, 8, 0)) == 0
    assert slaclock.business_minutes_between(datetime(2026, 5, 4, 7, 0), datetime(2026, 5, 4, 8, 30)) == 30
    assert slaclock.business_minutes_between(datetime(2026, 5, 4, 8, 0), datetime(2026, 5, 4, 16, 0)) == 480
    assert slaclock.business_minutes_between(datetime(2026, 5, 4, 15, 30), datetime(2026, 5, 4, 17, 0)) == 30
    assert slaclock.business_minutes_between(datetime(2026, 5, 4, 16, 0), datetime(2026, 5, 4, 18, 0)) == 0
    assert slaclock.business_minutes_between(datetime(2026, 5, 4, 16, 30), datetime(2026, 5, 4, 17, 30)) == 0
    assert slaclock.business_minutes_between(datetime(2026, 5, 8, 15, 0), datetime(2026, 5, 11, 9, 0)) == 120
    assert slaclock.business_minutes_between(datetime(2026, 5, 9, 9, 0), datetime(2026, 5, 10, 15, 0)) == 0

    # Granica MAX_DAYS = 366 dni kalendarzowych
    start_max = datetime(2026, 5, 4, 8, 0)
    end_366 = datetime(2027, 5, 5, 16, 0)
    assert slaclock.business_minutes_between(start_max, end_366) == 262 * 480
    with pytest.raises(ValueError):
        slaclock.business_minutes_between(start_max, datetime(2027, 5, 6, 8, 0))

    # Wlasnosc odwrotnosci z docstringa
    for mins in (0, 1, 15, 60, 479, 480, 481, 1500):
        due = slaclock.add_business_minutes(datetime(2026, 5, 8, 14, 20), mins)
        assert slaclock.business_minutes_between(datetime(2026, 5, 8, 14, 20), due) == mins


def test_escalation_tier_full_matrix():
    for bad_prio in ("P0", "P5", "p1", " P1", ""):
        with pytest.raises(ValueError):
            slaclock.escalation_tier(bad_prio, False, 0)
    for prio in ("P1", "P2", "P3", "P4"):
        with pytest.raises(ValueError):
            slaclock.escalation_tier(prio, False, -1)

    # P1: start 1, breached +2 (1 + 1 extra), reopens>=2 +1, cap 3
    assert slaclock.escalation_tier("P1", False, 0) == 1
    assert slaclock.escalation_tier("P1", False, 1) == 1
    assert slaclock.escalation_tier("P1", False, 2) == 2
    assert slaclock.escalation_tier("P1", False, 5) == 2
    assert slaclock.escalation_tier("P1", True, 0) == 3
    assert slaclock.escalation_tier("P1", True, 1) == 3
    assert slaclock.escalation_tier("P1", True, 2) == 3

    # P2: start 1, breached +1, reopens>=2 +1, cap 3
    assert slaclock.escalation_tier("P2", False, 0) == 1
    assert slaclock.escalation_tier("P2", False, 1) == 1
    assert slaclock.escalation_tier("P2", False, 2) == 2
    assert slaclock.escalation_tier("P2", False, 4) == 2
    assert slaclock.escalation_tier("P2", True, 0) == 2
    assert slaclock.escalation_tier("P2", True, 1) == 2
    assert slaclock.escalation_tier("P2", True, 2) == 3
    assert slaclock.escalation_tier("P2", True, 5) == 3

    # P3 i P4: start 0, breached +1, reopens>=2 +1
    for prio in ("P3", "P4"):
        assert slaclock.escalation_tier(prio, False, 0) == 0
        assert slaclock.escalation_tier(prio, False, 1) == 0
        assert slaclock.escalation_tier(prio, False, 2) == 1
        assert slaclock.escalation_tier(prio, False, 3) == 1
        assert slaclock.escalation_tier(prio, True, 0) == 1
        assert slaclock.escalation_tier(prio, True, 1) == 1
        assert slaclock.escalation_tier(prio, True, 2) == 2
        assert slaclock.escalation_tier(prio, True, 10) == 2


def test_parse_duration_valid_and_invalid():
    assert slaclock.parse_duration("1m") == 1
    assert slaclock.parse_duration("59m") == 59
    assert slaclock.parse_duration("60m") == 60
    assert slaclock.parse_duration("90m") == 90
    assert slaclock.parse_duration("0h60m") == 60
    assert slaclock.parse_duration("0d60m") == 60
    assert slaclock.parse_duration("0d0h60m") == 60
    assert slaclock.parse_duration("0d0h90m") == 90
    assert slaclock.parse_duration("1h") == 60
    assert slaclock.parse_duration("4h") == 240
    assert slaclock.parse_duration("1h0m") == 60
    assert slaclock.parse_duration("1h30m") == 90
    assert slaclock.parse_duration("1h59m") == 119
    assert slaclock.parse_duration("0d1h59m") == 119
    assert slaclock.parse_duration("1d") == 1440
    assert slaclock.parse_duration("2d") == 2880
    assert slaclock.parse_duration("1d4h") == 1680
    assert slaclock.parse_duration("1d0h5m") == 1445
    assert slaclock.parse_duration("1d0h59m") == 1499
    assert slaclock.parse_duration("  1d4h30m \n\t ") == 1710

    invalid_inputs = [
        "",
        "   ",
        "0m",
        "0h",
        "0d",
        "0d0h0m",
        "1h60m",
        "1h61m",
        "1d60m",
        "1d0h60m",
        "0d1h60m",
        "2d3h60m",
        "1.5h",
        "30m1h",
        "1h2d",
        "10m2d",
        "-5m",
        "-1h",
        "-1d",
        "1h-5m",
        "1 h",
        "1d 4h",
        "90M",
        "1H",
        "2D",
        "1h2h",
        "1d2d",
        "5m10m",
        "abc",
        "15",
    ]
    for bad in invalid_inputs:
        with pytest.raises(ValueError):
            slaclock.parse_duration(bad)