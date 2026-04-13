"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

from .recommender import load_songs, recommend_songs


# ---------------------------------------------------------------------------
# User Profiles
# Each profile is a dictionary of taste preferences used by score_song().
#
# Critique: a single profile captures one point in feature space. Because
# genre and mood are categorical (exact match only), a user who likes
# "indie pop" gets zero genre credit for any "pop" song — even though the
# two genres share the same energy and valence range. This profile design
# can differentiate "intense rock" from "chill lofi" cleanly (opposite ends
# of the energy + mood axes), but it can miss adjacent genres that a real
# listener would enjoy. A richer design would allow genre families or
# partial-match weights.
# ---------------------------------------------------------------------------

USER_PROFILES = {
    "pop_happy": {
        "genre": "pop",
        "mood": "happy",
        "energy": 0.8,
        "likes_acoustic": False,
    },
    "lofi_chill": {
        "genre": "lofi",
        "mood": "chill",
        "energy": 0.4,
        "likes_acoustic": True,
    },
    "metal_angry": {
        "genre": "metal",
        "mood": "angry",
        "energy": 0.95,
        "likes_acoustic": False,
    },
    "jazz_relaxed": {
        "genre": "jazz",
        "mood": "relaxed",
        "energy": 0.38,
        "likes_acoustic": True,
    },
}


# ---------------------------------------------------------------------------
# Adversarial / Edge-Case Profiles (Phase 4 stress test)
#
# These profiles are intentionally designed to expose weaknesses:
#   1. conflicting_sad_high_energy — "sad" mood is not in the 18-song catalog;
#      high energy contradicts the emotional intent. Tests cold-start for moods.
#   2. unknown_genre_reggae — "reggae" is not in the catalog at all.
#      Tests cold-start for genres; system must fall back to energy + acousticness.
#   3. contradictory_metal_acoustic — metal songs have acousticness ≈ 0.04,
#      but this user says likes_acoustic=True. Tests internal preference conflict.
#   4. extreme_low_energy — energy target 0.05 (near silence) with a mood
#      ("peaceful") not in the catalog. Tests the energy formula at extremes.
# ---------------------------------------------------------------------------

ADVERSARIAL_PROFILES = {
    "conflicting_sad_high_energy": {
        "genre": "rock",
        "mood": "sad",        # "sad" is not a mood in the 18-song catalog
        "energy": 0.9,        # high energy contradicts a sad mood intent
        "likes_acoustic": False,
    },
    "unknown_genre_reggae": {
        "genre": "reggae",    # not in catalog — pure cold-start scenario
        "mood": "chill",
        "energy": 0.55,
        "likes_acoustic": True,
    },
    "contradictory_metal_acoustic": {
        "genre": "metal",
        "mood": "angry",
        "energy": 0.97,
        "likes_acoustic": True,  # Shattered Glass (only metal) has acousticness 0.04
    },
    "extreme_low_energy": {
        "genre": "ambient",
        "mood": "peaceful",   # "peaceful" is not in the catalog
        "energy": 0.05,       # near-silence preference
        "likes_acoustic": True,
    },
}


def print_recommendations(label: str, user_prefs: dict, songs: list, k: int = 5) -> None:
    print(f"\n{'=' * 55}")
    print(f"  Profile: {label}")
    print(f"  Preferences: genre={user_prefs['genre']}, "
          f"mood={user_prefs['mood']}, energy={user_prefs['energy']}")
    print(f"{'=' * 55}")
    recommendations = recommend_songs(user_prefs, songs, k=k)
    if not recommendations:
        print("  No recommendations returned.")
        return
    for rank, rec in enumerate(recommendations, start=1):
        song, score, explanation = rec
        print(f"  {rank}. {song['title']} ({song['genre']} / {song['mood']}) — Score: {score:.2f}")
        print(f"     Because: {explanation}")
    print()


def main() -> None:
    songs = load_songs("data/songs.csv")

    print("\n" + "#" * 55)
    print("  STANDARD PROFILES")
    print("#" * 55)
    for label, prefs in USER_PROFILES.items():
        print_recommendations(label, prefs, songs, k=5)

    print("\n" + "#" * 55)
    print("  ADVERSARIAL / EDGE-CASE PROFILES")
    print("#" * 55)
    for label, prefs in ADVERSARIAL_PROFILES.items():
        print_recommendations(label, prefs, songs, k=5)


if __name__ == "__main__":
    main()
