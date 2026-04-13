# Reflection: Comparing Profile Outputs

This file compares the recommendation results for different user profiles side by side.
All comparisons are written for a non-programmer — no code, just plain explanations of
what changed and why it makes sense.

---

## 1. pop_happy vs lofi_chill

**pop_happy** (genre: pop, mood: happy, energy: 0.8, not acoustic)
Top results: Sunrise City, Gym Hero, Rooftop Lights, Drop Zone, Street Cypher

**lofi_chill** (genre: lofi, mood: chill, energy: 0.4, acoustic)
Top results: Library Rain, Midnight Coding, Focus Flow, Spacewalk Thoughts, Coffee Shop Stories

**What changed and why it makes sense:**

These two profiles are almost complete opposites — one wants loud, upbeat, danceable pop; the other wants quiet, mellow, acoustic lo-fi. The results are completely different, which is exactly what you'd hope for.

The pop profile gets songs that feel like a summer playlist — high energy, positive, easy to dance to. Sunrise City scores first because it perfectly matches the genre, mood, energy, and positivity all at once.

The lofi profile gets songs that feel like a study session — quiet, slow, with real-instrument textures like rain sounds or coffee shop ambiance. Library Rain wins because it is the closest lofi/chill song to the user's energy target (0.35 vs target 0.40).

Notice that "Coffee Shop Stories" (jazz) appears at #5 on the lofi list even though it is not a lofi song. It sneaks in because it has very high acousticness (0.89) and low energy (0.37), which are the texture signals the lofi profile is rewarding. This is an example of the system working correctly — the jazz song *feels* like lofi even though it is not labeled that way — but it also hints at the limitation: the system is matching texture, not understanding music culture.

---

## 2. metal_angry vs jazz_relaxed

**metal_angry** (genre: metal, mood: angry, energy: 0.95, not acoustic)
Top results: Shattered Glass, Drop Zone, Gym Hero, Street Cypher, Storm Runner

**jazz_relaxed** (genre: jazz, mood: relaxed, energy: 0.38, acoustic)
Top results: Coffee Shop Stories, Spacewalk Thoughts, Library Rain, Focus Flow, Nocturne in Blue

**What changed and why it makes sense:**

These two profiles sit at opposite ends of every axis — high energy vs. low energy, electronic vs. acoustic, intense vs. calm. The results mirror that completely.

The metal profile's #1 result (Shattered Glass) has a score of 6.87. All other results score below 3.0. That giant gap tells you something important: there is only one metal/angry song in the catalog. Everything after it is a fallback based purely on energy being similarly high. The system is doing its best, but it is running out of good matches.

The jazz profile has a similar pattern — Coffee Shop Stories (7.58) is far above #2 (2.92). Again, one perfect match and then fallbacks.

One surprising result: "Gym Hero" (pop/intense) shows up at #3 for the metal/angry profile. A metal fan might be confused to see a pop song recommended. But the system is being logical — Gym Hero has energy 0.93 which is very close to the target 0.95. The system has no concept of "Gym Hero sounds like pop, not metal." It only sees a number that is close to another number. This is a good example of where the system gets the math right but misses the cultural context that a human music fan would catch instantly.

---

## 3. conflicting_sad_high_energy vs unknown_genre_reggae

**conflicting_sad_high_energy** (genre: rock, mood: sad, energy: 0.9)
Top results: Storm Runner (#1, 4.96), Wildflower Ballad (#2, 2.92), Drop Zone, Gym Hero, Street Cypher

**unknown_genre_reggae** (genre: reggae, mood: chill, energy: 0.55)
Top results: Library Rain (#1, 4.06), Midnight Coding, Spacewalk Thoughts, Dusty Backroads, Coffee Shop Stories

**What changed and why it makes sense:**

Both profiles have a problem the system cannot fully solve: the conflicting profile has a mood ("sad") that barely exists in the catalog, and the reggae profile has a genre that does not exist in the catalog at all.

For the **conflicting profile**, notice that #1 is Storm Runner (rock/intense) and #2 is Wildflower Ballad (folk/sad). These two songs represent the two halves of the user's conflicting request. Storm Runner wins because it matches the genre (rock) and the high energy. Wildflower Ballad is the only sad song in the catalog and gets the mood bonus, but it is far too quiet (energy 0.29) to rank first. The system split the difference — it cannot give you one song that is both rock-loud and sad, because none exists, so it surfaces each piece separately.

For the **reggae profile**, all top scores hover around 4.0 — noticeably lower than the 6–7 range you see for well-matched profiles. This is the "cold-start" problem in action. Without a genre match, the system is flying blind and can only reward mood and acousticness. A reggae fan opening this app would get lofi and ambient music — technically similar in texture, but culturally completely different. The system should ideally tell the user "I don't have reggae in my catalog" rather than pretending these are good matches.

---

## 4. Why "Gym Hero" Keeps Appearing in High-Energy Profiles

If you run multiple high-energy profiles, Gym Hero (pop/intense, energy 0.93, danceability 0.88) shows up repeatedly — even for a metal fan, even for an EDM fan.

Here is the plain-language explanation: Gym Hero has two unusually high numbers — energy 0.93 and danceability 0.88. Whenever a user wants high energy, the system sees that Gym Hero's energy is close to that target. Whenever a user wants a happy or intense mood, the system also rewards high danceability. Gym Hero ticks both boxes for almost every "loud and active" user profile.

The problem is that a gym-pop workout song and a metal song sound completely different to a human listener, but to the algorithm they look almost identical on the features that matter for high-energy profiles. This is called a **feature collision** — two very different songs share similar numbers on the features being measured.

The fix would be to add more songs that cover the high-energy space across different genres, or to add genre family groupings so the system knows "metal" and "pop" should not be interchangeable, even if their energy numbers are close.

---

## 5. The Weight Experiment: What Doubled Energy Changed

When the energy weight was doubled (from ×1.5 to ×3.0) and the genre weight was halved (from +2.5 to +1.25), the most visible change in the pop/happy profile was that **Rooftop Lights jumped from #3 to #2**, swapping places with Gym Hero.

In plain terms: Rooftop Lights is an indie pop song with energy 0.76, very close to the target of 0.80. Gym Hero is a pop song (exact genre match) with energy 0.93, which is further from the target. With the baseline weights, the genre bonus for Gym Hero outweighed the better energy match for Rooftop Lights. When energy was given twice the importance, the energy proximity became the deciding factor and Rooftop Lights overtook Gym Hero.

This reveals something worth thinking about: there is no single "correct" weight. Both rankings feel defensible. A pop fan who cares most about genre might prefer the baseline. A pop fan who cares most about how pumped up the music feels might prefer the experiment result. The weights encode a design decision about what "best match" means — and different users might define it differently.
