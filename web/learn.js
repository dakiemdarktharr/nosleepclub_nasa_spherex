import {lessons} from "./assets/learn/lessons.js?v=1";

const questions = lessons.flatMap(({questions}) => questions);
const letters = ["A", "B", "C"];
const storageKey = "spherex.learn.v1";
const evidence = {
  epsilon: {
    field: "Epsilon Indi B",
    directory: "assets/mission/epsilon-sequence/",
    size: 71,
    pixel: [21, 39],
    observations: [
      ["2025W18_2B_0011_3-D6.png", "2025-05-01", ["xám", "gray"]],
      ["2025W19_1B_0344_3-D6.png", "2025-05-07", ["tím", "purple"]],
    ],
  },
  wise: {
    field: "WISE 0855",
    directory: "data/guided-transfer/",
    size: 37,
    pixel: [14, 22],
    observations: [
      ["2025W19_1B_0116_1-D6.png", "2025-05-05", ["cam", "orange"]],
      ["2026W20_1A_0033_1-D6.png", "2026-05-11", ["xám", "gray"]],
    ],
  },
};

function initialProgress() {
  const fallback = {lesson: 0, view: "lesson", question: 0, answers: []};
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey));
    if (saved && Number.isInteger(saved.lesson) && lessons[saved.lesson] &&
        ["lesson", "quiz", "results"].includes(saved.view) &&
        Number.isInteger(saved.question) && questions[saved.question] &&
        Array.isArray(saved.answers) &&
        [saved.question, saved.question + 1].includes(saved.answers.length) &&
        saved.answers.every((answer, index) => Number.isInteger(answer) && questions[index].choices[answer]) &&
        (saved.view !== "results" || saved.answers.length === questions.length)) return saved;
  } catch { /* A blocked store or invalid data still allows a new session. */ }
  return fallback;
}

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

export function mountLearn(root, language) {
  const get = (id) => root.querySelector(`#learn-${id}`);
  const say = (vi, en) => language() === "vi" ? vi : en;
  const tr = (pair) => pair[language()];
  const state = initialProgress();
  const tabs = get("nav");
  const check = get("check");
  const answers = get("answers");
  const feedback = get("feedback");
  let selected = null;
  let band = 0;

  function save() {
    try { localStorage.setItem(storageKey, JSON.stringify(state)); }
    catch { /* The in-page session works without storage. */ }
  }

  function link(url, text, className) {
    const element = node("a", className, text);
    element.href = url;
    element.target = "_blank";
    element.rel = "noopener";
    return element;
  }

  function savedSequence() {
    return link(`?lang=${language()}&field=epsilon&view=saved#night-sky`,
      say("Mở chuỗi ảnh NightSky ↗", "Open the NightSky sequence ↗"), "learn-button learn-saved-sequence");
  }

  function filterModel(container, video) {
    const heading = node("h3", "", say("Thử đổi bộ lọc", "Try changing the filter"));
    const filters = node("div", "learn-filters");
    filters.setAttribute("role", "group");
    filters.setAttribute("aria-label", heading.textContent);
    const preview = node("div", "learn-filter-preview learn-band-result");
    const sky = node("div", "learn-filter-sky");
    sky.setAttribute("aria-hidden", "true");
    sky.append(node("span", "learn-filter-dust"), node("span", "learn-filter-dot"));
    const caption = node("p");
    caption.setAttribute("role", "status");
    preview.append(sky, caption);
    const views = [
      say("Dải A · Khó thấy đám bụi.", "Band A · The dust is barely visible."),
      say("Dải B · Đám bụi hiện rõ.", "Band B · The dust stands out."),
      say("Dải C · Đám bụi hiện lờ mờ.", "Band C · The dust looks faint."),
    ];
    const buttons = letters.map((letter, index) => {
      const button = node("button", "", letter);
      button.type = "button";
      button.setAttribute("aria-label", say(`Dải ${letter}`, `Band ${letter}`));
      button.addEventListener("click", () => showBand(index));
      return button;
    });
    function showBand(index) {
      band = index;
      preview.dataset.band = letters[index].toLowerCase();
      buttons.forEach((button, i) => button.setAttribute("aria-pressed", String(i === index)));
      caption.textContent = views[index];
    }
    filters.append(...buttons);
    showBand(band);
    container.append(heading, node("p", "",
      say("Mô phỏng. Đổi dải rồi nhìn chấm và đám bụi.", "Simulation. Switch bands and watch the dot and the dust.")),
    filters, preview, link(video.url, tr(video.label), "learn-button"));
  }

  function showEvidence(container, {field, directory, size, pixel, observations}) {
    const pair = node("div", "learn-evidence");
    const dates = new Intl.DateTimeFormat(language(), {dateStyle: "medium", timeZone: "UTC"});
    observations.forEach(([filename, date, color], index) => {
      const figure = node("figure");
      const wrap = node("div", "learn-image-wrap");
      const image = node("img");
      image.src = directory + filename;
      image.width = image.height = size;
      const label = say(`Ảnh ${letters[index]}`, `Image ${letters[index]}`);
      image.alt = say(`${label} vùng ${field}, ô khoanh màu ${color[0]}.`,
        `${label} of the ${field} field, with a ${color[1]} pixel marked.`);
      const marker = node("span", "learn-image-mark");
      marker.setAttribute("aria-hidden", "true");
      marker.style.left = `${100 * pixel[0] / size}%`;
      marker.style.top = `${100 * pixel[1] / size}%`;
      marker.style.width = marker.style.height = `${100 / size}%`;
      image.addEventListener("error", () => { marker.hidden = true; });
      const dateLabel = node("time", "", `${dates.format(new Date(date))} UTC`);
      dateLabel.dateTime = date;
      const caption = node("figcaption", "", `${label} · `);
      caption.append(dateLabel);
      wrap.append(image, marker);
      figure.append(wrap, caption);
      pair.append(figure);
    });
    const legend = node("ul", "learn-legend");
    legend.append(
      node("li", "", say("Cam · ô bị loại", "Orange · excluded pixel")),
      node("li", "", say("Tím · thiếu dữ liệu", "Purple · missing data")),
    );
    container.append(node("h3", "", field), pair, legend);
  }

  function renderLesson() {
    const lesson = lessons[state.lesson];
    tabs.replaceChildren(...lessons.map((item, index) => {
      const button = node("button", "learn-tab");
      button.type = "button";
      if (index === state.lesson) button.setAttribute("aria-current", "true");
      button.append(node("span", "learn-tab-index", String(index + 1)),
        node("strong", "", tr(item.title)), node("small", "", say(`${item.minutes} phút`, `${item.minutes} min`)));
      button.addEventListener("click", () => goTo("lesson", index));
      return button;
    }));
    get("lesson-meta").textContent = say(`Bài ${state.lesson + 1} / ${lessons.length} · ${lesson.minutes} phút`,
      `Lesson ${state.lesson + 1} / ${lessons.length} · ${lesson.minutes} min`);
    get("lesson-heading").textContent = tr(lesson.title);
    get("lesson-lead").textContent = tr(lesson.lead);
    get("steps").replaceChildren(...lesson.steps.map((step) => {
      const section = node("section", "learn-step");
      section.append(node("h3", "", tr(step.title)), node("p", "", tr(step.text)));
      return section;
    }));
    const activity = get("lesson-activity");
    activity.replaceChildren();
    if (lesson.id === "filters") filterModel(activity, lesson.sources[0]);
    if (lesson.id === "nightsky") {
      activity.append(node("h3", "", "Epsilon Indi B"), node("p", "",
        say("Ba ảnh SPHEREx đã lưu. Chuỗi mở trong tab mới để bạn quay lại bài này.",
          "Three saved SPHEREx images. The sequence opens in a new tab so you can return to this lesson.")),
      savedSequence());
    }
    if (lesson.id === "evidence") showEvidence(activity, evidence.epsilon);
    get("sources").replaceChildren(...lesson.sources.filter((_, i) => lesson.id !== "filters" || i > 0)
      .map((source) => link(source.url, tr(source.label))));
    get("next-lesson").textContent = state.lesson < lessons.length - 1
      ? say("Bài tiếp theo", "Next lesson") : say("Làm quiz", "Take the quiz");
  }

  function renderAnswerState() {
    const question = questions[state.question];
    const response = state.answers[state.question];
    const checked = response !== undefined;
    [...answers.children].forEach((button, index) => {
      const chosen = index === (checked ? response : selected);
      button.setAttribute("aria-pressed", String(chosen));
      button.disabled = checked;
      delete button.dataset.state;
      let status = "";
      if (checked && index === question.answer) {
        button.dataset.state = "correct";
        status = say("Đáp án đúng", "Correct answer");
      } else if (checked && chosen) {
        button.dataset.state = "incorrect";
        status = say("Bạn chọn", "Your choice");
      } else if (chosen) {
        button.dataset.state = "selected";
        status = say("Đã chọn", "Selected");
      }
      button.lastElementChild.textContent = status;
    });
    const verdict = feedback.firstElementChild;
    const explanation = feedback.lastElementChild;
    if (checked) {
      const correct = response === question.answer;
      feedback.dataset.state = correct ? "correct" : "incorrect";
      verdict.textContent = correct ? say("Đúng rồi!", "You got it!") : say("Mình xem lại nhé.", "Let’s take another look.");
      explanation.textContent = tr(question.feedback);
    } else {
      delete feedback.dataset.state;
      verdict.textContent = explanation.textContent = "";
    }
    get("progress").value = state.answers.length;
    check.disabled = !checked && selected === null;
    check.textContent = !checked ? say("Kiểm tra đáp án", "Check answer") :
      state.question < questions.length - 1 ? say("Câu tiếp theo", "Next question") : say("Xem kết quả", "See results");
  }

  function renderQuiz() {
    const question = questions[state.question];
    get("quiz-back").textContent = say("← Về bài học", "← Back to lessons");
    get("question-number").textContent = say(`Câu ${state.question + 1} / ${questions.length}`,
      `Question ${state.question + 1} / ${questions.length}`);
    get("progress").max = questions.length;
    get("question").textContent = tr(question.prompt);
    const activity = get("quiz-evidence");
    activity.replaceChildren();
    if (question === lessons[1].questions[0]) activity.append(savedSequence());
    if (question === lessons[2].questions[0]) showEvidence(activity, evidence.wise);
    activity.hidden = !activity.childElementCount;
    answers.replaceChildren(...question.choices.map((choice, index) => {
      const button = node("button", "learn-answer");
      button.type = "button";
      button.append(node("span", "learn-answer-key", letters[index]),
        node("span", "learn-answer-text", tr(choice)), node("span", "learn-answer-status"));
      button.addEventListener("click", () => {
        selected = index;
        renderAnswerState();
      });
      return button;
    }));
    renderAnswerState();
  }

  function renderResults() {
    const score = state.answers.filter((answer, index) => answer === questions[index].answer).length;
    get("results-heading").textContent = say("Bạn đã xong sáu câu!", "You’ve finished all six questions!");
    get("score").textContent = `${score} / ${questions.length}`;
    get("results-summary").textContent = say("Thử mở một vùng trời bạn tò mò và dùng lại những gì vừa khám phá.",
      "Open a part of the sky you’re curious about and try what you just learned.");
    get("retry").textContent = say("Làm lại quiz", "Play again");
    get("results-back").textContent = say("Về bài học", "Back to lessons");
  }

  function render() {
    root.dataset.view = state.view;
    for (const view of ["lesson", "quiz", "results"]) get(view).hidden = state.view !== view;
    tabs.hidden = state.view !== "lesson";
    if (state.view === "lesson") renderLesson();
    if (state.view === "quiz") renderQuiz();
    if (state.view === "results") renderResults();
  }

  function goTo(view, lesson = state.lesson) {
    state.view = view;
    state.lesson = lesson;
    save();
    render();
    const heading = get(view === "quiz" ? "question" : `${view}-heading`);
    heading.focus({preventScroll: true});
    get(view).scrollIntoView({block: "start", behavior: "instant"});
  }

  function openQuiz() {
    goTo(state.answers.length === questions.length && state.view !== "quiz" ? "results" : "quiz");
  }

  get("start").addEventListener("click", () => goTo("lesson"));
  get("open-quiz").addEventListener("click", openQuiz);
  get("next-lesson").addEventListener("click", () => {
    if (state.lesson < lessons.length - 1) goTo("lesson", state.lesson + 1);
    else openQuiz();
  });
  get("quiz-back").addEventListener("click", () => goTo("lesson"));
  get("results-back").addEventListener("click", () => goTo("lesson"));
  get("retry").addEventListener("click", () => {
    state.question = 0;
    state.answers = [];
    selected = null;
    goTo("quiz");
  });
  check.addEventListener("click", () => {
    if (state.answers[state.question] === undefined) {
      if (selected === null) return;
      state.answers.push(selected);
      save();
      renderAnswerState();
      return;
    }
    selected = null;
    if (state.question === questions.length - 1) goTo("results");
    else {
      state.question += 1;
      goTo("quiz");
    }
  });
  document.addEventListener("spherex:language", render);
  render();
  get("start").disabled = get("open-quiz").disabled = false;
  if (!root.hidden && state.view !== "lesson") get(state.view).scrollIntoView({block: "start", behavior: "instant"});
}
