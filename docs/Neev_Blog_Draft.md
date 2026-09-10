# Nobody reads the paper that decides their house

### And honestly? Nobody could.

> **Draft for Medium. Not published.** Q16 on the Patchamomma form asks for a
> published Medium post and says plainly it won't affect ranking — so this is
> optional. It's here to be pasted, edited into your own voice, and published
> only if you feel like it.
>
> Medium doesn't render pasted Markdown. Two ways in: paste the text and apply
> Medium's own heading styles as you go, or use *Import a story* if you host it
> somewhere first. Images, in order: `figures/fig0_problem.png` near the top,
> `figures/fig1_lifecycle.png` at "Four moments", `figures/fig3_pipeline.png` at
> "Five readers".

---

Picture a kitchen table on a weekday evening.

There's a family sitting at it. They've got a plot of land — maybe it came down
from a grandparent, maybe it's on the edge of a city that's been quietly growing
out toward it for twenty years. They've got a sanction letter from a housing
finance company, which took months and a lot of paperwork to get. And they've
got a document the contractor dropped off: a Bill of Quantities. Eighty lines.
Sometimes a hundred and fifty. Every job in the build, with a quantity and a
rate next to it.

Somebody's going to sign that tonight, or maybe tomorrow. The contractor's
waiting. The monsoon isn't going to wait either.

Here's the thing I don't think most of us realise about that piece of paper.
It isn't paperwork. It's *the contract*. It's the thing that decides what
"branded fittings" turns out to mean six months from now. It decides what's
included and what gets billed later as an extra. And when there's an argument in
month seven — and there's usually an argument in month seven — it's the only
thing anyone can point at.

So it matters enormously. And the person signing it is going to build exactly
one house in their entire life.

The person who wrote it has built hundreds.

*[INSERT `figures/fig0_problem.png` — the asymmetry]*

## This isn't a story about crooked builders

I want to get that out of the way early, because it's where everyone's mind
goes first, and I think it's mostly wrong.

Think about sitting down to your first ever hand of cards against someone who's
played four hundred. They're not cheating. They don't need to. They just know
which way things tend to go, and you're finding out as you play.

That's the situation. A contractor who's priced four hundred houses knows what
RCC actually costs in that neighbourhood this year. They know which line items
get quietly left out and argued about later. They know how much of the money to
ask for up front, before there's anything standing on the plot to show for it.
None of that requires bad intentions. It only requires that one person has done
this before and the other hasn't.

Let me give you my favourite example, because it's the one that convinced me
this is a real problem and not just a vibe.

Steel. If someone's overcharging you on steel in an Indian house build, it
usually isn't the rate. It's the *grade*. There's Fe 415, Fe 500, Fe 500D —
and stronger steel means a properly designed structure needs fewer kilos of it
to do the same job. So a line that just says "TMT bars," with no grade written
down, has quietly left the door open: supply the weaker stuff, more of it, at a
rate that looks completely fine.

And it does look fine. That's the part that gets me. The owner checks the rate,
decides it seems about right, and they're *correct* — the rate was never where
the money was going.

You can't reasonably expect anyone to catch that. Not once in a lifetime, not
with the contractor's van idling outside, not in a subject they'll never need to
think about again.

## The advice is all out there already

And that's the frustrating bit, honestly. Search for this and you'll find plenty
— red-flag checklists, line-by-line walkthroughs, free spreadsheet templates.
People have written good, careful stuff about it. Most of it is right.

But look at what every single one of them quietly assumes. That you'll sit down
and work through a hundred-odd technical lines across a dozen sections. That
you'll check each rate against local benchmarks, which you don't have. And that
you'll spot the things that *aren't* there — which is so much harder than
spotting something wrong, because a missing item has nothing on the page for
your eye to snag on. You can't skim for an absence.

So the knowledge exists. It just can't reach the person who needs it, at the one
moment they need it. That's the whole gap — and it happens to be exactly the
kind of gap software is good at closing.

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
