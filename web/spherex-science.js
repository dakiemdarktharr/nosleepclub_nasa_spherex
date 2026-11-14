/* SPHEREx educational exhibit. All drawings are authored schematics, not data. */
(() => {
  "use strict";
  const instances = new WeakMap();
  let instanceCount = 0;
  const SOURCES = {
    mission: ["Bock et al. · 2026", "https://arxiv.org/abs/2511.02985"],
    orbit: ["JPL · Mission overview", "https://www.jpl.nasa.gov/press-kits/spherex/mission-overview/"],
    spacecraft: ["JPL · Spacecraft", "https://www.jpl.nasa.gov/press-kits/spherex/mission-overview/spacecraft/"],
    instrument: ["Caltech · Instrument", "https://spherex.caltech.edu/page/instrument"],
    calibration: ["Korngut et al. · 2026", "https://arxiv.org/abs/2603.29835"],
    inflation: ["Caltech · Inflation", "https://spherex.caltech.edu/page/the-origin-of-the-universe"],
    galaxies: ["Caltech · Galaxy formation", "https://spherex.caltech.edu/page/the-origin-and-history-of-galaxies"],
    ice: ["Caltech · Interstellar ices", "https://spherex.caltech.edu/page/the-origin-of-water-in-planetary-systems"],
    map: ["JPL · 18 Dec 2025", "https://www.jpl.nasa.gov/news/nasas-spherex-observatory-completes-first-cosmic-map-like-no-other/"],
    comet: ["NASA · 4 Feb 2026", "https://science.nasa.gov/blogs/3iatlas/2026/02/04/nasas-spherex-mission-tracks-brightening-of-interstellar-comet/"],
    cometPaper: ["Lisse et al. · 2026", "https://arxiv.org/abs/2601.06759"],
    icePaper: ["Hora et al. · ApJ 1001, 165", "https://authors.library.caltech.edu/records/ba2ay-z4658"],
    dwarf: ["NASA · 8 Oct 2026", "https://www.nasa.gov/missions/spherex/nasas-spherex-telescope-sees-menagerie-of-brown-dwarfs/"],
    dwarfPaper: ["Rustamkulov et al. · 2026", "https://arxiv.org/abs/2607.00543"],
    dr1: ["IRSA · DR1", "https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_dr1.html"],
    products: ["IRSA · Data products", "https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/"],
    supplement: ["IRSA · Explanatory supplement", "https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp.pdf"],
    pipeline: ["Akeson et al. · Pipeline", "https://arxiv.org/abs/2511.15823"],
    mapmaking: ["Cukierman et al. · Map making", "https://arxiv.org/abs/2603.25790"],
    publications: ["Caltech · Publications", "https://spherex.caltech.edu/page/publications"]
  };
  const BANDS = ["0.75–1.09", "1.10–1.62", "1.63–2.41", "2.42–3.82", "3.83–4.41", "4.42–5.00"];
  const COLORS = ["#80d8ff", "#69e1dc", "#ccff00", "#ffd35c", "#ff9965", "#eb8bcf"];
  const escape = value => String(value).replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));

  function mount(container) {
    if (!container || container.nodeType !== 1) return null;
    if (instances.has(container)) return instances.get(container);
    const prefix = "ss-" + (++instanceCount) + "-";
    const state = { goal: 0, orbit: 0, engineering: 0, detector: 0, position: 0 };
    let language = document.documentElement.lang.toLowerCase().startsWith("vi") ? "vi" : "en";
    const t = (vi, en) => language === "vi" ? vi : en;
    const id = name => prefix + name;
    const sources = (...keys) => `<div class="ss-sources">${keys.map(key => `<a href="${SOURCES[key][1]}" target="_blank" rel="noopener noreferrer">${SOURCES[key][0]} ↗</a>`).join("")}</div>`;
    const heading = (number, title, subtitle) => `<div class="ss-heading"><span class="ss-number" aria-hidden="true">${number}</span><div><h3>${title}</h3>${subtitle ? `<p>${subtitle}</p>` : ""}</div></div>`;
    const controls = (name, labels, active) => `<div class="ss-controls" role="group" aria-label="${escape(t("Chọn nội dung", "Choose a topic"))}">${labels.map((label, index) => `<button type="button" data-science-action="${name}" data-value="${index}" data-focus="${name}-${index}" aria-pressed="${index === active}" aria-controls="${id(name + "-panel")}">${label}</button>`).join("")}</div>`;
    const detail = (key, title, body) => `<details class="ss-detail" data-detail="${key}"><summary>${title}</summary><p>${body}</p></details>`;
    const svg = (key, title, body, viewBox = "0 0 600 390") => `<svg viewBox="${viewBox}" role="img" aria-labelledby="${id(key + "-svg-title")}"><title id="${id(key + "-svg-title")}">${escape(title)}</title>${body}</svg>`;
    const caption = extra => `<figcaption class="ss-caption">${t("Sơ đồ giải thích · không theo tỉ lệ.", "Explanatory schematic · not to scale.")} ${extra || ""}</figcaption>`;
    const star = (x, y, r = 3, color = "#f0f4ff") => `<circle cx="${x}" cy="${y}" r="${r}" fill="${color}"/>`;
    function goalDiagram() {
      const points = Array.from({ length: 52 }, (_, i) => ({ x: 60 + ((i * 79 + 17) % 470), y: 57 + ((i * 53 + 31) % 260) }));
      let body;
      if (state.goal === 0) {
        body = `<path d="M70 310L298 90L538 310ZM70 310L300 360L538 310M298 90L300 360" fill="#11254a" stroke="#59749b"/>` +
          points.map((p, i) => star(105 + (p.x - 60) * .8, 120 + (p.y - 57) * .72, 1.5 + i % 3, i % 4 ? "#91ddf4" : "#ccff00")).join("") +
          `<text x="30" y="35">${t("Thiên hà → dịch đỏ → bản đồ 3D", "Galaxies → redshifts → 3D distribution")}</text><text x="300" y="345" text-anchor="middle" class="ss-svg-small">${t("Mỗi chấm tượng trưng một thiên hà", "Each dot represents a galaxy")}</text>`;
      } else if (state.goal === 1) {
        body = `<ellipse cx="300" cy="195" rx="250" ry="125" fill="#18395a" stroke="#7598be"/><ellipse cx="300" cy="195" rx="250" ry="30" fill="#6cbccd" opacity=".18"/>` +
          points.map((p, i) => star(p.x, 92 + (p.y - 57) * .72, i % 5 ? 2 : 5, "#c8e4f5")).join("") +
          `<circle cx="300" cy="74" r="29" fill="none" stroke="#ccff00" stroke-width="3"/><circle cx="300" cy="316" r="29" fill="none" stroke="#ccff00" stroke-width="3"/><text x="300" y="31" text-anchor="middle" class="ss-svg-lime">${t("Vùng sâu gần cực hoàng đạo", "Deep fields near ecliptic poles")}</text><text x="300" y="367" text-anchor="middle">${t("Đo ánh sáng nền và độ gồ ghề của nó", "Measure background light and its fluctuations")}</text>`;
      } else {
        body = `<path d="M135 225C80 155 170 72 250 116C325 38 410 118 401 151C520 168 476 290 384 276C309 337 215 282 135 225Z" fill="#254878" stroke="#81d8f0" stroke-width="2"/>` +
          Array.from({ length: 18 }, (_, i) => star(160 + (i * 47 % 250), 140 + (i * 31 % 110), 5, "#7bdfff")).join("") +
          `<path d="M35 195H140M450 195H560" stroke="#ffd35c" stroke-width="3" stroke-dasharray="8 7"/><text x="300" y="42" text-anchor="middle">${t("Ánh sao đi qua bụi phủ băng", "Starlight through ice-coated dust")}</text><text x="300" y="323" text-anchor="middle" class="ss-svg-big">H₂O · CO₂ · CO</text><text x="300" y="359" text-anchor="middle" class="ss-svg-small">${t("Dấu hấp thụ giúp nhận ra phân tử", "Absorption features help identify molecules")}</text>`;
      }
      return `<figure class="ss-figure"><div class="ss-diagram">${svg("goal", t("Minh họa phương pháp của mục tiêu khoa học đang chọn", "Illustration of the selected science method"), body)}</div>${caption(t("Các chấm, đám mây và đường nét không phải dữ liệu đo.", "Dots, clouds and lines are not measured data."))}</figure>`;
    }
    function goalPanel() {
      const goals = [
        { title: t("Điều gì đã gieo mầm cấu trúc vũ trụ?", "What seeded cosmic structure?"), body: t("SPHEREx đo phổ thiên hà để ước lượng dịch đỏ và lập bản đồ phân bố ba chiều. Thống kê cách các thiên hà tụ lại giúp kiểm tra những mô hình lạm phát vũ trụ sơ khai.", "SPHEREx measures galaxy spectra to estimate redshifts and map their three-dimensional distribution. Galaxy clustering statistics test models of inflation in the early universe."), limit: t("Đây là phép suy luận từ cấu trúc quan sát được; kính không chụp trực tiếp khoảnh khắc Big Bang.", "This is an inference from observed structure; the telescope does not directly photograph the Big Bang."), advanced: t("Dịch đỏ cho biết các đặc trưng phổ bị dịch về bước sóng dài hơn. Phân tích vũ trụ học còn cần mô hình, lựa chọn mẫu và kiểm soát sai số hệ thống; một bản đồ đẹp chưa phải kết luận về cơ chế lạm phát.", "Redshift describes spectral features shifting to longer wavelengths. Cosmological inference also needs models, sample selection and systematic-error control; a striking map alone does not establish the mechanism of inflation."), source: "inflation" },
        { title: t("Ánh sáng thiên hà kể lại lịch sử nào?", "What history is hidden in galaxy light?"), body: t("Ngoài từng thiên hà, SPHEREx nghiên cứu ánh sáng nền ngoài Ngân Hà. Những vùng được quan sát sâu gần hai cực hoàng đạo cho phép đo biến thiên không gian của ánh sáng cộng dồn từ các quần thể thiên hà.", "Beyond individual galaxies, SPHEREx studies the extragalactic background light. Deep observations near the ecliptic poles measure spatial variations in the accumulated light of galaxy populations."), limit: t("Cần tách ánh sáng tiền cảnh và ảnh hưởng thiết bị trước khi suy ra lịch sử hình thành thiên hà.", "Foreground light and instrumental effects must be separated before inferring galaxy formation history."), advanced: t("Cực hoàng đạo là hai hướng vuông góc với mặt phẳng quỹ đạo Trái Đất quanh Mặt Trời, khác với cực Bắc và Nam địa lý. Chiến lược quét tạo nhiều lần quan sát tại các vùng này.", "The ecliptic poles are perpendicular to Earth’s orbital plane around the Sun, rather than Earth’s geographic poles. The survey strategy repeatedly visits these regions."), source: "galaxies" },
        { title: t("Nước và các phân tử được cất giữ ở đâu?", "Where are water and other molecules stored?"), body: t("Trong mây liên sao và vùng hình thành sao, các phân tử có thể đóng băng trên hạt bụi. Những vết hấp thụ trong phổ giúp SPHEREx khảo sát băng nước, carbon dioxide và carbon monoxide.", "In interstellar clouds and star-forming regions, molecules can freeze onto dust grains. Absorption features let SPHEREx investigate water, carbon dioxide and carbon monoxide ices."), limit: t("Tìm phân tử liên quan tới hóa học sự sống không có nghĩa là phát hiện sự sống.", "Finding molecules relevant to prebiotic chemistry is not a detection of life."), advanced: t("Các phân tử hấp thụ ở những dải bước sóng đặc trưng. Độ sâu của đặc trưng phải được phân tích cùng nền phổ, bụi, độ phân giải và sai số; màu hiển thị đơn lẻ không xác định thành phần hóa học.", "Molecules absorb in characteristic wavelength bands. Feature depth must be interpreted with the continuum, dust, resolution and uncertainties; a display color alone does not identify a chemical composition."), source: "ice" }
      ];
      const selected = goals[state.goal];
      return `<div class="ss-split">${goalDiagram()}<div class="ss-copy"><span class="ss-eyebrow">${t("Mục tiêu khoa học", "Science objective")} ${state.goal + 1} / 3</span><h4>${selected.title}</h4><p aria-live="polite">${selected.body}</p><p class="ss-note">${selected.limit}</p>${detail("goal-detail", t("Đi sâu hơn", "Go deeper"), selected.advanced)}${sources(selected.source)}</div></div>`;
    }
    function orbitPanel() {
      const labels = [t("Quỹ đạo cực", "Polar orbit"), t("Hướng an toàn với Mặt Trời", "Sun-safe pointing"), t("Quét bầu trời", "Survey coverage")];
      let drawing;
      if (state.orbit === 0) {
        drawing = `<circle cx="62" cy="192" r="37" fill="#ffd35c"/><path d="M110 130H240M110 192H240M110 254H240" stroke="#ffd35c" stroke-width="2" stroke-dasharray="7 7"/><circle cx="358" cy="192" r="76" fill="#326caa"/><path d="M358 116A76 76 0 0 1 358 268Z" fill="#111e3c"/><ellipse cx="358" cy="192" rx="45" ry="153" fill="none" stroke="#75e5ff" stroke-width="2"/><path d="M358 101V69M358 283V315" stroke="#b8cbe6" stroke-dasharray="3 4"/><rect x="347" y="30" width="22" height="20" fill="#ccff00"/><text x="62" y="252" text-anchor="middle">${t("Mặt Trời", "Sun")}</text><text x="358" y="200" text-anchor="middle">${t("Trái Đất", "Earth")}</text><text x="425" y="72">SPHEREx</text><path d="M420 76L369 40" stroke="#b8cbe6"/><text x="358" y="369" text-anchor="middle" class="ss-svg-small">${t("Gần ranh giới ngày / đêm", "Near the day / night boundary")}</text>`;
      } else if (state.orbit === 1) {
        drawing = `<circle cx="67" cy="205" r="38" fill="#ffd35c"/><text x="67" y="267" text-anchor="middle">${t("Mặt Trời", "Sun")}</text><path d="M112 205H321" stroke="#ffd35c" stroke-width="3" stroke-dasharray="8 6"/><path d="M338 202L370 48" stroke="#75e5ff" stroke-width="4"/><path d="M370 48L358 66M370 48L374 69" stroke="#75e5ff" stroke-width="3"/><path d="M286 205A52 52 0 0 1 349 154" fill="none" stroke="#ccff00" stroke-width="3"/><text x="242" y="145" class="ss-svg-big">≥ 91°</text><path d="M291 211L363 226L358 272L317 264Z" fill="#bbc4d9" stroke="#fff"/><rect x="318" y="267" width="37" height="34" fill="#b1955f"/><path d="M316 291H245V326H316" fill="#244f86" stroke="#81a2d2"/><text x="398" y="70" class="ss-svg-cyan">${t("Hướng miệng", "Shield opening")}</text><text x="398" y="90" class="ss-svg-small">${t("bộ chắn photon", "direction")}</text><text x="300" y="365" text-anchor="middle" class="ss-svg-small">${t("91° áp dụng cho bộ chắn, không phải trục kính", "91° applies to the shields, not the telescope axis")}</text>`;
      } else {
        drawing = `<ellipse cx="300" cy="190" rx="250" ry="132" fill="#13294b" stroke="#7491bb"/>${[-70, -35, 0, 35, 70].map((angle, i) => `<ellipse cx="300" cy="190" rx="${22 + i * 25}" ry="132" fill="none" stroke="${i === 2 ? "#ccff00" : "#6582a7"}" stroke-width="${i === 2 ? 8 : 2}" transform="rotate(${angle} 300 190)" opacity="${i === 2 ? .8 : .5}"/>`).join("")}<text x="300" y="34" text-anchor="middle">${t("Dải quét thay đổi theo mùa", "Survey strips advance with the seasons")}</text><text x="300" y="370" text-anchor="middle" class="ss-svg-small">${t("Sơ đồ vùng phủ; không phải bản đồ quan sát thực", "Coverage concept; not an actual observation map")}</text>`;
      }
      const descriptions = [
        t("SPHEREx bay quanh Trái Đất trên quỹ đạo gần cực, đồng bộ Mặt Trời, ở độ cao khoảng 650 km. Một vòng mất khoảng 98 phút. Quỹ đạo gần ranh giới ngày–đêm giúp duy trì điều kiện chiếu sáng thuận lợi.", "SPHEREx follows a near-polar, Sun-synchronous orbit about 650 km above Earth. One orbit takes about 98 minutes. Flying near the day–night boundary helps maintain favorable illumination."),
        t("Đồng bộ Mặt Trời không có nghĩa là kính nhìn vào Mặt Trời. Miệng bộ chắn photon hướng cách Mặt Trời ít nhất 91°. Kính bên trong hơi nghiêng về phía Mặt Trời để phủ đủ bầu trời, nhưng nhìn ra xa Trái Đất. Tấm pin gần như luôn hướng về Mặt Trời để nhận điện.", "Sun-synchronous does not mean Sun-pointing. The photon-shield opening points at least 91° away from the Sun. The telescope inside tilts slightly toward the Sun for full-sky coverage, while looking away from Earth. The solar panel almost always faces the Sun for power."),
        t("Trong mỗi vòng quỹ đạo, vệ tinh quan sát một dải trời. Khi Trái Đất đi quanh Mặt Trời, dải này tiến dần để bao phủ bầu trời trong khoảng sáu tháng. Kế hoạch khảo sát chính gồm bốn lượt quét toàn trời.", "Each orbit observes a strip of sky. As Earth travels around the Sun, that strip advances to cover the sky in roughly six months. The primary survey plan contains four all-sky passes.")
      ];
      return `<div class="ss-split"><figure class="ss-figure"><div class="ss-diagram">${svg("orbit", labels[state.orbit], drawing)}</div>${caption(t("Vị trí, góc nhìn và kích thước được giản lược; không phải theo dõi vệ tinh trực tiếp.", "Positions, viewpoints and sizes are simplified; this is not live satellite tracking."))}</figure><div class="ss-copy"><h4>${labels[state.orbit]}</h4><p aria-live="polite">${descriptions[state.orbit]}</p><div class="ss-facts"><div><strong>650 km</strong><span>${t("độ cao xấp xỉ", "approximate altitude")}</span></div><div><strong>98 ${t("phút", "min")}</strong><span>${t("một vòng quỹ đạo", "one orbit")}</span></div><div><strong>~6 ${t("tháng", "months")}</strong><span>${t("một lượt toàn trời", "one all-sky pass")}</span></div></div>${sources("orbit", "spacecraft", "mission")}</div></div>`;
    }
    function engineeringPanel() {
      const selected = state.engineering;
      const opacity = part => selected === part ? 1 : .32;
      const shield = `<g opacity="${opacity(1)}"><path d="M126 76L248 268L359 268L478 76" fill="#6786b1" fill-opacity=".2" stroke="#e2e9f4" stroke-width="5"/><path d="M162 90L261 254L346 254L442 90" fill="none" stroke="#99adca" stroke-width="5"/><path d="M203 108L275 244L331 244L400 108" fill="none" stroke="#cbd6e8" stroke-width="5"/><ellipse cx="302" cy="76" rx="176" ry="32" fill="none" stroke="#e2e9f4" stroke-width="5"/><ellipse cx="302" cy="90" rx="140" ry="26" fill="none" stroke="#99adca" stroke-width="4"/></g>`;
      const optics = `<g opacity="${opacity(0)}"><rect x="277" y="132" width="48" height="112" fill="#131d30" stroke="#c5e5ff" stroke-width="2"/><path d="M286 162L318 201L288 226L316 236" fill="none" stroke="#ccff00" stroke-width="3"/><path d="M284 197L299 202M311 223L321 227M279 234L291 238" stroke="#fff" stroke-width="4"/><path d="M286 60V162" stroke="#ccff00" stroke-dasharray="7 5" stroke-width="3"/><rect x="315" y="232" width="10" height="9" fill="#75e5ff"/></g>`;
      const cooling = `<g opacity="${opacity(2)}"><path d="M254 266L301 282L351 266M244 280L301 298L361 280M234 294L301 312L371 294" fill="none" stroke="#75e5ff" stroke-width="5"/><path d="M248 282L182 250L116 229M356 282L422 250L486 229" fill="none" stroke="#75e5ff" stroke-width="3" stroke-dasharray="8 6"/><path d="M116 229L127 245M116 229L136 227M486 229L474 245M486 229L466 227" fill="none" stroke="#75e5ff" stroke-width="3"/></g>`;
      const power = `<g opacity="${opacity(3)}"><rect x="264" y="316" width="75" height="56" fill="#b39b6d" stroke="#e8d1a6"/><rect x="112" y="313" width="137" height="60" fill="#244f86" stroke="#a6c8ee" stroke-width="2"/><path d="M145 313V373M179 313V373M213 313V373M112 343H249" stroke="#7896c1"/><path d="M249 343H286V328H315" stroke="#ffd35c" stroke-width="4" fill="none"/><path d="M303 350q40 0 47 34M303 350q55 0 65 34" stroke="#f2f5ff" fill="none"/><path d="M60 282L112 319M66 313L112 340" stroke="#ffd35c" stroke-width="3"/></g>`;
      const labels = [t("Đường đi của ánh sáng", "The light path"), t("Ba lớp chắn photon", "Three photon shields"), t("Đường thoát nhiệt", "The heat path"), t("Điện và liên lạc", "Power and communication")];
      const copy = [
        [t("Ánh sáng đi qua khẩu độ, được ba gương dẫn tới bộ tách chùm dichroic, rồi tới hai cụm detector. Kính nhôm có khẩu độ hiệu dụng 20 cm; trường nhìn khoảng 11,3° × 3,5°.", "Light enters the aperture and is relayed by three mirrors to a dichroic beam splitter and two detector assemblies. The aluminum telescope has a 20 cm effective aperture and a field of view of about 11.3° × 3.5°."), t("Bộ tách dichroic phân chia ánh sáng thành nhánh bước sóng ngắn và dài. Đường gấp khúc trong hình chỉ mô tả thứ tự chức năng, không phải phép truy vết tia quang học.", "The dichroic separates shorter and longer wavelengths. The drawn zigzag shows functional order, not a validated optical ray trace.")],
        [t("Ba lớp nón lồng nhau chặn ánh sáng và nhiệt từ Mặt Trời, Trái Đất. Các tấm nhôm với lõi tổ ong tạo cấu trúc nhẹ. Phần nón rộng bảo vệ nhiệt; đó không phải một gương thu sáng khổng lồ.", "Three nested cones intercept light and heat from the Sun and Earth. Aluminum sheets with a honeycomb core provide a light structure. The broad cones provide thermal protection; they are not an enormous collecting mirror."), t("Khẩu độ kính nằm sâu trong bộ chắn. Giữ vật liệu, hình học và vị trí tương đối chính xác quan trọng với kiểm soát nhiệt; sơ đồ này không thay thế bản vẽ chế tạo.", "The telescope aperture sits deep inside the shields. Materials, geometry and relative placement matter to thermal control; this schematic is not a manufacturing drawing.")],
        [t("Các bộ tản nhiệt rãnh V bên dưới kính giúp bức xạ nhiệt thoát ra không gian. Chúng là bộ phận khác với ba lớp chắn phía trên. Làm lạnh thụ động giúp giảm ánh hồng ngoại do chính thiết bị phát ra.", "V-groove radiators below the telescope direct thermal radiation toward space. They are distinct from the three shields above. Passive cooling reduces the infrared glow produced by the instrument itself."), t("Thiết bị hoạt động ở nhiệt độ rất thấp mà không cần máy làm lạnh chủ động trong vận hành bình thường. “Thụ động” mô tả cơ chế làm lạnh; máy tính và detector vẫn cần điện.", "The instrument operates at very low temperatures without active refrigeration during normal operation. “Passive” describes the cooling mechanism; computers and detectors still require electricity.")],
        [t("Tấm pin biến ánh sáng Mặt Trời thành điện cho hệ thống; pin tích trữ hỗ trợ những lúc cần thiết. Thân vệ tinh chứa máy tính, điều khiển tư thế và thiết bị liên lạc để gửi dữ liệu xuống các trạm mặt đất.", "The solar panel converts sunlight into electrical power; a battery provides stored energy when needed. The bus contains computers, attitude control and communications for downlinking data to ground stations."), t("Đường vàng biểu diễn năng lượng điện; đường xanh biểu diễn nhiệt thoát đi. Hai đường này khác đường đi của photon mà kính thu từ thiên thể.", "Yellow traces represent electrical energy; cyan traces represent escaping heat. Both differ from the path of photons collected from celestial sources.")]
      ];
      const facts = [
        ["20 cm", t("khẩu độ hiệu dụng", "effective aperture")],
        ["3", t("lớp chắn lồng nhau", "nested photon shields")],
        [t("Thụ động", "Passive"), t("cơ chế làm lạnh", "cooling method")],
        ["~750 W", t("công suất tấm pin theo thiết kế", "solar panel design power")]
      ];
      return `<div class="ss-split"><figure class="ss-figure"><div class="ss-diagram">${svg("engineering", labels[selected] + ". " + t("Bộ phận được chọn sáng lên trong mặt cắt giản lược.", "The selected subsystem is highlighted in a simplified cutaway."), `<text x="26" y="31">${labels[selected]}</text>${shield}${optics}${cooling}${power}`, "0 0 600 420")}</div>${caption(t("Mặt cắt chức năng, không phải mô hình CAD; số bộ phận nhỏ được giản lược.", "Functional cutaway, not CAD; small components are simplified."))}</figure><div class="ss-copy"><h4>${labels[selected]}</h4><p aria-live="polite">${copy[selected][0]}</p><div class="ss-facts"><div><strong>${facts[selected][0]}</strong><span>${facts[selected][1]}</span></div></div>${detail("engineering-detail", t("Điểm dễ nhầm", "A useful distinction"), copy[selected][1])}${sources(selected === 0 ? "instrument" : "spacecraft", selected === 0 || selected === 2 ? "calibration" : "mission")}</div></div>`;
    }
    function wavelengthDiagram() {
      const x = 92 + state.position * 104;
      const color = COLORS[state.detector];
      return `<div class="ss-diagram">${svg("wavelength", t("Nguồn sáng nằm ở vị trí khác nhau trên một bộ lọc LVF, nên được đo ở dải bước sóng khác nhau.", "A source lands at different positions on an LVF and is measured in different wavelength bands."), `<defs><linearGradient id="${id("lvf-gradient")}"><stop stop-color="#56caef"/><stop offset=".5" stop-color="#ccff00"/><stop offset="1" stop-color="#ee8ccc"/></linearGradient></defs><text x="30" y="36">D${state.detector + 1} · ${BANDS[state.detector]} µm</text><text x="570" y="36" text-anchor="end" class="ss-svg-small">${t("một LVF", "one LVF")}</text><path d="M${x} 77V137" stroke="#f4f7ff" stroke-width="3" stroke-dasharray="6 5"/><path d="M${x - 12} 89L${x + 12} 65M${x - 12} 65L${x + 12} 89M${x - 17} 77H${x + 17}" stroke="#f4f7ff" stroke-width="3"/><rect x="40" y="145" width="520" height="102" rx="3" fill="url(#${id("lvf-gradient")})" opacity=".75"/>${Array.from({ length: 5 }, (_, i) => `<path d="M${92 + i * 104} 145V247" stroke="#102444" stroke-dasharray="4 6"/><text x="${92 + i * 104}" y="276" text-anchor="middle">λ${"₁₂₃₄₅"[i]}</text>`).join("")}<rect x="${x - 12}" y="139" width="24" height="114" fill="none" stroke="white" stroke-width="3"/><path d="M66 310H534" stroke="${color}" stroke-width="3"/><path d="M534 310L521 302M534 310L521 318" stroke="${color}" stroke-width="3"/><text x="300" y="342" text-anchor="middle">${t("Vị trí trên bộ lọc → bước sóng được đo", "Position on the filter → wavelength sampled")}</text><text x="300" y="376" text-anchor="middle" class="ss-svg-small">${t("Màu và 5 vị trí chỉ minh họa nguyên lý", "Colors and five positions illustrate the principle")}</text>`, "0 0 600 400")}</div>`;
    }
    function wavelengthReadout() {
      return t(`Vị trí ${state.position + 1}/5 · Bộ lọc trước D${state.detector + 1} cho một phần hẹp của dải ${BANDS[state.detector]} µm đi qua. Khi đổi hướng trỏ, cùng nguồn trời rơi lên vị trí khác và được đo ở bước sóng khác.`, `Position ${state.position + 1}/5 · The filter in front of D${state.detector + 1} passes a narrow part of its ${BANDS[state.detector]} µm range. Repointing places the same sky source at another position, sampling another wavelength.`);
    }
    function wavelengthPanel() {
      return `<div class="ss-split"><figure class="ss-figure"><div data-wavelength-diagram>${wavelengthDiagram()}</div><div class="ss-range"><label for="${id("position")}">${t("Đổi vị trí ảnh của cùng nguồn", "Move the image of the same source")}</label><output for="${id("position")}" data-position-output>${state.position + 1} / 5</output><input id="${id("position")}" data-science-range type="range" min="0" max="4" step="1" value="${state.position}" data-focus="wavelength-position" aria-describedby="${id("wavelength-description")}" aria-valuetext="${escape(t("Vị trí ", "Position ") + (state.position + 1) + " / 5")}"></div>${caption(t("Không mô phỏng một exposure thật, không tính bước sóng hiệu chuẩn từ thanh kéo.", "Not an actual exposure; the slider does not calculate a calibrated wavelength."))}</figure><div class="ss-copy"><h4>${t("Sáu detector, nhiều lần quan sát", "Six detectors, repeated observations")}</h4><p>${t("Bộ tách dichroic tạo hai nhánh: ba detector ở bước sóng ngắn và ba ở bước sóng dài. Mỗi detector có một bộ lọc biến thiên tuyến tính (LVF) cố định phía trước.", "A dichroic produces two branches: three shorter-wavelength detectors and three longer-wavelength detectors. Each has a fixed linear variable filter (LVF) in front of it.")}</p><div class="ss-detectors" role="group" aria-label="${escape(t("Chọn detector", "Select a detector"))}">${BANDS.map((band, index) => `<button type="button" data-science-action="detector" data-value="${index}" data-focus="detector-${index}" aria-pressed="${index === state.detector}">D${index + 1}<span>${band} µm</span></button>`).join("")}</div><p id="${id("wavelength-description")}" data-wavelength-description aria-live="polite">${wavelengthReadout()}</p><p class="ss-note">${t("102 là số kênh phổ danh nghĩa của khảo sát, không phải 102 camera. Một ảnh detector chứa các bước sóng khác nhau theo vị trí; phổ được ghép từ nhiều phép đo.", "102 is the survey’s nominal spectral-channel count, not 102 cameras. Wavelength varies across a detector image; spectra are assembled from multiple measurements.")}</p>${detail("wavelength-detail", t("Vì sao ảnh ở hai thời điểm có thể khác nhau?", "Why can two dates look different?"), t("Khác bước sóng, nền trời, PSF, mask hoặc thang kéo sáng đều có thể làm ảnh thay đổi. Muốn kiểm tra biến quang hay chuyển động, cần đối chiếu những yếu tố này và sai số; không kết luận từ một đoạn nhấp nháy.", "Wavelength, background, PSF, masks and display stretch can all change an image’s appearance. Testing variability or motion requires accounting for these and their uncertainties; a blink animation alone is not a detection."))}${sources("instrument", "mission", "supplement")}</div></div>`;
    }
    function resultRows() {
      const rows = [
        { date: "2025-12-18", display: "18 · 12 · 2025", kind: t("Mốc khảo sát", "Survey milestone"), title: t("Bản đồ toàn trời đầu tiên", "First all-sky map"), copy: t("NASA công bố bản đồ từ lượt khảo sát đầu. Thành tựu này mở đường cho phân tích; nó chưa phải lời giải cuối cùng cho ba mục tiêu khoa học.", "NASA announced the first survey’s all-sky map. This enables analysis; it is not a final answer to all three science objectives."), refs: ["map"] },
        { date: "2026-02-04", display: "04 · 02 · 2026", kind: t("Kết quả quan sát", "Observational result"), title: t("Sao chổi liên sao 3I/ATLAS", "Interstellar comet 3I/ATLAS"), copy: t("Quan sát tháng 12/2025 ghi nhận hoạt động tăng sau cận nhật cùng dấu hiệu bụi và khí trong coma. Đây là nghiên cứu một thiên thể, không phải bằng chứng về sự sống.", "December 2025 observations recorded increased post-perihelion activity and dust and gas signatures in the coma. This is a study of one object, not evidence of life."), refs: ["comet", "cometPaper"] },
        { date: "2026-04-15", display: "15 · 04 · 2026", kind: t("Bài báo khoa học", "Research paper"), title: t("Bản đồ băng và PAH", "Maps of ices and PAHs"), copy: t("Hora và cộng sự công bố bản đồ phổ ở Cygnus X và vùng Tinh vân Bắc Mỹ, cho thấy các đặc trưng băng liên sao và hydrocarbon thơm đa vòng. Màu gán cho phân tử là cách trực quan hóa.", "Hora and collaborators published spectral maps of Cygnus X and the North America Nebula region, revealing interstellar-ice and polycyclic aromatic hydrocarbon features. Colors assigned to molecules are a visualization."), refs: ["icePaper"] },
        { date: "2026-10-08", display: "08 · 10 · 2026", kind: t("NASA giới thiệu nghiên cứu", "NASA research feature"), title: t("Phổ của 37 sao lùn nâu", "Spectra of 37 brown dwarfs"), copy: t("Nghiên cứu của Rustamkulov và cộng sự so sánh phổ với mô hình khí quyển. Các mô hình mô tả được xu hướng lớn nhưng còn lệch ở một số đặc trưng, nhất là vùng chuyển tiếp L/T.", "Rustamkulov and collaborators compared observed spectra with atmospheric models. Models capture broad trends but mismatch some features, particularly around the L/T transition."), refs: ["dwarf", "dwarfPaper"] },
        { date: "2026-11", display: "11 · 2026", kind: t("Phát hành dữ liệu", "Data release"), title: "DR1", copy: t("IRSA phát hành ảnh phổ xử lý lại và cube toàn trời. Ảnh DR1 được thiết kế để dùng cùng QR3 trong một bộ xử lý đồng nhất. Phải kiểm tra hạn chế từng sản phẩm trước khi phân tích.", "IRSA released reprocessed spectral images and an all-sky cube. DR1 images are designed for use with QR3 as a uniformly processed set. Check each product’s limitations before analysis."), refs: ["dr1"] }
      ];
      return rows.map(row => `<article><div><time datetime="${row.date}">${row.display}</time><span class="ss-tag">${row.kind}</span></div><h4>${row.title}</h4><div><p>${row.copy}</p>${sources(...row.refs)}</div></article>`).join("");
    }
    function dataSection() {
      const steps = [
        [t("Ghi nhận", "Measure"), t("Detector ghi tín hiệu theo thời gian; xử lý trên vệ tinh giảm khối lượng dữ liệu truyền xuống.", "Detectors record signals over time; onboard processing reduces the volume sent to Earth.")],
        [t("Hiệu chuẩn", "Calibrate"), t("Pipeline hiệu chỉnh đáp ứng thiết bị, xác định tọa độ, độ sáng và các cờ chất lượng.", "The pipeline corrects instrument response and assigns coordinates, brightness and quality flags.")],
        [t("Lập sản phẩm", "Build products"), t("Ảnh phổ giữ thông tin từng lần quan sát. Cube ghép nhiều phép đo theo vị trí và kênh phổ.", "Spectral images retain individual observations. Cubes combine measurements by position and spectral channel.")],
        [t("Kiểm chứng", "Validate"), t("Nghiên cứu cần truy nguồn, sai số, mask và phương pháp tái lập trước khi diễn giải kết quả.", "Research needs provenance, uncertainties, masks and reproducible methods before interpreting results.")]
      ];
      return `<ol class="ss-pipeline">${steps.map((step, index) => `<li><b>0${index + 1}</b><h4>${step[0]}</h4><p>${step[1]}</p></li>`).join("")}</ol>${sources("pipeline", "mapmaking")}<div class="ss-data-details">
        <div class="ss-readout"><h4>${t("Ảnh đẹp và số đo", "Pictures and measurements")}</h4><p>${t("Ảnh PNG và màu giả giúp nhìn thấy cấu trúc; phân tích định lượng cần FITS, đơn vị, hiệu chuẩn và sai số. Cam, sáng hay tối phụ thuộc chú giải và thang hiển thị đang dùng.", "PNG images and false color reveal structure; quantitative work needs FITS, units, calibration and uncertainties. Orange, bright or dark depends on the current legend and display stretch.")}</p></div>
        <div class="ss-readout"><h4>${t("Một lần chụp ≠ một cube thời gian", "An exposure ≠ a time cube")}</h4><p>${t("Các lát của cube toàn trời là kênh phổ, không phải các thời điểm kế tiếp. So sánh thời gian cần chọn các observation riêng và kiểm tra bước sóng tương ứng.", "All-sky cube slices are spectral channels, not successive dates. Time comparison requires individual observations and matched wavelength information.")}</p></div>
        ${detail("fits-detail", t("Đọc một tệp ảnh phổ", "Read a spectral-image file"), t("IMAGE: độ sáng bề mặt (MJy/sr); FLAGS: cờ từng pixel; VARIANCE: phương sai; ZODI: mô hình ánh sáng hoàng đạo chưa trừ khỏi IMAGE; EPSF: đáp ứng điểm hiệu dụng ở DR1/QR3. Giữ các lớp này cùng nhau.", "IMAGE: surface brightness (MJy/sr); FLAGS: per-pixel flags; VARIANCE: variance; ZODI: zodiacal-light model not subtracted from IMAGE; EPSF: effective point response in DR1/QR3. Preserve these layers together."))}
        ${detail("wave-detail", t("Bước sóng có độ chính xác nào?", "Which wavelength precision?"), t("WCS-WAVE hỗ trợ trực quan hóa. Khi phân tích khoa học, dùng CWAVE và CBAND trong sản phẩm hiệu chuẩn Spectral WCS, theo tài liệu phiên bản dữ liệu.", "WCS-WAVE supports visualization. For scientific analysis, use CWAVE and CBAND in the Spectral WCS calibration product, following the release documentation."))}
        ${detail("cube-detail", t("Hạn chế đã biết của cube DR1", "Known DR1 cube limitations"), t("Kênh 51 và 52 để trống; một số vạch phát xạ và cấu trúc phổ mạnh gây sọc. Cube đã trừ ZODI, khác ảnh phổ. HiPS PNG có dải hiển thị giới hạn và chỉ dùng để xem.", "Channels 51 and 52 are blank; some emission lines and strong spectral features cause stripes. The cube subtracts ZODI, unlike spectral images. HiPS PNGs have limited display range and are for viewing only."))}
        ${detail("provenance-detail", t("Một kết quả có thể kiểm tra lại", "A result others can check"), t("Lưu URL/DOI, observation ID, release, phiên bản pipeline, thời điểm, detector, tọa độ WCS, bước sóng, mask, đơn vị, hash và mọi thao tác xử lý. Một nhận xét trong bài học chưa phải phát hiện thiên văn.", "Keep URL/DOI, observation ID, release, pipeline version, time, detector, WCS coordinates, wavelength, masks, units, hashes and processing steps. A learning-activity response is not an astronomical discovery."))}
      </div>${sources("products", "supplement", "dr1")}`;
    }
    function render() {
      const focused = container.contains(document.activeElement) ? document.activeElement.getAttribute("data-focus") : null;
      const openDetails = [...container.querySelectorAll("details[open]")].map(element => element.dataset.detail);
      container.classList.remove("about-mission");
      container.classList.add("spherex-science");
      container.setAttribute("aria-labelledby", id("title"));
      container.setAttribute("lang", language);
      container.innerHTML = `
        <header class="ss-intro"><div><span class="ss-eyebrow">${t("SPHEREx đo được gì?", "What SPHEREx measures")}</span><h2 id="${id("title")}">${t("Một bầu trời.<br>Nhiều câu hỏi.", "One sky.<br>Many questions.")}</h2></div><div><p>${t("Từ câu hỏi khoa học tới lựa chọn kỹ thuật: khám phá cách SPHEREx biến ánh sáng hồng ngoại thành dữ liệu có thể nghiên cứu.", "From scientific questions to engineering choices: explore how SPHEREx turns infrared light into research data.")}</p><nav class="ss-jump" aria-label="${escape(t("Mục lục SPHEREx", "SPHEREx contents"))}"><a href="#about-story-title">${t("Lịch sử", "History")}</a><a href="#${id("goals")}">${t("Mục tiêu", "Goals")}</a><a href="#${id("orbit")}">${t("Quỹ đạo", "Orbit")}</a><a href="#${id("engineering")}">${t("Thiết kế", "Design")}</a><a href="#${id("spectrum")}">${t("102 kênh", "102 channels")}</a><a href="#${id("results")}">${t("Kết quả", "Results")}</a><a href="#${id("data")}">${t("Dữ liệu", "Data")}</a></nav></div></header>
        <section class="ss-section" id="${id("goals")}">${heading("01", t("Ba câu hỏi lớn", "Three big questions"))}${controls("goal", [t("Vũ trụ sơ khai", "Early universe"), t("Lịch sử thiên hà", "Galaxy history"), t("Băng liên sao", "Interstellar ice")], state.goal)}<div id="${id("goal-panel")}">${goalPanel()}</div></section>
        <section class="ss-section" id="${id("orbit")}">${heading("02", t("Lấy năng lượng từ Mặt Trời.<br>Nhìn về bầu trời.", "Powered by the Sun.<br>Looking at the sky."))}${controls("orbit", [t("Quỹ đạo", "Orbit"), t("Mặt Trời & hướng nhìn", "Sun & pointing"), t("Vùng phủ", "Coverage")], state.orbit)}<div id="${id("orbit-panel")}">${orbitPanel()}</div></section>
        <section class="ss-section" id="${id("engineering")}">${heading("03", t("Một thiết kế để giữ ánh sáng yếu", "Built to capture faint light"), t("Chọn một hệ thống để xem nó làm gì.", "Select a subsystem to see its role."))}${controls("engineering", [t("Quang học", "Optics"), t("Chắn photon", "Photon shields"), t("Tản nhiệt", "Cooling"), t("Điện & dữ liệu", "Power & data")], state.engineering)}<div id="${id("engineering-panel")}">${engineeringPanel()}</div></section>
        <section class="ss-section" id="${id("spectrum")}">${heading("04", t("Một nguồn sáng, 102 kênh phổ", "One light source, 102 spectral channels"), t("Kéo thanh bên dưới để hiểu vì sao vệ tinh phải quan sát lặp lại.", "Move the slider to see why repeated observations matter."))}<div id="${id("wavelength-panel")}">${wavelengthPanel()}</div></section>
        <section class="ss-section" id="${id("results")}">${heading("05", t("Điều đã được công bố", "What has been published"), t("Các ví dụ chọn lọc, kiểm tra đến 14/11/2026. Mốc dữ liệu, kết quả nghiên cứu và mục tiêu tương lai được phân biệt rõ.", "Selected examples, checked through 14 November 2026. Data milestones, research results and future objectives are distinguished."))}<div class="ss-ledger">${resultRows()}</div>${sources("publications")}</section>
        <section class="ss-section" id="${id("data")}">${heading("06", t("Từ photon tới bằng chứng", "From photons to evidence"), t("Một bức ảnh là điểm bắt đầu. Nguồn gốc và chất lượng dữ liệu quyết định điều ta có thể kết luận.", "An image is a starting point. Data provenance and quality determine what we can conclude."))}${dataSection()}<footer class="ss-end"><p>${t("Các sơ đồ trong phần này được dựng để giảng giải, không phải ảnh quan sát, mô phỏng vật lý hay phép đo. Nguồn gốc khoa học nằm tại các liên kết NASA, JPL, Caltech/IPAC và bài báo tương ứng.", "These authored diagrams explain concepts; they are not observations, physical simulations or measurements. Scientific sources are linked to NASA, JPL, Caltech/IPAC and the relevant papers.")}</p><p>${t("Mốc rà soát nội dung: 14/11/2026. Xem tài liệu archive đang dùng trước mỗi phân tích mới.", "Content review date: 14 November 2026. Check the applicable archive documentation before each new analysis.")}</p></footer></section>`;
      openDetails.forEach(key => { const element = container.querySelector(`[data-detail="${key}"]`); if (element) element.open = true; });
      if (focused) container.querySelector(`[data-focus="${focused}"]`)?.focus({ preventScroll: true });
    }
    function updatePanel(action) {
      const panelRenderers = { goal: goalPanel, orbit: orbitPanel, engineering: engineeringPanel };
      const panel = container.querySelector(`#${id(action + "-panel")}`);
      if (panel && panelRenderers[action]) panel.innerHTML = panelRenderers[action]();
      container.querySelectorAll(`[data-science-action="${action}"]`).forEach(button => button.setAttribute("aria-pressed", String(Number(button.dataset.value) === state[action])));
    }
    function updateWavelength() {
      container.querySelector("[data-wavelength-diagram]").innerHTML = wavelengthDiagram();
      container.querySelector("[data-wavelength-description]").textContent = wavelengthReadout();
      container.querySelector("[data-position-output]").textContent = `${state.position + 1} / 5`;
      container.querySelector("[data-science-range]").setAttribute("aria-valuetext", t("Vị trí ", "Position ") + (state.position + 1) + " / 5");
      container.querySelectorAll('[data-science-action="detector"]').forEach(button => button.setAttribute("aria-pressed", String(Number(button.dataset.value) === state.detector)));
    }
    function onClick(event) {
      const button = event.target.closest("button[data-science-action]");
      if (!button || !container.contains(button)) return;
      const action = button.dataset.scienceAction;
      if (!["goal", "orbit", "engineering", "detector"].includes(action)) return;
      const value = Number(button.dataset.value);
      if (!Number.isInteger(value) || value < 0 || value >= ({ goal: 3, orbit: 3, engineering: 4, detector: 6 }[action])) return;
      state[action] = value;
      if (action === "detector") updateWavelength(); else updatePanel(action);
    }
    function onInput(event) {
      if (!event.target.matches("[data-science-range]")) return;
      state.position = Math.max(0, Math.min(4, Math.round(Number(event.target.value) || 0)));
      updateWavelength();
    }
    function onLanguage(event) {
      const requested = event.detail?.language || document.documentElement.lang;
      language = String(requested).toLowerCase().startsWith("vi") ? "vi" : "en";
      render();
    }
    container.addEventListener("click", onClick);
    container.addEventListener("input", onInput);
    document.addEventListener("spherex:language", onLanguage);
    render();
    const api = { destroy() { container.removeEventListener("click", onClick); container.removeEventListener("input", onInput); document.removeEventListener("spherex:language", onLanguage); instances.delete(container); } };
    instances.set(container, api);
    return api;
  }
  window.SpherexScience = Object.freeze({ mount });
  const autoMount = () => mount(document.getElementById("spherex-science"));
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", autoMount, { once: true });
  else autoMount();
})();
