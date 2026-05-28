from ba_monitor.providers import _recent_match_from_stb


def test_recent_match_falls_back_to_rating_delta_for_unknown_winner() -> None:
    match = _recent_match_from_stb(
        123,
        42,
        {
            "MapId": 12,
            "EndTime": 1772992500,
            "TotalPlayTimeInSec": 1800,
            "Data": {
                "42": {
                    "TeamId": 1,
                    "OldRating": 1500,
                    "NewRating": 1512.5,
                    "DestructionScore": 3000,
                    "LossesScore": 2000,
                }
            },
        },
    )

    assert match.result == "win"
