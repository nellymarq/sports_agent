# specialists/domain_prompts.py
# Domain-specific analytical guidance for each specialist.
# These are appended to the generic specialist template to provide
# targeted analysis frameworks.

DOMAIN_GUIDANCE = {
    "style": """
### Domain: Style Analysis

Focus on fighting archetype classification and stylistic matchup dynamics:

**Classification Framework:**
- Primary style: Striker (Boxing/Kickboxing/Muay Thai), Wrestler, Grappler, Hybrid
- Sub-archetype: Pressure fighter, Counter-striker, Volume striker, Point fighter,
  Clinch specialist, Chain wrestler, Submission hunter, Ground-and-pounder
- Stance: Orthodox, Southpaw, Switch — note advantages/disadvantages vs opponent

**Key Analysis Points:**
- Range management: Who controls distance? Long-range vs short-range preference?
- Offensive toolkit: Primary weapons (jab, leg kicks, body shots, clinch knees, takedowns)
- Defensive tendencies: Head movement, footwork, cage awareness, takedown defense
- Style clash dynamics: How does each fighter's style interact with the opponent's?
- Historical performance vs similar styles (record against wrestlers, strikers, etc.)
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
""",
}


def get_domain_guidance(specialist_name: str) -> str:
    """Return domain-specific guidance for a specialist, or empty string if none."""
    return DOMAIN_GUIDANCE.get(specialist_name, "")
