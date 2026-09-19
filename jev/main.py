"""Outage Excuse Court: Jev judges why prod went down, code hands out the sentence.

Jev answers narrow typed questions about each excuse. The courtroom rules
(what counts as guilty, what the punishment is) live in plain Python below.
"""

from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

EXCUSES = [
    {
        "engineer": "Priya, backend",
        "excuse": "Checkout was down for 40 minutes. Turns out our DNS TTL was set to "
        "a week and the old load balancer IP got recycled. Classic.",
    },
    {
        "engineer": "Dave, platform",
        "excuse": "I merged at 5:45pm Friday because the tests were green. Honestly I "
        "think a cosmic ray flipped a bit in the config. Mercury is also in retrograde.",
    },
    {
        "engineer": "Sam, SRE",
        "excuse": "My migration dropped an index on the orders table. I rolled it back, "
        "added a CI check, and wrote the postmortem already. That one is on me.",
    },
    {
        "engineer": "Alex, frontend",
        "excuse": "It worked on my machine. The new intern probably touched something. "
        "Or AWS. Probably AWS.",
    },
]

QUESTIONS = {
    "blames": Choice(
        instructions="Who or what does `excuse` blame for the outage?",
        criteria={
            "dns": "DNS records, TTLs, or name resolution",
            "cache": "A stale, cold, or poisoned cache",
            "vendor": "A cloud provider or third-party service",
            "teammate": "Another person, such as an intern or a colleague",
            "cosmic": "Cosmic rays, solar flares, astrology, gremlins, or bad luck",
            "self": "The engineer's own change or mistake",
        },
    ),
    "owns_it": Noul(
        instructions="In `excuse`, the engineer takes personal responsibility for the outage.",
        criteria={
            "true": "They admit their part and describe fixing or preventing it.",
            "false": "They deflect, speculate, or blame something else.",
        },
    ),
    "friday_deploy": Noul(
        instructions="According to `excuse`, the change that caused the outage was shipped "
        "on a Friday afternoon or evening.",
    ),
    "plausibility": Score(
        instructions="How plausible is `excuse` as the real root cause of a production outage?",
        criteria=[
            "Supernatural or physically absurd; no engineer would accept it",
            "Vague hand-waving with no evidence of an actual failure",
            "A believable failure mode, but unconfirmed",
            "A concrete, well-evidenced root cause seen in real production systems",
        ],
    ),
}


def sentence(result) -> str:
    """Courtroom policy: plain code over Jev's typed judgments."""
    blames = result.choices["blames"]
    owns_it = result.nouls["owns_it"].noul
    friday = result.nouls["friday_deploy"].noul
    plausible = result.scores["plausibility"].score  # 0..3

    if blames.confidence < 0.5:
        verdict = "Hung jury. Escalated to the SRE council."
    elif owns_it > 0.8:
        verdict = "Acquitted with honors. Blameless postmortem, buy this person a coffee."
    elif blames.choice == "dns" and plausible >= 2:
        verdict = "It's always DNS. Case dismissed."
    elif blames.choice == "cosmic":
        verdict = "Guilty. Must write the postmortem in rhyming couplets."
    elif blames.choice in ("teammate", "vendor") and plausible < 2:
        verdict = "Guilty of finger-pointing. Must pair with the intern for a week."
    else:
        verdict = "Probation. Add a runbook before the next on-call shift."

    if friday > 0.7:
        verdict += " Plus: pizza for the entire on-call rotation (Friday deploy)."
    return verdict


def bar(p: float, width: int = 20) -> str:
    filled = round(p * width)
    return "#" * filled + "." * (width - filled)


def main() -> None:
    with TypeSafeClient() as client:
        for case in EXCUSES:
            result = client.system_one(case, QUESTIONS)
            blames = result.choices["blames"]
            plausibility = result.scores["plausibility"]

            print(f"\n=== {case['engineer']} ===")
            print(f'"{case["excuse"]}"\n')
            print(f"  blames          {blames.choice:<8} (confidence {blames.confidence:.2f})")
            print(f"  owns it         [{bar(result.nouls['owns_it'].noul)}] {result.nouls['owns_it'].noul:.2f}")
            print(f"  friday deploy   [{bar(result.nouls['friday_deploy'].noul)}] {result.nouls['friday_deploy'].noul:.2f}")
            print(f"  plausibility    [{bar(plausibility.score / 3)}] {plausibility.score:.2f} / 3")
            print(f"\n  VERDICT: {sentence(result)}")


if __name__ == "__main__":
    main()
