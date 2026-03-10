# specialists/domain_prompts.py
# Domain-specific analytical guidance for each specialist.
# These are appended to the generic specialist template to provide
# targeted analysis frameworks.
#
# v2.0 — Enhanced with advanced MMA analytics frameworks inspired by
# FightMetric, Verdicts MMA, Tapology, and professional handicapping.

DOMAIN_GUIDANCE = {
    "style": """
### Domain: Style Analysis

Focus on fighting archetype classification and stylistic matchup dynamics:

**Classification Framework:**
- Primary style: Striker (Boxing/Kickboxing/Muay Thai), Wrestler, Grappler, Hybrid
- Sub-archetype: Pressure fighter, Counter-striker, Volume striker, Point fighter,
  Clinch specialist, Chain wrestler, Submission hunter, Ground-and-pounder
- Stance: Orthodox, Southpaw, Switch — note advantages/disadvantages vs opponent
- Stance-specific patterns: Orthodox vs Southpaw has distinct dynamics (open stance = power hand exposed)

**Key Analysis Points:**
- Range management: Who controls distance? Long-range vs short-range preference?
- Offensive toolkit: Primary weapons (jab, leg kicks, body shots, clinch knees, takedowns)
- Defensive tendencies: Head movement, footwork, cage awareness, takedown defense
- Style clash dynamics: How does each fighter's style interact with the opponent's?
- Historical performance vs similar styles (record against wrestlers, strikers, etc.)
- Transition game: How does each fighter handle style shifts mid-fight? (e.g., striker forced to grapple)
- Predictability factor: How easily can the opponent game-plan for this style?
  (one-dimensional fighters are easier to prepare for)

**Style Clash Predictability Guide:**
- Striker vs Wrestler: Medium predictability — depends on takedown defense and wall work
- Striker vs Striker: Lower predictability — small technical edges decide close exchanges
- Grappler vs Grappler: Higher predictability — positional hierarchy and scramble ability determine winner
- Pressure vs Counter: Depends on cardio sustainability and counter-striker's takedown defense
""",

    "form": """
### Domain: Form & Momentum Analysis

Analyze recent trajectory and current competitive form:

**Form Framework:**
- Last 5 fights: results, quality of opposition, performance level
- Win streak / loss streak implications
- Finish rate trends: more/fewer finishes recently?
- Performance trajectory: improving, plateauing, or declining?
- Layoff analysis: ring rust risk vs recovery benefit

**Key Analysis Points:**
- Quality of recent wins (ranked opponents, finishes vs decisions)
- Quality of recent losses (close fights, dominations, stoppages)
- Age curve: peak performance window, signs of decline
- Camp changes: new coaches, training partners, skill development
- Injury history and recovery timelines

**Advanced Form Factors:**
- Division strength context: Improving while fighting in a stacked division is more
  meaningful than beating lower-ranked opponents in a thin division
- Opponent-type filtering: Separate recent record by opponent archetype —
  losses to wrestlers vs losses to strikers reveal specific vulnerabilities
- Ring rust timeline: <6 months layoff = minimal concern, 6-12 months = moderate risk,
  12+ months = significant rust factor (first round especially vulnerable)
- Training environment trajectory: Has the fighter's gym improved overall?
  (team-wide improvement signals better coaching/sparring partners)
- Performance windows: Does the fighter start fast (R1 finisher) or build momentum (R3-5 closer)?
  Map recent fights to identify their optimal performance window
""",

    "grappling": """
### Domain: Grappling & Wrestling Analysis

Deep analysis of ground game and wrestling dynamics:

**Grappling Framework:**
- Takedown accuracy and defense percentages (use stats if available)
- Chain wrestling ability: single-leg, double-leg, body lock sequences
- Top control: ground-and-pound, positional advancement, submission attempts
- Bottom game: sweeps, scrambles, submission off back, ability to stand up
- Clinch work: dirty boxing, trips, cage wrestling

**Key Analysis Points:**
- Who dictates where the fight takes place?
- Submission threat level: active hunter or positional control?
- Scramble dynamics: who wins the transition exchanges?
- Cardio impact of grappling exchanges
- Cage wrestling: can either fighter effectively pin against the fence?

**Advanced Grappling Framework:**
- Threat sequencing: Map common takedown chains — single-leg → back control,
  double-leg → mount progression, clinch trip → side control → submission
- Position-specific submission threat: Which positions does each fighter hunt
  submissions from? (back control, mount, side control, half guard)
- Mat return efficiency: What % of times taken down does the fighter return to feet
  vs stay engaged on the ground? (critical for predicting fight location)
- Top control time vs active damage: Does the top fighter damage or just control?
  (judges score damage higher under unified rules)
- Submission defense layers:
  * Recognition speed (sees the submission setup early)
  * Escape strength (can power out of locked submissions)
  * Positional prevention (prevents dangerous positions from developing)
- Clinch control time: How long can each fighter maintain clinch position?
  (affects pace, cardio, and scoring)
""",

    "damage": """
### Domain: Damage & Durability Analysis

Assess damage absorption, chin durability, and finish resistance:

**Durability Framework:**
- Strikes absorbed per minute (SApM) — higher = more damage taken
- Striking defense percentage
- Historical knockdowns: how many times dropped? Recovery quality?
- TKO/KO losses: recency, manner (flash KO vs accumulated damage)
- Submission losses: late-round fatigue submissions vs early catches

**Key Analysis Points:**
- Chin durability trends: has the fighter shown chin degradation?
- Body work vulnerability: does the fighter fade under body attack?
- Accumulation resilience: performance in rounds 3-5 under pressure
- Recovery ability: how quickly does the fighter recover when hurt?
- Power differential: who is more likely to end the fight with one shot?

**Advanced Durability Analysis:**
- Damage source specificity:
  * Striking durability: chin vs body damage tolerance (some fighters absorb head shots
    well but fold to body work, or vice versa)
  * Grappling durability: submission escape strength vs positional escape speed
  * Cumulative neurological fatigue: impacts R4-5 reflexes and reaction time,
    distinct from cardio fatigue — watch for fighters who slow defensively late
- Cut susceptibility: Does the fighter accumulate cuts under pressure?
  (cuts can stop fights and impair vision)
- Chin degradation trajectory: Recent KO/TKO losses within last 2-3 fights
  are a STRONG signal of chin decline — weight this heavily
- Power sustainability: Does the fighter maintain knockout power in late rounds?
  (some fighters are R1-2 finishers only)
- Damage recovery timeline: How has the fighter looked AFTER absorbing significant damage
  in previous fights? (lingering effects can persist across fights)
""",

    "pace": """
### Domain: Pace & Cardio Analysis

Evaluate output volume, cardio capacity, and pace dynamics:

**Pace Framework:**
- Significant strikes per minute (SLpM) — output volume
- Total strike attempts per round
- Output differential: early rounds vs late rounds
- Championship round performance (4th and 5th rounds)
- Clinch/grappling time impact on striking output

**Key Analysis Points:**
- Who controls the pace? Pressure fighter vs counter-puncher dynamics
- Cardio sustainability: who fades first in deep waters?
- Altitude/venue effects on cardio
- Weight cut impact on endurance
- Activity rate advantage: volume striker vs patient counter-striker

**Advanced Pace Analysis:**
- Grappling-to-striking cardio transfer: Great wrestlers may gas in prolonged
  striking exchanges (different energy systems). A fighter who wrestles for 3 rounds
  then must strike in R4-5 may fade differently than expected
- Pressure sustainability: Who can maintain offensive urgency in R5?
  (separates 3-round fighters from true 5-round athletes)
- Muscle fiber type inference: High-output explosive strikers (fast-twitch dominant)
  often fade after R2; grinding wrestlers (slow-twitch) can maintain pace for 25 minutes
- Round-by-round output tracking: If stats show R1 output = 60 strikes but R3 = 25,
  that's a 58% decline — quantify the fade rate
- Pace manipulation strategy: Does either fighter benefit from stalling, clinching,
  or slowing the fight? (fighters who slow pace to recover are harder to finish)
""",

    "fight_iq": """
### Domain: Fight IQ & Adaptability Analysis

Assess in-fight decision-making, adaptability, and cage IQ:

**Fight IQ Framework:**
- Mid-fight adjustments: does the fighter adapt when Plan A fails?
- Round awareness: adjustment between rounds, corner advice implementation
- Scoring awareness: does the fighter fight to win rounds on the scorecards?
- Risk management: appropriate aggression vs recklessness
- Clinch/fence IQ: intelligent use of cage position

**Key Analysis Points:**
- History of comebacks or in-fight adjustments
- Performance when losing on the scorecards
- Ability to implement specific gameplans
- Experience advantage: championship rounds, main events, title fights
- Composure under adversity: performance when hurt or taken down

**Decomposed Adjustment Categories:**
- Defensive adjustments: stance changes, footwork modification, range adjustment,
  improved head movement after getting tagged
- Tactical pivots: switching from striking to grappling offense (or vice versa)
  when initial approach fails
- Meta-game reads: recognizing opponent's gameplan mid-fight and countering it
  (e.g., realizing opponent is targeting the body, adjusting guard position)
- Decision-point management: behavior when losing rounds — fighters who increase
  urgency intelligently (not recklessly) tend to win close fights

**Corner Responsiveness:**
- Does the fighter implement corner advice between rounds?
- Can they execute complex tactical instructions under pressure?
- Fighters who ignore corners in late rounds often lose close decisions

**Experience Weighting:**
- Championship round experience: fighters with 5+ five-round fights have significant
  advantage in late-round decision-making
- Title fight pressure: first-time title challengers historically underperform
  (approximately 40% win rate vs ~55% for returning champions)
""",

    "gameplan": """
### Domain: Gameplan & Strategy Analysis

Design optimal strategic approaches for each fighter:

**Gameplan Framework:**
- Path to victory for Fighter A: what must they do to win?
- Path to victory for Fighter B: what must they do to win?
- Key tactical adjustments: what happens if primary strategy fails?
- Round-by-round strategy: early pressure vs late push
- Finish vs decision strategy: which approach favors which fighter?

**Key Analysis Points:**
- Range control: who needs to close/maintain distance?
- Takedown strategy: offensive wrestling or takedown defense priority?
- Pace manipulation: who benefits from a fast vs slow pace?
- Corner strategy: likely between-round adjustments
- Key moments: critical junctures where the fight likely turns

**Advanced Gameplan Analysis:**
- Plan depth assessment: What are Plan A, B, and C for each fighter?
  * Single-plan fighters are vulnerable to mid-fight adjustments
  * Multi-plan fighters can adapt when neutralized
- Resource management: When does each fighter typically abandon a failing strategy?
  (some fighters stubbornly commit to wrestling even when stuffed repeatedly)
- Position-specific strategy shifts: How does the gameplan change based on fight location?
  * On the feet at range vs in the clinch vs on the ground — each requires different tactics
  * Fighters who only have one mode (e.g., can only strike at distance) have limited paths to victory
- Contingency assessment: If Fighter A can't get takedowns, do they have a striking backup?
  If Fighter B can't keep it standing, can they survive on the ground?
- Finish windows: Identify the specific round/scenario where each fighter is most likely to finish
  (e.g., "Fighter A's best chance is an R1 blitz before cardio fades")
""",

    "judging": """
### Domain: Judging & Scoring Analysis

Analyze how fights are likely to be scored under MMA unified rules:

**Judging Framework:**
- Round-by-round scoring criteria: effective striking, grappling, aggression, cage control
- How do judges typically score this style matchup?
- Which fighter benefits from a decision? Who needs a finish?
- Historical judging tendencies at this venue/with likely judges
- Close round dynamics: who wins the swing rounds?

**Key Analysis Points:**
- Octagon control: who occupies center cage more?
- Effective aggression vs volume: what do judges prioritize?
- Takedown scoring: do they value attempts or control time?
- Late-round momentum: does finishing strong sway judges?
- Split decision likelihood based on style matchup

**Advanced Judging Analysis:**
- 10-8 round scenarios: When is accumulated damage or position dominance enough for 10-8?
  (under new unified rules, 10-8 rounds are more common — dominant rounds should be flagged)
- Weight class judging variance: Heavyweight fights often emphasize power/knockdowns,
  lighter divisions reward volume and activity
- Swing round identification: In a 5-round fight, identify which rounds are likely to be
  close (swing rounds) and which fighter's style tends to edge swing rounds
- Split decision tendencies: Grappling-heavy fights produce more split decisions
  than striking-dominant fights (judges disagree on control time value)
- Clinch scoring: Extended clinch work with minimal damage often frustrates judges —
  the fighter who separates and lands clean strikes after clinch exchanges typically
  gets the nod in close rounds
""",

    "scramble": """
### Domain: Scramble & Transition Analysis

Analyze grappling transitions, reversals, and scramble dynamics:

**Scramble Framework:**
- Scramble win rate: who typically ends up on top after a scramble?
- Mat return ability: can they take opponents back down after standup?
- Reversal ability: sweeps from bottom, underhook battles
- Transition defense: ability to prevent position advancement
- Chain wrestling: linking takedown attempts in scramble situations

**Key Analysis Points:**
- Athletic advantages in scramble situations
- Fatigue impact on scramble ability
- Scramble-to-submission transitions
- Stand-up ability from bottom position
- Clinch scramble dynamics: who wins the underhook battle?

**Advanced Scramble Analysis:**
- Scramble initiation vs reaction: Who initiates scrambles vs reacts?
  (initiators tend to end up in better positions)
- Transition chain mapping: Common scramble sequences —
  * Failed takedown → front headlock → guillotine/anaconda
  * Sweep attempt → back exposure → back take
  * Stand-up attempt → re-shot → mat return
- Athletic burst capacity: Scrambles require explosive hip movement and grip strength —
  fighters who have multiple fast-twitch scramble bursts per round win positional battles
- Late-round scramble degradation: How much does scramble ability decline in R4-5?
  (scrambles are the most energy-intensive grappling exchanges)
""",

    "sentiment": """
### Domain: Sentiment & Narrative Analysis

Analyze pre-fight narrative, media coverage, and psychological factors:

**Sentiment Framework:**
- Pre-fight confidence levels and trash talk dynamics
- Media narrative: who is the perceived favorite/underdog?
- Motivation factors: revenge, legacy, title implications
- Mental toughness history: performance under pressure
- Camp atmosphere: distractions, drama, focus issues

**Key Analysis Points:**
- Public perception vs analytical reality
- Pressure of favorites vs underdog mentality
- Historical performance when heavily favored/underdog
- Weight cut stress and its psychological impact
- Championship pressure: first-time title challenger dynamics

**Advanced Psychological Factors:**
- Underdog motivation premium: Fighters who are significant underdogs (+300 or more)
  and have elite experience sometimes outperform — they have nothing to lose
- Revenge fight dynamics: Rematches where one fighter was finished in the first fight
  often see significant tactical adjustments from the loser
- Career crossroads fights: Fighters on 2-3 fight losing streaks facing potential release
  sometimes fight with desperation — can be positive (urgency) or negative (reckless)
- Home crowd advantage: Fighters competing in their home country/city show approximately
  5-8% better performance in close fights (crowd energy, familiarity, judge influence)
""",

    "weightcut": """
### Domain: Weight Cut Analysis

Assess weight cutting history and its impact on performance:

**Weight Cut Framework:**
- Current division fit: natural weight class or cutting significantly?
- Weight cut history: missed weight, difficult cuts, last-minute changes
- Rehydration patterns: how much weight is regained after weigh-in?
- Performance at different weights: better at heavier/lighter?

**Key Analysis Points:**
- Impact on cardio and chin: severe cuts compromise both
- First-round power vs late-round fade from weight cutting
- Opponent's weight cut comparison: who has the size advantage?
- Age-related weight cut difficulty
- Moving up/down in weight: adjustment period and performance trends

**Advanced Weight Cut Factors:**
- Division move performance: Fighters moving UP tend to have better cardio but less power;
  fighters moving DOWN tend to have more power but worse cardio
- Weight cut severity signals: Fighters who have missed weight in the past are at higher
  risk of compromised performance even when they make weight (pushed to the limit)
- Age-weight interaction: Fighters 33+ have significantly harder weight cuts —
  this compounds with chin degradation and cardio decline
- Rehydration advantage: Fighters who rehydrate 15+ lbs have a significant size advantage
  but increased chin vulnerability from the cut itself
""",

    "metadata": """
### Domain: Physical & Statistical Metadata

Analyze measurable physical attributes and statistical profiles:

**Metadata Framework:**
- Height, reach, leg reach comparisons
- Stance matchup implications (orthodox vs southpaw)
- Age differential and career stage
- Professional record breakdown (KO/Sub/Dec ratios)
- Statistical comparisons: SLpM, str accuracy, str defense, TD accuracy, TD defense

**Key Analysis Points:**
- Reach advantage utilization: jab, front kicks, long-range weapons
- Size advantage: who is the naturally bigger fighter?
- Statistical outliers: any extreme stats that indicate clear edges?
- Record quality: strength of schedule, level of competition
- Physical peak assessment: optimal athletic window

**Advanced Statistical Analysis:**
- Reach advantage threshold: 3+ inch reach advantage is significant and correlates with
  higher striking accuracy at range; 5+ inches is a major factor
- Striking accuracy vs volume tradeoff: High accuracy + low volume (counter-striker) vs
  low accuracy + high volume (pressure fighter) — different paths to winning rounds
- Defensive stat reliability: Striking defense % is more predictive of fight outcomes
  than offensive striking stats — elite defense (60%+) is a strong indicator
- Record context: Wins against currently-ranked opponents weighted 2-3x more than
  wins against unranked/debuting fighters
- Statistical sample size: Fighters with fewer than 5 UFC fights have unreliable stats —
  wider uncertainty bands on predictions
""",

    "knowledge": """
### Domain: Deep Knowledge & Historical Context

Provide long-term contextual analysis and career arc assessment:

**Knowledge Framework:**
- Career trajectory: origin, development, peak, current phase
- Historical comparisons: similar fighters, similar matchups in history
- Divisional landscape: how does this matchup fit in the division?
- Legacy implications: what's at stake beyond the fight itself?

**Key Analysis Points:**
- Evolution of skills over career
- Performance in similar matchups historically
- Training lineage and gym affiliations
- Strength of schedule and quality of wins
- Historical upset patterns in similar style matchups

**Advanced Historical Analysis:**
- Gym quality tiers: Elite camps (ATT, City Kickboxing, Elevation, Tiger Muay Thai, etc.)
  produce more consistent performances — fighters who recently joined elite camps often
  show 1-2 fight improvement curves
- Career phase mapping:
  * Rising (first 5-8 UFC fights): High ceiling, inconsistent floor
  * Peak (ages 28-33 for most divisions): Most reliable prediction window
  * Veteran (33+): Technical peak but physical decline — fight IQ compensates
  * Late career (37+): Significant decline risk — upset vulnerability increases
- Historical matchup parallels: Compare current matchup to similar historical style
  clashes in the same division for pattern-based prediction support
""",
}


def get_domain_guidance(specialist_name: str) -> str:
    """Return domain-specific guidance for a specialist, or empty string if none."""
    return DOMAIN_GUIDANCE.get(specialist_name, "")
