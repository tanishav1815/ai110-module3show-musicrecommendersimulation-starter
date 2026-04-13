"""
Music Recommender — hybrid content-based + collaborative-style filtering.

Algorithm design inspired by how Spotify and YouTube Music work:
  - Content-Based Filtering : scores each song against audio features
    (genre, mood, energy, valence, danceability, acousticness) — the same
    feature space Spotify exposes via its audio-features API.
  - Collaborative-Style Signals : saved tracks boost a song's score;
    skipped tracks suppress it — mirroring how platforms weight intentional
    actions (saves, skips) far more heavily than passive streams.
  - Hybrid blend : content score + behavioral adjustment = final rank.
"""

import csv
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class Song:
    """
    Represents a song and its Spotify-style audio attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float        # 0–1  perceptual intensity
    tempo_bpm: float
    valence: float       # 0–1  musical positivity (happy ↑, sad ↓)
    danceability: float  # 0–1  rhythm + beat strength
    acousticness: float  # 0–1  acoustic vs. electronic


@dataclass
class UserProfile:
    """
    Represents a user's taste preferences plus behavioral history.
    Required by tests/test_recommender.py

    saved_song_ids  — deliberate saves (strong positive signal, like Spotify "heart")
    skipped_song_ids — early skips (strong negative signal)
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool
    saved_song_ids: List[int] = field(default_factory=list)
    skipped_song_ids: List[int] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Functional API  (used by src/main.py)
# ---------------------------------------------------------------------------

def load_songs(csv_path: str) -> List[Dict]:
    """Read a CSV catalog via csv.DictReader and return a list of dicts with numeric fields cast to float/int."""
    songs: List[Dict] = []
    try:
        with open(csv_path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                row["id"] = int(row["id"])
                row["energy"] = float(row["energy"])
                row["tempo_bpm"] = float(row["tempo_bpm"])
                row["valence"] = float(row["valence"])
                row["danceability"] = float(row["danceability"])
                row["acousticness"] = float(row["acousticness"])
                songs.append(row)
    except FileNotFoundError:
        print(f"Warning: could not find '{csv_path}'. Returning empty catalog.")
    print(f"Loaded {len(songs)} songs from {csv_path}.")
    return songs


def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """Apply the weighted Algorithm Recipe to one song and return (numeric_score, reason_strings).

    Weights: genre match +2.5 | mood match +2.0 | energy proximity +0–1.5 |
             valence +0–1.0 | danceability +0–0.8 | acousticness +0–1.0 |
             save boost +1.5 | skip penalty −3.0
    """
    score = 0.0
    reasons: List[str] = []

    genre = str(song.get("genre", "")).lower()
    mood = str(song.get("mood", "")).lower()
    energy = float(song.get("energy", 0.5))
    valence = float(song.get("valence", 0.5))
    danceability = float(song.get("danceability", 0.5))
    acousticness = float(song.get("acousticness", 0.5))

    pref_genre = str(user_prefs.get("genre", "")).lower()
    pref_mood = str(user_prefs.get("mood", "")).lower()
    target_energy = float(user_prefs.get("energy", 0.5))
    likes_acoustic = bool(user_prefs.get("likes_acoustic", False))
    skipped_ids = user_prefs.get("skipped_ids", [])
    saved_ids = user_prefs.get("saved_ids", [])

    # --- Content-Based Filtering ---

    # 1. Genre match
    if genre == pref_genre:
        score += 2.5
        reasons.append(f"Matches your favorite genre ({genre})")

    # 2. Mood match
    if mood == pref_mood:
        score += 2.0
        reasons.append(f"Matches your preferred mood ({mood})")

    # 3. Energy proximity — (1 − |diff|) × 1.5 so max contribution = 1.5
    energy_diff = abs(energy - target_energy)
    score += (1.0 - energy_diff) * 1.5
    if energy_diff < 0.15:
        reasons.append(
            f"Energy ({energy:.2f}) closely matches your target ({target_energy:.2f})"
        )

    # 4. Valence bonus for upbeat-preferring users
    if pref_mood in ("happy", "euphoric", "relaxed"):
        score += valence * 1.0
        if valence > 0.75:
            reasons.append(f"High positivity score ({valence:.2f}) suits your upbeat vibe")
    elif pref_mood in ("moody", "intense", "focused"):
        score += (1.0 - valence) * 0.5  # darker valence rewarded slightly

    # 5. Danceability — rewarded for energetic / happy users
    if pref_mood in ("happy", "intense") or target_energy > 0.75:
        score += danceability * 0.8
        if danceability > 0.75:
            reasons.append(f"Highly danceable ({danceability:.2f})")

    # 6. Acousticness preference
    if likes_acoustic:
        score += acousticness * 1.0
        if acousticness > 0.7:
            reasons.append(f"Acoustic texture ({acousticness:.2f}) matches your preference")
    else:
        score += (1.0 - acousticness) * 0.5  # mild boost for non-acoustic

    # --- Collaborative-Style Behavioral Signals ---

    song_id = song.get("id")
    if song_id in skipped_ids:
        score -= 3.0
        reasons = ["Previously skipped — low priority"]
    elif song_id in saved_ids:
        score += 1.5
        reasons.append("Matches a track you previously saved")

    if not reasons:
        reasons.append("Broadly aligns with your listening profile")

    return (round(score, 3), reasons)


def recommend_songs(
    user_prefs: Dict, songs: List[Dict], k: int = 5
) -> List[Tuple[Dict, float, str]]:
    """Score every song with score_song(), sort descending, and return the top-k (song, score, explanation) tuples.

    Sorting choice — .sort() vs sorted():
      list.sort()  mutates the list in-place and returns None. It is slightly
                   faster and uses less memory because no copy is made.
      sorted()     returns a new sorted list and leaves the original unchanged.
                   Use it when you need to keep the original order for other code.
    Here we use .sort() because `scored` is a local variable built just for
    this function — we own it exclusively and have no reason to preserve its
    original insertion order after sorting.
    """
    if not songs:
        print("No songs in catalog — check that data/songs.csv loaded correctly.")
        return []

    scored: List[Tuple[Dict, float, str]] = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        explanation = " | ".join(reasons)
        scored.append((song, score, explanation))

    # .sort() mutates in-place (faster, no copy) — correct here because
    # `scored` is local and we don't need the pre-sort order preserved.
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]


# ---------------------------------------------------------------------------
# OOP API  (used by tests/test_recommender.py)
# ---------------------------------------------------------------------------

class Recommender:
    """
    Object-oriented recommender that wraps a Song catalog.
    Required by tests/test_recommender.py
    """

    def __init__(self, songs: List[Song]) -> None:
        self.songs = songs

    # ------------------------------------------------------------------
    # Internal scoring (same logic as score_song but works on dataclasses)
    # ------------------------------------------------------------------

    def _score(self, user: UserProfile, song: Song) -> Tuple[float, List[str]]:
        """Same Algorithm Recipe as score_song() but operates on typed Song/UserProfile dataclasses."""
        score = 0.0
        reasons: List[str] = []

        # 1. Genre match
        if song.genre.lower() == user.favorite_genre.lower():
            score += 2.5
            reasons.append(f"Matches your favorite genre ({song.genre})")

        # 2. Mood match
        if song.mood.lower() == user.favorite_mood.lower():
            score += 2.0
            reasons.append(f"Matches your preferred mood ({song.mood})")

        # 3. Energy proximity
        energy_diff = abs(song.energy - user.target_energy)
        score += (1.0 - energy_diff) * 1.5
        if energy_diff < 0.15:
            reasons.append(
                f"Energy ({song.energy:.2f}) closely matches your target ({user.target_energy:.2f})"
            )

        # 4. Valence
        if user.favorite_mood in ("happy", "euphoric", "relaxed"):
            score += song.valence * 1.0
            if song.valence > 0.75:
                reasons.append(f"High positivity ({song.valence:.2f})")
        elif user.favorite_mood in ("moody", "intense", "focused"):
            score += (1.0 - song.valence) * 0.5

        # 5. Danceability
        if user.favorite_mood in ("happy", "intense") or user.target_energy > 0.75:
            score += song.danceability * 0.8
            if song.danceability > 0.75:
                reasons.append(f"Highly danceable ({song.danceability:.2f})")

        # 6. Acousticness preference
        if user.likes_acoustic:
            score += song.acousticness * 1.0
            if song.acousticness > 0.7:
                reasons.append(f"Acoustic texture ({song.acousticness:.2f}) suits you")
        else:
            score += (1.0 - song.acousticness) * 0.5

        # 7. Behavioral signals (collaborative-style)
        if song.id in user.skipped_song_ids:
            score -= 3.0
            reasons = ["Previously skipped — low priority"]
        elif song.id in user.saved_song_ids:
            score += 1.5
            reasons.append("Matches a track you previously saved")

        if not reasons:
            reasons.append("Broadly aligns with your listening profile")

        return round(score, 3), reasons

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Returns top-k Song objects sorted by descending score."""
        scored = [(song, self._score(user, song)[0]) for song in self.songs]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [song for song, _ in scored[:k]]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Returns a human-readable explanation for why song was recommended."""
        _, reasons = self._score(user, song)
        return " | ".join(reasons)
