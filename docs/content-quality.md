# Content And Quality Standards

## Target Format

- Length: 35 to 60 seconds.
- Script: 105 to 145 spoken words.
- Scope: one financial mechanism per Short.
- Structure: contrarian hook, precise term, plain-English translation, tiny
  number example, practical takeaway, short CTA.
- Tone: professionally simple, credible, and clear to a normal adult.

Avoid get-rich framing, fake urgency, broad motivation, and unsupported market
claims.

## Script Quality Gate

The generator reviews the LLM draft before TTS. It checks:

- Grammar, punctuation, fragments, and run-on sentences.
- Awkward or unclear sentence structure.
- Vague pronouns and buried main ideas.
- Misleading finance terminology, guarantees, market timing, and advice
  phrasing.
- Claims that require current rate or market data.
- TTS-hostile notation such as `$1,000`, `4%`, or ticker-like acronyms.
- Inconsistent loan/APR/payment/interest math.

Minor pacing drift can become a warning. Grammar problems, risky finance claims,
current-data claims, placeholders, and broken finance math remain blocking.

## TTS-Friendly Numbers

The spoken script is normalized before Piper receives it:

- `$1,000` becomes `one thousand dollars`
- `4%` becomes `four percent`
- `$1.50` becomes `one dollar and fifty cents`
- `$1.5M` becomes `one point five million dollars`
- `401(k)` becomes `four oh one k`

Professional acronyms should be written as spoken text in the script, such as
`E T F` and `A P R`.

Every generated script should end with:

```text
Follow for more practical money tips.
```

## Finance Math Guardrails

When a script combines loan principal, APR, term, monthly payment, or total
interest, the generator estimates amortized payment and total interest before
TTS. Inconsistent examples fail before voice, captions, or rendering.

If a script states principal, APR, and total interest without a term, it also
fails because the example is under-specified.
