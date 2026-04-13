"""
Music Recommender — hybrid content-based + collaborative-style filtering.

Algorithm design inspired by how Spotify and YouTube Music work:
  - Content-Based Filtering : scores each song against audio features
    (genre, mood, energy, valence, danceability, acousticness, popularity,
    release decade, mood tags, instrumentalness) — the same feature space
    Spotify exposes via its audio-features API plus editorial metadata.
  - Collaborative-Style Signals : saved tracks boost a song's score;
    skipped tracks suppress it — mirroring how platforms weight intentional
    actions (saves, skips) far more heavily than passive streams.
  - Hybrid blend : content score + behavioral adjustment = final rank.

Optional Extension Challenges implemented here:
  Challenge 1 — Advanced features: popularity, release_decade, mood_tags,
                instrumentalness, liveness scored against new UserProfile prefs.
  Challenge 2 — Scoring Modes (Strategy pattern): swap a ScoringWeights object
                to switch between balanced / genre_first / mood_first /
                energy_focused / discovery ranking strategies.
  Challenge 3 — Diversity penalty: recommend_with_diversity() uses greedy
                re-ranking to cap songs per genre and per artist.
"""

import csv
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Challenge 2 — Scoring Modes (Strategy Pattern)
# ---------------------------------------------------------------------------

@dataclass
class ScoringWeights:
    """
    Weight multipliers for every scoring signal.

    Swap the entire object to change ranking strategy without touching the
    scoring logic — this is the Strategy design pattern. Negative values
    invert a signal (e.g. popularity < 0 rewards obscure tracks).
    """
    # Categorical signals (binary: full bonus or zero)
    genre: float = 2.5
    mood: float = 2.0
    # Continuous proximity signals (scaled 0–max by distance formula)
    energy: float = 1.5         # max contribution when song energy == target
    valence: float = 1.0        # max for happy/relaxed/euphoric moods
    danceability: float = 0.8   # max for energetic/happy users
    # Texture preferences
    acousticness_like: float = 1.0    # song.acousticness × weight (likes_acoustic=True)
    acousticness_unlike: float = 0.5  # (1−acousticness) × weight (likes_acoustic=False)
    # Advanced feature signals (Challenge 1)
    popularity: float = 1.5     # (popularity/100) × weight; set negative to reward obscure
    decade: float = 0.8         # proximity bonus when preferred_decade is set
    mood_tag: float = 0.4       # bonus per matching detailed mood tag
    instrumentalness: float = 0.6  # song.instrumentalness × weight (likes_instrumental=True)
    # Behavioral signals (collaborative-style)
    save_boost: float = 1.5
    skip_penalty: float = 3.0


# Four ready-made modes — each is just a different ScoringWeights configuration.
SCORING_MODES: Dict[str, ScoringWeights] = {
    # Default: all signals at baseline weights
    "balanced": ScoringWeights(),
    # Genre-First: genre signal amplified 2×, continuous signals reduced
    "genre_first": ScoringWeights(
        genre=5.0, mood=1.0, energy=0.8, danceability=0.4
    ),
    # Mood-First: mood signal amplified, genre reduced to secondary
    "mood_first": ScoringWeights(
        genre=1.0, mood=5.0, energy=0.8
    ),
    # Energy-Focused: continuous energy + danceability dominate
    "energy_focused": ScoringWeights(
        genre=1.0, mood=1.0, energy=4.0, danceability=1.2
    ),
    # Discovery: penalises popular songs to surface lower-profile tracks
    "discovery": ScoringWeights(
        genre=1.5, mood=1.5, energy=1.5, popularity=-1.5
    ),
}


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class Song:
    """Represents a song with Spotify-style audio features plus extended metadata."""
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
    # Challenge 1 — advanced features (defaulted so existing tests don't break)
    popularity: int = 50          # 0–100  Spotify-style popularity score
    release_decade: int = 2020    # e.g. 1990, 2000, 2010, 2020
    mood_tags: str = ""           # comma-separated detail tags: "nostalgic,warm,cozy"
    instrumentalness: float = 0.0 # 0–1  1.0 = fully instrumental (no vocals)
    liveness: float = 0.1         # 0–1  presence of live-audience character


@dataclass
class UserProfile:
    """User taste preferences and behavioral history."""
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool
    # Behavioral history (collaborative-style signals)
    saved_song_ids: List[int] = field(default_factory=list)
    skipped_song_ids: List[int] = field(default_factory=list)
    # Challenge 1 — advanced preferences (all optional, defaulted to "no preference")
    preferred_decade: int = 0           # 0 = no era preference
    preferred_tags: List[str] = field(default_factory=list)  # e.g. ["nostalgic","cozy"]
    min_popularity: int = 0             # songs below this get a penalty
    likes_instrumental: bool = False    # prefers tracks with few/no vocals


# ---------------------------------------------------------------------------
# Functional API  (used by src/main.py)
# ---------------------------------------------------------------------------

def load_songs(csv_path: str) -> List[Dict]:
    """Read a CSV catalog via csv.DictReader and return a list of dicts with numeric fields cast."""
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
                # Challenge 1 new columns (graceful: skip if CSV is old format)
                row["popularity"] = int(row.get("popularity", 50) or 50)
                row["release_decade"] = int(row.get("release_decade", 2020) or 2020)
                row["mood_tags"] = str(row.get("mood_tags", "") or "")
                row["instrumentalness"] = float(row.get("instrumentalness", 0.0) or 0.0)
                row["liveness"] = float(row.get("liveness", 0.1) or 0.1)
                songs.append(row)
    except FileNotFoundError:
        print(f"Warning: could not find '{csv_path}'. Returning empty catalog.")
    print(f"Loaded {len(songs)} songs from {csv_path}.")
    return songs


def score_song(
    user_prefs: Dict,
    song: Dict,
    weights: Optional[ScoringWeights] = None,
) -> Tuple[float, List[str]]:
    """Apply the weighted Algorithm Recipe to one song and return (score, reason_strings).

    Pass a ScoringWeights object via `weights` to switch scoring strategy (Challenge 2).
    Defaults to the 'balanced' mode when weights is None.
    """
    w = weights or ScoringWeights()
    score = 0.0
    reasons: List[str] = []

    # --- Extract song attributes ---
    genre = str(song.get("genre", "")).lower()
    mood = str(song.get("mood", "")).lower()
    energy = float(song.get("energy", 0.5))
    valence = float(song.get("valence", 0.5))
    danceability = float(song.get("danceability", 0.5))
    acousticness = float(song.get("acousticness", 0.5))
    popularity = int(song.get("popularity", 50))
    release_decade = int(song.get("release_decade", 2020))
    mood_tags = [t.strip() for t in str(song.get("mood_tags", "")).split(",") if t.strip()]
    instrumentalness = float(song.get("instrumentalness", 0.0))

    # --- Extract user preferences ---
    pref_genre = str(user_prefs.get("genre", "")).lower()
    pref_mood = str(user_prefs.get("mood", "")).lower()
    target_energy = float(user_prefs.get("energy", 0.5))
    likes_acoustic = bool(user_prefs.get("likes_acoustic", False))
    skipped_ids = user_prefs.get("skipped_ids", [])
    saved_ids = user_prefs.get("saved_ids", [])
    preferred_decade = int(user_prefs.get("preferred_decade", 0))
    preferred_tags = [t.lower() for t in user_prefs.get("preferred_tags", [])]
    min_popularity = int(user_prefs.get("min_popularity", 0))
    likes_instrumental = bool(user_prefs.get("likes_instrumental", False))

    # -----------------------------------------------------------------------
    # Content-Based Filtering
    # -----------------------------------------------------------------------

    # 1. Genre match
    if genre == pref_genre:
        score += w.genre
        reasons.append(f"Matches your favorite genre ({genre})")

    # 2. Mood match
    if mood == pref_mood:
        score += w.mood
        reasons.append(f"Matches your preferred mood ({mood})")

    # 3. Energy proximity — (1 − |diff|) × weight, max = weight
    energy_diff = abs(energy - target_energy)
    score += (1.0 - energy_diff) * w.energy
    if energy_diff < 0.15:
        reasons.append(
            f"Energy ({energy:.2f}) closely matches your target ({target_energy:.2f})"
        )

    # 4. Valence bonus — mood-gated
    if pref_mood in ("happy", "euphoric", "relaxed"):
        score += valence * w.valence
        if valence > 0.75:
            reasons.append(f"High positivity ({valence:.2f}) suits your upbeat vibe")
    elif pref_mood in ("moody", "intense", "focused"):
        score += (1.0 - valence) * (w.valence * 0.5)

    # 5. Danceability — energetic/happy users only
    if pref_mood in ("happy", "intense") or target_energy > 0.75:
        score += danceability * w.danceability
        if danceability > 0.75:
            reasons.append(f"Highly danceable ({danceability:.2f})")

    # 6. Acousticness preference
    if likes_acoustic:
        score += acousticness * w.acousticness_like
        if acousticness > 0.7:
            reasons.append(f"Acoustic texture ({acousticness:.2f}) matches your preference")
    else:
        score += (1.0 - acousticness) * w.acousticness_unlike

    # -----------------------------------------------------------------------
    # Challenge 1 — Advanced Feature Scoring
    # -----------------------------------------------------------------------

    # 7. Popularity signal — positive = reward mainstream, negative = reward obscure
    pop_contribution = (popularity / 100) * w.popularity
    score += pop_contribution
    if w.popularity < 0 and popularity < 55:
        reasons.append(f"Hidden gem (popularity {popularity}) suits discovery mode")
    elif w.popularity > 0 and popularity >= 75:
        reasons.append(f"Widely loved track (popularity {popularity})")

    # 8. Popularity floor penalty — if user wants minimum quality threshold
    if min_popularity > 0 and popularity < min_popularity:
        score -= 1.0
        reasons.append(f"Below your popularity threshold ({popularity} < {min_popularity})")

    # 9. Release decade proximity — only when user has a preference
    if preferred_decade > 0:
        decade_diff = abs(release_decade - preferred_decade) / 50  # normalise: max gap = 50 yrs
        decade_score = (1.0 - decade_diff) * w.decade
        score += decade_score
        if decade_diff == 0:
            reasons.append(f"From your preferred era ({release_decade}s)")
        elif decade_diff <= 0.2:
            reasons.append(f"Close to your preferred era ({release_decade}s)")

    # 10. Detailed mood tag matching
    if preferred_tags:
        matching = [t for t in preferred_tags if t in mood_tags]
        if matching:
            tag_score = len(matching) * w.mood_tag
            score += tag_score
            reasons.append(f"Mood tags match: {', '.join(matching)}")

    # 11. Instrumentalness preference
    if likes_instrumental:
        score += instrumentalness * w.instrumentalness
        if instrumentalness > 0.7:
            reasons.append(f"Largely instrumental ({instrumentalness:.2f}) — no vocals to distract")
    else:
        score += (1.0 - instrumentalness) * (w.instrumentalness * 0.4)

    # -----------------------------------------------------------------------
    # Collaborative-Style Behavioral Signals
    # -----------------------------------------------------------------------

    song_id = song.get("id")
    if song_id in skipped_ids:
        score -= w.skip_penalty
        reasons = ["Previously skipped — low priority"]
    elif song_id in saved_ids:
        score += w.save_boost
        reasons.append("Matches a track you previously saved")

    if not reasons:
        reasons.append("Broadly aligns with your listening profile")

    return (round(score, 3), reasons)


def recommend_songs(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5,
    weights: Optional[ScoringWeights] = None,
) -> List[Tuple[Dict, float, str]]:
    """Score every song with score_song(), sort descending, return top-k (song, score, explanation) tuples.

    Sorting choice — .sort() vs sorted():
      list.sort()  mutates the list in-place, returns None, no copy — used here
                   because `scored` is a local variable we own exclusively.
      sorted()     returns a new sorted list, leaves the original unchanged.
                   Use it when the original order matters elsewhere.
    """
    if not songs:
        print("No songs in catalog — check that data/songs.csv loaded correctly.")
        return []

    scored: List[Tuple[Dict, float, str]] = []
    for song in songs:
        score, reasons = score_song(user_prefs, song, weights)
        scored.append((song, score, " | ".join(reasons)))

    # .sort() in-place: faster, no copy needed for a local list
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]


# ---------------------------------------------------------------------------
# Challenge 3 — Diversity-Aware Recommendations
# ---------------------------------------------------------------------------

def recommend_with_diversity(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5,
    max_per_genre: int = 2,
    max_per_artist: int = 1,
    weights: Optional[ScoringWeights] = None,
) -> List[Tuple[Dict, float, str]]:
    """Greedy re-ranking that caps songs per genre and per artist for catalog diversity.

    Algorithm:
      1. Score and rank ALL songs (full catalog pass).
      2. Walk the ranked list greedily: accept a song only if it doesn't
         exceed max_per_genre or max_per_artist limits.
      3. Stop once k songs are selected.

    This prevents the top-5 from being monopolised by a single genre or
    by the same artist appearing multiple times.
    """
    all_scored = recommend_songs(user_prefs, songs, k=len(songs), weights=weights)

    selected: List[Tuple[Dict, float, str]] = []
    genre_counts: Dict[str, int] = {}
    artist_counts: Dict[str, int] = {}

    for song, score, explanation in all_scored:
        genre = str(song.get("genre", "")).lower()
        artist = str(song.get("artist", "")).lower()

        genre_ok = genre_counts.get(genre, 0) < max_per_genre
        artist_ok = artist_counts.get(artist, 0) < max_per_artist

        if genre_ok and artist_ok:
            selected.append((song, score, explanation))
            genre_counts[genre] = genre_counts.get(genre, 0) + 1
            artist_counts[artist] = artist_counts.get(artist, 0) + 1

        if len(selected) >= k:
            break

    return selected


# ---------------------------------------------------------------------------
# OOP API  (used by tests/test_recommender.py)
# ---------------------------------------------------------------------------

class Recommender:
    """Object-oriented recommender that wraps a Song catalog."""

    def __init__(self, songs: List[Song]) -> None:
        self.songs = songs

    def _score(
        self, user: UserProfile, song: Song, weights: Optional[ScoringWeights] = None
    ) -> Tuple[float, List[str]]:
        """Same Algorithm Recipe as score_song() but operates on typed Song/UserProfile dataclasses."""
        w = weights or ScoringWeights()
        score = 0.0
        reasons: List[str] = []

        # 1. Genre match
        if song.genre.lower() == user.favorite_genre.lower():
            score += w.genre
            reasons.append(f"Matches your favorite genre ({song.genre})")

        # 2. Mood match
        if song.mood.lower() == user.favorite_mood.lower():
            score += w.mood
            reasons.append(f"Matches your preferred mood ({song.mood})")

        # 3. Energy proximity
        energy_diff = abs(song.energy - user.target_energy)
        score += (1.0 - energy_diff) * w.energy
        if energy_diff < 0.15:
            reasons.append(
                f"Energy ({song.energy:.2f}) closely matches your target ({user.target_energy:.2f})"
            )

        # 4. Valence
        if user.favorite_mood in ("happy", "euphoric", "relaxed"):
            score += song.valence * w.valence
            if song.valence > 0.75:
                reasons.append(f"High positivity ({song.valence:.2f})")
        elif user.favorite_mood in ("moody", "intense", "focused"):
            score += (1.0 - song.valence) * (w.valence * 0.5)

        # 5. Danceability
        if user.favorite_mood in ("happy", "intense") or user.target_energy > 0.75:
            score += song.danceability * w.danceability
            if song.danceability > 0.75:
                reasons.append(f"Highly danceable ({song.danceability:.2f})")

        # 6. Acousticness
        if user.likes_acoustic:
            score += song.acousticness * w.acousticness_like
            if song.acousticness > 0.7:
                reasons.append(f"Acoustic texture ({song.acousticness:.2f}) suits you")
        else:
            score += (1.0 - song.acousticness) * w.acousticness_unlike

        # 7. Popularity (Challenge 1)
        pop_contribution = (song.popularity / 100) * w.popularity
        score += pop_contribution
        if w.popularity < 0 and song.popularity < 55:
            reasons.append(f"Hidden gem (popularity {song.popularity})")
        elif w.popularity > 0 and song.popularity >= 75:
            reasons.append(f"Widely loved track (popularity {song.popularity})")

        # 8. Release decade (Challenge 1)
        if user.preferred_decade > 0:
            decade_diff = abs(song.release_decade - user.preferred_decade) / 50
            score += (1.0 - decade_diff) * w.decade
            if decade_diff == 0:
                reasons.append(f"From your preferred era ({song.release_decade}s)")

        # 9. Mood tags (Challenge 1)
        if user.preferred_tags:
            song_tags = [t.strip() for t in song.mood_tags.split(",") if t.strip()]
            matching = [t for t in user.preferred_tags if t.lower() in song_tags]
            if matching:
                score += len(matching) * w.mood_tag
                reasons.append(f"Mood tags match: {', '.join(matching)}")

        # 10. Instrumentalness (Challenge 1)
        if user.likes_instrumental:
            score += song.instrumentalness * w.instrumentalness
            if song.instrumentalness > 0.7:
                reasons.append(f"Largely instrumental ({song.instrumentalness:.2f})")
        else:
            score += (1.0 - song.instrumentalness) * (w.instrumentalness * 0.4)

        # 11. Behavioral signals
        if song.id in user.skipped_song_ids:
            score -= w.skip_penalty
            reasons = ["Previously skipped — low priority"]
        elif song.id in user.saved_song_ids:
            score += w.save_boost
            reasons.append("Matches a track you previously saved")

        if not reasons:
            reasons.append("Broadly aligns with your listening profile")

        return round(score, 3), reasons

    def recommend(
        self, user: UserProfile, k: int = 5, mode: str = "balanced"
    ) -> List[Song]:
        """Return top-k Song objects sorted by descending score for the given mode."""
        w = SCORING_MODES.get(mode, ScoringWeights())
        scored = [(song, self._score(user, song, w)[0]) for song in self.songs]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [song for song, _ in scored[:k]]

    def recommend_with_diversity(
        self,
        user: UserProfile,
        k: int = 5,
        mode: str = "balanced",
        max_per_genre: int = 2,
        max_per_artist: int = 1,
    ) -> List[Song]:
        """Greedy diversity-aware version of recommend() for the OOP API."""
        w = SCORING_MODES.get(mode, ScoringWeights())
        all_scored = [(song, self._score(user, song, w)[0]) for song in self.songs]
        all_scored.sort(key=lambda x: x[1], reverse=True)

        selected: List[Song] = []
        genre_counts: Dict[str, int] = {}
        artist_counts: Dict[str, int] = {}

        for song, _ in all_scored:
            g = song.genre.lower()
            a = song.artist.lower()
            if genre_counts.get(g, 0) < max_per_genre and artist_counts.get(a, 0) < max_per_artist:
                selected.append(song)
                genre_counts[g] = genre_counts.get(g, 0) + 1
                artist_counts[a] = artist_counts.get(a, 0) + 1
            if len(selected) >= k:
                break

        return selected

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return a human-readable explanation for why song was recommended."""
        _, reasons = self._score(user, song)
        return " | ".join(reasons)
