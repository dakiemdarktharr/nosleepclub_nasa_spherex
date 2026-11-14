const sources = {
  selection: "https://science.nasa.gov/blogs/spherex/2025/03/11/nasas-spherex-mission-2/",
  telescope: "https://science.nasa.gov/photojournal/spherex-telescope-at-jpl/",
  shields: "https://www.jpl.nasa.gov/news/nasa-to-preview-sky-mapping-space-telescope-ahead-of-launch/",
  integration: "https://science.nasa.gov/blogs/punch/2025/03/04/nasas-spherex-punch-spacecraft-encapsulated-as-launch-nears/",
  launch: "https://www.nasa.gov/news-release/nasa-launches-missions-to-study-sun-universes-beginning/",
  scanning: "https://www.jpl.nasa.gov/news/nasas-spherex-space-telescope-begins-capturing-entire-sky/",
  map: "https://www.jpl.nasa.gov/images/pia26600-spherexs-first-all-sky-map/",
  archive: "https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-releases/",
  future: "https://www.jpl.nasa.gov/press-kits/spherex/mission-overview/"
};

const layerFiles = {
  instrument: "instrument.webp", shield: "shield.webp", core: "shield-core.webp",
  adapter: "adapter.webp", shell: "fairing-shell.webp", packed: "packed-stack.webp",
  payload: "payload.webp", spacecraft: "in-orbit.webp", map: "first-map.webp"
};

const archiveImages = [
  {key: "spacecraft", credit: "NASA/JPL-Caltech", date: ["03/06/2022", "3 Jun 2022"], iso: "2022-06-03", href: "https://spherex.caltech.edu/image/spherex03062022b-sectional-view-of-the-spherex-with-cosmic-structures", caption: ["Minh họa thiết kế SPHEREx bay phía trên Trái Đất.", "Artist’s concept of the SPHEREx design above Earth."]},
  {key: "instrument", credit: "NASA/JPL-Caltech", date: ["09/2023", "Sep 2023"], iso: "2023-09", href: sources.telescope, caption: ["Kính hồng ngoại và khung đỡ thử nghiệm trong phòng sạch JPL.", "The infrared telescope and its test support in a JPL cleanroom."]},
  {key: "shield", credit: "BAE Systems", date: ["11/2024 · công bố", "Nov 2024 · published"], iso: "2024-11", href: sources.shields, caption: ["Ba nón chắn photon như trong ảnh phòng sạch được JPL công bố.", "Three concentric photon shields in the cleanroom photograph published by JPL."]},
  {key: "payload", credit: "BAE Systems / Benjamin Fry", date: ["27/02/2025", "27 Feb 2025"], iso: "2025-02-27", href: sources.integration, caption: ["SPHEREx trên bộ gá tải trọng bên trong một nửa vỏ Falcon 9. Ba lớp cắt từ ảnh này được dùng cho đoạn lắp ráp.", "SPHEREx on its payload adapter inside one half of the Falcon 9 fairing. Three cutouts from this photograph appear in the assembly sequence."]},
  {key: "packed", credit: "SpaceX", date: ["03/2025 · ảnh chiến dịch phóng", "Mar 2025 · launch campaign"], iso: "2025-03", href: "https://www.spacex.com/launches/spherex", caption: ["Vỏ tải trọng Falcon 9 đã đóng. SpaceX công bố ảnh trong hồ sơ phóng; ngày chụp cụ thể chưa được ghi trong hồ sơ.", "The closed Falcon 9 fairing in SpaceX’s launch gallery. The gallery has no specific capture date."]},
  {key: "map", credit: "NASA/JPL-Caltech", date: ["18/12/2025 · công bố", "18 Dec 2025 · published"], iso: "2025-12-18", href: sources.map, caption: ["Ảnh ghép hồng ngoại toàn trời từ các quan sát tháng 5–12/2025. Màu hiển thị đại diện cho một số bước sóng hồng ngoại.", "An all-sky infrared mosaic from May–December 2025 observations. Display colors represent selected infrared wavelengths."]}
];

// Position, keyframed width and opacity are normalized to the sticky stage.
const milestones = [
  {
    date: ["02 / 2019", "Feb 2019"], iso: "2019-02", link: sources.selection, credit: "NASA/JPL-Caltech",
    title: ["NASA chọn SPHEREx", "NASA selects SPHEREx"],
    body: ["NASA chọn nhiệm vụ để khảo sát toàn trời bằng phổ hồng ngoại, phục vụ nghiên cứu lịch sử vũ trụ, thiên hà và băng trong Dải Ngân Hà.",
      "NASA selected SPHEREx for an all-sky infrared survey of cosmic history, galaxies and ice in the Milky Way."],
    view: ["Minh họa thiết kế SPHEREx", "SPHEREx design illustration"],
    layers: {spacecraft: [50, 50, 68, 1], instrument: [47, 30, 28, 0]}
  },
  {
    date: ["09 / 2023", "Sep 2023"], iso: "2023-09", link: sources.telescope, credit: "NASA/JPL-Caltech",
    title: ["Thử kính hồng ngoại", "Testing the infrared telescope"],
    body: ["JPL thử kính trong phòng sạch. Ba gương thu ánh sáng vào sáu detector hồng ngoại.",
      "JPL tested the telescope in a cleanroom. Three mirrors coupled infrared light to six detectors."],
    view: ["Kính hồng ngoại và khung thử nghiệm ở JPL", "Infrared telescope and its test support at JPL"],
    layers: {instrument: [51, 49, 37, 1], core: [30, 42, 23, 0], spacecraft: [59, 55, 55, 0]}
  },
  {
    date: ["11 / 2024", "Nov 2024"], iso: "2024-11", link: sources.shields, credit: "BAE Systems",
    title: ["Lắp ba lớp chắn photon", "Three photon shields"],
    body: ["Ba nón lồng nhau che ánh sáng và nhiệt từ Mặt Trời và Trái Đất. Đài quan sát hoàn thành thử nghiệm môi trường tại BAE Systems.",
      "Three nested cones shield the telescope from sunlight and heat. The observatory finished environmental testing at BAE Systems."],
    view: ["Ảnh lắp ghép từ kính và các nón chắn trong phòng sạch", "Photo collage of the telescope and concentric shields in the cleanroom"],
    layers: {instrument: [57, 60, 28, .48], shield: [47, 47, 56, 1], core: [49, 49, 31.6, 1], adapter: [50, 104, 52, 0], shell: [95, 47, 23, 0]}
  },
  {
    date: ["27 / 02 / 2025", "27 Feb 2025"], iso: "2025-02-27", link: sources.integration, credit: "BAE Systems / Benjamin Fry",
    title: ["Gắn lên bộ gá phóng", "Mounted for launch"],
    body: ["SPHEREx và bốn vệ tinh PUNCH được đặt chung trên bộ gá tải trọng trong khoang Falcon 9.",
      "SPHEREx and four PUNCH satellites shared the Falcon 9 payload adapter."],
    view: ["Ảnh đài quan sát, bộ gá tải trọng và mặt trong vỏ Falcon 9 được cắt ghép", "Photo cutouts of the observatory, payload adapter and Falcon 9 fairing interior"],
    layers: {payload: [48, 36, 47, 1], adapter: [50, 69, 54, 1], shell: [69, 48, 23, 1], packed: [89, 51, 31, 0]}
  },
  {
    date: ["02 / 03 / 2025", "2 Mar 2025"], iso: "2025-03-02", link: sources.integration, credit: "SpaceX",
    title: ["Khép vỏ bảo vệ Falcon 9", "Closing the Falcon 9 fairing"],
    body: ["Kỹ sư khép hai nửa vỏ để bảo vệ các vệ tinh trong lúc tên lửa bay qua khí quyển.",
      "Technicians closed the fairing halves to protect the satellites during ascent through the atmosphere."],
    view: ["Hai nửa ảnh của vỏ tải trọng Falcon 9 gặp nhau ở đường nối", "Two photographic halves of the closed Falcon 9 fairing meet at the center"],
    layers: {payload: [49, 37, 44, .15], adapter: [50, 70, 40, .12], shell: [53, 46, 18, .05], packed: [50, 51, 33, 1], map: [50, 86, 77, 0]}
  },
  {
    date: ["11 / 03 / 2025", "11 Mar 2025"], iso: "2025-03-11", link: sources.launch, credit: "NASA/JPL-Caltech",
    title: ["Lên quỹ đạo cực", "Into polar orbit"],
    body: ["Falcon 9 đưa SPHEREx lên quỹ đạo thấp đồng bộ Mặt Trời. Kính hướng ra xa Trái Đất và tránh ánh sáng trực tiếp từ Mặt Trời.",
      "Falcon 9 carried SPHEREx into low Sun-synchronous orbit. The telescope looks away from Earth and avoids direct sunlight."],
    view: ["Minh họa SPHEREx trên quỹ đạo", "Illustration of SPHEREx in orbit"],
    layers: {spacecraft: [48, 45, 68, 1], packed: [50, 10, 29, 0]}
  },
  {
    date: ["01 / 05 / 2025", "1 May 2025"], iso: "2025-05-01", link: sources.scanning, credit: "NASA/JPL-Caltech",
    title: ["Bắt đầu quan sát khoa học", "Science observations begin"],
    body: ["SPHEREx bắt đầu quét bầu trời trong 102 dải hồng ngoại. Các lần quét lặp cho phép quan sát một vùng ở các thời điểm khác nhau.",
      "SPHEREx began scanning the sky in 102 infrared bands. Repeat visits give astronomers multiple views of the same field."],
    view: ["Minh họa vệ tinh và nền ảnh hồng ngoại công bố sau đó", "SPHEREx illustration with an infrared map released later"],
    layers: {spacecraft: [56, 40, 58, 1], map: [50, 67, 78, .27]}
  },
  {
    date: ["18 / 12 / 2025", "18 Dec 2025"], iso: "2025-12-18", link: sources.map, credit: "NASA/JPL-Caltech",
    title: ["Bản đồ toàn trời đầu tiên", "The first all-sky map"],
    body: ["NASA công bố ảnh ghép toàn trời đầu tiên, tổng hợp các phép đo từ đợt quét hồng ngoại đầu tiên.",
      "NASA released the first all-sky mosaic, combining measurements from the observatory’s first infrared survey."],
    view: ["Ảnh ghép toàn trời từ dữ liệu hồng ngoại SPHEREx", "All-sky mosaic from SPHEREx infrared observations"],
    layers: {spacecraft: [52, 38, 46, .45], map: [50, 51, 91, 1]}
  },
  {
    date: ["11 / 2026", "Nov 2026"], iso: "2026-11", link: sources.archive, credit: "NASA / IPAC",
    title: ["Mở dữ liệu DR1", "The first data release"],
    body: ["IRSA công bố bản DR1. Kho lưu trữ cho phép tải ảnh phổ theo từng lần quan sát và truy cập các sản phẩm khảo sát.",
      "IRSA published DR1. The public archive provides spectral images by observation and survey data products."],
    view: ["Ảnh ghép toàn trời SPHEREx", "SPHEREx all-sky mosaic"],
    layers: {spacecraft: [55, 35, 40, .30], map: [50, 50, 94, 1]}
  },
  {
    date: ["Tiếp theo", "Planned"], iso: "", link: sources.future, credit: "NASA/JPL-Caltech",
    title: ["Quét lại bầu trời", "Revisiting the sky"],
    body: ["Kế hoạch của nhiệm vụ chính là bốn lượt quét toàn trời. Các lượt lặp mở rộng dữ liệu để đối chiếu cùng một vùng.",
      "The prime mission calls for four all-sky surveys. Repeat passes expand the record for comparing individual fields."],
    view: ["Minh họa SPHEREx và dữ liệu hồng ngoại đã công bố", "SPHEREx illustration with previously released infrared data"],
    layers: {spacecraft: [51, 41, 60, 1], map: [51, 68, 80, .48]}
  }
];

const chooseLanguage = () => document.documentElement.lang === "en" ? 1 : 0;
const clamp = (value) => Math.max(0, Math.min(1, value));
const lerp = (a, b, amount) => a + (b - a) * amount;
const smooth = (value) => {
  const t = clamp(value);
  return t * t * (3 - 2 * t);
};

function make(tag, className) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  return element;
}

function buildArchive() {
  const archive = make("details", "story-archive");
  const summary = make("summary");
  const list = make("ul", "story-archive-grid");
  const captions = archiveImages.map((item) => {
    const row = make("li");
    const source = make("a");
    source.href = item.href;
    source.target = "_blank";
    source.rel = "noopener noreferrer";
    const image = make("img", "story-archive-image");
    image.src = new URL("./assets/mission/story/" + layerFiles[item.key], import.meta.url);
    image.alt = "";
    image.loading = "lazy";
    image.decoding = "async";
    image.width = 126;
    image.height = 102;
    const date = make("time", "story-archive-date");
    date.dateTime = item.iso;
    const caption = make("p");
    const credit = make("p", "story-archive-credit");
    credit.textContent = item.credit;
    row.append(image, date, caption, credit, source);
    list.append(row);
    return (lang) => {
      date.textContent = item.date[lang];
      caption.textContent = item.caption[lang];
      source.textContent = lang ? "Original ↗" : "Mở tư liệu gốc ↗";
      source.setAttribute("aria-label", source.textContent + " · " + item.caption[lang]);
    };
  });
  archive.append(summary, list);
  return {
    archive,
    localize(lang) {
      summary.textContent = lang ? "Image archive and credits" : "Kho hình ảnh và nguồn tư liệu";
      for (const translate of captions) translate(lang);
    }
  };
}

function words(element, sentence) {
  const readable = make("span", "sr-only");
  readable.textContent = sentence;
  const display = make("span");
  display.setAttribute("aria-hidden", "true");
  const fragment = document.createDocumentFragment();
  for (const piece of sentence.split(/(\s+)/)) {
    if (!piece) continue;
    if (/^\s+$/.test(piece)) {
      fragment.append(piece);
    } else {
      const word = make("span", "story-word");
      word.textContent = piece;
      fragment.append(word);
    }
  }
  display.append(fragment);
  element.replaceChildren(readable, display);
  return Array.from(display.children);
}

function milestoneChapter(item, index) {
  const chapter = make("article", "story-chapter");
  chapter.id = "about-milestone-" + index;
  chapter.tabIndex = -1;
  const date = make(item.iso ? "time" : "span", "story-date");
  if (item.iso) date.dateTime = item.iso;
  const title = make("h3", "story-milestone-title");
  title.id = "about-milestone-title-" + index;
  chapter.setAttribute("aria-labelledby", title.id);
  const body = make("p");
  const source = make("a", "story-source");
  source.href = item.link;
  source.target = "_blank";
  source.rel = "noopener noreferrer";
  chapter.append(date, title, body, source);
  return {chapter, date, title, body, source, words: []};
}

export function mountAboutStory(container) {
  if (container.querySelector(".about-story")) return;
  const story = make("section", "about-story");
  story.setAttribute("aria-labelledby", "about-story-title");
  const heading = make("h2", "story-heading");
  heading.id = "about-story-title";
  const layout = make("div", "story-layout");
  const guide = make("nav", "story-guide");
  const track = make("div", "story-track");
  track.setAttribute("aria-hidden", "true");
  const fill = make("span");
  track.append(fill);
  const dates = make("ol", "story-date-list");
  const visual = make("figure", "story-visual");
  const art = make("div", "story-art");
  art.setAttribute("role", "img");
  const caption = make("figcaption", "story-credit");
  const chapters = make("div", "story-chapters");
  const archive = buildArchive();
  const translations = Array.from(container.querySelectorAll("[data-about-en]"), (node) => [node, node.textContent]);
  const figureImage = container.querySelector("[data-about-alt-en]");
  const originalAlt = figureImage?.alt;
  const media = matchMedia("(prefers-reduced-motion: reduce)");
  const compact = matchMedia("(max-width: 740px)");
  const images = [];
  let updateRequest;
  let current = -1;

  const artwork = (className, key) => {
    const layer = make("div", "story-layer " + className);
    const image = make("img");
    image.alt = "";
    image.decoding = "async";
    image.src = new URL("./assets/mission/story/" + layerFiles[key], import.meta.url);
    image.draggable = false;
    layer.append(image);
    art.append(layer);
    images.push({layer, key, className});
  };
  for (const key of ["map", "shell", "adapter", "instrument", "shield", "core", "payload", "spacecraft"]) artwork("story-layer-" + key, key);
  artwork("story-layer-fairing-left", "packed");
  artwork("story-layer-fairing-right", "packed");

  const aim = () => window.innerHeight * (compact.matches ? .71 : .53);

  const timeline = milestones.map((item, index) => {
    const meta = milestoneChapter(item, index);
    const li = make("li");
    const button = make("button", "story-date-button");
    button.type = "button";
    button.addEventListener("click", () => {
      const rect = meta.chapter.getBoundingClientRect();
      window.scrollTo({top: window.scrollY + rect.top + rect.height / 2 - aim(), behavior: media.matches ? "instant" : "smooth"});
      meta.chapter.focus({preventScroll: true});
    });
    li.append(button);
    dates.append(li);
    chapters.append(meta.chapter);
    return {...meta, button};
  });
  guide.append(track, dates);
  visual.append(art, caption);
  layout.append(guide, visual, chapters);
  story.append(heading, layout, archive.archive);
  container.insertBefore(story, container.querySelector("#spherex-science"));

  function localize() {
    const lang = chooseLanguage();
    for (const [node, vietnamese] of translations) node.textContent = lang ? node.dataset.aboutEn : vietnamese;
    if (figureImage) figureImage.alt = lang ? figureImage.dataset.aboutAltEn : originalAlt;
    heading.textContent = lang ? "From cleanroom to sky" : "Từ phòng sạch đến bầu trời";
    guide.setAttribute("aria-label", lang ? "Mission milestones" : "Các mốc sứ mệnh");
    archive.localize(lang);
    timeline.forEach((entry, index) => {
      const item = milestones[index];
      entry.date.textContent = entry.button.textContent = item.date[lang];
      entry.button.setAttribute("aria-label", item.date[lang] + " · " + item.title[lang]);
      entry.words = [...words(entry.title, item.title[lang]), ...words(entry.body, item.body[lang])];
      entry.source.textContent = lang ? "Source ↗" : "Nguồn ↗";
      entry.source.setAttribute("aria-label", entry.source.textContent + " · " + item.title[lang]);
    });
    current = -1;
    refresh();
  }

  function pose(key, from, to, progress, className) {
    const before = milestones[from].layers[key];
    const after = milestones[to].layers[key];
    if (!before && !after) return [50, 50, 30, 0];
    let a = before || [after[0], after[1] + 11, after[2], 0];
    let b = after || [before[0], before[1] - 10, before[2], 0];
    if (key === "packed" && !media.matches) {
      const side = className.endsWith("left") ? -1 : 1;
      if (a[3] === 0) a = [a[0] + side * 24, a[1], a[2], a[3]];
      if (b[3] === 0) b = [b[0] + side * 16, b[1], b[2], b[3]];
    }
    return a.map((value, index) => lerp(value, b[index], progress));
  }

  function render() {
    updateRequest = 0;
    if (container.hidden || !story.getClientRects().length) return;
    const viewport = window.innerHeight;
    const middle = aim();
    const bounds = timeline.map(({chapter}) => chapter.getBoundingClientRect());
    const centers = bounds.map((rect) => rect.top + rect.height / 2);
    const segment = centers.findIndex((center) => center > middle);
    const right = segment < 0 ? centers.length - 1 : segment;
    const left = Math.max(0, right - 1);
    const raw = right === left ? 0 : clamp((middle - centers[left]) / (centers[right] - centers[left]));
    const active = raw >= .5 ? right : left;
    const reduce = media.matches;
    const blend = reduce ? Number(raw >= .5) : smooth(raw);
    fill.style.setProperty("--story-progress", (left + raw) / (centers.length - 1));

    for (const {layer, key, className} of images) {
      const [x, y, width, opacity] = pose(key, left, right, blend, className);
      layer.style.left = x + "%";
      layer.style.top = y + "%";
      layer.style.width = width + "%";
      layer.style.opacity = opacity;
    }
    if (current !== active) {
      if (current >= 0) timeline[current].button.removeAttribute("aria-current");
      const item = milestones[active];
      current = active;
      timeline[current].button.setAttribute("aria-current", "step");
      art.setAttribute("aria-label", item.view[chooseLanguage()]);
      caption.textContent = item.credit;
      if (compact.matches) {
        const menu = dates.getBoundingClientRect();
        const button = timeline[current].button.getBoundingClientRect();
        if (button.left < menu.left || button.right > menu.right) dates.scrollLeft += button.left - menu.left;
      }
    }
    timeline.forEach((entry, index) => {
      const {top, bottom} = bounds[index];
      if (top >= viewport * 1.15 || bottom <= -viewport * .15) return;
      const center = centers[index];
      const progress = reduce ? 1 : clamp((viewport * 1.14 - center) / (viewport * (compact.matches ? .45 : .68)));
      const exit = reduce ? 0 : smooth((viewport * (compact.matches ? .55 : .31) - center) / (viewport * .28));
      const isCurrent = index === active;
      entry.chapter.style.opacity = isCurrent ? 1 : 1 - exit * .77;
      entry.chapter.style.setProperty("--story-shift", (18 * (1 - smooth(progress)) - 24 * exit) + "px");
      entry.words.forEach((word, position) => {
        const start = position / Math.max(1, entry.words.length - 1) * .68;
        word.style.opacity = reduce || isCurrent ? 1 : .68 + .32 * smooth((progress - start) / .32);
      });
    });
  }

  function refresh() {
    if (!updateRequest) updateRequest = requestAnimationFrame(render);
  }
  window.addEventListener("scroll", refresh, {passive: true});
  window.addEventListener("resize", refresh);
  media.addEventListener("change", refresh);
  compact.addEventListener("change", refresh);
  document.addEventListener("spherex:language", localize);
  new ResizeObserver(refresh).observe(story);
  localize();
}
