# Three Sky Explorations with SPHEREx

Draft lesson content for students in grades 6–9. The three lessons and six-question quiz take about 25 minutes. Student-facing copy uses a friendly first-person voice.

## Lesson 1. Why does SPHEREx photograph the same patch of sky again?

*6 minutes*

Pay attention to the dust cloud in this video. It is the same part of the sky, but the dust looks clear in one image and harder to see in another. What might have changed between the images? [SPHEREx scans the sky](https://science.nasa.gov/photojournal/spherex-scans-the-sky/)

**Try it with a sheet of paper.** Draw a dot to represent a patch of sky. Take a strip of paper, divide it into three sections labeled A, B, and C, then slide each section over the dot. Imagine that each section is part of a filter and lets through a different range of light. The dot stays in the same place, while the light measured through each section changes.

SPHEREx does something similar as it surveys the sky. The overlapping images mean the same region passes through different parts of the filter. The telescope measures infrared light that our eyes cannot see, and NASA assigns visible colors so we can tell the bands apart on screen. Some things stand out only in the right band. Measurements across several infrared bands help astronomers find signs of ice in a star-forming region. [Water-ice map of Cygnus X](https://science.nasa.gov/photojournal/nasas-spherex-mission-maps-water-ice-throughout-cygnus-x/)

## Lesson 2. Can you find the same group of dots again?

*6 minutes*

Open **NightSky → Datasets → Epsilon Indi B → Open saved sequence**. Select **Play**, then **Pause** on any image. Choose a group of dots that is easy to remember. Use **Previous image** and **Next image** to find it again. Look at the pattern the dots make, then check the date beneath the image.

These are three real SPHEREx images taken on 29 April, 1 May, and 7 May 2025 UTC. To check whether a dot changes over time, start with two images of the **same region, taken on different dates, at similar wavelengths**. Remember the dust cloud from the previous lesson? Changing the wavelength alone can make the same region look different. [Epsilon Indi B sequence: guide and sources](../SKY_EXPLORER.md)

## Lesson 3. Did the bright dot really disappear?

*7 minutes*

The first image has a bright dot. In the next image, a purple square appears at the same position. At a glance, it may look as if the bright dot turned off. Open the legend and check what the purple square means.

Under **How to use → Try a guided comparison**, open the Epsilon Indi B image pair. A **purple square** marks missing data. An **orange square** marks data rejected during quality checks. A **dark square** is faint on the current display scale. Now try the WISE 0855 image pair and use the legend to read the marked position.

If the dot you are tracking seems to shift to the right, check the nearby dots first. If the whole group shifts in the same direction, those stars may help align the images. A preview can show where closer inspection is useful. To confirm that an object brightened, faded, or moved, we need to inspect the measurements and their uncertainties. [WISE 0855 image-pair sources](../../web/data/guided-transfer/provenance.json)

## Six-question quiz

You may reopen the images and legend while answering. Each question has one correct answer.

### 1. SPHEREx photographs a patch of sky through filter section A. If it observes the patch through section B, what additional information does the telescope measure?

- **A.** How the patch looks when zoomed in.
- **B.** How much light the patch emits in a different infrared band.
- **C.** Whether the patch became brighter over time.

### 2. In NASA’s video, the same patch of sky appears blue in one image and red in another. What do the colors on screen represent?

- **A.** The colors your eyes would see if you traveled closer.
- **B.** Two temperatures of the region.
- **C.** Two infrared bands that NASA assigned visible colors to for display.

### 3. Open the Epsilon Indi B sequence and check the dates below the images. On what dates were the earliest and latest images taken?

- **A.** 29 April and 7 May.
- **B.** 29 April and 1 May.
- **C.** 1 May and 7 May.

### 4. You want to check whether a bright dot changed over time. Which pair of images should you open first?

- **A.** The same region on the same date, in two different infrared bands.
- **B.** The same region on different dates, in two infrared bands far apart.
- **C.** The same region on different dates, in two similar infrared bands.

### 5. Look at the marked pixel in the WISE 0855 image pair. Image A shows an orange square and image B shows a gray square. What should you write in your observing notes?

- **A.** The data in image A were rejected. To compare brightness, find usable data at the same position in both images.
- **B.** The dot faded between the observations because the orange square became gray.
- **C.** The dot brightened between the observations because image B shows a gray square.

### 6. Imagine that the dot you are tracking and the three dots next to it all shift right by about the same amount. What should you do to check whether your target moved independently?

- **A.** Measure the distance from the target to the right edge of each image.
- **B.** Align the images using the nearby dots, then check whether the target still shifts relative to them.
- **C.** Zoom in on the later image until the target looks clearest.

## Answers and feedback

1. **B.** Changing the filter section lets SPHEREx measure another infrared band from the same patch of sky.
2. **C.** NASA uses visible colors to distinguish infrared bands that our eyes cannot see.
3. **A.** The sequence can loop. Check the date below each image to see which was taken first.
4. **C.** Two similar bands reduce the chance that the images look different only because of wavelength.
5. **A.** The orange square means the data there were rejected. To compare brightness, both observations need usable data at the same position.
6. **B.** A shift shared by the surrounding group may mean the images themselves are misaligned. Aligning the nearby dots helps show whether the target still moves relative to them.

## Try the lessons with students

- Run `python scripts/serve_demo.py` from the project directory. Open [NightSky](http://127.0.0.1:8766/?lang=en#night-sky) and the [guided image comparison](http://127.0.0.1:8766/?lang=en#field-guide). Both activities use saved images. For question 5, let students inspect the WISE 0855 pair and legend before showing the answer.
- Note where students need help opening the sequence, finding the same position again, and explaining their answers to questions 4–6. In the final minute, invite each student to open a sky region they would like to explore next.
- After the session, check whether students can find an image independently, explain why two images might look different, and identify what evidence they would inspect next. The Epsilon Indi sequence dates and the orange/gray squares in the WISE pair have been checked against the images and metadata. The lesson has not yet been tested with students.
