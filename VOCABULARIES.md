# Project categories — we need your eyes on these

We're building a searchable record of how DFO has handled Fisheries Act
authorizations, so that when a new application comes up we can pull what was
actually required on comparable past work. It only works if every authorization
gets sorted onto categories you can filter by.

Those category lists are below. **We need you to confirm them and tell us what's
missing.** It's a read-and-react, not homework. But it's worth your time now
rather than later, because these lists decide what questions the record can
answer, and changing them after everything is sorted means sorting it again.

## Why we're redoing this

The previous summary sorted work by project type. It has 98 projects and 80
distinct type labels. Almost every project sits in a category of its own, so
looking for comparable work returns a single result. That's not a search.

Read those labels and you can see what happened. Three quarters of them are
doing two jobs at once:

- `Bridge / transportation infrastructure`
- `Mine / open pit gold project`
- `Bank stabilization / SAR critical habitat`   (SAR = species at risk)
- `Maintenance dredging / marine disposal`

Left of the slash is what physically happens in the water. Right of it is the
kind of undertaking it serves. A few aren't project types at all. Species-at-risk
critical habitat is a species flag that ended up in the only column available.

Split those apart and each one becomes searchable. We think the in-water work is
the stronger of the two, because conditions attach to the work rather than the
client. A culvert replacement under a highway and one in a subdivision will
draw similar conditions. Two highway projects might not.

## What we've got so far

Everything below came out of one source: the package DFO put out under Access to
Information request A-2020-02093. It's 1,842 scanned pages holding roughly 130
authorizations, issued across all six regions. We'll call it the release. It's
all we're working from at the moment, though there are other release packages
sitting untouched.

So these lists were cut from real authorizations, not invented. Counts are
authorizations, so 14 means fourteen separate ones covered that work.

### Activity — what happens in the water (a job can have several)

Out of 58 authorizations where we could read the authorized-works clause.

| | |
|---|---|
| infilling | 19 |
| culvert installation or replacement | 14 |
| dredging | 13 |
| wharf or dock construction | 9 |
| channel realignment or diversion | 9 |
| dewatering | 8 |
| excavation or trenching | 7 |
| bank or shoreline stabilization (riprap, armouring) | 7 |
| watercourse crossing | 6 |
| bridge construction or replacement | 5 |
| temporary works (cofferdam, causeway) | 5 |
| blasting | 4 |
| water intake or outfall | 3 |
| pile driving | 3 |
| breakwater or marine structure | 3 |
| impoundment or dam works | 2 |

### Sector — the kind of undertaking

transportation (road, highway) · railway · marine and ports · municipal
infrastructure · residential or commercial development · mining · forestry ·
energy (hydroelectric, pipeline) · water supply and wastewater

### Setting

freshwater (63) · marine (33) · estuarine (2)

### Habitat features (a site can have several)

salt marsh · wetland · riparian · intertidal · subtidal · coastal marsh ·
spawning habitat · impoundment or headpond

### Waterbody

stream or tributary · river · lake · pond or impoundment · harbour · estuary ·
open coast

Nothing captures this today. We added it because "small tributary crossing" is
a real class of precedent and setting alone can't express it.

### Proponent

provincial or territorial · municipal · private company · authority or
commission · federal · Indigenous government

### Offsetting approach (often several)

Out of 73 authorizations that describe offsetting.

| | |
|---|---|
| channel or spawning works | 20 |
| riparian planting | 13 |
| reef or marine structure | 13 |
| habitat bank | 9 |
| substrate placement | 8 |
| fish passage | 5 |
| salt marsh creation | 3 |
| wetland creation | 1 |
| on-site habitat creation | 1 |

### Financial security

letter of credit · performance bond · none required · exempt (crown applicant)

### Species at risk

none identified · listed species present · determined not likely to adversely
affect

Three states, not two. The middle and last aren't the same finding, and reading
them as one is how they got conflated before.

### Condition type

timing · mitigation · monitoring · reporting · offsetting · contingency ·
financial

This is what makes conditions searchable on their own. Every numbered condition
gets one, so you can ask for in-water timing windows across a region without
reading the authorizations around them.

Unlike the categories above, this one is assigned while the document is being
read rather than sorted afterwards, because the reader is already looking at the
condition. It lands in the `Topic` column of the `Conditions` sheet.

### Free from the file number

Region comes straight out of the PATH number, so it needs no sorting: `HPAC`
Pacific, `HCAA` Central & Arctic, `HGLF` Gulf, `HMAR` Maritimes, `HQUE` Quebec,
`HNFL` Newfoundland & Labrador. Same for province and for whether the
authorization was issued under s.34.4(2)(b), s.35(2)(b), or both.

## What the first sorting pass turned up

Sorting fifteen authorizations onto these lists produced five entries the lists
have no term for. Each is a real approach, not a variant of something already
here:

| list | missing |
|---|---|
| Activity | dyke raising and widening |
| Activity | landing ramp construction, maintenance and removal |
| Offsetting | species reintroduction (an Alewife reintroduction plan) |
| Offsetting | urban stormwater retrofit (catchbasin shields) |
| Offsetting | fish salvage and relocation |

One more question, and it is about the lists rather than a gap in them. Three
offsetting terms shade into each other — **substrate placement**, **channel or
spawning works**, and **on-site habitat creation**. Rootwads and in-water log
features went to the first, constructed riffles and spawning beds to the second,
and a bare "creation of open fish habitat" to the third. Those boundaries were a
judgement call, not something the list settles, and where you draw them decides
whether a search for one returns the others.

## Where we're thin, and you'll spot it faster than we will

**The activity list came from fewer than half the documents.** We could reliably
find the authorized-works clause in 58 of 129. Anything that only appears in the
other 71 is missing from that table, and the counts under-report everything.
Tell us what you'd expect to see that isn't there.

**Proponent type is barely tested.** Sorting by name left 22 unsorted and found
exactly one Indigenous proponent, which is our matching being crude rather than
anything true about the release. The categories look right. The counts don't
mean anything yet.

**A labelling run says municipal drains need a term.** Where a row fits none of
the terms offered, a labeller writes the value's own words rather than forcing
the nearest match, and a term that collects several of those is a term the list
is missing. Over 54 rows, three landed on municipal drains — Young Drain, Van
Gaal Drain, McNamara Municipal Drain — which the waterbody list has no home for.
The others were one-offs: a university proponent, two French demolition works, a
landing ramp. The drains look like a real class; the rest may just be rare.

**We haven't grouped the numbers yet.** Searching by size means putting things
in buckets — under 100 m², 100 to 1,000, and so on. Where you draw those lines
decides whether a search hands back useful neighbours or files a footbridge next
to a mine. Impact area, monitoring duration and offsetting ratio all need lines
drawn. We'd rather set them against how the numbers actually fall than pick
round figures, so they're not in this draft.

## What we'd do next

Sort all 130 authorizations onto these categories, then hand you a sample to
check before we trust any of it. After that the record answers questions like: every
authorization in Pacific region involving culvert replacement in a stream, and
what offsetting ratio each one carried.

Two things would help most right now.

First, tell us which categories you'd actually reach for. If you'd never filter
on sector, we'll drop it and save the argument about where a log handling
facility belongs.

Second, tell us what's missing. The lists came out of one release. You've seen
many, and you'll know what shows up that this one happens not to contain.
