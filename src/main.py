"""
Command line runner for the Music Recommender Simulation.
Demonstrates all four Optional Extension Challenges.
"""

from .recommender import (
    load_songs,
    recommend_songs,
    recommend_with_diversity,
    SCORING_MODES,
    ScoringWeights,
)

# ---------------------------------------------------------------------------
# Standard user profiles
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
# ---------------------------------------------------------------------------

ADVERSARIAL_PROFILES = {
    "conflicting_sad_high_energy": {
        "genre": "rock",
        "mood": "sad",        # "sad" is not a mood in the 18-song catalog
        "energy": 0.9,
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
        "likes_acoustic": True,  # metal songs are never acoustic
    },
    "extreme_low_energy": {
        "genre": "ambient",
        "mood": "peaceful",   # not in catalog
        "energy": 0.05,
        "likes_acoustic": True,
    },
}

# ---------------------------------------------------------------------------
# Challenge 1 — Profiles that use the new advanced features
# ---------------------------------------------------------------------------

ADVANCED_PROFILES = {
    # Wants nostalgic songs from the 2010s with specific mood tags
    "nostalgic_2010s": {
        "genre": "folk",
        "mood": "melancholic",
        "energy": 0.35,
        "likes_acoustic": True,
        "preferred_decade": 2010,
        "preferred_tags": ["nostalgic", "wistful", "melancholic"],
        "min_popularity": 0,
        "likes_instrumental": False,
    },
    # Wants popular, euphoric tracks — mainstream party mode
    "mainstream_euphoric": {
        "genre": "edm",
        "mood": "euphoric",
        "energy": 0.95,
        "likes_acoustic": False,
        "preferred_decade": 2020,
        "preferred_tags": ["euphoric", "energetic", "electric"],
        "min_popularity": 70,
        "likes_instrumental": False,
    },
    # Wants instrumental study music — no vocals, acoustic texture
    "instrumental_focus": {
        "genre": "classical",
        "mood": "peaceful",
        "energy": 0.25,
        "likes_acoustic": True,
        "preferred_decade": 2000,
        "preferred_tags": ["contemplative", "serene", "focused"],
        "min_popularity": 0,
        "likes_instrumental": True,
    },
}


# ---------------------------------------------------------------------------
# Challenge 4 — ASCII Table Formatter
# ---------------------------------------------------------------------------

def _truncate(text: str, width: int) -> str:
    """Truncate text to width, appending '…' if cut."""
    return text if len(text) <= width else text[: width - 1] + "…"


def format_table(
    recommendations: list,
    label: str = "",
    mode: str = "balanced",
    diversity: bool = False,
) -> str:
    """Render recommendations as a fixed-width ASCII table.

    Columns: rank | title | genre/mood | pop | score | top reason
    Falls back gracefully if tabulate is not installed.
    """
    # Try tabulate first for prettier output
    try:
        from tabulate import tabulate

        rows = []
        for rank, (song, score, explanation) in enumerate(recommendations, 1):
            top_reason = explanation.split(" | ")[0]
            rows.append([
                rank,
                _truncate(song.get("title", ""), 22),
                f"{song.get('genre', '')} / {song.get('mood', '')}",
                song.get("popularity", "—"),
                f"{score:.2f}",
                _truncate(top_reason, 38),
            ])
        headers = ["#", "Title", "Genre / Mood", "Pop", "Score", "Top Reason"]
        tag = f"  Mode: [{mode.upper()}]{'  |  Diversity ON' if diversity else ''}"
        if label:
            tag = f"  Profile: {label}  |  {tag.strip()}"
        return tag + "\n" + tabulate(rows, headers=headers, tablefmt="rounded_outline")

    except ImportError:
        pass

    # Manual ASCII fallback
    C = [4, 23, 20, 5, 7, 40]  # column widths
    divider = "+" + "+".join("-" * (c + 2) for c in C) + "+"
    def row_line(cells):
        parts = []
        for cell, width in zip(cells, C):
            parts.append(f" {_truncate(str(cell), width):<{width}} ")
        return "|" + "|".join(parts) + "|"

    lines = []
    tag = f"Mode: [{mode.upper()}]{'  |  Diversity ON' if diversity else ''}"
    if label:
        tag = f"Profile: {label}  |  {tag}"
    lines.append(f"\n  {tag}")
    lines.append(divider)
    lines.append(row_line(["#", "Title", "Genre / Mood", "Pop", "Score", "Top Reason"]))
    lines.append(divider)
    for rank, (song, score, explanation) in enumerate(recommendations, 1):
        top_reason = explanation.split(" | ")[0]
        gm = f"{song.get('genre', '')} / {song.get('mood', '')}"
        lines.append(row_line([
            rank,
            song.get("title", ""),
            gm,
            song.get("popularity", "—"),
            f"{score:.2f}",
            top_reason,
        ]))
    lines.append(divider)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helper printer
# ---------------------------------------------------------------------------

def print_recommendations(
    label: str,
    user_prefs: dict,
    songs: list,
    k: int = 5,
    mode: str = "balanced",
    diversity: bool = False,
) -> None:
    """Score and display top-k recommendations for a profile."""
    weights = SCORING_MODES.get(mode, ScoringWeights())
    if diversity:
        results = recommend_with_diversity(user_prefs, songs, k=k, weights=weights)
    else:
        results = recommend_songs(user_prefs, songs, k=k, weights=weights)

    print(format_table(results, label=label, mode=mode, diversity=diversity))
    print()


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> None:
    songs = load_songs("data/songs.csv")

    # ── Standard profiles ────────────────────────────────────────────────────
    print("\n" + "█" * 58)
    print("  STANDARD PROFILES  (balanced mode)")
    print("█" * 58)
    for label, prefs in USER_PROFILES.items():
        print_recommendations(label, prefs, songs)

    # ── Challenge 1: Advanced Features ───────────────────────────────────────
    print("\n" + "█" * 58)
    print("  CHALLENGE 1 — ADVANCED FEATURES")
    print("  (popularity, decade, mood tags, instrumentalness)")
    print("█" * 58)
    for label, prefs in ADVANCED_PROFILES.items():
        print_recommendations(label, prefs, songs)

    # ── Challenge 2: Scoring Modes ────────────────────────────────────────────
    print("\n" + "█" * 58)
    print("  CHALLENGE 2 — SCORING MODES  (pop_happy profile)")
    print("█" * 58)
    for mode in SCORING_MODES:
        print_recommendations("pop_happy", USER_PROFILES["pop_happy"], songs, mode=mode)

    # ── Challenge 3: Diversity ────────────────────────────────────────────────
    print("\n" + "█" * 58)
    print("  CHALLENGE 3 — DIVERSITY PENALTY")
    print("  max 2 songs per genre, max 1 song per artist")
    print("█" * 58)
    for label, prefs in USER_PROFILES.items():
        print_recommendations(label, prefs, songs, diversity=True)

    # ── Adversarial profiles ──────────────────────────────────────────────────
    print("\n" + "█" * 58)
    print("  ADVERSARIAL / EDGE-CASE PROFILES")
    print("█" * 58)
    for label, prefs in ADVERSARIAL_PROFILES.items():
        print_recommendations(label, prefs, songs)


if __name__ == "__main__":
    main()
