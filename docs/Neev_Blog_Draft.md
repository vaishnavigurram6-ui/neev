# Your contractor has priced four hundred houses. You're pricing one.

> **Draft for Medium. Not published.** Q16 on the Patchamomma form asks for a
> published Medium post and says plainly that it will not affect ranking — so
> this is optional, and it is here to be pasted, edited in your own voice, and
> published only if you want to.
>
> Medium does not render pasted Markdown. Two ways in: paste the text and apply
> Medium's own heading/quote styles as you go, or use *Import a story* if you
> host this somewhere first. Suggested images, in order: `figures/fig0_problem.png`
> near the top, `figures/fig1_lifecycle.png` at "Four moments", and
> `figures/fig3_pipeline.png` at "Five readers". Sub-title suggestion: *"The most
> important document in an Indian home loan is the one nobody reads."*

---

There is a moment, in a lot of Indian households, that decides more about the
next two years than anyone in the room realises.

A family has a plot. Often it was inherited, often it is on the edge of a city
that has grown out to meet it. They have a sanction letter from a housing
finance company. And they have a document from a contractor: a Bill of
Quantities, eighty to a hundred and fifty lines long, listing every activity in
the build with a quantity and a rate.

Someone signs it. Usually after an evening of looking at it, because the
contractor is waiting and the monsoon is coming and the money has been
approved.

That document is not paperwork. It is the contract. It decides what "branded
fittings" turns out to mean. It decides what is inside the scope and what will
be billed later as an extra. It is the only thing anyone can point at when there
is an argument in month seven.

And the person signing it will build **one house in their lifetime.** The person
who wrote it has built hundreds.

## The asymmetry is not about honesty

It would be easier if this were a story about bad contractors. It mostly isn't.

It is a story about a document that requires expertise to read, handed to
someone who has no reason to have that expertise, at the one moment in their
life when they need it. A contractor who has priced four hundred houses knows
what a fair rate for RCC is in that locality this year. They know which line
items are usually left out and argued about later. They know how much of the
money to ask for before the slab is cast. None of that requires malice. It
requires only that one side has done this before.

Here is my favourite example, because it is the one that convinced me the
problem is real rather than theoretical.

Steel overcharging in Indian residential construction usually does not happen
through the rate. It happens through the **grade**. Fe 415, Fe 500, Fe 500D —
higher grade steel is stronger, so a correctly designed structure needs fewer
kilograms of it for the same result. A quote that says "TMT bars" with no grade
named has left itself room to supply a lower grade, in a higher quantity, at a
rate that looks entirely normal on the page.

An owner reading that line sees "TMT bars — 4,200 kg — ₹68/kg" and thinks: that
rate seems about right. And it is about right. The rate was never the problem.

You cannot expect someone to catch that. Not once, not under time pressure, not
in a domain they will encounter exactly once.

## The advice already exists. It just cannot be used.

There is no shortage of guidance for Indian homeowners. Red-flag checklists.
Line-by-line walkthrough articles. Free spreadsheet templates. Every one of them
is well meant and most of them are correct.

And every one of them assumes the owner will sit down and manually audit a
hundred-odd technical line items across a dozen sections, checking each rate
against local benchmarks they do not have, looking for scope that is absent —
which is much harder than looking for scope that is wrong, because absence has
nothing on the page to catch your eye.

The knowledge exists. The person who needs it cannot apply it. That gap is the
whole problem, and it is a gap that software is unusually well suited to close.

## What goes wrong is slow, and then total

The failure does not show up at signing. It shows up months later, when nothing
can be done.

For the family: the money runs out before the house is habitable. This is worse
than it sounds, because a half-built structure is worth **less** than the bare
plot was — clearing it costs money. By the time the shortfall is obvious there
is no leverage left, no room to re-scope, and they are still paying rent
somewhere else.

For the lender: money has gone out against work that does not exist, or against
a budget that was never going to reach completion. If the borrower walks, the
security is an unfinished building.

Both of those trace back to the same document, unread. And it is not a rare
document — self-construction is a substantial share of affordable-housing
lending in India. Every one of those loans has a Bill of Quantities that nobody
audited line by line.

## The idea

So: read the document.

Not summarise it. Read it, the way a quantity surveyor who had seen four hundred
houses would read it — every line, against what that item actually costs in
*that locality*, this year. Flag the rate that is 22% above benchmark. Flag the
waterproofing that is missing entirely. Flag "good quality tiles" for having no
brand and no IS standard. Flag the payment schedule that wants 45% of the money
before there is any meaningful structure to show for it.

Then keep reading it. That is the part I think matters most, and the part that
makes this more than a document checker.

A construction loan is not disbursed once. It goes out in tranches, against
milestones — foundation, plinth, slab, brickwork, finishing. Each of those is a
moment where somebody says "this stage is done, release the money." So the same
contract can be checked again at every one of them: does the site actually look
like the stage being claimed? Is the money released so far in line with the
value of what is standing there? And when the contractor comes back with an
extra — as they will — what is it worth against the line that was originally
signed?

## Four moments, one contract

That gives four points where the same document is worth reading, and they are
not the same question:

- **Before signing** — what in here is inflated, missing, or vague enough to be
  argued about later?
- **At sanction** — will the approved amount actually finish this house at local
  rates? Not "is the budget internally consistent", but "does this end with a
  roof".
- **Through the build** — do the photographs from site show the stage being
  claimed for payment?
- **On every change** — what is this extra worth, measured against what was
  agreed?

## Five readers, and one rule

Under the hood this is five specialised agents in sequence, each handing its
findings to the next: one that prices the quote line by line, one that prices
what is *absent* and asks whether the sanction actually finishes the house, one
that looks at site photographs and decides what stage they show, one that turns
that into a release-or-hold judgement, and one that writes the finding twice —
once for the family, once for the credit officer.

But the design decision I would defend hardest is not about the agents. It is a
rule about restraint:

> **Every number has to come from somewhere checkable, and where there is
> nothing to check, the system says nothing.**

An item with no benchmark is withheld, not estimated. A photograph the inspector
cannot read produces no measurement, and therefore no figure derived from a
measurement. Provisional data says on screen that it is provisional.

This is not modesty for its own sake. It is the difference between a tool a
credit officer can use and one they cannot. A confident wrong number in a
lending decision is worse than a blank, because someone will act on it. The
hardest engineering in this project was not getting the agents to speak — it was
getting them to stop.

## Both sides of the table

One last thing, and it is the reason the product has two faces rather than one.

The disputes this is meant to prevent are disputes about what was agreed. That
means it is not enough for the borrower to have a good reading of the contract,
or for the lender to have one. They have to be looking at the *same* reading.

So the borrower sees their contract read line by line, in plain language, with a
note they can send their contractor themselves — because the point is that they
negotiate, not that software negotiates for them. And the lender sees the same
findings, plus their whole book ranked by exposure, plus the site photographs
next to the milestone that was claimed.

One document. One set of numbers. Two people who can now have a specific
conversation instead of a vague one.

---

*Neev — नींव — is the Hindi word for the foundation of a building. It is the
first thing that gets built, and the first thing worth verifying.*
