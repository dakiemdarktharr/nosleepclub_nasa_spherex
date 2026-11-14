(() => {
  "use strict";
  const copy = {
    brand: ["SPHEREx đã thấy gì?", "What Did SPHEREx See?"],
    skipPublic: ["Đến nội dung", "Skip to content"],
    guideTitle: ["Cách sử dụng ↓", "How to use ↓"],
    guideHeading: ["Cách sử dụng", "How to use"],
    openSky: ["Mở bầu trời ↗", "Open the sky ↗"],
    guideOne: ["Chọn vùng trời", "Choose a sky field"],
    guideOneDetail: ["Chọn Trái Đất, rồi bấm dấu sao hoặc nhập RA/Dec.", "Select Earth, then choose a star marker or enter RA/Dec."],
    guideTwo: ["Mở ảnh toàn khung", "Open a full detector image"],
    guideTwoDetail: ["Xem vùng quan sát, ngày chụp và dải bước sóng.", "Inspect the observed field, date and wavelength band."],
    guideThree: ["So ảnh qua thời gian", "Compare across time"],
    guideThreeDetail: ["So sánh hai khung hoặc phát chuỗi quan sát đã lưu.", "Compare two frames or play a saved observation sequence."],
    datasets: ["Bộ dữ liệu", "Datasets"],
    navigation: ["Điều hướng", "Navigation"],
    language: ["Chuyển sang tiếng Anh", "Switch to Vietnamese"],
    homeLink: ["SPHEREx đã thấy gì? · Trang chủ", "What Did SPHEREx See? · Home"],
    skyNav: ["Bầu trời", "Night sky"],
    aboutNav: ["Về SPHEREx", "About SPHEREx"],
    kicker: ["Đài quan sát hồng ngoại trên quỹ đạo", "An infrared observatory in orbit"],
    tagline: ["Từ quỹ đạo SPHEREx, xuống Trái Đất và nhìn lên những vùng trời vệ tinh đã chụp.", "From SPHEREx’s orbit, look back up from Earth at the places it has observed."],
    explore: ["Khám phá bầu trời", "Explore the sky"],
    aboutObject: ["Chọn vệ tinh để tìm hiểu SPHEREx", "Select the spacecraft to learn about SPHEREx"],
    earthObject: ["Chọn Trái Đất để khám phá bầu trời", "Select Earth to explore the night sky"],
    earth: ["Trái Đất", "Earth"],
    orbitalIllustration: ["Minh họa quỹ đạo · NASA / JPL-Caltech", "Orbit illustration · NASA / JPL-Caltech"],
    pauseMotion: ["Dừng chuyển động", "Pause motion"],
    resumeMotion: ["Bật chuyển động", "Resume motion"],
    backOrbit: ["← Về quỹ đạo", "← Back to orbit"],
    aboutTitle: ["Về nhiệm vụ SPHEREx", "About SPHEREx"],
    aboutIntro: ["SPHEREx là đài quan sát hồng ngoại của NASA. Từ quỹ đạo thấp, vệ tinh lập bản đồ bầu trời theo bước sóng để nghiên cứu các thiên hà, lịch sử vũ trụ và băng trong các vùng hình thành sao.", "SPHEREx is NASA’s infrared observatory. From low Earth orbit, it maps the sky by wavelength to study galaxies, the history of the universe, and ice in star-forming regions."],
    spectralBands: ["kênh phổ danh nghĩa", "nominal spectral channels"],
    infrared: ["bước sóng hồng ngoại", "infrared wavelengths"],
    shields: ["tấm chắn photon hình nón", "conical photon shields"],
    aboutExplanation: ["Ba lớp chắn photon giữ thiết bị đủ lạnh để ghi nhận nguồn hồng ngoại mờ. Quan sát lặp lại cùng một vùng ở các thời điểm và bước sóng khác nhau tạo nên dữ liệu để khám phá.", "Three photon shields help keep the instrument cold enough to see faint infrared sources. Repeated observations build up images of each field at different times and wavelengths."],
    spacecraftRef: ["Cấu tạo vệ tinh · JPL ↗", "Spacecraft engineering · JPL ↗"],
    eyesRef: ["Mở trong NASA Eyes ↗", "Open in NASA Eyes ↗"],
    animationRef: ["Hoạt họa nhiều góc ↗", "Multi-angle animation ↗"],
    orbitImage: ["Minh họa vệ tinh SPHEREx bay trên rìa Trái Đất", "Illustration of SPHEREx above Earth’s limb"],
    aboutCaption: ["Minh họa SPHEREx trên quỹ đạo · NASA/JPL-Caltech PIA26531", "SPHEREx in orbit illustration · NASA/JPL-Caltech PIA26531"],
    skyTitle: ["Tìm vùng trời", "Find a patch of sky"],
    skyIntro: ["Kéo bầu trời hoặc chọn một mục tiêu để xem ảnh SPHEREx của vùng đó.", "Drag the sky or choose a target to see a SPHEREx image of that field."],
    markerLegend: ["Vùng có ảnh mẫu", "Fields with preview images"],
    zoomOut: ["Thu nhỏ", "Zoom out"],
    zoomIn: ["Phóng to", "Zoom in"],
    resetView: ["Về góc đầu", "Reset view"],
    skyCanvas: ["Vòm trời tương tác theo tọa độ xích đạo", "Interactive equatorial sky view"],
    skyGuide: ["Kéo hoặc dùng phím mũi tên để đổi hướng. Đường chân trời minh họa · tọa độ ICRS.", "Drag or use the arrow keys to look around. Illustrated horizon · ICRS coordinates."],
    skyCredits: ["Ảnh nền · NASA SVS ↗", "Star map · NASA SVS ↗"],
    findRegion: ["Tìm vùng quan sát", "Find an observed field"],
    searchLabel: ["Tên mục tiêu mẫu", "Example target name"],
    searchHint: ["Tìm tên mục tiêu mẫu", "Search example targets"],
    noTargets: ["Thử tên khác, hoặc mở tìm theo tọa độ.", "Try another name or search by coordinates."],
    enterCoordinates: ["Nhập tọa độ RA / Dec →", "Enter RA / Dec →"],
    searchCenter: ["Tìm ảnh tại tâm ngắm", "Find images at the crosshair"],
    observedField: ["Ảnh quan sát SPHEREx", "SPHEREx observation"],
    compareImages: ["So sánh ảnh", "Compare images"],
    archivedSequence: ["Mở chuỗi ảnh đã lưu", "Open saved sequence"],
    archivedTitle: ["Epsilon Indi B · chuỗi DR1 đã lưu", "Epsilon Indi B · saved DR1 sequence"],
    archivedDescription: ["Ba ảnh SPHEREx DR1 D6 đã lưu dùng cùng lưới WCS và thang hiển thị. Chuỗi này dùng để xem vùng trời, chưa xác nhận chuyển động hay biến quang.", "Three saved SPHEREx DR1 D6 images share a WCS grid and display scale. Use them to view the field. Motion and variability remain unconfirmed."],
    archivedPlay: ["Phát chuỗi", "Play sequence"],
    archivedPause: ["Tạm dừng", "Pause"],
    archivedPrev: ["Ảnh trước", "Previous image"],
    archivedNext: ["Ảnh sau", "Next image"],
    archivedFits: ["FITS khung đang xem ↗", "Current frame FITS ↗"],
    archivedMetadata: ["Nguồn và thông số JSON ↗", "Sources and settings JSON ↗"],
    archivedLoading: ["Đang mở ba ảnh đã lưu…", "Opening three saved images…"],
    archivedError: ["Chưa mở được chuỗi đã lưu. Hãy đóng hộp thoại và thử lại.", "The saved sequence could not open. Close this dialog and try again."],
    fullFrame: ["FITS gốc cả detector ↗", "Full detector FITS ↗"],
    fullFieldLimit: ["Ảnh toàn detector đã giảm độ phân giải và kéo sáng riêng. Vòng xanh đánh dấu tâm truy vấn. Nút So sánh ảnh tìm ảnh DR1 quanh tâm này.", "Downsampled, individually stretched full detector image. The blue circle marks the query center. Compare images searches DR1 around that point."],
    enlargeImage: ["Mở ảnh lớn", "Open larger image"],
    close: ["Đóng", "Close"],
    team: ["Dự án độc lập của NoSleepClub", "An independent NoSleepClub project"],
    irsaSource: ["Kho dữ liệu NASA/IPAC IRSA ↗", "NASA/IPAC IRSA archive ↗"],
    researchNav: ["Tài liệu kiểm chứng", "Validation reports"],
    loadingFields: ["Đang mở danh sách vùng mẫu…", "Opening example fields…"],
    fieldsUnavailable: ["Tạm thời chưa tải được vùng mẫu. Bạn có thể tìm theo tọa độ.", "Example fields are unavailable. You can still search by coordinates."],
    loadingPreview: ["Đang tải ảnh mẫu…", "Loading preview…"],
    previewUnavailable: ["Tạm thời chưa tải được ảnh mẫu. Bạn có thể tìm ảnh DR1 cho vùng này.", "This preview is unavailable. You can search DR1 for this field."],
    workspaceLoading: ["Đang mở công cụ so ảnh…", "Opening the comparison workspace…"],
    workspaceError: ["Chưa mở được công cụ. Hãy tải lại trang để thử lại.", "The workspace could not open. Reload the page to try again."],
    skyFallback: ["Dùng danh sách mục tiêu để chọn vùng.", "Use the target list to choose a field."]
  };

  const supported = (value) => value === "en" || value === "vi";
  const key = "spherex.language";
  const storedLanguage = () => {
    try { return localStorage.getItem(key); } catch { return null; }
  };
  const requested = new URL(location.href).searchParams.get("lang");
  const saved = storedLanguage();
  let language = supported(requested) ? requested : supported(saved) ? saved : "vi";
  document.documentElement.lang = language;

  function text(id) {
    return copy[id]?.[language === "en" ? 1 : 0] || id;
  }

  function apply(next) {
    if (supported(next)) language = next;
    document.documentElement.lang = language;
    for (const el of document.querySelectorAll("[data-copy]")) el.textContent = text(el.dataset.copy);
    for (const el of document.querySelectorAll("[data-label]")) el.setAttribute("aria-label", text(el.dataset.label));
    for (const el of document.querySelectorAll("[data-placeholder]")) el.placeholder = text(el.dataset.placeholder);
    for (const el of document.querySelectorAll("[data-language]")) {
      el.textContent = language === "en" ? "Tiếng Việt" : "English";
      el.lang = language === "en" ? "vi" : "en";
    }
    window.SpherexWorkspaceLanguage?.apply(language);
    document.dispatchEvent(new CustomEvent("spherex:language", {detail: {language}}));
  }

  window.SpherexSite = {text, apply, language: () => language};
  document.addEventListener("DOMContentLoaded", () => {
    apply(language);
    for (const button of document.querySelectorAll("[data-language]")) {
      button.addEventListener("click", () => {
        const next = language === "en" ? "vi" : "en";
        const url = new URL(location.href);
        url.searchParams.set("lang", next);
        history.replaceState(history.state, "", url);
        try { localStorage.setItem(key, next); } catch { /* The URL keeps the setting. */ }
        apply(next);
      });
    }
  });
})();
