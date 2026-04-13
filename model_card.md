# Model Card: Music Recommender Simulation

## 1. Model Name

**VibeFinder 1.0**

---

## 2. Goal / Task

VibeFinder's task is: given a user's stated preferences, rank every song in the catalog from most to least relevant and return the top 5. It is a **content-based ranking system** — it scores each song against what the user says they like, not against what other users have listened to.

---

## 3. Intended Use and Non-Intended Use

**Intended use:**
- Classroom exploration of how scoring-based recommender systems work
- Learning how audio features (energy, valence, danceability) translate into ranked suggestions
- Experimenting with weight design and its effect on results
- Demonstrating the difference between content-based filtering and collaborative filtering

**Not intended for:**
- Real users making actual listening decisions — the 18-song catalog is too small to produce meaningful variety
- Any genre or mood not represented in the catalog (e.g., reggae, K-pop, Afrobeats) — the system has no way to surface relevant music and will silently return weak fallbacks
- Personalization over time — the system has no memory between sessions, no learning, and no ability to evolve with a user's taste
- Groups or shared listening contexts — the profile assumes one user with one fixed preference set

---

## 4. Algorithm Summary

Imagine you describe yourself to a music-obsessed friend: "I love pop, I'm in a happy mood right now, and I want something with high energy but not too heavy." Your friend then mentally runs through every song they know and gives each one a score based on how well it matches what you said.

VibeFinder does the same thing, but with math. For every song in the catalog it adds up points:

- It gives the biggest bonus if the song's genre matches yours — because genre is like the entire personality of a song.
- It gives the second biggest bonus if the mood matches — because you usually listen to music that matches how you feel.
- It gives smaller bonuses based on how close the song's energy, positivity (called "valence"), rhythm, and acoustic texture are to what you said you wanted. The closer, the more points.
- If you've explicitly saved a song before, it gets a boost. If you've skipped a song, it gets penalized so strongly that it will never appear in your top results again.

After every song has a score, the system sorts them from highest to lowest and hands you the top five.

---

## 5. Data Used

The catalog contains **18 songs** stored in `data/songs.csv`. Each song has 10 attributes: a unique ID, title, artist, genre, mood, energy (0–1), tempo in BPM, valence (0–1), danceability (0–1), and acousticness (0–1).

**Genres represented:** pop, lofi, rock, ambient, jazz, synthwave, indie pop, R&B, hip-hop, classical, country, metal, folk, EDM, blues (15 genres across 18 songs — most genres have only one representative).

**Moods represented:** happy, chill, intense, relaxed, focused, moody, romantic, energetic, peaceful, melancholic, angry, sad, euphoric (13 moods).

8 songs came with the starter project; 10 were added to expand genre and mood coverage. The catalog was built to serve as a teaching example, not to reflect real listener demographics. Songs with Western, English-language genres dominate — there is no K-pop, Afrobeats, reggae, Latin, or classical non-Western music. The data reflects the taste assumptions of whoever designed the starter, which skews young and Western.

---

## 6. Strengths

The system works most reliably when the user's genre and mood both appear in the catalog and a well-matched song exists. For example:

- A **jazz/relaxed** user receives "Coffee Shop Stories" as #1 with a score of 7.58 — far ahead of #2 at 2.92. The recommendation is immediately intuitive.
- A **lofi/chill** user receives only lofi or ambient songs in the top 4, all at low energy and high acousticness. The energy proximity formula correctly separates the lofi tracks from each other by which one is closer to the target.
- The system is **fully transparent**: every recommendation comes with a plain-English reason so users know exactly why a song was suggested. No black-box behavior.
- The skip/save behavioral layer correctly demotes songs a user has already rejected, which a pure content-based system would ignore.

---

## 7. Observed Behavior / Biases

**Genre over-prioritization.** The genre weight of +2.5 dominates the scoring. A mediocre exact-genre match will rank higher than a great adjacent-genre match almost every time. During testing, "Gym Hero" (pop/intense) consistently ranked #2 for a pop/happy user — not because it is a happy song, but because it carries the genre bonus. A listener who said they want happy music and gets an intense workout track might be confused why that appeared.

**Exact-match brittleness for similar moods.** "Chill" and "relaxed" are virtually the same feeling, but the system scores them as completely unrelated. A user who wants "relaxed" music gets zero mood credit for any "chill" song. Similarly, "R&B" and "soul" would be strangers to each other. Real platforms handle this by using similarity embeddings, where related genres are placed near each other in mathematical space.

**Cold-start failure for unknown genres and moods.** If a user's genre is not in the catalog (e.g., "reggae"), the genre bonus never fires. The adversarial test showed that an unknown-genre user gets results clustered around only the mood match and acousticness — the top 3 all scored around 4.0 instead of the usual 6.5–7.5 for well-matched users. The system produces lower-confidence recommendations with no warning to the user.

**Contradictory preferences are accepted silently.** A user who says `genre=metal, likes_acoustic=True` is expressing conflicting preferences — metal songs are almost never acoustic. The system accepts these contradictions and scores accordingly. In the adversarial test, the metal/acoustic contradiction lowered the top song's score from 6.87 to 6.46 without any explanation to the user about why the result felt off. A better system would detect and warn about self-contradictory inputs.

**Behavioral signals never decay.** A song skipped once carries a −3.0 penalty forever. There is no concept of "I skipped this on a bad day but might like it now." In a real system, skip signals decay over time and can be overridden by later saves.

---

## 8. Evaluation Process

**Standard profiles tested:**

| Profile | #1 Result | Score | Intuition Check |
|---|---|---|---|
| pop / happy / energy 0.8 | Sunrise City (pop/happy) | 7.85 | Correct — genre + mood + energy all align |
| lofi / chill / energy 0.4 | Library Rain (lofi/chill) | 6.79 | Correct — closest lofi/chill by energy |
| metal / angry / energy 0.95 | Shattered Glass (metal/angry) | 6.87 | Correct — only metal/angry in catalog |
| jazz / relaxed / energy 0.38 | Coffee Shop Stories (jazz/relaxed) | 7.58 | Correct — only jazz/relaxed in catalog |

**Adversarial profiles and what they revealed:**

| Profile | What Was Tested | Finding |
|---|---|---|
| rock / sad / energy 0.9 | Mood not in catalog + conflicting energy | System fell back to genre (rock) + energy; mood "sad" fired only on Wildflower Ballad (#2). Genre dominated. |
| reggae / chill / energy 0.55 | Genre not in catalog | Genre bonus never fired. All top results were mood/acousticness-only matches scoring ~4.0. Cold-start exposed. |
| metal / angry + likes_acoustic | Contradictory preferences | Shattered Glass still won (only metal/angry), but at reduced score (6.46 vs 6.87) due to low acousticness. Contradiction accepted silently. |
| ambient / peaceful / energy 0.05 | Mood not in catalog + extreme energy | Spacewalk Thoughts won via genre match. #2–5 were all pure acousticness matches — the system produced reasonable results but only because ambient happened to be in the catalog. |

**Weight experiment — doubled energy, halved genre:**

Changing genre from +2.5 → +1.25 and energy multiplier from ×1.5 → ×3.0 caused Rooftop Lights to jump from #3 to #2 in the pop/happy profile, swapping with Gym Hero. This happened because Rooftop Lights (energy 0.76) is closer to target 0.80 than Gym Hero (energy 0.93), and the larger energy weight made that distance matter more than the genre bonus. The experiment confirmed that the baseline genre weight suppresses energy proximity in rankings.

**What surprised me:** The biggest surprise was how clearly the adversarial profiles exposed the cold-start problem. An unknown-genre user's top scores (~4.0) look acceptable on the surface but are significantly weaker than a matched user (~7.5). Without displaying a confidence level, the system would mislead a reggae or K-pop fan into thinking they were getting good recommendations when they were actually getting the system's best guesses from an unrelated catalog.

---

## 9. Ideas for Improvement

- **Genre families / soft matching**: Instead of exact genre matching, assign related genres similarity weights. "Indie pop" and "pop" would share 70% of the genre bonus. This is how real embedding-based systems handle genre proximity.
- **Mood vectors**: Replace the binary mood match with a mood similarity matrix. "Chill" and "relaxed" are adjacent; "happy" and "angry" are opposites. Scoring by mood distance would be more nuanced than the current on/off switch.
- **Energy range instead of target point**: Allow users to express `min_energy` and `max_energy` rather than a single target. A listener who wants 0.7–0.9 energy should not be penalized for liking a song at 0.85.
- **Score normalization and confidence display**: Show users when their profile is poorly matched to the catalog so they know the system is operating in low-confidence mode.
- **Behavioral signal decay**: Weight saves and skips by recency so a two-month-old skip doesn't permanently suppress a song.
- **Catalog expansion**: 18 songs across 15 genres means most genres have one representative. Meaningful recommendations require at minimum 5–10 songs per genre.

---

## 10. Personal Reflection

**What was my biggest learning moment?**

The weight experiment was the clearest moment of insight. Halving the genre weight and doubling the energy weight caused Rooftop Lights to jump from #3 to #2 in the pop/happy profile — and both rankings felt equally defensible depending on what you think "best match" means. That was the moment it became obvious that every weight in the system is a hidden design decision made by a human. There is no mathematically correct answer. Every recommender system, including Spotify's, encodes someone's judgment about what matters most — it is just buried deep enough in the math that most users never see it.

**How did using AI tools help, and when did I need to double-check them?**

AI tools were most useful for research and explaining concepts — the breakdown of collaborative filtering vs. content-based filtering, how Spotify's audio features map to listening behavior, and the `.sort()` vs. `sorted()` distinction were all made clearer through AI-assisted explanations. The place where I had to be most careful was in code suggestions: AI-generated code sometimes returned the wrong type (`[]` instead of a `(float, list)` tuple in `score_song`), scored songs without actually reading the weights I had defined, or added complexity that wasn't needed. Treating AI output as a first draft to review and test — not as finished code — was the right mindset throughout.

**What surprised me about how simple algorithms can still "feel" like recommendations?**

The most surprising thing was how readable the "Because:" output made the results feel. Even though the algorithm is just arithmetic — adding up five or six numbers — the reason strings ("Matches your favorite genre (pop) | Energy closely matches your target") make it feel like the system understands you. The same output from a black-box neural network would carry no explanation at all. A simple transparent system with clear reasons often feels more trustworthy than a complex one that is more accurate but cannot explain itself. That is a real tension in production AI systems that I had not fully appreciated before building this.

**What would I try next if I extended this project?**

The most interesting next step would be replacing the exact genre/mood matches with similarity embeddings — numerical vectors that place "indie pop" close to "pop" and "chill" close to "relaxed" in mathematical space. This would eliminate the biggest limitation (exact-match brittleness) without changing the overall scoring architecture. A second priority would be adding a confidence display so users know when their genre is underrepresented in the catalog, rather than receiving silently weak recommendations. Both changes could be implemented with the current codebase structure — they are parameter changes, not architectural rewrites.
