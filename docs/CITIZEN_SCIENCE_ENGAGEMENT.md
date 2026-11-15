# Engaging New Participants in Citizen Astronomy

[Undermind search](https://app.undermind.ai/projects/631a4a62-67aa-48ff-98c6-41e4f376367d?path=/What%20helps%20new%20volunteers%20do%20and%20return%20to%20citizen%20astronomy)

**Search date: 14 November 2026.** Undermind returned 203 results. This synthesis selects original studies on how newcomers start, classify accurately, learn, and return. It prioritizes field experiments in online astronomy projects and uses adjacent citizen-science research when the task is similar. The ranking below reflects how direct the evidence is, its fit with SPHEREx image comparison, and operating cost. I found no published evaluation of this workflow with Vietnamese-language users. [Search question and results](https://app.undermind.ai/projects/631a4a62-67aa-48ff-98c6-41e4f376367d?path=/What%20helps%20new%20volunteers%20do%20and%20return%20to%20citizen%20astronomy)

## Ten approaches, ranked by priority

### 1. Let newcomers practice step by step on the images

Open a verified image pair with the same sky region and wavelength. Ask users to compare two times and choose an interpretation. Increase difficulty as they succeed, from recognizing an image edge or masked area to distinguishing noise from a signal that needs further review. Experienced users may go directly to the comparison tool. Measure accuracy on new image pairs, step abandonment, and returning sessions.

In a Gravity Spy experiment with 386 participants, the adaptive-training group averaged 90% accuracy, completed 228 tasks, and participated in 2.5 sessions, compared with 54% accuracy, 121 tasks, and 2 sessions for participants given all training content at once. This was a noise-classification experiment on gravitational-wave data. Sky Lab could test an editor-curated sequence of examples; its effect must be measured separately. [Jackson et al., 2020](https://doi.org/10.1016/j.chb.2019.106198)

### 2. Let people try it first; make registration optional

The first image and activity should open on a phone without an account. After the trial, let users save progress locally or reopen the comparison by link. If the project has a public submission queue, monitor duplicate and spam submissions separately. Measure the rate at which new visitors complete one valid task, alongside the rate of submissions that must be rejected.

In a controlled experiment by Jay et al., about 13% of visitors contributed when registration was optional, compared with 8% when it was required. The authors report a 62% relative increase and found no quality difference in the sample of submissions they scored. That project used paleontology images. [Jay et al., 2016](https://doi.org/10.1145/2858036.2858319)

### 3. Explain what participants are being asked to check

Invite users to check whether a difference remains at the same coordinates and wavelength across two observations. Show what they need to do and who will use the result. If the first step is practice, label it clearly as practice. Measure time from invitation to first valid classification and monitor quality separately.

An email experiment with 36,513 people found that scientist-focused invitations generated the most first contributions, while science-focused invitations generated the most total contributions. Another field experiment found that clear information about task requirements improved quality and could reduce the number of contributions. These results measure specific messages in contexts other than a SPHEREx homepage. [Lee et al., 2018](https://doi.org/10.22323/2.17010202) · [Lyons & Zhang, 2019](https://doi.org/10.1371/journal.pone.0224946)

### 4. Explain why an image can be misleading

After each practice item, identify the visual cue that changes the interpretation—for example, the difference is near the image edge, disappears when both frames use the same display scale, or falls in a masked region. Offer **Not enough data**. Label each item as a verified real observation, a synthetic control, or a pair awaiting review. Show an answer only for items with a reference label.

Space Warps inserted real non-lens images and simulated lenses into its task stream to provide immediate feedback. The project demonstrates the mechanism at scale, with multiple components implemented together. In BeeWatch, newcomers who received an explanation classified better in their first session and showed signs of returning longer. Evidence for an effect on accuracy in a longer experiment was less certain. Check transfer using image pairs that were not used for practice. [Marshall et al., 2015](https://doi.org/10.1093/mnras/stv2009) · [van der Wal et al., 2016](https://doi.org/10.1111/cobi.12705)

### 5. Let users choose a target while keeping one clear question per image pair

After the first exercise, let users choose a sky region, object, or question about change over time or wavelength. Provide a ready-to-use image so beginners do not have to search the sky first. Each submission should focus on one interpretation and retain image IDs, coordinates, and observing conditions. Compare return rates, false reports, and agreement with expert review between self-selected and guided flows.

In Planet Four: Craters, users with an interface offering more choice and more task types returned more often. Some specific tasks achieved higher agreement. The simplest workflow collected the most data and also produced more false positives than experts. The results support testing choice and task structure separately, since these factors varied together in the project. [Sprinks et al., 2019](https://doi.org/10.1111/maps.13277)

### 6. Let users resume where they stopped

After an activity, let users stop, open a nearby image pair, or save their place. A continuation link should reopen the same region, time, and filter. If an image is no longer available, retain its metadata and link back to the query. If users opt into follow-up messages, connect each reminder to something specific, such as their previous comparison session or feedback. Measure how many return to complete more tasks, including people who return on their own.

Across 16 citizen-science projects, emails targeted at volunteers who had stopped participating increased the number who returned to contribute compared with a control group. A log analysis of seven Zooniverse projects also found that most participants were active for only a short time. Saving a session on-device is a Sky Lab design hypothesis motivated by this problem. [Segal et al., 2015](https://doi.org/10.1145/2740908.2743051) · [Sauermann & Franzoni, 2015](https://doi.org/10.1073/pnas.1408907112)

### 7. Return reviewed results when someone is responsible for them

A successfully submitted item should receive an ID or link that users can reopen. Show real states such as **Received**, **More images needed**, or **Reviewed**, with a short reason and evidence. When no reviewer is responsible, let users keep a private observation note. Measure response time, review time per valid submission, and how often users reopen the evidence.

Price and Lee tracked 333 people with data before and after six months in an astronomy project. Social participation was associated with changes in attitudes toward science. The BeeWatch experiment also supports the value of a specific explanation. These studies do not directly verify that submission status would make SPHEREx users return. [Price & Lee, 2013](https://doi.org/10.1002/tea.21090) · [van der Wal et al., 2016](https://doi.org/10.1111/cobi.12705)

### 8. Translate the full workflow and test phones and keyboard access

Translate invitations, examples, buttons, image-loading errors, and result explanations into Vietnamese and English. Preserve source names, IDs, UTC, µm, and coordinates. Provide a sky-region list, movement buttons, and adjacent metadata as alternatives to 3D dragging. Test task completion separately by language, device, and input method.

An IAU NameExoWorlds case study describes strong participation by Japanese groups after Japanese translation and local outreach. The authors collected 124 responses. Translation occurred alongside other recruitment activities, so its independent effect still needs measurement. Keyboard support and slow-network behavior are product accessibility requirements. [Usuda-Sato et al., 2018, p. 13](https://zenodo.org/records/14977336/files/23_04.pdf?download=1)

### 9. Offer a facilitated group session

Give clubs or teachers a link with two image pairs so learners can inspect them, explain their reasoning, and compare results with a facilitator. Use disagreements to discuss evidence quality. Try this in a group session with group-level feedback and aggregate data. A prototype can report completion per session without collecting students' ages or contact details. Measure whether learners can explain the evidence in a different image at the end of the session or the following week.

An exploratory study used interviews and diaries from 34 people aged 11–19 in environmental projects on Zooniverse. Some applied what they learned in another context, and many already had prior science experience. Price and Lee's six-month study suggests value in the social aspects of an astronomy project, with the limits of observational research. [Herodotou et al., 2022](https://doi.org/10.1016/j.compedu.2022.104515) · [Price & Lee, 2013](https://doi.org/10.1002/tea.21090)

### 10. Recognize skills and evidence a user has inspected

Show individual milestones, such as reading a UTC timestamp or explaining a case suspected to be noise. Tie each milestone to an observable action and let users reopen the image pair. Prefer a private observation log before trying public recognition. Track return rate alongside submission quality and false-report rate.

Interviews with Old Weather participants found that some liked climbing the leaderboard, while others felt it was disconnected from the goal or preferred contributing at their own pace. In a survey of 1,476 Galaxy Zoo volunteers, classification count and participation duration had a small association with astrophysics knowledge. Both studies show why a milestone feature should be evaluated by testing explanation on new images. [Eveleigh et al., 2013](https://doi.org/10.1145/2583008.2583019) · [Raddick et al., 2019](https://doi.org/10.1177/0963662519840222)

## First prototype

The **Try a guided image comparison** button opens two Epsilon Indi B images from 29 April and 1 May 2025 UTC. Both use DR1 detector D6, the same sky region, and a central wavelength near 4.458 µm. The first activity asks why a pixel with data in the earlier frame appears orange in the later frame. **Try another case** opens the 1 May and 7 May pair to identify purple as missing data. A later activity uses WISE 0855 to let viewers apply mask-reading skills to two images they have not seen in the practice. [Three activity cases](../web/assets/mission/epsilon-sequence/activities.json) · [Epsilon Indi B image sources](../web/assets/mission/epsilon-sequence/provenance.json) · [WISE 0855 image sources](../web/data/guided-transfer/provenance.json)

Image pairs for temporal comparison should include metadata for sky region, UTC, release, detector, wavelength, and mask state. For different-wavelength pairs, ask about spectral differences and show each frame's parameters. Save IDs, RA/Dec, metadata, status, and reasoning with every submitted candidate so the same evidence can be reopened. Use **Candidate for review** for an interpretation that has not been reviewed.

| Metric | Measurement |
|---|---|
| **First-time completion** | Number of new visitors who complete the first activity with a valid action divided by the number of new visitors invited to try it. Track image errors and time to result separately. |
| **Contribution quality** | Number of submissions that reviewers judge to have sufficient data divided by all submissions. Also report false-report rate on checked negative samples, agreement, and reviewer minutes per submission. |
| **Transfer to new images** | Show image pairs outside practice, including stable, noisy, and incomplete cases. Score label and reasoning against the same criteria. Compare score change before and after practice between guided and static-instruction groups, using equivalent image sets. |
| **Useful return** | Number of users who complete at least one more task on days 2–7 divided by the number who completed the first task and have had a full seven-day follow-up window. |
| **Accessibility** | Check completion on mobile, keyboard, and both languages. State that sessions on another device may be counted separately when only a local session ID is used. |

Start with observed testing with newcomers, astronomy hobbyists, and facilitated school clubs if available. Then compare a guided task entry point with a map-only entry point. Fix image samples, denominators, and criteria before testing. Allow the full return window and report sample size and uncertainty intervals if the analysis supports them. Do not use clicks as the outcome measure. An image task can teach a specific skill. The controlled YardMap experiment illustrates why learning should be measured directly instead of inferred from participation. [Dickinson & Crain, 2019](https://doi.org/10.5334/cstp.218)

## Decision recorded

Place a guided image-comparison entry point in the user guide. End with an explanation, an option to try another pair, and a private note linked to the exact two images. A data card opens the time series or A/B image comparison.

Store the note locally with region ID, coordinates, both observation IDs, UTC, wavelength, data version, and the user's choice made before seeing the explanation. Allow users to reopen a saved case and export the note. Use about 90 seconds as a testing target while letting users work at their own pace. Check that **Try another case** always has data, users can choose **Need more data**, and both languages support the full keyboard and touch workflow.

The WISE 0855 pair uses two DR1 D6 observations from 5 May 2025 and 11 May 2026 UTC, with central wavelength near 4.967 µm and the same 37×37 TAN grid. Both observations and coordinates differ from the Epsilon Indi B set. An answer in this case can test whether the skill transfers to a different image. Measuring brightness or motion requires checking FITS and error data. If public submissions are accepted later, a reviewer must be responsible and a response-time commitment must be defined. [WISE 0855 image sources](../web/data/guided-transfer/provenance.json) · [IRSA SPHEREx data products](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/)

## Research summary

The highest-priority design is a short, guided comparison of two verified SPHEREx frames from the same sky region and wavelength. Offer it without mandatory registration. Ask one scientific question, allow uncertainty, and explain evidence on curated training cases. Then let users choose another region or resume from a saved link. Next priorities are real review feedback, complete English and Vietnamese task flows, optional facilitated club sessions, and private mastery milestones tied to evidence.

Gravity Spy tested progressive training with 386 volunteers. Optional registration and recruitment framing also have experimental support in specific projects. Case studies from Planet Four, Space Warps, and NameExoWorlds inform design choices but involve different tasks and audiences. These studies provide no direct effect estimate for a Vietnamese SPHEREx tool. [Gravity Spy field experiment](https://doi.org/10.1016/j.chb.2019.106198) · [Optional registration study](https://doi.org/10.1145/2858036.2858319) · [Recruitment experiment](https://doi.org/10.22323/2.17010202) · [Undermind search](https://app.undermind.ai/projects/631a4a62-67aa-48ff-98c6-41e4f376367d?path=/What%20helps%20new%20volunteers%20do%20and%20return%20to%20citizen%20astronomy)

The user guide links to a short activity using verified Epsilon Indi B previews from 29 April and 1 May 2025 UTC. It teaches readers to recognize orange masked pixels. A follow-up compares 1 May and 7 May to identify purple missing data. A third case asks readers to apply the skill to two independent WISE 0855 observations from 5 May 2025 and 11 May 2026 UTC. Each case ends with an explanation and an optional private note tied to the exact observations. [Bilingual activity content](../web/assets/mission/epsilon-sequence/activities.json) · [Epsilon Indi B provenance](../web/assets/mission/epsilon-sequence/provenance.json) · [WISE 0855 provenance](../web/data/guided-transfer/provenance.json)
