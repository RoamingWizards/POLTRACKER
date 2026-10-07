"""Matching must be exact enough to trust: every uncertain case stays unmatched and is explained."""

import pytest

from poltracker.politician_match import match_politician
from poltracker.providers.politicians import OfficialMember


def member(bio, first, last, chamber="house", middle=None, state="TX", suffix=None, **kw):
    return OfficialMember(bio, first, last, chamber, middle_name=middle, suffix=suffix, state=state, full_name=f"{first} {last}", **kw)


ROSTER = [
    member("D000399", "Lloyd", "Doggett"),
    member("T000001", "David", "Taylor", middle="J.", state="OH"),
    member("G000591", "Michael", "Guest", state="MS"),
    member("C001120", "Daniel", "Crenshaw"),
    member("W000779", "Ron", "Wyden", chamber="senate", state="OR"),
    member("J000299", "Mike", "Johnson", state="LA"),
    member("J000999", "Mike", "Johnson", state="OH"),
    member("K000001", "John", "Kennedy", chamber="senate", middle="Neely", state="LA"),
    member("O000001", "Pat", "O'Halleran", state="AZ"),
    member("N000001", "José", "Núñez", state="CA"),
    member("S000001", "Pat", "Smith Jones", suffix="Jr.", state="TX"),
]


def run(name, chamber="house", state=None, roster=ROSTER):
    return match_politician(name, chamber, state, roster)


def test_an_exact_name_in_the_right_chamber_matches():
    r = run("Lloyd Doggett")
    assert (r.status, r.member.bioguide_id, r.rule) == ("matched", "D000399", "exact_name+chamber")


def test_case_honorifics_and_suffixes_do_not_matter():
    assert run("Mr. LLOYD doggett").member.bioguide_id == "D000399"
    assert run("Pat Smith Jones").member.bioguide_id == "S000001"
    assert run("Pat Smith Jones Jr.").member.bioguide_id == "S000001"


def test_accents_and_punctuation_are_folded():
    assert run("Pat OHalleran").member.bioguide_id == "O000001"
    assert run("Jose Nunez").member.bioguide_id == "N000001"


def test_a_middle_initial_on_either_side_is_ignored():
    assert run("David J. Taylor").member.bioguide_id == "T000001"
    assert run("David Taylor").member.bioguide_id == "T000001"  # initial only in the official record
    assert run("David J Taylor").member.bioguide_id == "T000001"


def test_a_conflicting_middle_initial_is_not_matched():
    r = run("David Q. Taylor")
    assert r.status == "unmatched" and r.member is None


def test_a_full_middle_name_must_agree_with_the_official_one():
    assert run("John Neely Kennedy", "senate").member.bioguide_id == "K000001"
    assert run("John Kennedy", "senate").member.bioguide_id == "K000001"
    assert run("John Wrong Kennedy", "senate").status == "unmatched"


def test_extra_middle_names_match_only_when_first_and_last_agree_and_it_is_unique():
    r = run("Michael Patrick Guest")
    assert (r.status, r.member.bioguide_id, r.rule) == ("matched", "G000591", "name_with_extra_middle+chamber")


def test_nicknames_are_never_guessed_but_the_surname_is_reported():
    r = run("Dan Crenshaw")  # official first name is Daniel
    assert r.status == "unmatched" and r.member is None
    assert "Daniel Crenshaw" in r.note and "C001120" in r.note  # a hint for a human; nothing assigned


def test_the_chamber_must_match():
    r = run("Ron Wyden", "house")
    assert r.status == "unmatched"
    assert run("Ron Wyden", "senate").member.bioguide_id == "W000779"


def test_two_officials_with_one_name_are_ambiguous_and_nothing_is_chosen():
    r = run("Mike Johnson")
    assert r.status == "ambiguous" and r.member is None
    assert {m.bioguide_id for m in r.candidates} == {"J000299", "J000999"}
    assert "J000299" in r.note and "J000999" in r.note


def test_a_known_state_resolves_the_tie_and_a_wrong_state_rules_out_the_match():
    assert run("Mike Johnson", state="OH").member.bioguide_id == "J000999"
    assert run("Mike Johnson", state="LA").rule.endswith("+state")
    assert run("Mike Johnson", state="TX").status == "unmatched"


def test_an_unknown_name_is_unmatched_with_a_plain_reason():
    r = run("Nobody Atall")
    assert r.status == "unmatched" and r.note.startswith("no official member")


def test_an_empty_roster_matches_nothing():
    assert run("Lloyd Doggett", roster=[]).status == "unmatched"
